# Plan 0001: agentmemory REST bridge for Tau

Status: **Approved** — the owner approved Tasks 1–3 for supervised implementation on 2026-09-16. This approval does not authorize integration or publication.

## Goal and source

Implement the approved REST-native Tau extension in
[`docs/specs/0001-rest-bridge.md`](../specs/0001-rest-bridge.md), revision 1,
approved by the owner on 2026-09-16. The architectural rationale is
[`docs/adr/0001-rest-native-bridge.md`](../adr/0001-rest-native-bridge.md), accepted
on 2026-09-16.

This plan is the canonical execution map. No GitHub tickets are needed for this
single-owner, sequential implementation.

## Capture checkpoint

- **Vocabulary:** no new glossary terms are required. “REST-native bridge,”
  “native `memory_*` tool,” and “MCP coexistence” are sufficiently defined by
  the specification and ADR.
- **Decision:** ADR 0001 owns the accepted REST-native architecture and the
  coexistence boundary with tau-mcp.
- **Behavior:** Spec 0001 revision 1 owns the 10-tool surface, configuration,
  failures, testing, and four acceptance examples.
- **Uncertainty:** no material design decisions remain. Planning evidence
  confirmed Tau 0.4.4’s extension APIs and the installed skills’ use of
  `memory_sessions.limit`.

## Constraints and non-goals

- Use Python’s standard library for production code. Tau is the host API, not an
  extension-owned runtime dependency.
- Target the installed Tau 0.4.4 extension API and Python 3.12 or newer.
- Do not spawn, supervise, configure, retry, or poll the agentmemory server.
- Do not add MCP support, capture hooks, automatic context injection, or the
  long-tail REST surface.
- Return successful response bodies unchanged after JSON syntax validation.
  Raise sanitized exceptions for failures so Tau marks tool results as errors.
- Never expose `AGENTMEMORY_SECRET` in text, diagnostics, exception chaining, or
  sidebar content.

## Requirement map

| Requirement | Source | Tasks |
| --- | --- | --- |
| Loadable Tau package and native `memory_*` registration | Goal, Architecture, Registration | 1, 2 |
| Environment → `.env` → default configuration precedence | Interfaces: Configuration | 1 |
| Ten exact tools and REST mappings, including `memory_sessions.limit` | Interfaces: Tool table | 1, 2 |
| 10-second requests, bearer auth, GET query/body serialization | Data flow | 1, 2 |
| Sanitized unreachable, HTTP, 401, malformed-JSON behavior | Failures | 1, 2 |
| Non-blocking session-start probe, sidebar status, prompt guidelines | Registration | 3 |
| MCP/Pi coexistence without shared names or code | Migration / coexistence | 3 |
| Acceptance examples 1–4 | Acceptance examples | 2, 3 |

## Validation units

- **V1 — loadable health slice (normal risk, `new-test`):** proves package
  discovery, configuration precedence, request timeout/auth construction, JSON
  validation, and one complete `memory_health` call through Tau’s tool executor.
  Distinct failure mode: the extension loads but cannot reach or safely decode
  the configured service.
- **V2 — declarative tool surface (high risk, `new-test`):** proves every tool’s
  schema, HTTP method, path, query/body mapping, and error behavior. The
  destructive delete route and credential boundary make this high risk.
  Distinct failure mode: a valid skill invocation reaches the wrong endpoint,
  changes parameter shape, or leaks a secret. Require immediate independent
  review before accepting this unit.
- **V3 — session integration (normal risk, `new-test`):** proves prompt
  guidelines and session-start health behavior without blocking a session when
  the service is unavailable. Distinct failure mode: optional UI behavior
  prevents extension loading or normal session use.
- **Global candidate review:** after Tasks 1–3, review only unreviewed code and
  integration effects; do not reopen findings settled by V2’s immediate review.

## Task 1 — Deliver a loadable `memory_health` tracer bullet

**Owned surfaces**

- Create `pyproject.toml`.
- Create `src/tau_agentmemory/__init__.py`.
- Create `src/tau_agentmemory/config.py`.
- Create `src/tau_agentmemory/client.py`.
- Create `src/tau_agentmemory/tools.py`.
- Create `src/tau_agentmemory/extension.py`.
- Create `tests/fake_server.py`.
- Create `tests/test_config.py`.
- Create `tests/test_client.py`.
- Create `tests/test_extension.py`.

**Interfaces consumed**

- Tau 0.4.4 `ExtensionAPI.register_tool(AgentTool(...))`.
- Tau `AgentToolResult` and `TextContent` for successful text output.
- `urllib.request`, `urllib.parse`, `json`, `asyncio`, and `pathlib`.

**Interfaces produced**

- `config.load_config(...) -> Config` resolving `AGENTMEMORY_URL` and
  `AGENTMEMORY_SECRET` in the approved order.
- `client.AgentMemoryClient.request(method, path, params) -> str`, implemented
  with `asyncio.to_thread` around `urllib` so the async tool executor does not
  block Tau’s event loop.
- A small declarative `TOOL_SPECS` table and tool factory that initially exposes
  `memory_health`.
- `extension.setup(tau)` as the manifest entry point.

**Steps**

- [ ] Add a minimal uv-compatible package with
  `[tool.tau].extensions = ["src/tau_agentmemory/extension.py"]`, Python
  `>=3.12`, no production dependencies, and a development group containing
  Tau 0.4.4 and pytest.
- [ ] Write a strict, dependency-free `.env` reader for `KEY=value` lines. Ignore
  blank/comment/malformed lines, do not implement shell syntax, and preserve
  first-hit precedence.
