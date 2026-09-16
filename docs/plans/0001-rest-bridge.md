# Plan 0001: agentmemory REST bridge for Tau

Status: **Approved** — the owner approved the ticketized execution map for
supervised implementation on 2026-09-16. This approval does not authorize
integration or publication.

## Goal and source

Implement the approved REST-native Tau extension in
[`docs/specs/0001-rest-bridge.md`](../specs/0001-rest-bridge.md), revision 1,
approved by the owner on 2026-09-16. The architectural rationale is
[`docs/adr/0001-rest-native-bridge.md`](../adr/0001-rest-native-bridge.md), accepted
on 2026-09-16.

GitHub issues own the canonical task bodies. This plan is the thin execution and
dependency overview; task details are not duplicated here.

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

## Tickets and dependency order

1. [#1 — Deliver a loadable `memory_health` tracer bullet](https://github.com/legout/tau-agentmemory/issues/1)
2. [#2 — Complete the declarative 10-tool bridge](https://github.com/legout/tau-agentmemory/issues/2), blocked by #1
3. [#3 — Add session integration and finish acceptance](https://github.com/legout/tau-agentmemory/issues/3), blocked by #1 and #2

Execute sequentially. The tickets share transport, tool-table, extension, and
test surfaces, so parallel writers would create avoidable coordination risk.
Issue #2 requires immediate independent review because it includes bearer
credentials and destructive deletion. Issue #3 closes with the candidate
integration review.

## Requirement coverage

| Requirement | Source | Canonical ticket |
| --- | --- | --- |
| Loadable Tau package and native `memory_*` registration | Goal, Architecture, Registration | [#1](https://github.com/legout/tau-agentmemory/issues/1), [#2](https://github.com/legout/tau-agentmemory/issues/2) |
| Environment → `.env` → default configuration precedence | Interfaces: Configuration | [#1](https://github.com/legout/tau-agentmemory/issues/1) |
| Ten exact tools and REST mappings, including `memory_sessions.limit` | Interfaces: Tool table | [#1](https://github.com/legout/tau-agentmemory/issues/1), [#2](https://github.com/legout/tau-agentmemory/issues/2) |
| 10-second requests, bearer auth, GET query/body serialization | Data flow | [#1](https://github.com/legout/tau-agentmemory/issues/1), [#2](https://github.com/legout/tau-agentmemory/issues/2) |
| Sanitized unreachable, HTTP, 401, malformed-JSON behavior | Failures | [#1](https://github.com/legout/tau-agentmemory/issues/1), [#2](https://github.com/legout/tau-agentmemory/issues/2) |
| Non-blocking session-start probe, sidebar status, prompt guidelines | Registration | [#3](https://github.com/legout/tau-agentmemory/issues/3) |
| MCP/Pi coexistence without shared names or code | Migration / coexistence | [#3](https://github.com/legout/tau-agentmemory/issues/3) |
| Acceptance examples 1–4 | Acceptance examples | [#2](https://github.com/legout/tau-agentmemory/issues/2), [#3](https://github.com/legout/tau-agentmemory/issues/3) |

## Global validation

```bash
uv run pytest
```

Required CI, if added later, remains authoritative and need not be duplicated in
each ticket.

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
