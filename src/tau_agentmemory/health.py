# pyright: reportMissingImports=false
from __future__ import annotations

from tau_coding.extensions import ExtensionContext

from .client import AgentMemoryClient, AgentMemoryError
from .config import Config


async def handle_session_start(
    event: object,
    context: ExtensionContext,
    *,
    client: AgentMemoryClient,
    config: Config,
) -> None:
    del event
    try:
        await client.request("GET", "/agentmemory/livez", {})
    except AgentMemoryError as error:
        status = str(error)
    else:
        status = f"agentmemory: ok · {config.url}"

    ui = getattr(context, "ui", None)
    sidebar = getattr(ui, "sidebar", None)
    if sidebar is None or not getattr(sidebar, "supported", False):
        return
    set_section = getattr(sidebar, "set_section", None)
    if callable(set_section):
        set_section("status", title="agentmemory", content=(status,))
