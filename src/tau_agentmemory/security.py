"""Plaintext bearer guard (Spec 0002, "Security and privacy")."""

from __future__ import annotations

import sys
import threading
import warnings
from urllib.parse import urlsplit, urlunsplit

_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


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
