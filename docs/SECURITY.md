# Security model

## Protected assets

- local source code and binaries
- filesystem outside configured project roots
- the local debug token
- the OpenAI tunnel runtime credential

## Default controls

- bridge binds to `127.0.0.1` only
- no public relay, inbound firewall rule, or public localhost exposure
- explicit allowlisted project roots
- canonical path containment after path resolution
- absolute paths rejected
- bounded text/binary reads
- normal file editing enabled
- deletion disabled by default
- general command execution disabled by default
- read-only Git status/diff helpers
- atomic file replacement for writes and patches
- optional `expected_sha256` concurrency guards
- local audit log for file operations

## Write boundary

`BRIDGE_ALLOW_WRITE=true` enables `write_file`, `apply_patch`, `create_directory`, `move_file`, and `rename_file` inside configured roots.

Deletion has a separate switch and remains off unless `BRIDGE_ALLOW_DELETE=true` is explicitly configured. Deleting a project root is always rejected.

General process execution has a separate switch and executable allowlist. `run_command` requires both `BRIDGE_ALLOW_COMMAND=true` and an exact executable name in `BRIDGE_COMMAND_ALLOWLIST`. It never uses a shell.

## Path boundary

Every user-supplied tool path must be relative to the selected project root. The bridge canonicalizes it and rejects any resolved target outside that root. Recursive traversal also skips entries that resolve outside the root.

This protects against normal `..` traversal and existing symlink/junction escapes. This project is still not an operating-system sandbox, so it should run as a normal non-admin Windows user.

Do not allowlist `C:\`, `C:\Users`, or the entire Desktop.

## Tunnel boundary

The OpenAI Secure MCP Tunnel is transport only. `tunnel-client` reaches the local MCP server over localhost and reaches OpenAI over outbound HTTPS.

The tunnel runtime credential is stored outside the repository at:

```text
%APPDATA%\ChatGPT-Local-Bridge\tunnel.env
```

The existing tunnel configuration script applies a user-only ACL. Do not commit or paste that credential into source files.
