$ErrorActionPreference = "Stop"

if (-not (Get-Command tunnel-client -ErrorAction SilentlyContinue)) {
    throw "tunnel-client was not found in PATH. Install the official OpenAI tunnel-client first."
}

if (-not $env:CONTROL_PLANE_API_KEY) {
    throw "CONTROL_PLANE_API_KEY is not set."
}

if (-not $env:CONTROL_PLANE_TUNNEL_ID) {
    throw "CONTROL_PLANE_TUNNEL_ID is not set."
}

$mcpUrl = "http://127.0.0.1:8765/mcp"

Write-Host "Starting Secure MCP Tunnel"
Write-Host "Tunnel: $($env:CONTROL_PLANE_TUNNEL_ID)"
Write-Host "Local MCP: $mcpUrl"

$arguments = @(
    "run",
    "--control-plane.tunnel-id",
    $env:CONTROL_PLANE_TUNNEL_ID,
    "--mcp.server-url",
    $mcpUrl
)

& tunnel-client @arguments
