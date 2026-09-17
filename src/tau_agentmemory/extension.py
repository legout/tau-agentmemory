# pyright: reportMissingImports=false
from functools import partial

from tau_coding.extensions import ExtensionAPI

from .client import AgentMemoryClient
from .config import load_config
from .health import handle_session_start
from .tools import TOOL_SPECS, make_tool


def setup(tau: ExtensionAPI) -> None:
    config = load_config()
    client = AgentMemoryClient(
        config.url, config.secret, require_https=config.require_https
    )
    for spec in TOOL_SPECS:
        tau.register_tool(make_tool(spec, client))
    tau.add_prompt_guideline(
        "Use memory_smart_search / memory_recall to recall prior decisions, "
        "preferences, bugs, and workflows."
    )
    tau.add_prompt_guideline(
        "Use memory_save when you discover durable facts worth remembering beyond "
        "this session."
    )
    tau.on(
        "session_start",
        partial(handle_session_start, client=client, config=config),
    )
