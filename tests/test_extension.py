# pyright: reportMissingImports=false
import asyncio
import socket
from pathlib import Path

from fake_server import fake_server
from tau_coding.extensions.runtime import ExtensionRuntime
from tau_coding.resources import TauResourcePaths

REPOSITORY = Path(__file__).parents[1]
TOOL_NAMES = [
    "memory_health",
    "memory_save",
    "memory_smart_search",
    "memory_recall",
    "memory_sessions",
    "memory_commits",
    "memory_commit_lookup",
    "memory_governance_delete",
    "memory_lesson_save",
    "memory_lesson_recall",
]
GUIDELINES = (
    (
        "Use memory_smart_search / memory_recall to recall prior decisions, "
        "preferences, bugs, and workflows."
    ),
    (
        "Use memory_save when you discover durable facts worth remembering beyond "
        "this session."
    ),
)


class SidebarUi:
    def __init__(self, *, supported: bool = True) -> None:
        self.supports_sidebar = supported
        self.sections = []

    def set_sidebar_section(self, extension, key, *, title, content):
        self.sections.append((extension, key, title, content))


def load_runtime(monkeypatch, tmp_path, url, *, ui=None):
    monkeypatch.setenv("AGENTMEMORY_URL", url)
    monkeypatch.delenv("AGENTMEMORY_SECRET", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    runtime = ExtensionRuntime(ui=ui)
    runtime.load(
        TauResourcePaths(root=tmp_path / ".tau"),
        extra_paths=[REPOSITORY],
        include_resource_dirs=False,
    )
    return runtime


def closed_local_url():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    url = f"http://127.0.0.1:{sock.getsockname()[1]}"
    sock.close()
    return url


def test_real_runtime_registers_acceptance_surface_and_reports_healthy_sidebar(
    monkeypatch, tmp_path
):
    ui = SidebarUi()
    with fake_server() as server:
        runtime = load_runtime(monkeypatch, tmp_path, server.url, ui=ui)

        assert runtime.diagnostics == ()
        assert [tool.name for tool in runtime.extension_tools] == TOOL_NAMES
        assert runtime.prompt_guidelines == GUIDELINES
        asyncio.run(runtime.emit_session_start("startup"))

    assert runtime.diagnostics == ()
    assert [request["path"] for request in server.requests] == [
        "/agentmemory/livez"
    ]
    assert ui.sections == [
        (
            "tau_agentmemory",
            "status",
            "agentmemory",
            (f"agentmemory: ok · {server.url}",),
        )
    ]


def test_session_start_reports_unreachable_without_failing(monkeypatch, tmp_path):
    url = closed_local_url()
    ui = SidebarUi()
    runtime = load_runtime(monkeypatch, tmp_path, url, ui=ui)

    asyncio.run(runtime.emit_session_start("startup"))

    assert runtime.diagnostics == ()
    assert ui.sections == [
        (
            "tau_agentmemory",
            "status",
            "agentmemory",
            (
                (
                    f"agentmemory is unreachable at {url} — start the server, "
                    "or set AGENTMEMORY_URL"
                ),
            ),
        )
    ]


def test_session_start_probes_with_unsupported_sidebar(monkeypatch, tmp_path):
    ui = SidebarUi(supported=False)
    with fake_server() as server:
        runtime = load_runtime(monkeypatch, tmp_path, server.url, ui=ui)
        asyncio.run(runtime.emit_session_start("startup"))

    assert runtime.diagnostics == ()
    assert [request["path"] for request in server.requests] == [
        "/agentmemory/livez"
    ]
    assert ui.sections == []


def test_session_start_probes_without_ui(monkeypatch, tmp_path):
    with fake_server() as server:
        runtime = load_runtime(monkeypatch, tmp_path, server.url)
        asyncio.run(runtime.emit_session_start("startup"))

    assert runtime.diagnostics == ()
    assert [request["path"] for request in server.requests] == [
        "/agentmemory/livez"
    ]
