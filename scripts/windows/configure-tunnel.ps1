$ErrorActionPreference = "Stop"

if (-not (Get-Command tunnel-client -ErrorAction SilentlyContinue)) {
    throw "tunnel-client was not found on PATH. Install the latest official OpenAI tunnel-client release first."
}

$TunnelId = Read-Host "Tunnel ID (tunnel_...)"

if ($TunnelId -notmatch "^tunnel_[A-Za-z0-9_-]+$") {
    throw "Invalid tunnel ID."
}

$SecureKey = Read-Host "Runtime API key" -AsSecureString
$Ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureKey)

try {
    $ApiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Ptr)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Ptr)
}

$Profile = Read-Host "Tunnel profile [chatgpt-local-bridge]"

if ([string]::IsNullOrWhiteSpace($Profile)) {
    $Profile = "chatgpt-local-bridge"
}

$ConfigDir = Join-Path $env:APPDATA "ChatGPT-Local-Bridge"
$RuntimeEnv = Join-Path $ConfigDir "tunnel.env"

New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

@(
    "CONTROL_PLANE_API_KEY=$ApiKey"
    "TUNNEL_ID=$TunnelId"
    "TUNNEL_PROFILE=$Profile"
    "TUNNEL_HEALTH_ADDR=127.0.0.1:8766"
    "MCP_SERVER_URL=http://127.0.0.1:8765/mcp"
) | Set-Content -Path $RuntimeEnv -Encoding UTF8

$Principal = "$env:USERDOMAIN\$env:USERNAME"

& icacls.exe $ConfigDir /inheritance:r /grant:r "${Principal}:(OI)(CI)F" | Out-Null
& icacls.exe $RuntimeEnv /inheritance:r /grant:r "${Principal}:F" | Out-Null

$env:CONTROL_PLANE_API_KEY = $ApiKey

tunnel-client init --force --sample sample_mcp_remote_no_auth --profile $Profile --tunnel-id $TunnelId --health-listen-addr "127.0.0.1:8766" --mcp-server-url "http://127.0.0.1:8765/mcp"

tunnel-client doctor --profile $Profile --explain

$env:CONTROL_PLANE_API_KEY = $null
$ApiKey = $null

Write-Host ""
Write-Host "Tunnel configured."
Write-Host "Runtime config: $RuntimeEnv"
Write-Host "Next: run .\scripts\windows\start-all.ps1"
