# Architecture

## Final transport

```text
ChatGPT
  |
  | OpenAI-hosted Secure MCP Tunnel
  v
tunnel-client on Windows
  |
  | localhost HTTP
  v
127.0.0.1:8765/mcp
ChatGPT Local Bridge
  |
  v
Explicit read-only project roots
```

There is no self-hosted relay, domain, reverse proxy, VPS, or inbound port.

The local bridge binds only to `127.0.0.1`. `tunnel-client` makes outbound HTTPS requests to OpenAI and forwards MCP requests to the local `/mcp` endpoint.

## Local project boundary

Initial project:

```text
project: ssemu
root: C:\Users\hatim\Desktop\SSEMU-2.5.9
```

Every tool takes a project ID. Every path is relative to its allowlisted root. Absolute paths and path escapes are rejected after canonical resolution.

## Tool families

General read-only tools:

- projects
- health
- list_files
- stat
- search_files
- search_text
- read_text
- read_range
- hash_file

Binary research tools:

- pe_info
- pe_sections
- va_to_offset
- read_va
- find_bytes
- strings
- disassemble

The large binary stays on the workstation. Only requested bounded results cross the MCP tunnel.
