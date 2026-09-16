from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import TypedDict, cast


class RecordedRequest(TypedDict):
    method: str
    path: str
    headers: dict[str, str]
    body: bytes


class FakeServer(ThreadingHTTPServer):
    response_status = 200
    response_body = b'{"status":"ok"}'
    response_content_type = "application/json"

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), FakeHandler)
        self.requests: list[RecordedRequest] = []

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_port}"


class FakeHandler(BaseHTTPRequestHandler):
    def _handle(self) -> None:
        server = cast(FakeServer, self.server)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        server.requests.append(
            {
                "method": self.command,
                "path": self.path,
                "headers": dict(self.headers),
                "body": body,
            }
        )
        self.send_response(server.response_status)
        self.send_header("Content-Type", server.response_content_type)
        self.end_headers()
        self.wfile.write(server.response_body)

    do_GET = _handle
    do_POST = _handle
    do_DELETE = _handle

    def log_message(self, format: str, *args: object) -> None:
        pass


@contextmanager
def fake_server(
    *,
    status: int = 200,
    body: bytes = b'{"status":"ok"}',
    content_type: str = "application/json",
) -> Iterator[FakeServer]:
    server = FakeServer()
    server.response_status = status
    server.response_body = body
    server.response_content_type = content_type
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
