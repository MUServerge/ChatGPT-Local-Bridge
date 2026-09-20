$ErrorActionPreference = "Stop"

$LocalTunnel = Join-Path $env:LOCALAPPDATA "ChatGPT-Local-Bridge\tunnel-client\tunnel-client.exe"

function Resolve-TunnelClient {
    if (Test-Path $LocalTunnel) { return $LocalTunnel }

    $command = Get-Command tunnel-client -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    Write-Host "Tunnel client is missing; installing it automatically..."
    & (Join-Path $PSScriptRoot "install-tunnel.ps1")

    if (Test-Path $LocalTunnel) { return $LocalTunnel }

    $command = Get-Command tunnel-client -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    throw "tunnel-client installation did not produce an executable."
}

$TunnelClient = Resolve-TunnelClient
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

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    throw "Runtime API key cannot be empty."
}

$Profile = Read-Host "Tunnel profile [chatgpt-local-bridge]"
if ([string]::IsNullOrWhiteSpace($Profile)) {
    $Profile = "chatgpt-local-bridge"
}

$ConfigDir = Join-Path $env:APPDATA "ChatGPT-Local-Bridge"
$RuntimeEnv = Join-Path $ConfigDir "tunnel.env"
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

$lines = @(
    "CONTROL_PLANE_API_KEY=$ApiKey"
    "TUNNEL_ID=$TunnelId"
    "TUNNEL_PROFILE=$Profile"
    "TUNNEL_HEALTH_ADDR=127.0.0.1:8766"
    "MCP_SERVER_URL=http://127.0.0.1:8765/mcp"
)
[IO.File]::WriteAllLines($RuntimeEnv, $lines, (New-Object Text.UTF8Encoding($false)))

$Principal = "$env:USERDOMAIN\$env:USERNAME"
& icacls.exe $ConfigDir /inheritance:r /grant:r "${Principal}:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to protect tunnel config directory ACL." }
& icacls.exe $RuntimeEnv /inheritance:r /grant:r "${Principal}:F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to protect tunnel credential file ACL." }

$env:CONTROL_PLANE_API_KEY = $ApiKey
try {
    & $TunnelClient init --force --sample sample_mcp_remote_no_auth --profile $Profile --tunnel-id $TunnelId --health-listen-addr "127.0.0.1:8766" --mcp-server-url "http://127.0.0.1:8765/mcp"
    if ($LASTEXITCODE -ne 0) { throw "tunnel-client init failed with exit code $LASTEXITCODE." }

    & $TunnelClient doctor --profile $Profile --explain
    if ($LASTEXITCODE -ne 0) { throw "tunnel-client doctor failed with exit code $LASTEXITCODE." }
}
finally {
    $env:CONTROL_PLANE_API_KEY = $null
    $ApiKey = $null
}

Write-Host ""
Write-Host "Tunnel configured."
Write-Host "Runtime config: $RuntimeEnv"
Write-Host "The normal START.cmd launcher will now start both bridge and tunnel."
