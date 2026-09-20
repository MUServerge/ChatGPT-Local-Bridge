# ChatGPT Local Bridge

A read-only local research bridge that lets ChatGPT work with large project files without uploading entire repositories or binary dumps.

The first target is:

```text
Machine: home-ssemu
Project: ssemu
Root: C:\Users\hatim\Desktop\SSEMU-2.5.9
```

## Architecture

```text
ChatGPT
   |
   | MCP Streamable HTTP / HTTPS
   v
Self-hosted Relay
   |
   | authenticated request routing
   | persistent outbound WebSocket
   v
Windows Local Agent
   |
   v
Allowlisted read-only project roots
```

The Windows machine does not expose an inbound public port. The agent connects outward to the relay.

## Current read-only tools

General:

- `machines`
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

No write/edit/delete/shell/process tools exist in this version.

## 1. Update the Windows checkout

From the bridge repository:

```powershell
git fetch origin
git switch feature/self-hosted-mcp-relay
git pull
setup-local.bat
```

Edit `.env`:

```env
BRIDGE_MACHINE_ID=home-ssemu
BRIDGE_PROJECT_ID=ssemu
BRIDGE_ROOT=C:\Users\hatim\Desktop\SSEMU-2.5.9

BRIDGE_TOKEN=LOCAL_RANDOM_SECRET
BRIDGE_MAX_READ_BYTES=4194304
BRIDGE_MAX_TEXT_BYTES=1048576
BRIDGE_AUDIT_LOG=bridge-audit.log

RELAY_WS_URL=wss://bridge.example.com/agent/ws
RELAY_AGENT_TOKEN=AGENT_RANDOM_SECRET
```

Generate secrets with:

```powershell
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

Use separate values for the local token, agent token, and MCP token.

The local debug API still works:

```text
run-local.bat
http://127.0.0.1:8765/health
```

The outbound relay agent is:

```text
run-agent.bat
```

## 2. Deploy the relay

A small VPS with Docker and a DNS name is enough.

Copy this repository to the server and create `.env.relay`:

```env
RELAY_AGENT_TOKEN=AGENT_RANDOM_SECRET
RELAY_MCP_TOKEN=MCP_RANDOM_SECRET
RELAY_REQUEST_TIMEOUT=30
```

Set the public domain before starting Compose:

```bash
export BRIDGE_DOMAIN=bridge.example.com
docker compose up -d --build
```

Caddy terminates HTTPS automatically. DNS for `bridge.example.com` must point to the relay server.

Health check:

```text
https://bridge.example.com/healthz
```

The ChatGPT-facing MCP endpoint is:

```text
https://bridge.example.com/mcp
```

Authenticate MCP requests with:

```text
Authorization: Bearer <RELAY_MCP_TOKEN>
```

## 3. Connect ChatGPT

Create a developer/custom MCP connection pointing to:

```text
https://bridge.example.com/mcp
```

Use bearer authentication with the `RELAY_MCP_TOKEN`.

After the Windows agent is running, the first call should be:

```text
machines()
```

Expected shape:

```json
{
  "machines": [
    {
      "machine": "home-ssemu",
      "projects": ["ssemu"]
    }
  ]
}
```

Then a 152 MB runtime dump can be researched without uploading it:

```text
pe_info(machine="home-ssemu", project="ssemu", path="main-runtime-image.bin")

disassemble(
  machine="home-ssemu",
  project="ssemu",
  path="main-runtime-image.bin",
  va="0x00545180",
  length=512,
  max_instructions=80,
  mode="memory"
)
```

Only the requested analysis crosses the relay.

## Multi-project support

For several roots on one PC, replace `BRIDGE_PROJECT_ID/BRIDGE_ROOT` with:

```env
BRIDGE_PROJECTS_JSON={"ssemu":"C:\\Users\\hatim\\Desktop\\SSEMU-2.5.9","arkania":"D:\\Projects\\ArkaniaWeb"}
```

Every request still names one project and remains constrained to that root.

## Security

Read [docs/SECURITY.md](docs/SECURITY.md) before exposing the relay publicly.

The main rules are:

- use narrow project roots;
- run the agent as a non-admin Windows user;
- keep agent and MCP secrets different;
- never publish the local debug API;
- keep the current bridge read-only while the research workflow is being validated.

## Development

```powershell
pip install -r requirements.txt
pytest -q
```

Architecture and protocol details:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/PROTOCOL.md](docs/PROTOCOL.md)
- [docs/SECURITY.md](docs/SECURITY.md)
