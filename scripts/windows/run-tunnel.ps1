$ErrorActionPreference = "Stop"

$RuntimeEnv = Join-Path $env:APPDATA "ChatGPT-Local-Bridge\tunnel.env"

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

if (-not (Get-Command tunnel-client -ErrorAction SilentlyContinue)) {
    throw "tunnel-client was not found on PATH."
}

if ([string]::IsNullOrWhiteSpace($env:TUNNEL_PROFILE)) {
    throw "TUNNEL_PROFILE is missing from tunnel.env."
}

tunnel-client run --profile $env:TUNNEL_PROFILE
