$ErrorActionPreference = "Continue"
Write-Host "ChatGPT Local Bridge status"
try {
    $health = Invoke-RestMethod "http://127.0.0.1:8765/health" -TimeoutSec 3
    Write-Host ("Bridge: RUNNING  version=" + $health.version + "  projects=" + ($health.projects -join ","))
    Write-Host ("Write=" + $health.capabilities.write + " Delete=" + $health.capabilities.delete + " Command=" + $health.capabilities.command)
}
catch { Write-Host "Bridge: STOPPED" }

try {
    $tunnel = Invoke-RestMethod "http://127.0.0.1:8766/readyz" -TimeoutSec 3
    Write-Host "Tunnel: RUNNING"
    $tunnel | ConvertTo-Json -Depth 4
}
catch {
    $tunnelEnv = Join-Path $env:APPDATA "ChatGPT-Local-Bridge\tunnel.env"
    if (Test-Path $tunnelEnv) { Write-Host "Tunnel: CONFIGURED, NOT READY" }
    else { Write-Host "Tunnel: NOT CONFIGURED" }
}
