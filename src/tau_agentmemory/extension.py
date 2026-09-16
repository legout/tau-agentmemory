from tau_coding.extensions import ExtensionAPI

from .client import AgentMemoryClient
from .config import load_config
from .tools import TOOL_SPECS, make_tool


def setup(tau: ExtensionAPI) -> None:
    config = load_config()
    client = AgentMemoryClient(config.url, config.secret)
    for spec in TOOL_SPECS:
        tau.register_tool(make_tool(spec, client))