- [ ] Implement URL normalization, bearer-header injection, 10-second timeout,
  GET query serialization, JSON-body serialization, JSON syntax validation,
  and sanitized exception messages. Validate at this HTTP boundary only.
- [ ] Add the fake server with request capture and configurable status/body, then
  register `memory_health` through the real extension entry point.
- [ ] **Red:** add tests for config precedence, auth omission/inclusion, health
  success, malformed JSON, HTTP error truncation, rejected credentials, and an
  unreachable closed port.
- [ ] **Green:** implement only enough code for those tests and the
  `memory_health` tracer bullet.
- [ ] Run `uv run pytest tests/test_config.py tests/test_client.py tests/test_extension.py`.

**Completion evidence**

- V1 passes.
- `ExtensionRuntime.load(..., include_resource_dirs=False)` discovers the
  manifest entry and exposes `memory_health`.
- No exception or assertion output contains the configured secret.

## Task 2 — Complete the declarative 10-tool bridge

**Prerequisite:** Task 1 accepted.

**Owned surfaces**

- Modify `src/tau_agentmemory/tools.py` and, only where shared transport behavior
  requires it, `src/tau_agentmemory/client.py`.
- Modify `tests/fake_server.py`.
- Create `tests/test_tools.py`; extend `tests/test_client.py` only for transport
  behavior not already covered.

**Interfaces consumed**

- `Config` and `AgentMemoryClient` from Task 1.
- The exact names, schemas, methods, paths, and parameters in Spec 0001’s tool
  table.

**Interfaces produced**

- Ten registered tools: `memory_health`, `memory_save`,
  `memory_smart_search`, `memory_recall`, `memory_sessions`, `memory_commits`,
  `memory_commit_lookup`, `memory_governance_delete`, `memory_lesson_save`, and
  `memory_lesson_recall`.
- One executor factory that sends POST/DELETE parameters as JSON and GET
  parameters as URL-encoded query values, omitting absent optional values.

**Steps**

- [ ] **Red:** parameterize one round-trip test over all ten tool specs, asserting
  registration name/schema and the captured method, path, query, body, and
  bearer header. Include `memory_sessions.limit` and list/string values used by
  the installed skills.
- [ ] Add focused error assertions for 400, 401, 500, malformed JSON, and the
  approximately 2 KiB body truncation without duplicating Task 1’s transport
  setup tests.
- [ ] Add all remaining rows to `TOOL_SPECS` and keep tool construction data
  driven; do not add a class hierarchy or per-tool executor wrappers.
- [ ] **Green:** run `uv run pytest tests/test_tools.py tests/test_client.py`.
- [ ] Run V2’s immediate independent review with the approved specification,
  actual skill call shapes, credential boundary, and destructive-delete path in
  the reviewer context. One authorized fix pass and one delta recheck maximum.

**Completion evidence**

- V2 passes and its review is accepted or any residual blocker is returned to
  the owner.
- Existing recall, remember, recap, handoff, forget, session-history,
  commit-context, and commit-history skill call shapes are represented by the
  table-driven tests.

## Task 3 — Add session integration and finish acceptance

**Prerequisite:** Tasks 1 and 2 accepted.

**Owned surfaces**

- Create `src/tau_agentmemory/health.py`.
- Modify `src/tau_agentmemory/extension.py`.
- Extend `tests/test_extension.py`.
- Update `README.md` installation and verification instructions only after the
  tested commands are known.

**Interfaces consumed**

- Tau `ExtensionAPI.add_prompt_guideline(...)` and
  `ExtensionAPI.on("session_start", ...)`.
- Feature-detected `context.ui.sidebar` with `supported` and `set_section(...)`.
- `AgentMemoryClient` and `Config` from Task 1.

**Interfaces produced**

- Two approved memory-use prompt guidelines.
- A session-start livez probe that reports `agentmemory: ok · <url>` when a
  supported sidebar exists and emits the approved actionable failure warning
  without failing session startup.

**Steps**

- [ ] **Red:** load the extension through `ExtensionRuntime`, assert all ten tools
  and both prompt guidelines, emit `session_start`, and cover supported,
  unsupported, absent-UI, healthy, and unreachable cases.
- [ ] Implement one health handler that reuses the shared client and guards all
  sidebar access by feature detection. Do not add loops, retries, state caches,
  or a background task.
- [ ] **Green:** run `uv run pytest tests/test_extension.py`.
- [ ] Update `README.md` with `tau install`, configuration, server prerequisite,
  and one `memory_health` smoke check that matches the tested package layout.
- [ ] Run `uv run pytest` and the global candidate review.

**Completion evidence**

- V3 and the full suite pass.
- With the real local server running, a manual Tau smoke session can invoke
  `memory_health` and `memory_smart_search`; if the server is unavailable, report
  that manual check as skipped rather than replacing hermetic evidence.
- The repository remains free of MCP client code, server lifecycle code, and
  non-stdlib production dependencies.

## Global validation

```bash
uv run pytest
```

Required CI, if added later, remains authoritative and need not be duplicated in
each task.

## Residual risks

- Tau extension APIs are pre-1.0. The tests pin development evidence to Tau
  0.4.4; a later Tau upgrade requires rerunning the real load test.
- A fake server proves request contracts, not compatibility with every future
  agentmemory release. The optional real-server smoke covers the installed
  version without making local service availability a test-suite prerequisite.

## Handoff provenance

- Planning contract: version 1.
- Installed planning skill provenance: unknown.
- Execution mode after plan approval: supervised.
