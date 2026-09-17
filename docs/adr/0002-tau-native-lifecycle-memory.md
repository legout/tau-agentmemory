# ADR 0002: Tau-native lifecycle memory with default-on capture

Status: Accepted (owner approved the complete design on 2026-09-17)

Spec 0001 deliberately stopped at explicit REST tools, but matching agentmemory's
Pi experience requires automatic recall, observation capture, and session
tracking. We will preserve Tau's broader ten-tool bridge and add this behavior
through Tau's native `input`, `tool_result`, `agent_end`, `session_start`, and
`session_shutdown` seams rather than cloning Pi's smaller tool surface or
changing Tau core.

Automatic capture is enabled by default, with a master opt-out and a separate
tool-observation opt-out. Recall enters through a delimited `input` transform
because Tau 0.4.4 has no dynamic system-prompt hook. Observation and
consolidation delivery is best-effort: tasks are retained only until completion,
with no retry or shutdown drain. Capture excludes `memory_*` tools, applies
bounded redaction and truncation, and warns or refuses before sending bearer
credentials over non-loopback plaintext HTTP.

This keeps the existing tool contract stable and avoids a Tau dependency while
accepting that abrupt process exit can lose observations and that transformed
recall is user-role context rather than system-role context. Observable behavior
and privacy controls are owned by Spec 0002.
