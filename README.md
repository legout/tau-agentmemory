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

1. The `AGENTMEMORY_URL` or `AGENTMEMORY_SECRET` environment variable.
2. The matching key in `~/.agentmemory/.env`, using one `KEY=value` per line
   (without `export`).
3. `http://localhost:3111` for the URL and no secret.

For example:

```dotenv
AGENTMEMORY_URL=http://localhost:3111
AGENTMEMORY_SECRET=your-secret
```

## Verification

With agentmemory already running, ask Tau to invoke the installed health tool:

```bash
tau -p 'Call memory_health exactly once and print its result.'
```

A healthy service returns its JSON health response. If the service is not
running, the tool reports how to start it or configure `AGENTMEMORY_URL`.
