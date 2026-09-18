# tau-agentmemory

A Tau extension that exposes agentmemory's REST API as native `memory_*` tools.

## Installation

Install the extension from GitHub:

```bash
tau install git:github.com/legout/tau-agentmemory
```

agentmemory is a separate service. Start it yourself before using the extension;
tau-agentmemory does not install, configure, or start the server.

## Configuration

Each setting is resolved independently in this order:

1. The matching `AGENTMEMORY_*` environment variable.
2. The matching key in `~/.agentmemory/.env`, using one `KEY=value` per line
   (without `export`).
3. The default below.

| Key | Default | Effect |
| --- | --- | --- |
| `AGENTMEMORY_URL` | `http://localhost:3111` | Server base URL. |
| `AGENTMEMORY_SECRET` | none | Bearer credential for every request. |
| `AGENTMEMORY_PROJECT_NAME` | derived | Stable project identifier; otherwise Git-root basename, then directory name. |
| `AGENTMEMORY_CAPTURE` | `1` | `0` (exact value) disables prompt, tool, and conversation observations; recall, explicit tools, and session tracking stay on. |
| `AGENTMEMORY_TOOL_OBSERVE` | `1` | `0` (exact value) disables tool observations only. |
| `AGENTMEMORY_REQUIRE_HTTPS` | `0` | `1` (exact value) refuses bearer requests to non-loopback plaintext HTTP before any network I/O. |

For example:

```dotenv
AGENTMEMORY_URL=http://localhost:3111
AGENTMEMORY_SECRET=your-secret
```

## Automatic behavior

With default settings the extension also gives Tau automatic memory behavior:

- **Automatic recall.** Each interactive prompt is searched against project
  memory first; when usable results exist, a bounded `<agentmemory-context>`
  reference block (at most five results, 8,000 characters) is prepended to the
  prompt. Extension-generated inputs are never recalled.
- **Session tracking.** Tau sessions are announced to agentmemory and ended on
  session transitions; quitting schedules one best-effort consolidation.
- **Automatic capture.** Each interactive prompt, each non-`memory_*` tool
  call (redacted arguments plus rendered result), and each final assistant
  answer are sent to the server as observations.

## Privacy: automatic capture is on by default

Prompts, tool arguments, tool results, and assistant answers are sent to the
configured agentmemory server unless you opt out. Before capture, values
under common credential keys (`password`, `token`, `api_key`, `authorization`,
`cookie`, and similar), bearer values, sensitive `key=value` / `key: value`
text, and every occurrence of the exact `AGENTMEMORY_SECRET` are replaced with
`[REDACTED]`, and captured text is capped at 8,000 characters. Redaction is
best-effort: it cannot prove that arbitrary prose is free of sensitive
information, so avoid pasting secrets into conversations with capture enabled.

Two capture opt-outs exist (rows in the table above; only the exact value `0`
disables):

```dotenv
AGENTMEMORY_CAPTURE=0       # no prompt, tool, or conversation observations;
                            # recall, explicit tools, and session tracking stay on
AGENTMEMORY_TOOL_OBSERVE=0  # no tool observations only
```

Identical observations within five minutes are sent once. Capture is
best-effort: observations are fire-and-forget background requests that are
never retried and can be lost when Tau exits abruptly.

## Project resolution

Memories are scoped by project name, resolved once per session: the basename
of the Git repository root for the working directory, or the directory name
outside a Git repository. Set `AGENTMEMORY_PROJECT_NAME` to override the
derived identifier.

## Bearer credentials and plaintext HTTP

With `AGENTMEMORY_SECRET` set, requests to a non-loopback plaintext HTTP URL
print one warning per extension generation before being sent. Set
`AGENTMEMORY_REQUIRE_HTTPS=1` to refuse such requests instead. Loopback HTTP
and HTTPS are always allowed and never warn.

## Verification

With agentmemory already running, ask Tau to invoke the installed health tool:

```bash
tau -p 'Call memory_health exactly once and print its result.'
```

A healthy service returns its JSON health response. If the service is not
running, the tool reports how to start it or configure `AGENTMEMORY_URL`.
