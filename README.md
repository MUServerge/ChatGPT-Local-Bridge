# ChatGPT Local Bridge

A read-only local research bridge for ChatGPT. It keeps source trees and large binary dumps on the Windows machine and exposes only bounded MCP tools through OpenAI Secure MCP Tunnel.

## Architecture

```text
ChatGPT
   |
   | OpenAI Secure MCP Tunnel
   v
tunnel-client
   |
   | localhost HTTP
   v
127.0.0.1:8765/mcp
ChatGPT Local Bridge
   |
   v
Allowlisted project roots
```

No domain, VPS, reverse proxy, self-hosted relay, port forwarding, or public localhost exposure is required.

The first project is:

```text
project = ssemu
root = C:\Users\hatim\Desktop\SSEMU-2.5.9
```

## Read-only MCP tools

General:

- `projects`
- `health`
- `list_files`
- `stat`
- `search_files`
- `search_text`
- `read_text`
- `read_range`
- `hash_file`

Binary research:

- `pe_info`
- `pe_sections`
- `va_to_offset`
- `read_va`
- `find_bytes`
- `strings`
- `disassemble`

There are no write/edit/delete/shell/process/Git mutation tools.

## Windows setup

Requirements:

- Python 3.11+
- a Secure MCP Tunnel ID and runtime API key

The official OpenAI `tunnel-client` can be installed by this repository's verified Windows installer.

Update the repository:

```powershell
git fetch origin
git switch feature/secure-mcp-tunnel
git pull
setup-local.bat
```

Edit `.env`:

```env
BRIDGE_PROJECT_ID=ssemu
BRIDGE_ROOT=C:\Users\hatim\Desktop\SSEMU-2.5.9
BRIDGE_TOKEN=replace-with-a-long-random-local-token
BRIDGE_MAX_READ_BYTES=4194304
BRIDGE_MAX_TEXT_BYTES=1048576
BRIDGE_AUDIT_LOG=bridge-audit.log
```

Generate the local debug token with:

```powershell
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Verify the local bridge

Start it:

```text
run-local.bat
```

Then open:

```text
http://127.0.0.1:8765/health
```

Expected shape:

```json
{"ok":true,"version":"0.3.0","projects":["ssemu"],"mcp_path":"/mcp"}
```

Optional PowerShell smoke test:

```powershell
.\scripts\windows\smoke.ps1
```

## Install and configure Secure MCP Tunnel

Install the latest official OpenAI Windows amd64 tunnel client:

```powershell
.\scripts\windows\install-tunnel.ps1
```

The installer resolves the latest public release from `openai/tunnel-client`, verifies the release SHA-256 digest, and installs the executable under the current user's LocalAppData.

Then configure the tunnel:

```powershell
.\scripts\windows\configure-tunnel.ps1
```

The wizard asks for the `tunnel_...` ID and runtime API key, initializes the profile against:

```text
http://127.0.0.1:8765/mcp
```

and runs `tunnel-client doctor`.

The runtime credential is stored outside the repository at:

```text
%APPDATA%\ChatGPT-Local-Bridge\tunnel.env
```

with a user-only ACL.

Start the bridge and tunnel together:

```powershell
.\scripts\windows\start-all.ps1
```

In another PowerShell window:

```powershell
.\scripts\windows\smoke.ps1
```

## ChatGPT connection

Create a developer-mode app/connection in ChatGPT and choose `Tunnel` as the connection type. Select the same `tunnel_...` ID used by `tunnel-client`.

Once connected, the first MCP call should be:

```text
projects()
```

For the SSEMU dump, examples are:

```text
pe_info(project="ssemu", path="main-runtime-image.bin")

disassemble(
  project="ssemu",
  path="main-runtime-image.bin",
  va="0x00545180",
  length=512,
  max_instructions=80,
  mode="memory"
)
```

The full 152 MB dump remains on the PC.

## Multiple local projects

You can replace `BRIDGE_PROJECT_ID` / `BRIDGE_ROOT` with:

```env
BRIDGE_PROJECTS_JSON={"ssemu":"C:\\Users\\hatim\\Desktop\\SSEMU-2.5.9","arkania":"D:\\Projects\\ArkaniaWeb"}
```

Each request is still constrained to one configured root.

## Security

Read `docs/SECURITY.md`. The bridge should stay bound to `127.0.0.1` and should be run as a normal non-admin Windows user.
