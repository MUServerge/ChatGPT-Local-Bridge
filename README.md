# ChatGPT Local Bridge

A small read-only Windows file bridge for controlled access to large local project files.

The first use case is MU/SSEMU research: source trees, DLLs, logs, and large runtime dumps that are impractical to upload manually.

## Security model

- Read-only by design.
- One explicit allowlisted root folder.
- Bearer-token authentication.
- Paths are resolved and checked against the allowlisted root.
- Symlink/junction escapes are rejected by resolved-path containment checks.
- Binary reads are range-limited.
- No shell, command execution, write, rename, or delete endpoints.
- Every successful data access is written to an audit log.

## MVP API

- `GET /health`
- `GET /v1/list?path=.`
- `GET /v1/stat?path=...`
- `GET /v1/search?path=.&pattern=*.cpp&limit=200`
- `GET /v1/read-range?path=...&offset=0&length=65536`
- `GET /v1/hash?path=...`

`read-range` returns base64 so binary files can be read safely in chunks.

## Windows setup

Requirements: Python 3.11+.

```powershell
git clone https://github.com/MUServerge/ChatGPT-Local-Bridge.git
cd ChatGPT-Local-Bridge

py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
```

Edit `.env` and set:

```env
BRIDGE_ROOT=C:\path\to\your\project
BRIDGE_TOKEN=replace-with-a-long-random-token
```

Then start:

```powershell
python -m uvicorn bridge.app:app --host 127.0.0.1 --port 8765
```

Test locally:

```powershell
$token = "replace-with-a-long-random-token"
Invoke-RestMethod http://127.0.0.1:8765/health

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer $token" } `
  "http://127.0.0.1:8765/v1/list?path=."
```

## Large binary example

Read 64 KiB starting at offset `0x145180` from a runtime dump:

```text
GET /v1/read-range?path=main-runtime-image.bin&offset=1331584&length=65536
```

The bridge does not need to transfer the whole dump for address research.

## Internet/ChatGPT connectivity

The MVP intentionally binds to localhost only. Do not expose port 8765 directly to the internet.

The next layer will add an authenticated HTTPS transport/relay or connector integration after the local agent is verified.
