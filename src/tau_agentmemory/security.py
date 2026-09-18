"""Plaintext bearer guard and capture redaction (Spec 0002, "Security and privacy").

The redaction helpers bound the disclosure risk of default-on capture: common
structured credential keys, the configured bearer secret, bearer authorization
text, and equivalent sensitive ``key=value`` / ``key: value`` forms are
replaced with ``[REDACTED]`` before any truncation. Redaction is best-effort;
it is not a secrecy guarantee for arbitrary prose.
"""

from __future__ import annotations

import re
import sys
import threading
import warnings
from typing import Any
from urllib.parse import urlsplit, urlunsplit

_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# Normalized (case-insensitive, ``_``/``-`` stripped) keys whose values are
# replaced with ``[REDACTED]`` in captured structures (Spec 0002).
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "token",
        "secret",
        "apikey",
        "authorization",
        "cookie",
        "setcookie",
        "clientsecret",
        "accesstoken",
        "refreshtoken",
        "privatekey",
    }
)

# Textual forms: bearer authorization values, then sensitive key=value and
# key: value pairs (including JSON-ish "key": "value" shapes). A quoted
# value runs to its closing quote; a bare value runs whole to the next
# whitespace-delimited ``key=`` / ``key:`` pair boundary or the end of the
# line (never across it), so multi-word credentials are not left behind.
# Quote characters and quoted segments count as bare-value content, not as
# boundaries.
# The value pattern also swallows an already-redacted ``bearer [REDACTED]``
# payload so an authorization pair collapses into one marker.
_BEARER_PATTERN = re.compile(r"(?i)\b(bearer)(\s+)([^\s\"',;&]+)")
_KEY_ALTERNATION = (
    r"password|passwd|token|secret|api[-_]?key|authorization|set[-_]?cookie|"
    r"cookie|client[-_]?secret|access[-_]?token|refresh[-_]?token|private[-_]?key"
)
_KEY_VALUE_PATTERN = re.compile(
    rf"(?i)\b(?P<key>{_KEY_ALTERNATION})(?P<mid>[\"']?\s*[=:]\s*)"
    r"(?:(?P<q>[\"'])(?P<qvalue>(?:bearer\s+)?(?:(?!(?P=q))[^\n])*)(?P=q)"
    rf"|(?P<value>(?:bearer\s+)?[\"']*[^\s\"']+(?:[^\S\n]+(?!['\"]?[-\w.]+['\"]?\s*[=:])[^\s]+)*))"
)
_REDACTED = "[REDACTED]"


class PlaintextBearerWarning(UserWarning):
    """The bearer credential is crossing non-loopback plaintext HTTP."""


def is_insecure_transport(url: str) -> bool:
    """Report whether a credential sent to ``url`` leaves the host unencrypted.

    Only HTTPS and loopback HTTP (``localhost``, ``127.0.0.1``, ``::1``;
    case-insensitive) are allowed; every other transport is treated as
    attacker-observable plaintext.
    """
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme == "https":
        return False
    hostname = parts.hostname
    return not (scheme == "http" and hostname is not None and hostname in _LOOPBACK_HOSTS)


def redacted_url(url: str, secret: str | None = None) -> str:
    """Return a display form of ``url`` that never carries the bearer secret.

    Userinfo credentials are stripped from the authority and any occurrence
    of the configured secret is replaced with ``[REDACTED]`` (Spec 0001;
    Spec 0002: guard warning/error name the URL and risk, never the secret),
    while still naming the host and port.
    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    if ":" in host:  # IPv6 literal needs its brackets back
        host = f"[{host}]"
    try:
        port = parts.port
    except ValueError:
        port = None
    netloc = host if port is None else f"{host}:{port}"
    display = urlunsplit(parts._replace(netloc=netloc))
    if secret:
        display = display.replace(secret, "[REDACTED]")
    return display


def _normalize_key(key: str) -> str:
    return key.replace("_", "").replace("-", "").lower()


def redact_structure(value: Any, *, secret: str | None = None) -> Any:
    """Redact a captured structure recursively (Spec 0002, "Capture redaction").

    Values under sensitive normalized keys become ``[REDACTED]``; the exact
    configured secret is replaced wherever it appears in string values.
    """
    if isinstance(value, dict):
        return {
            key: (
                _REDACTED
                if isinstance(key, str) and _normalize_key(key) in _SENSITIVE_KEYS
                else redact_structure(item, secret=secret)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        redacted = [redact_structure(item, secret=secret) for item in value]
        return type(value)(redacted) if isinstance(value, tuple) else redacted
    if isinstance(value, str):
        return value.replace(secret, _REDACTED) if secret else value
    return value


def redact_text(text: str, *, secret: str | None = None) -> str:
    """Redact captured free text (Spec 0002, "Capture redaction").

    Replaces the configured secret, bearer authorization values, and sensitive
    ``key=value`` / ``key: value`` forms; a sensitive value is consumed whole
    (quoted values to their closing quote, bare values to the next pair
    boundary or end of line). Best-effort only: prose is not proven
    secret-free.
    """
    if secret:
        text = text.replace(secret, _REDACTED)
    text = _BEARER_PATTERN.sub(r"\1\2[REDACTED]", text)
    return _KEY_VALUE_PATTERN.sub(_redact_key_value_match, text)


def _redact_key_value_match(match: re.Match[str]) -> str:
    """Replace one sensitive key/value pair, keeping the key and any quotes."""
    quote = match.group("q") or ""
    value = match.group("value") or match.group("qvalue") or ""
    if not value:
        return match.group(0)
    return f"{match.group('key')}{match.group('mid')}{quote}{_REDACTED}{quote}"


class PlaintextBearerGuard:
    """Emit one warning per extension generation for insecure bearer transport."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._warned = False
        # The guard owns the warning registry: the default filter's
        # location-based registry would otherwise show this warning only once
        # per process, hiding the risk from later extension generations.
        self._registry: dict[str, int] = {}

    def warn_once(self, url: str, *, secret: str | None = None) -> None:
        # Locking keeps the warning at exactly one even when requests run on
        # separate asyncio.to_thread workers within the same generation.
        with self._lock:
            if self._warned:
                return
            self._warned = True
            warnings.warn_explicit(
                f"agentmemory: bearer credential is sent over plaintext HTTP to "
                f"{redacted_url(url, secret)}; the credential is observable on the "
                "network. Use HTTPS or a loopback URL, or set "
                "AGENTMEMORY_REQUIRE_HTTPS=1 to refuse the request.",
                PlaintextBearerWarning,
                filename=__file__,
                lineno=sys._getframe().f_lineno,
                module="tau_agentmemory.security",
                registry=self._registry,
            )
