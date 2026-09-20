# Security model

## Protected assets

- local source code
- runtime dumps and binaries
- filesystem outside the configured project roots
- the local debug token
- the OpenAI tunnel runtime credential

## Controls

- bridge binds to loopback only
- no public relay or inbound firewall rule
- explicit allowlisted project roots
- canonical path containment
- absolute paths rejected
- read-only MCP tool surface
- bounded text and binary reads
- no shell or process execution
- no write/edit/delete/rename tools
- no Git mutation tools
- local audit log for file access

## Tunnel boundary

The OpenAI Secure MCP Tunnel is transport only. `tunnel-client` reaches the local MCP server over localhost and reaches OpenAI over outbound HTTPS.

The tunnel runtime API key is not stored in this repository. Keep it in the environment or the tunnel-client credential mechanism.

## Operating-system boundary

This project is not an OS sandbox. Run it as a normal non-admin Windows user and allowlist only specific project directories.

Do not configure `C:\`, `C:\Users`, or the whole Desktop as a project root.
