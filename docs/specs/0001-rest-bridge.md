# Spec 0001: agentmemory REST bridge for Tau

Status: **Approved, revision 1** — the owner approved A1 (REST-native core
set), A2 (MCP coexistence), and the complete specification on 2026-09-16.

## Goal

Register native `memory_*` Tau tools backed by a running agentmemory REST
server, so the installed agentmemory skill suite works in Tau exactly as
written — the skills name tools like `memory_smart_search` and pass documented
parameters; no skill text changes.

## Non-goals

- Full 130-endpoint surface. Long-tail operations remain reachable via the
  `agentmemory-rest-api` skill (curl over bash).
- Session-observation capture hooks (the agentmemory-hooks equivalent).
  Possible follow-up extension work, not this one.
- Token-spending features (auto-compress, context injection) — server-side
  flags, not this extension's concern.
- Spawning, supervising, or configuring the agentmemory server.

## Architecture

One Tau extension, stdlib-only (`urllib.request`, `json`), no dependencies
beyond Python's standard library (survives `uv tool upgrade tau-ai`).

```
src/tau_agentmemory/
  extension.py    setup(tau): reads config, registers tools + guideline
  config.py       AGENTMEMORY_URL / AGENTMEMORY_SECRET resolution
  client.py       thin async-friendly REST client (timeout, bearer, errors)
  tools.py        declarative tool table -> AgentTool factory
  health.py       session_start health probe + sidebar status (feature-detected)
tests/
  fake_server.py  minimal http.server fixture answering the mapped endpoints
  test_*.py       per-tool mapping, auth, error paths, config parsing
```

Packaging: `[tool.tau] extensions = ["src/tau_agentmemory/extension.py"]`,
loaded from `~/.tau/extensions/tau-agentmemory` (symlink or `tau install`).

## Interfaces

### Configuration resolution (first hit wins)

1. Environment: `AGENTMEMORY_URL`, `AGENTMEMORY_SECRET`
2. `~/.agentmemory/.env` (one `KEY=value` per line, no `export`)
3. Defaults: `http://localhost:3111`, no auth

Secrets are never included in tool results, logs, or diagnostics.

### Tool table (v1 core set — 10 tools)

Names and parameters are exactly what the agentmemory MCP reference documents
(the contract the skills were written against); the REST mapping is the
implementation detail.

| Tool | REST call | Parameters (`*` required) |
| --- | --- | --- |
| `memory_health` | `GET /agentmemory/livez` | none |
| `memory_save` | `POST /agentmemory/remember` | `content*`, `type`, `concepts`, `files`, `project`, `agentId` |
| `memory_smart_search` | `POST /agentmemory/smart-search` | `query*`, `expandIds`, `limit` |
| `memory_recall` | `POST /agentmemory/search` | `query*`, `limit`, `format`, `token_budget` |
| `memory_sessions` | `GET /agentmemory/sessions` | `limit` |
| `memory_commits` | `GET /agentmemory/commits` | `branch`, `repo`, `limit` |
| `memory_commit_lookup` | `GET /agentmemory/session/by-commit` | `sha*` |
| `memory_governance_delete` | `DELETE /agentmemory/governance/memories` | `memoryIds*`, `reason` |
| `memory_lesson_save` | `POST /agentmemory/lessons` | `content*`, `context`, `confidence`, `project`, `tags` |
| `memory_lesson_recall` | `POST /agentmemory/lessons/search` | `query*`, `project`, `minConfidence`, `limit` |

Adding a tool later = one declarative table row (name, method, path, params,
description). Parameters pass through as a JSON body (POST/DELETE) or query
string (GET); unknown fields are dropped server-side, so pass-through is safe.
`memory_sessions.limit` is intentionally accepted even though the MCP reference
lists no parameters because the installed recap, handoff, and session-history
skills pass it and the REST endpoint supports it.

### Registration

All tools register in `setup()` (schemas are statically known — no dynamic
registration). Two prompt guidelines mirror the Pi extension's contract:

- Use `memory_smart_search` / `memory_recall` to recall prior decisions,
  preferences, bugs, and workflows.
- Use `memory_save` when you discover durable facts worth remembering beyond
  this session.

`session_start` runs one `livez` probe: success updates a feature-detected
sidebar section (`agentmemory: ok · <url>`); failure shows the actionable
warning below. The probe never blocks or fails the session.

## Data flow

Model calls `memory_smart_search {query, limit}` → executor serializes the
JSON body → `urllib` POST with 10s timeout and optional bearer header →
JSON responses are syntax-validated, then the original response body is returned
verbatim as tool text content. GET tools serialize documented parameters into
the query string.

## Failures

| Failure | Behavior |
| --- | --- |
| Server unreachable / timeout | Single-line error: `agentmemory is unreachable at <url> — start the server, or set AGENTMEMORY_URL`. The executor raises so Tau marks the tool result as an error. |
| HTTP 4xx/5xx | Status code + response body (truncated to ~2 KB) as error text. |
| `AGENTMEMORY_SECRET` set but 401 | Error text states the credential was rejected, never echoes the secret. |
| Malformed response JSON | Error text with content-type and first 200 bytes. |
| Missing config file | Defaults apply; no diagnostic needed. |

Every failure is per-call; no retries, no background loops.

## Migration / coexistence

- tau-mcp may load agentmemory's MCP server concurrently; its tools appear as
  prefixed proxy targets and cannot collide with these bare `memory_*` names.
- Pi keeps its own extension; nothing on the Pi side changes.

## Testing

Hermetic: `pytest` with a `http.server`-based fake speaking the mapped
endpoints (201/200 happy paths, 400 validation, unreachable case via a closed
port). Extension loading is tested through the real `ExtensionRuntime.load`
with `include_resource_dirs=False` (per Tau's extension testing guide), using
`AGENTMEMORY_URL` pointed at the fixture. Config parsing tested against env,
`.env`, and precedence rules.

## Acceptance examples

1. With the real server running, the `recall` skill executes verbatim in a
   Tau session and returns grouped observations from `memory_smart_search`.
2. With the server stopped, `memory_health` returns the one-line unreachable
   error; the session otherwise works normally.
3. `~/.agentmemory/.env` containing `AGENTMEMORY_SECRET=x` produces
   `Authorization: Bearer x` on every request (asserted by the fake server).
4. A skill referencing any core tool name passes its documented parameters
   through unchanged (round-trip asserted per tool by tests).

## Decision log

- 2026-09-15, owner: A1 (REST-native core bridge) **and** A2 (MCP coexistence
  via tau-mcp) chosen over full-surface A3. Tool scope "as recommended"
  (~10–11, skills-frequency driven). Folder `/home/volker/coding/tau-agentmemory`.
- 2026-09-16, owner: revision 1 approved with the 10-tool table,
  `memory_sessions.limit` compatibility behavior, JSON validation semantics, and
  the capture-checkpoint outcome recorded in the implementation plan.
