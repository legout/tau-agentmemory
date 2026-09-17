# pyright: reportMissingImports=false
import asyncio
import json
import socket
import warnings
from urllib.parse import parse_qs, urlsplit

import pytest
from fake_server import fake_server

from tau_agentmemory.client import AgentMemoryClient, AgentMemoryError
from tau_agentmemory.security import PlaintextBearerWarning


def run_request(client, method="GET", path="/agentmemory/livez", params=None):
    return asyncio.run(client.request(method, path, params or {}))


class CannedResponse:
    def __init__(self):
        self.headers = {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return b"{}"


def record_urlopen(monkeypatch):
    opened = []

    def open_request(request, *, timeout):
        opened.append(request)
        return CannedResponse()

    monkeypatch.setattr("tau_agentmemory.client.urlopen", open_request)
    return opened


def test_health_success_preserves_body_and_omits_auth():
    body = '{ "status": "ok" }\n'
    with fake_server(body=body.encode()) as server:
        result = run_request(AgentMemoryClient(server.url))

    assert result == body
    assert server.requests[0]["path"] == "/agentmemory/livez"
    assert "Authorization" not in server.requests[0]["headers"]


def test_bearer_auth_and_get_query_are_sent():
    with fake_server() as server:
        run_request(
            AgentMemoryClient(server.url, "top-secret"),
            path="/agentmemory/livez",
            params={"limit": 3, "query": "two words"},
        )

    request = server.requests[0]
    assert request["headers"]["Authorization"] == "Bearer top-secret"
    assert parse_qs(urlsplit(request["path"]).query) == {
        "limit": ["3"],
        "query": ["two words"],
    }


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_write_methods_use_json_body(method):
    with fake_server() as server:
        run_request(
            AgentMemoryClient(server.url),
            method=method,
            path="/agentmemory/remember",
            params={"content": "remember me"},
        )

    request = server.requests[0]
    assert request["headers"]["Content-Type"] == "application/json"
    assert json.loads(request["body"]) == {"content": "remember me"}


def test_request_uses_ten_second_timeout(monkeypatch):
    observed = {}

    class Response:
        def __init__(self):
            self.headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b"{}"

    def open_request(request, *, timeout):
        observed["timeout"] = timeout
        return Response()

    monkeypatch.setattr("tau_agentmemory.client.urlopen", open_request)

    assert run_request(AgentMemoryClient("http://example.test")) == "{}"
    assert observed["timeout"] == 10


def test_malformed_json_reports_type_and_only_first_200_bytes():
    body = b"x" * 200 + b"DO-NOT-INCLUDE"
    with (
        fake_server(body=body, content_type="text/plain") as server,
        pytest.raises(AgentMemoryError) as error,
    ):
        run_request(AgentMemoryClient(server.url))

    message = str(error.value)
    assert "malformed JSON" in message
    assert "text/plain" in message
    assert "x" * 200 in message
    assert "DO-NOT-INCLUDE" not in message


def test_http_400_includes_status_and_response_body():
    with (
        fake_server(status=400, body=b'{"error":"content is required"}') as server,
        pytest.raises(AgentMemoryError) as error,
    ):
        run_request(AgentMemoryClient(server.url))

    assert str(error.value) == (
        'agentmemory returned HTTP 400: {"error":"content is required"}'
    )


def test_http_error_body_is_truncated_to_2_kib():
    body = b"a" * 2048 + b"DO-NOT-INCLUDE"
    with (
        fake_server(status=500, body=body) as server,
        pytest.raises(AgentMemoryError) as error,
    ):
        run_request(AgentMemoryClient(server.url))

    message = str(error.value)
    assert "500" in message
    assert "a" * 2048 in message
    assert "DO-NOT-INCLUDE" not in message


def test_rejected_credential_never_echoes_secret():
    secret = "credential-must-stay-private"
    with (
        fake_server(status=401, body=b'{"error":"unauthorized"}') as server,
        pytest.raises(AgentMemoryError) as error,
    ):
        run_request(AgentMemoryClient(server.url, secret))

    message = str(error.value)
    assert "credential was rejected" in message
    assert "401" in message
    assert secret not in message


def test_unreachable_closed_port_has_actionable_one_line_error():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    url = f"http://127.0.0.1:{sock.getsockname()[1]}"
    sock.close()

    with pytest.raises(AgentMemoryError) as error:
        run_request(AgentMemoryClient(url))

    assert str(error.value) == (
        f"agentmemory is unreachable at {url} — start the server, "
        "or set AGENTMEMORY_URL"
    )
    assert "\n" not in str(error.value)


def test_loopback_http_with_secret_sends_without_warning():
    body = '{ "status": "ok" }\n'
    with (
        fake_server(body=body.encode()) as server,
        warnings.catch_warnings(record=True) as caught,
    ):
        warnings.simplefilter("always")
        assert run_request(AgentMemoryClient(server.url, "top-secret")) == body

    # "always"+record captures every interpreter warning (e.g. unrelated
    # ResourceWarnings), so assert on the guard's category, not on emptiness.
    assert not any(w.category is PlaintextBearerWarning for w in caught)
    assert server.requests[0]["headers"]["Authorization"] == "Bearer top-secret"


def test_https_with_secret_sends_without_warning(monkeypatch):
    opened = record_urlopen(monkeypatch)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert run_request(
            AgentMemoryClient("https://agent.example:3111", "top-secret")
        ) == "{}"

    assert not any(w.category is PlaintextBearerWarning for w in caught)
    assert len(opened) == 1
    assert opened[0].get_header("Authorization") == "Bearer top-secret"


def test_remote_http_with_secret_warns_once_then_sends_each_request(monkeypatch):
    opened = record_urlopen(monkeypatch)

    client = AgentMemoryClient("http://agent.example:3111", "secret-value")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert run_request(client) == "{}"
        assert run_request(client) == "{}"

    assert len(caught) == 1
    assert caught[0].category is PlaintextBearerWarning
    message = str(caught[0].message)
    assert "http://agent.example:3111" in message
    assert "plaintext" in message
    assert "secret-value" not in message
    assert len(opened) == 2
    assert opened[0].get_header("Authorization") == "Bearer secret-value"


def test_userinfo_secret_never_appears_in_warning_or_enforcement_error(monkeypatch):
    opened = record_urlopen(monkeypatch)
    url = "http://hushhush@agent.example:3111"

    client = AgentMemoryClient(url, "hushhush")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert run_request(client) == "{}"

    assert len(caught) == 1
    warning = str(caught[0].message)
    assert "hushhush" not in warning
    assert "agent.example" in warning
    assert opened[0].get_header("Authorization") == "Bearer hushhush"

    blocked = AgentMemoryClient(url, "hushhush", require_https=True)
    with pytest.raises(AgentMemoryError) as error:
        run_request(blocked)

    message = str(error.value)
    assert "hushhush" not in message
    assert "agent.example" in message
    assert "\n" not in message
    assert len(opened) == 1


def test_require_https_blocks_remote_http_before_any_network_io(monkeypatch):
    opened = record_urlopen(monkeypatch)

    client = AgentMemoryClient(
        "http://agent.example:3111", "secret-value", require_https=True
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(AgentMemoryError) as error:
            run_request(client)
        with pytest.raises(AgentMemoryError):
            run_request(client)

    message = str(error.value)
    assert "http://agent.example:3111" in message
    assert "secret-value" not in message
    assert "\n" not in message
    assert opened == []
    assert caught == []


def test_require_https_still_allows_loopback_http():
    body = '{ "status": "ok" }\n'
    with fake_server(body=body.encode()) as server:
        assert run_request(
            AgentMemoryClient(server.url, "top-secret", require_https=True)
        ) == body
