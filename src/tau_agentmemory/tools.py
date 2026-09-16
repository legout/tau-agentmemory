from __future__ import annotations

from collections.abc import Mapping

from tau_agent.messages import TextContent
from tau_agent.tools import (
    AgentTool,
    AgentToolResult,
    ToolCancellationToken,
    ToolUpdateCallback,
)
from tau_agent.types import JSONValue

from .client import AgentMemoryClient

TOOL_SPECS = (
    {
        "name": "memory_health",
        "method": "GET",
        "path": "/agentmemory/livez",
        "description": "Check whether the agentmemory service is healthy.",
    },
)


def make_tool(spec: Mapping[str, str], client: AgentMemoryClient) -> AgentTool:
    async def execute(
        tool_call_id: str,
        arguments: Mapping[str, JSONValue],
        signal: ToolCancellationToken | None = None,
        on_update: ToolUpdateCallback | None = None,
    ) -> AgentToolResult:
        del tool_call_id, signal, on_update
        text = await client.request(spec["method"], spec["path"], arguments)
        return AgentToolResult(content=[TextContent(text=text)])

    return AgentTool(
        name=spec["name"],
        label=spec["name"],
        description=spec["description"],
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        execute_fn=execute,
    )
