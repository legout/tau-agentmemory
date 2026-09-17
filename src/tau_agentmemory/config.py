from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_URL = "http://localhost:3111"
_KEYS = ("AGENTMEMORY_URL", "AGENTMEMORY_SECRET", "AGENTMEMORY_REQUIRE_HTTPS")


@dataclass(frozen=True, slots=True)
class Config:
    url: str
    secret: str | None
    require_https: bool = False


def _read_dotenv(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return {}

    values: dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in _KEYS and key not in values:
            values[key] = value
    return values


def load_config(
    *, environ: Mapping[str, str] | None = None, home: Path | None = None
) -> Config:
    environment = os.environ if environ is None else environ
    dotenv = _read_dotenv((home or Path.home()) / ".agentmemory" / ".env")
    url = environment.get("AGENTMEMORY_URL", dotenv.get("AGENTMEMORY_URL", _DEFAULT_URL))
    secret = environment.get("AGENTMEMORY_SECRET", dotenv.get("AGENTMEMORY_SECRET"))
    require_https_raw = environment.get(
        "AGENTMEMORY_REQUIRE_HTTPS", dotenv.get("AGENTMEMORY_REQUIRE_HTTPS", "0")
    )
    return Config(
        url=url.rstrip("/"),
        secret=secret or None,
        require_https=require_https_raw == "1",
    )
