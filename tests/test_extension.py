# pyright: reportMissingImports=false
import asyncio
from pathlib import Path

from fake_server import fake_server
from tau_coding.extensions.runtime import ExtensionRuntime
from tau_coding.resources import TauResourcePaths

REPOSITORY = Path(__file__).parents[1]


def test_real_runtime_discovers_and_executes_memory_health(monkeypatch, tmp_path):
    with fake_server(body=b'{"status":"ok"}') as server:
        monkeypatch.setenv("AGENTMEMORY_URL", server.url)
        monkeypatch.delenv("AGENTMEMORY_SECRET", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runtime = ExtensionRuntime()
        runtime.load(
            TauResourcePaths(root=tmp_path / ".tau"),
            extra_paths=[REPOSITORY],
            include_resource_dirs=False,
        )

        assert runtime.diagnostics == ()
        assert [tool.name for tool in runtime.extension_tools] == ["memory_health"]
        result = asyncio.run(
            runtime.extension_tools[0].execute_fn("call-id", {}, None, None)
        )

    assert getattr(result.content[0], "text", None) == '{"status":"ok"}'
