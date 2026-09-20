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
    throw "tunnel-client was not found. Run CONNECT CHATGPT.cmd."
}

if (-not (Test-Path $RuntimeEnv)) {
    throw "Tunnel is not configured. Run CONNECT CHATGPT.cmd."
}

Get-Content -LiteralPath $RuntimeEnv -Encoding UTF8 | ForEach-Object {
    if ($_ -match "^[ ]*([^#][^=]*)=(.*)$") {
        $Name = $matches[1].Trim().TrimStart([char]0xFEFF)
        $Value = $matches[2]
        [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
    }
}

if ([string]::IsNullOrWhiteSpace($env:TUNNEL_PROFILE)) {
    throw "TUNNEL_PROFILE is missing from tunnel.env."
}
if ([string]::IsNullOrWhiteSpace($env:CONTROL_PLANE_API_KEY)) {
    throw "CONTROL_PLANE_API_KEY is missing from tunnel.env."
}

Write-Host "Starting Secure MCP Tunnel"
Write-Host ("Profile: " + $env:TUNNEL_PROFILE)
Write-Host "Local MCP: http://127.0.0.1:8765/mcp"

& $TunnelClient run --profile $env:TUNNEL_PROFILE
if ($LASTEXITCODE -ne 0) {
    throw "tunnel-client exited with code $LASTEXITCODE."
}
