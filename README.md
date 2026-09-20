# ChatGPT Local Bridge

A read-only Windows MCP bridge for large local source trees, binaries, DLLs, logs, and runtime dumps.

The first project is:

```text
Project: ssemu
Root: C:\Users\hatim\Desktop\SSEMU-2.5.9
```

## Architecture

```text
ChatGPT
   |
   | OpenAI Secure MCP Tunnel
   v
tunnel-client
   |
   | loopback only
   v
http://127.0.0.1:8765/mcp
   |
   v
ChatGPT Local Bridge
   |
   v
C:\Users\hatim\Desktop\SSEMU-2.5.9
```

There is no VPS, domain, public relay, reverse proxy, or inbound port.

The local MCP server remains private on `127.0.0.1`. The official OpenAI `tunnel-client` makes the outbound HTTPS connection.

## Tools

General read-only tools:

- `projects`
- `health`
- `list_files`
- `stat`
- `search_files`
- `search_text`
- `read_text`
- `read_range`
- `hash_file`

Binary / MU client research:

- `pe_info`
- `pe_sections`
- `va_to_offset`
- `read_va`
- `find_bytes`
- `strings`
- `disassemble`

No shell, process execution, write/edit, delete, rename, or Git mutation tools are exposed.

## First-time Windows setup

Switch to the feature branch:

```powershell
git fetch origin
git switch feature/self-hosted-mcp-relay
git pull
setup-local.bat
```

Copy `.env.example` to `.env` if setup did not already do it.

Use:

```env
BRIDGE_PROJECT_ID=ssemu
BRIDGE_ROOT=C:\Users\hatim\Desktop\SSEMU-2.5.9
BRIDGE_TOKEN=YOUR_LOCAL_DEBUG_TOKEN
BRIDGE_MAX_READ_BYTES=4194304
BRIDGE_MAX_TEXT_BYTES=1048576
BRIDGE_AUDIT_LOG=bridge-audit.log
```

Generate the local debug token with:

```powershell
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Install the official tunnel-client

The installer downloads the latest official Windows amd64 release from `openai/tunnel-client`, verifies the release SHA-256 digest published by GitHub, and installs it under the current user's LocalAppData.

```powershell
.\scripts\windows\install-tunnel.ps1
```

No system-wide installation is required.

## Configure Secure MCP Tunnel

Create a tunnel in OpenAI Platform tunnel settings, then run:

```powershell
.\scripts\windows\configure-tunnel.ps1
```

The script asks for:

- the `tunnel_...` ID
- a runtime API key
- an optional profile name

The runtime key is stored outside this repository at:

```text
%APPDATA%\ChatGPT-Local-Bridge\tunnel.env
```

with a user-only Windows ACL.

The tunnel profile forwards to:

```text
http://127.0.0.1:8765/mcp
```

## Start everything

```powershell
.\scripts\windows\start-all.ps1
```

This starts the local MCP server, waits for `/readyz`, and then starts the official tunnel client.

Smoke test in another PowerShell window:

```powershell
.\scripts\windows\smoke.ps1
```

## Connect ChatGPT

Enable ChatGPT Developer Mode and create a developer MCP connection using **Connection = Tunnel**.

Select or paste the same `tunnel_...` ID used by `configure-tunnel.ps1`.

The local MCP server does not need public authentication because it never leaves loopback; tunnel-client authenticates separately to OpenAI.

After the connection is enabled, a first read-only test is:

```text
Call projects, then list_files for project "ssemu" at path ".".
```

For the runtime dump:

```text
pe_info(project="ssemu", path="main-runtime-image.bin")
```

and:

```text
disassemble(
  project="ssemu",
  path="main-runtime-image.bin",
  va="0x00545180",
  length=512,
  max_instructions=80,
  mode="memory"
)
```

Only the requested result crosses the tunnel. The 150 MB+ dump remains on the Windows machine.

## Local debug API

The existing REST debug API still runs on loopback:

```text
http://127.0.0.1:8765/health
```

The `/v1/*` debug endpoints require `BRIDGE_TOKEN`. They are not used by ChatGPT's MCP tunnel.

## Multi-project support

To expose several specific folders later:

```env
BRIDGE_PROJECTS_JSON={"ssemu":"C:\\Users\\hatim\\Desktop\\SSEMU-2.5.9","arkania":"D:\\Projects\\ArkaniaWeb"}
```

Every MCP call still names one project and remains confined to that root.

## Security

Read:

- `docs/ARCHITECTURE.md`
- `docs/PROTOCOL.md`
- `docs/SECURITY.md`

Do not configure broad roots such as `C:\`, `C:\Users`, or the entire Desktop.

## Development

```powershell
pip install -r requirements.txt
python -m pytest -q
```
