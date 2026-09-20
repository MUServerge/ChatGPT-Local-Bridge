$ErrorActionPreference = "Stop"
$Bridge = Invoke-RestMethod "http://127.0.0.1:8765/health" -TimeoutSec 5
if (-not $Bridge.ok) { throw "Local bridge health check failed." }

Write-Host "Bridge OK"
Write-Host ("Version: " + $Bridge.version)
Write-Host ("Projects: " + ($Bridge.projects -join ", "))
Write-Host ("MCP path: " + $Bridge.mcp_path)
Write-Host ("Write: " + $Bridge.capabilities.write)
Write-Host ("Delete: " + $Bridge.capabilities.delete)
Write-Host ("Command: " + $Bridge.capabilities.command)

$tunnelEnv = Join-Path $env:APPDATA "ChatGPT-Local-Bridge\tunnel.env"
if (Test-Path $tunnelEnv) {
    try {
        $Tunnel = Invoke-RestMethod "http://127.0.0.1:8766/readyz" -TimeoutSec 3
        Write-Host "Tunnel readiness endpoint OK"
        $Tunnel | ConvertTo-Json -Depth 5
    }
    catch {
        Write-Warning "Tunnel is configured but is not currently ready. START.cmd will try to start it."
    }
}
else {
    Write-Warning "Tunnel credentials are not configured yet. Run CONNECT CHATGPT.cmd once."
}
