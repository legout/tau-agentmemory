# pyright: reportMissingImports=false
import asyncio
import json
import socket
from urllib.parse import parse_qs, urlsplit

import pytest
from fake_server import fake_server

from tau_agentmemory.client import AgentMemoryClient, AgentMemoryError


def run_request(client, method="GET", path="/agentmemory/livez", params=None):
    return asyncio.run(client.request(method, path, params or {}))


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
