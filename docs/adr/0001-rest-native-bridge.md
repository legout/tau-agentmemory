# ADR 0001: REST-native bridge, not MCP

Status: Accepted (owner approved the REST-native bridge and MCP coexistence on 2026-09-15; Spec 0001 revision 1 approved on 2026-09-16)

## Context

Tau has no MCP client. agentmemory's primary surface is HTTP REST at
`http://localhost:3111`; its MCP server is itself a bridge over that REST API.
The user's Pi integration already talks to agentmemory via a direct REST
extension (~275 lines), not via MCP. A separate project (`tau-mcp`,
github.com/nicobailon/pi-mcp-adapter port) will add generic MCP support to Tau
later.

## Decision

tau-agentmemory is a direct REST client registering native `memory_*` tools at
extension setup. It does not spawn or manage processes (the server is a
user-run service), and it does not route through MCP.

The MCP path remains available as a secondary route: agentmemory's MCP server
can be configured in `~/.tau/mcp.json` for tau-mcp, exposing the same
operations as `mcp__agentmemory__*` proxy targets. The two surfaces coexist;
they share no code and no tool names.

## Consequences

- Skills calling `memory_*` tools work unchanged (bare names, first
  registration wins, no MCP naming prefix).
- No subprocess lifecycle, handshake, or metadata cache to own; failure
  handling is one HTTP timeout away.
- The tool surface is a curated core set (~11 tools). Long-tail operations
  stay reachable through the `agentmemory-rest-api` skill (curl) until a tool
  is promoted into the declarative table.
- If agentmemory's REST API changes, this extension's mapping table changes
  with it; the MCP route would track the MCP schema instead.
