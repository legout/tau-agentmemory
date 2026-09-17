# Plan 0002: Tau-native agentmemory lifecycle integration

Status: **Approved** — the owner approved the ticketized execution map and
GitHub issue publication on 2026-09-17.

## Goal and source

Implement
[`docs/specs/0002-lifecycle-memory.md`](../specs/0002-lifecycle-memory.md),
approved revision 1, without changing the ten-tool contract owned by
[`docs/specs/0001-rest-bridge.md`](../specs/0001-rest-bridge.md).
Architecture rationale is recorded in
[`docs/adr/0002-tau-native-lifecycle-memory.md`](../adr/0002-tau-native-lifecycle-memory.md).

Capture checkpoint:

- **Vocabulary:** no new glossary terms are required.
- **Decision:** ADR 0002 records Tau-native input injection, default-on capture,
  and best-effort delivery.
- **Behavior:** Spec 0002 revision 1 owns lifecycle behavior and acceptance;
  Spec 0001 remains authoritative for explicit tools.
- **Uncertainty:** no implementation-blocking decision remains.
- **Contract:** planning-contract version 1; installed skill provenance revision
  unknown.

Pinned planning base: `9f7661aa07d2c74d144e3088ea45df9933d58e07`.

## Constraints and sequencing

- Python >=3.12 and Tau 0.4.4.
- Production dependencies remain stdlib plus Tau host APIs.
- No MCP, server lifecycle, retries, polling loops, durable queue, Tau core
  change, or new slash command.
- Keep the ten declarative tools and their response behavior unchanged.
- Execute sequentially because all slices share configuration, lifecycle state,
  extension registration, and runtime tests.
- Security boundaries are the bearer credential, external recalled content, and
  default-on capture of session content.
- Each task receives at most one parent-authorized fix pass and one delta-only
  recheck. Unresolved findings return to the owner.

## Canonical tickets

The GitHub issues below own the editable task bodies. This plan owns only their
order, dependencies, requirement coverage, and global gate.

| Order | Ticket | Dependency | Validation |
| --- | --- | --- | --- |
| 1 | [#4 Guard bearer credentials on plaintext transport](https://github.com/legout/tau-agentmemory/issues/4) | none | high risk, `new-test`, immediate independent review |
| 2 | [#5 Add project-scoped recall and reason-aware sessions](https://github.com/legout/tau-agentmemory/issues/5) | #4 accepted | high risk, `new-test`, immediate independent review |
| 3 | [#6 Add default-on redacted lifecycle capture](https://github.com/legout/tau-agentmemory/issues/6) | #5 accepted | high risk, `new-test`, immediate independent review |

## Requirement coverage

| Spec 0002 requirement | Ticket |
| --- | --- |
| Plaintext bearer warning/enforcement | [#4](https://github.com/legout/tau-agentmemory/issues/4) |
| Project identity and lifecycle state | [#5](https://github.com/legout/tau-agentmemory/issues/5) |
| Reason-aware start/end and health/sidebar | [#5](https://github.com/legout/tau-agentmemory/issues/5) |
| Interactive-only bounded recall injection | [#5](https://github.com/legout/tau-agentmemory/issues/5) |
| Recovery announcement | [#5](https://github.com/legout/tau-agentmemory/issues/5) |
| Default-on prompt/tool/conversation capture | [#6](https://github.com/legout/tau-agentmemory/issues/6) |
| Master and tool-only opt-outs | [#6](https://github.com/legout/tau-agentmemory/issues/6) |
| `memory_*` exclusion | [#6](https://github.com/legout/tau-agentmemory/issues/6) |
| Redaction and truncation | [#6](https://github.com/legout/tau-agentmemory/issues/6) |
| Best-effort tasks and consolidation | [#6](https://github.com/legout/tau-agentmemory/issues/6) |
| Deduplication | [#6](https://github.com/legout/tau-agentmemory/issues/6) |
| Migration/privacy documentation | [#6](https://github.com/legout/tau-agentmemory/issues/6) |
| Existing ten-tool compatibility | #4–#6 and the candidate gate |

## Candidate gate

After all three tickets are independently accepted, assemble their reviewed
commits in order and run on the exact candidate head:

```bash
uv lock --check
uv run pytest
uvx ruff check pyproject.toml src tests
uv run python -m compileall -q src tests
git diff --check
```

A fresh read-only candidate review checks only unreviewed code and integration
seams: shared client/config composition, reload/rebind state, observation
ordering, credential/capture boundaries, unchanged explicit tools, and README
accuracy. Integration, push, issue closure, and publication remain separate
owner gates.

## Residual risks and manual evidence

- Abrupt exit can lose best-effort observations or consolidation by design.
- Common-key/text redaction cannot prove arbitrary prose contains no secrets.
- Input-hook recall is user-role context rather than Pi's system-prompt context.
- Hermetic tests establish the contract. If an already-running real agentmemory
  server is available, an optional manual Tau session may verify project-scoped
  recall and grouped observations; skipping it does not replace or invalidate
  hermetic evidence.
