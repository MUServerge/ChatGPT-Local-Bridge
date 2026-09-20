# Security model

## Protected assets

- source code under configured project roots
- runtime dumps and DLLs
- the rest of the workstation filesystem
- OpenAI tunnel runtime credentials

## Controls

- local server binds to `127.0.0.1`
- no inbound internet listener
- explicit project-root allowlist
- canonical path resolution
- absolute paths rejected
- path traversal/junction escapes rejected
- read-only MCP tools
- bounded text and binary reads
- no shell or process execution
- no write/edit/delete/Git mutation tools
- successful reads recorded in a local audit log
- tunnel runtime API key stored outside the repository under the current Windows user profile

## Tunnel credential boundary

The runtime API key is used by `tunnel-client` to authenticate to OpenAI's tunnel control plane. It is not an MCP tool argument and should never be committed to Git.

The setup script stores it under:

```text
%APPDATA%\ChatGPT-Local-Bridge\tunnel.env
```

and applies a user-only ACL.

## Important limitation

This bridge is not an OS sandbox. Run it as a normal non-admin Windows user and expose only narrow project directories.

Do not use `C:\`, `C:\Users`, the whole Desktop, or another broad parent folder as a project root.
