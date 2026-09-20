# Security model

## Protected assets

- source code and configuration below local project roots
- runtime dumps and binaries
- the rest of the workstation filesystem
- relay credentials

## Controls

- explicit project-root allowlist
- canonical path resolution after joins
- absolute paths rejected
- path escapes rejected
- read-only tool surface
- bounded text and binary reads
- no shell/process/browser/desktop tools
- no write, patch, rename, delete, or Git mutation tools
- local audit log for successful reads
- separate agent and MCP bearer credentials
- outbound-only agent transport
- TLS termination through Caddy in production

## Important limitation

This bridge is not an operating-system sandbox. Run the local agent as a normal non-admin Windows user and allowlist only the specific project directories that ChatGPT should be able to read.

Never use `C:\`, `C:\Users`, the whole Desktop, or another broad parent folder as a project root.

Rotate both relay secrets if they may have leaked.
