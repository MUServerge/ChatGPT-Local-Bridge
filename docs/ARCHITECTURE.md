# Architecture

## Final transport

```text
ChatGPT
  |
  | OpenAI Secure MCP Tunnel
  v
tunnel-client (outbound HTTPS only)
  |
  | loopback MCP HTTP
  v
127.0.0.1:8765/mcp
ChatGPT Local Bridge
  |
  v
Explicit allowlisted project roots
```

There is no public relay, VPS, domain, reverse proxy, or inbound firewall rule.

The local MCP server binds only to `127.0.0.1`. OpenAI's `tunnel-client` runs on the same Windows machine and forwards tunnel traffic to the loopback MCP endpoint.

## Project boundary

Each exposed project has a short project ID and one canonical root.

Initial project:

- project: `ssemu`
- root: `C:\Users\hatim\Desktop\SSEMU-2.5.9`

All tool paths are relative to the selected root. Absolute paths and canonical path escapes are rejected.

## Read-only policy

The bridge intentionally exposes no shell, process, browser, desktop, write, patch, rename, delete, or Git mutation tools.

The current tool surface is for source/binary research only.

## Binary research

Large binaries remain local. PE analysis and x86 disassembly execute on the Windows machine and only bounded results are returned through MCP.

Supported analysis includes:

- PE headers and section map
- virtual-address mapping
- bounded reads by VA
- wildcard byte signatures
- printable strings
- bounded x86 disassembly
