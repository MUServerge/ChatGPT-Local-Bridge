$ErrorActionPreference = "Stop"

$health = Invoke-RestMethod "http://127.0.0.1:8765/health"

if (-not $health.ok) {
    throw "Local bridge health check failed."
}

Write-Host "Bridge OK"
Write-Host ("Projects: " + ($health.projects -join ", "))
Write-Host ("MCP path: " + $health.mcp_path)

if (Get-Command tunnel-client -ErrorAction SilentlyContinue) {
    Write-Host "tunnel-client found."
}
else {
    Write-Warning "tunnel-client is not installed or not in PATH."
}
