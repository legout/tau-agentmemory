# pyright: reportMissingImports=false
import warnings

import pytest

from tau_agentmemory.security import (
    PlaintextBearerGuard,
    PlaintextBearerWarning,
    is_insecure_transport,
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
