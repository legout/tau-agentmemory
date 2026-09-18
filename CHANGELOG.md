# Changelog

## Unreleased

## 0.2.0 - 2026-09-17

First published release: the complete Tau extension for agentmemory — the
native ten-tool REST bridge plus the automatic lifecycle memory integration.

### Added

- Native `memory_*` tools backed by the agentmemory REST API (`memory_health`,
  `memory_save`, `memory_smart_search`, `memory_recall`, `memory_sessions`,
  `memory_commits`, `memory_commit_lookup`, `memory_governance_delete`,
  `memory_lesson_save`, `memory_lesson_recall`), preserving the agentmemory
  skill contract with MCP-compatible string schemas (#1, #2).
- Session integration: non-blocking session-start health probe with
  feature-detected sidebar status and two memory-use prompt guidelines (#3).
- Plaintext bearer guard: one warning per extension generation when
  `AGENTMEMORY_SECRET` crosses non-loopback HTTP; `AGENTMEMORY_REQUIRE_HTTPS=1`
  refuses such requests before any network I/O. Guard text never contains the
  secret (#4).
- Automatic project-scoped recall: interactive prompts are searched against
  project memory and prefixed with a bounded, read-only
  `<agentmemory-context>` block (five results, 8,000-character cap, delimiter
  escaping); the original prompt is preserved unchanged (#5).
- Reason-aware session tracking: sessions are announced, ended on Tau session
  transitions, and consolidated once on quit (best-effort, five-second
  session-end timeout); reload never rotates the remote session (#5).
- Default-on redacted observation capture: interactive prompts, non-`memory_*`
  tool arguments/results, and final assistant answers are sent as project-
  scoped observations. Structured and textual redaction (credential keys,
  bearer values, sensitive `key=value`/`key: value` forms, the configured
  secret) runs before 8,000-character truncation; duplicates are suppressed
  for five minutes (#6).
- Capture opt-outs: `AGENTMEMORY_CAPTURE=0` disables all observation capture;
  `AGENTMEMORY_TOOL_OBSERVE=0` disables tool observations only. Recall,
  explicit tools, health, and session tracking stay active (#6).
- Project resolution for memory scoping: `AGENTMEMORY_PROJECT_NAME`, else
  Git-root basename, else directory name (#5).

### Changed

- Planning artifacts moved from `docs/` to the `project/` namespace.

### Privacy

Automatic capture is enabled by default. Prompts, tool content, and assistant
answers leave the host for the configured agentmemory server unless you set
`AGENTMEMORY_CAPTURE=0`. Redaction is best-effort and cannot prove arbitrary
prose is secret-free.

[0.1.0]: never published (development baseline for the REST bridge)
