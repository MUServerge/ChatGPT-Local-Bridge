$ErrorActionPreference = "Stop"

$Bridge = Invoke-RestMethod "http://127.0.0.1:8765/readyz"

if (-not $Bridge.ready) {
    throw "Local bridge readiness check failed."
}

Write-Host "Bridge OK"
Write-Host ("Projects: " + ($Bridge.projects -join ", "))
Write-Host ("MCP path: " + $Bridge.mcp_path)

$LocalTunnel = Join-Path $env:LOCALAPPDATA "ChatGPT-Local-Bridge\tunnel-client\tunnel-client.exe"

if (Test-Path $LocalTunnel) {
    Write-Host ("tunnel-client: " + $LocalTunnel)
}
elseif (Get-Command tunnel-client -ErrorAction SilentlyContinue) {
    Write-Host ("tunnel-client: " + (Get-Command tunnel-client).Source)
}
else {
    throw "tunnel-client is not installed. Run scripts\windows\install-tunnel.ps1."
}

try {
    $Tunnel = Invoke-RestMethod "http://127.0.0.1:8766/readyz" -TimeoutSec 3
    Write-Host "Tunnel readiness endpoint OK"
    $Tunnel | ConvertTo-Json -Depth 5
}
catch {
    Write-Warning "Tunnel is installed but not currently ready. Start scripts\windows\start-all.ps1."
}
