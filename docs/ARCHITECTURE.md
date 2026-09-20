# Architecture

```text
ChatGPT
  |
  | OpenAI Secure MCP Tunnel
  v
tunnel-client on Windows
  |
  | localhost HTTP
  v
127.0.0.1:8765/mcp
ChatGPT Local Bridge
  |
  +--> allowlisted local project roots
  |
  +--> bounded filesystem operations
  |
  +--> read-only Git status/diff
```

There is no self-hosted relay, VPS, domain, reverse proxy, public port, or inbound firewall rule.

## Default project

The one-click Windows bootstrap configures:

```text
project: mu-rnd-5.2
root: %USERPROFILE%\Desktop\MU-RND-5.2
```

The bootstrap uses the current Windows user's profile instead of hardcoding a username.

## Filesystem service

Every tool receives a project ID and paths relative to that project. The registry resolves paths against the project root and rejects canonical targets outside it.

Read operations are bounded by configured byte/line/output limits. File writes use a temporary file in the destination directory followed by an atomic replace. Patch operations use exact-text replacement and reject ambiguous matches by default.

## Capability layers

Always available:

- read/navigation/search/hash
- PE/binary research helpers
- Git status/diff

Enabled by default:

- create/update/patch/move/rename inside allowlisted roots

Disabled by default:

- delete
- general process execution

## Windows lifecycle

`INSTALL AND START.cmd` is the bootstrap entry point. It installs the local environment, writes project configuration, registers a per-user Startup launcher, and starts the service in the background.

Runtime state and logs live under:

```text
%APPDATA%\ChatGPT-Local-Bridge
```

The Startup launcher invokes `scripts/windows/start-background.ps1`, which is idempotent: it leaves an already-running bridge alone and starts the tunnel only when tunnel credentials exist.
