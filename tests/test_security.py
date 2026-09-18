# pyright: reportMissingImports=false
import warnings

import pytest

from tau_agentmemory.security import (
    PlaintextBearerGuard,
    PlaintextBearerWarning,
    is_insecure_transport,
    redact_structure,
    redact_text,
)


@pytest.mark.parametrize(
    ("url", "insecure"),
    [
        ("https://agent.example:3111", False),
        ("http://localhost:3111", False),
        ("http://LOCALHOST:3111", False),
        ("http://127.0.0.1:9", False),
        ("http://[::1]:3111", False),
        ("http://agent.example:3111", True),
        ("http://127.0.0.2:3111", True),
        ("http://localhost.attacker.example:3111", True),
        ("ftp://agent.example", True),
    ],
)
def test_url_classification_allows_only_https_and_loopback(url, insecure):
    assert is_insecure_transport(url) is insecure


def test_guard_warns_once_per_generation_and_names_url_and_risk():
    guard = PlaintextBearerGuard()
    url = "http://agent.example:3111"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        guard.warn_once(url)
        guard.warn_once(url)
        guard.warn_once(url)

    assert len(caught) == 1
    assert caught[0].category is PlaintextBearerWarning
    message = str(caught[0].message)
    assert url in message
    assert "plaintext" in message
    assert "credential" in message


def test_next_extension_generation_warns_again():
    url = "http://agent.example:3111"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        PlaintextBearerGuard().warn_once(url)
        PlaintextBearerGuard().warn_once(url)

    assert len(caught) == 2


def _warn_from_one_call_site(guard, url):
    # Mirrors client._request: every generation warns from the same line, so
    # under the default filter the location-based warning registry would
    # swallow the second generation unless the guard controls its own.
    guard.warn_once(url)


def test_second_generation_warns_again_under_default_warning_filter():
    url = "http://agent.example:3111"

    with warnings.catch_warnings(record=True) as caught:
        warnings.resetwarnings()  # Python's default "default" action
        _warn_from_one_call_site(PlaintextBearerGuard(), url)
        _warn_from_one_call_site(PlaintextBearerGuard(), url)

    assert len(caught) == 2
    assert all(c.category is PlaintextBearerWarning for c in caught)


def test_repeated_calls_within_one_generation_warn_once_under_default_filter():
    guard = PlaintextBearerGuard()
    url = "http://agent.example:3111"

    with warnings.catch_warnings(record=True) as caught:
        warnings.resetwarnings()
        _warn_from_one_call_site(guard, url)
        _warn_from_one_call_site(guard, url)

    assert len(caught) == 1


def test_guard_warning_redacts_userinfo_secret():
    guard = PlaintextBearerGuard()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        guard.warn_once("http://hushhush@agent.example:3111", secret="hushhush")

    assert len(caught) == 1
    message = str(caught[0].message)
    assert "hushhush" not in message
    assert "agent.example" in message
    assert "plaintext" in message


# --- capture redaction (Spec 0002, "Capture redaction") ----------------------


def test_redact_structure_replaces_sensitive_keys_case_insensitively():
    value = {
        "config": {
            "api_key": "k-123",
            "APIKey": "k-456",
            "Authorization": "Bearer k-789",
            "clientSecret": "cs-1",
            "private-key": "pk-1",
            "setCookie": "sess-1",
            "db": {"PASSWORD": "p-1", "Passwd": "p-2"},
            "items": [{"access_token": "at-1", "refresh_token": "rt-1"}],
        },
        "name": "safe value",
        "count": 3,
    }

    redacted = redact_structure(value)

    assert redacted == {
        "config": {
            "api_key": "[REDACTED]",
            "APIKey": "[REDACTED]",
            "Authorization": "[REDACTED]",
            "clientSecret": "[REDACTED]",
            "private-key": "[REDACTED]",
            "setCookie": "[REDACTED]",
            "db": {"PASSWORD": "[REDACTED]", "Passwd": "[REDACTED]"},
            "items": [{"access_token": "[REDACTED]", "refresh_token": "[REDACTED]"}],
        },
        "name": "safe value",
        "count": 3,
    }
    assert value["config"]["api_key"] == "k-123"  # input untouched


def test_redact_structure_replaces_configured_secret_wherever_it_appears():
    value = {
        "note": "connect with hushhush tomorrow",
        "nested": ["plain", {"deep": "token=hushhush inside"}],
    }

    redacted = redact_structure(value, secret="hushhush")

    assert "hushhush" not in repr(redacted)
    assert redacted["note"] == "connect with [REDACTED] tomorrow"
    assert redacted["nested"][1]["deep"] == "token=[REDACTED] inside"


def test_redact_text_redacts_bearer_and_sensitive_key_value_forms():
    texts = [
        "Authorization: Bearer sk-live-123",
        "authorization: bearer sk-live-123",
        "token: abc123",
        'api_key="xyz999"',
        "password=hunter2",
        'Set-Cookie: sess=abc123',
        '{"client_secret": "cs-77"}',
        "PRIVATE-KEY: open sesame",
    ]

    for text in texts:
        redacted = redact_text(text)
        assert "sk-live-123" not in redacted, text
        assert "abc123" not in redacted, text
        assert "xyz999" not in redacted, text
        assert "hunter2" not in redacted, text
        assert "cs-77" not in redacted, text
        assert "open sesame" not in redacted, text
        assert "sesame" not in redacted, text  # no multi-word residue
        assert "[REDACTED]" in redacted, text


def test_redact_text_redacts_multi_word_sensitive_values_whole():
    """A bare sensitive value runs past one token to the line end/pair boundary."""
    redacted = redact_text("password: correct horse battery staple")

    assert redacted == "password: [REDACTED]"


def test_redact_text_bare_value_consumes_quoted_segments():
    """Quotes inside a bare value are value content, not a stop boundary."""
    redacted = redact_text('password: correct "horse battery" staple')

    assert redacted == "password: [REDACTED]"


def test_redact_text_value_stops_before_next_pair_on_the_same_line():
    redacted = redact_text("password=abc123 token=xyz789")

    assert redacted == "password=[REDACTED] token=[REDACTED]"


def test_redact_text_multi_word_value_never_crosses_a_line_break():
    redacted = redact_text("token=abc def ghi\nplain next line")

    assert redacted == "token=[REDACTED]\nplain next line"


def test_redact_text_leaves_non_sensitive_prose_intact():
    text = "username=bob count=3 set the cookie jar down tokenised words"

    assert redact_text(text) == text


def test_redact_text_replaces_configured_secret():
    text = "use hushhush to connect"

    assert redact_text(text, secret="hushhush") == "use [REDACTED] to connect"
