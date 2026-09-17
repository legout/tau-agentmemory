from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .security import PlaintextBearerGuard, is_insecure_transport, redacted_url


class AgentMemoryError(RuntimeError):
    """A safe-to-display agentmemory request failure."""


class AgentMemoryClient:
    def __init__(
        self, url: str, secret: str | None = None, *, require_https: bool = False
    ) -> None:
        self.url = url.rstrip("/")
        self.secret = secret
        self.require_https = require_https
        self._plaintext_guard = PlaintextBearerGuard()

    async def request(
        self, method: str, path: str, params: Mapping[str, Any]
    ) -> str:
        return await asyncio.to_thread(self._request, method, path, params)

    def _request(self, method: str, path: str, params: Mapping[str, Any]) -> str:
        if self.secret and is_insecure_transport(self.url):
            if self.require_https:
                raise AgentMemoryError(
                    "agentmemory request blocked: bearer credential would be sent "
                    f"over plaintext HTTP to {redacted_url(self.url, self.secret)}; "
                    "use HTTPS or a loopback URL, or unset "
                    "AGENTMEMORY_REQUIRE_HTTPS to allow it"
                )
            self._plaintext_guard.warn_once(self.url, secret=self.secret)

        url = f"{self.url}/{path.lstrip('/')}"
        headers = {"Accept": "application/json"}
        if self.secret:
            headers["Authorization"] = f"Bearer {self.secret}"

        body = None
        if method == "GET":
            query = urlencode(params, doseq=True)
            if query:
                url = f"{url}?{query}"
        elif method in {"POST", "DELETE"}:
            body = json.dumps(params, separators=(",", ":")).encode()
            headers["Content-Type"] = "application/json"

        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=10) as response:
                response_body = response.read()
                content_type = response.headers.get("Content-Type", "unknown")
        except HTTPError as error:
            response_body = error.read(2048)
            if error.code == 401 and self.secret:
                raise AgentMemoryError(
                    "agentmemory returned HTTP 401: configured credential was rejected"
                ) from None
            detail = self._safe_preview(response_body)
            raise AgentMemoryError(
                f"agentmemory returned HTTP {error.code}: {detail}"
            ) from None
        except (URLError, TimeoutError, OSError):
            raise AgentMemoryError(
                f"agentmemory is unreachable at {self.url} — start the server, "
                "or set AGENTMEMORY_URL"
            ) from None

        try:
            text = response_body.decode("utf-8")
            json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError):
            preview = self._safe_preview(response_body[:200])
            raise AgentMemoryError(
                f"agentmemory returned malformed JSON ({content_type}): {preview}"
            ) from None
        return text

    def _safe_preview(self, body: bytes) -> str:
        preview = body.decode("utf-8", errors="replace")
        if self.secret:
            preview = preview.replace(self.secret, "[REDACTED]")
        return preview
