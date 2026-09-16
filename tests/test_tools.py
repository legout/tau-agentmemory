# pyright: reportMissingImports=false
import asyncio
import json
from urllib.parse import parse_qs, urlsplit

import pytest
from fake_server import fake_server

from tau_agentmemory.client import AgentMemoryClient
from tau_agentmemory.tools import TOOL_SPECS, make_tool

EMPTY_SCHEMA = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

EXPECTED_TOOLS = {
    "memory_health": {
        "method": "GET",
        "path": "/agentmemory/livez",
        "description": "Check whether the agentmemory service is healthy.",
        "parameters": EMPTY_SCHEMA,
    },
    "memory_save": {
        "method": "POST",
        "path": "/agentmemory/remember",
        "description": (
            "Explicitly save an important insight, decision, or pattern to "
            "long-term memory."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The insight or decision to remember",
                },
                "type": {
                    "type": "string",
                    "description": (
                        "Memory type: pattern, preference, architecture, bug, "
                        "workflow, or fact"
                    ),
                },
                "concepts": {
                    "type": "string",
                    "description": "Comma-separated key concepts",
                },
                "files": {
                    "type": "string",
                    "description": "Comma-separated relevant file paths",
                },
                "project": {
                    "type": "string",
                    "description": (
                        "Stable canonical project identifier this memory belongs to "
                        "(e.g. a slug, UUID, or registry key). Must match the value "
                        "used when the session was started. Do not use filesystem "
                        "paths or ad-hoc display names — those change across machines "
                        "and will silently break project scoping."
                    ),
                },
                "agentId": {"type": "string"},
            },
            "required": ["content"],
            "additionalProperties": False,
        },
    },
    "memory_smart_search": {
        "method": "POST",
        "path": "/agentmemory/smart-search",
        "description": "Hybrid semantic+keyword search with progressive disclosure.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "expandIds": {
                    "type": "string",
                    "description": "Comma-separated observation IDs to expand",
                },
                "limit": {
                    "type": "number",
                    "description": "Max results (default 10)",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    "memory_recall": {
        "method": "POST",
        "path": "/agentmemory/search",
        "description": (
            "Search past session observations for relevant context. Use when you "
            "need to recall what happened in previous sessions, find past decisions, "
            "or look up how a file was modified before."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (keywords, file names, concepts)",
                },
                "limit": {
                    "type": "number",
                    "description": "Max results to return (default 10)",
                },
                "format": {
                    "type": "string",
                    "description": (
                        "Result format: full, compact, or narrative (default full)"
                    ),
                },
                "token_budget": {
                    "type": "number",
                    "description": "Optional token budget to trim returned results",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    "memory_sessions": {
        "method": "GET",
        "path": "/agentmemory/sessions",
        "description": "List recent sessions with their status and observation counts.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "number"}
            },
            "additionalProperties": False,
        },
    },
    "memory_commits": {
        "method": "GET",
        "path": "/agentmemory/commits",
        "description": (
            "List recent commits linked to agent sessions, optionally filtered by "
            "branch or repo."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "branch": {
                    "type": "string",
                    "description": "Filter by branch name",
                },
                "repo": {"type": "string", "description": "Filter by remote URL"},
                "limit": {
                    "type": "number",
                    "description": "Max results (default 100, max 500)",
                },
            },
            "additionalProperties": False,
        },
    },
    "memory_commit_lookup": {
        "method": "GET",
        "path": "/agentmemory/session/by-commit",
        "description": (
            "Look up the agent session(s) that produced a specific git commit, "
            "given its SHA. Returns the commit metadata and linked sessions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sha": {"type": "string", "description": "Full git commit SHA"}
            },
            "required": ["sha"],
            "additionalProperties": False,
        },
    },
    "memory_governance_delete": {
        "method": "DELETE",
        "path": "/agentmemory/governance/memories",
        "description": "Delete specific memories with audit trail.",
        "parameters": {
            "type": "object",
            "properties": {
                "memoryIds": {
                    "type": "string",
                    "description": "Comma-separated memory IDs to delete",
                },
                "reason": {"type": "string", "description": "Reason for deletion"},
            },
            "required": ["memoryIds"],
            "additionalProperties": False,
        },
    },
    "memory_lesson_save": {
        "method": "POST",
        "path": "/agentmemory/lessons",
        "description": (
            "Save a lesson learned from this session. Lessons have confidence scores "
            "that strengthen when reinforced and decay when not used. Duplicate "
            "content auto-strengthens the existing lesson."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": (
                        "The lesson learned (what worked, what to avoid, when to use "
                        "X approach)"
                    ),
                },
                "context": {
                    "type": "string",
                    "description": "When/where this lesson applies",
                },
                "confidence": {
                    "type": "number",
                    "description": "Initial confidence 0.0-1.0 (default 0.5)",
                },
                "project": {
                    "type": "string",
                    "description": "Project this lesson is about",
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated tags",
                },
            },
            "required": ["content"],
            "additionalProperties": False,
        },
    },
    "memory_lesson_recall": {
        "method": "POST",
        "path": "/agentmemory/lessons/search",
        "description": (
            "Search lessons by query. Returns lessons sorted by confidence and "
            "recency. Use to check what the agent has learned before making decisions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "project": {
                    "type": "string",
                    "description": "Filter by project",
                },
                "minConfidence": {
                    "type": "number",
                    "description": "Minimum confidence threshold (default 0.1)",
                },
                "limit": {
                    "type": "number",
                    "description": "Max results (default 10)",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}

ROUND_TRIPS = (
    ("memory_health", {}, {}, None),
    (
        "memory_save",
        {
            "content": "keep this",
            "type": "fact",
            "concepts": " alpha, beta, ,gamma ",
            "files": " src/a.py, , tests/a.py ",
            "project": "tau-agentmemory",
            "agentId": "agent-1",
        },
        {},
        {
            "content": "keep this",
            "type": "fact",
            "concepts": ["alpha", "beta", "gamma"],
            "files": ["src/a.py", "tests/a.py"],
            "project": "tau-agentmemory",
            "agentId": "agent-1",
        },
    ),
    (
        "memory_smart_search",
        {"query": "past choice", "expandIds": " obs-1, ,obs-2 ", "limit": 7},
        {},
        {"query": "past choice", "expandIds": ["obs-1", "obs-2"], "limit": 7},
    ),
    (
        "memory_recall",
        {"query": "bridge", "limit": 4, "format": "compact", "token_budget": 500},
        {},
        {"query": "bridge", "limit": 4, "format": "compact", "token_budget": 500},
    ),
    ("memory_sessions", {"limit": 8}, {"limit": ["8"]}, None),
    (
        "memory_commits",
        {"branch": "feature/two words", "repo": "owner/repo", "limit": 12},
        {"branch": ["feature/two words"], "repo": ["owner/repo"], "limit": ["12"]},
        None,
    ),
    ("memory_commit_lookup", {"sha": "abc123"}, {"sha": ["abc123"]}, None),
    (
        "memory_governance_delete",
        {"memoryIds": " memory-1, ,memory-2 ", "reason": "obsolete"},
        {},
        {"memoryIds": ["memory-1", "memory-2"], "reason": "obsolete"},
    ),
    (
        "memory_lesson_save",
        {
            "content": "prefer stdlib",
            "context": "small bridges",
            "confidence": 0.9,
            "project": "tau-agentmemory",
            "tags": "python,rest",
        },
        {},
        {
            "content": "prefer stdlib",
            "context": "small bridges",
            "confidence": 0.9,
            "project": "tau-agentmemory",
            "tags": "python,rest",
        },
    ),
    (
        "memory_lesson_recall",
        {"query": "stdlib", "project": "tau-agentmemory", "minConfidence": 0.4, "limit": 3},
        {},
        {"query": "stdlib", "project": "tau-agentmemory", "minConfidence": 0.4, "limit": 3},
    ),
)

REQUIRED_ONLY = {
    "memory_health": {},
    "memory_save": {"content": "keep this"},
    "memory_smart_search": {"query": "past choice"},
    "memory_recall": {"query": "bridge"},
    "memory_sessions": {},
    "memory_commits": {},
    "memory_commit_lookup": {"sha": "abc123"},
    "memory_governance_delete": {"memoryIds": " memory-1, ,memory-2 "},
    "memory_lesson_save": {"content": "prefer stdlib"},
    "memory_lesson_recall": {"query": "stdlib"},
}


def get_spec(name):
    return next(spec for spec in TOOL_SPECS if spec["name"] == name)


def execute(tool, arguments):
    return asyncio.run(tool.execute_fn("call-id", arguments, None, None))


def test_all_ten_tools_have_exact_names_schemas_and_descriptions():
    assert [spec["name"] for spec in TOOL_SPECS] == list(EXPECTED_TOOLS)

    client = AgentMemoryClient("http://example.test")
    for name, expected in EXPECTED_TOOLS.items():
        spec = get_spec(name)
        tool = make_tool(spec, client)
        assert spec["method"] == expected["method"]
        assert spec["path"] == expected["path"]
        assert tool.name == name
        assert tool.label == name
        assert tool.description == expected["description"]
        assert tool.parameters == expected["parameters"]


@pytest.mark.parametrize(("name", "arguments", "expected_query", "expected_body"), ROUND_TRIPS)
def test_tool_round_trip(name, arguments, expected_query, expected_body):
    response = '{ "tool": "ok" }\n'
    with fake_server(body=response.encode()) as server:
        spec = get_spec(name)
        result = execute(make_tool(spec, AgentMemoryClient(server.url, "secret")), arguments)

    request = server.requests[0]
    split_path = urlsplit(request["path"])
    assert request["method"] == EXPECTED_TOOLS[name]["method"]
    assert split_path.path == EXPECTED_TOOLS[name]["path"]
    assert parse_qs(split_path.query) == expected_query
    assert request["headers"]["Authorization"] == "Bearer secret"
    assert (json.loads(request["body"]) if request["body"] else None) == expected_body
    assert getattr(result.content[0], "text", None) == response


@pytest.mark.parametrize(("name", "arguments"), REQUIRED_ONLY.items())
def test_absent_optional_values_are_omitted(name, arguments):
    with fake_server() as server:
        spec = get_spec(name)
        execute(make_tool(spec, AgentMemoryClient(server.url)), arguments)

    request = server.requests[0]
    split_path = urlsplit(request["path"])
    if EXPECTED_TOOLS[name]["method"] == "GET":
        assert parse_qs(split_path.query) == {
            key: [str(value)] for key, value in arguments.items()
        }
        assert request["body"] == b""
    else:
        expected = dict(arguments)
        if name == "memory_governance_delete":
            expected["memoryIds"] = ["memory-1", "memory-2"]
        assert json.loads(request["body"]) == expected
