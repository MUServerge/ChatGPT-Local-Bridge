$ErrorActionPreference = "Stop"

$LocalTunnel = Join-Path $env:LOCALAPPDATA "ChatGPT-Local-Bridge\tunnel-client\tunnel-client.exe"
$RuntimeEnv = Join-Path $env:APPDATA "ChatGPT-Local-Bridge\tunnel.env"

if (Test-Path $LocalTunnel) {
    $TunnelClient = $LocalTunnel
}
elseif (Get-Command tunnel-client -ErrorAction SilentlyContinue) {
    $TunnelClient = (Get-Command tunnel-client).Source
}
else {
    throw "tunnel-client was not found. Run scripts\windows\install-tunnel.ps1 first."
}

if (-not (Test-Path $RuntimeEnv)) {
    throw "Tunnel is not configured. Run scripts\windows\configure-tunnel.ps1 first."
}

Get-Content $RuntimeEnv | ForEach-Object {
    if ($_ -match "^[ ]*([^#][^=]*)=(.*)$") {
        $Name = $matches[1].Trim()
        $Value = $matches[2]
        [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
    }
}

if ([string]::IsNullOrWhiteSpace($env:TUNNEL_PROFILE)) {
    throw "TUNNEL_PROFILE is missing from tunnel.env."
}

Write-Host "Starting Secure MCP Tunnel"
Write-Host ("Profile: " + $env:TUNNEL_PROFILE)
Write-Host "Local MCP: http://127.0.0.1:8765/mcp"

& $TunnelClient run --profile $env:TUNNEL_PROFILE
