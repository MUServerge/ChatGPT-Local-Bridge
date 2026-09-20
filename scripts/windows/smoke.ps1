$ErrorActionPreference = "Stop"

Write-Host "Checking local bridge..."

$Bridge = Invoke-RestMethod "http://127.0.0.1:8765/health"

if (-not $Bridge.ok) {
    throw "Local bridge health check failed."
}

Write-Host "Local bridge OK."
Write-Host ("Projects: " + ($Bridge.projects -join ", "))
Write-Host ("MCP: " + $Bridge.mcp_url)

try {
    $Tunnel = Invoke-RestMethod "http://127.0.0.1:8766/readyz" -TimeoutSec 3
    Write-Host "Tunnel ready:"
    $Tunnel | ConvertTo-Json -Depth 5
}
catch {
    Write-Warning "Tunnel readiness endpoint is not available. Start scripts\windows\start-all.ps1 first."
}
