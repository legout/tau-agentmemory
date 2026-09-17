# pyright: reportMissingImports=false

from tau_coding.extensions import ExtensionAPI

from .client import AgentMemoryClient
from .config import load_config
from .lifecycle import register_lifecycle
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
    register_lifecycle(tau, client=client, config=config)
