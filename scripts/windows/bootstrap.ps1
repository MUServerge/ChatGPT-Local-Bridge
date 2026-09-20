param(
    [string]$ProjectRoot = "",
    [string]$ProjectId = "mu-rnd-5.2",
    [switch]$SkipTunnelInstall
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Join-Path $env:USERPROFILE "Desktop\MU-RND-5.2"
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "Project folder was not found: $ProjectRoot"
}
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path

function Find-Python {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) { return @($py.Source, "-3") }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { return @($python.Source) }

    throw "Python 3.11+ was not found. Install Python once, then run this launcher again."
}

$pythonCommand = Find-Python
$pythonExe = $pythonCommand[0]
$pythonPrefix = @()
if ($pythonCommand.Count -gt 1) { $pythonPrefix = $pythonCommand[1..($pythonCommand.Count - 1)] }

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating local Python environment..."
    & $pythonExe @pythonPrefix -m venv (Join-Path $repoRoot ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Failed to create virtual environment." }
}

Write-Host "Installing/updating bridge dependencies..."
& $venvPython -m pip install --disable-pip-version-check --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to update pip." }
& $venvPython -m pip install --disable-pip-version-check -r (Join-Path $repoRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Failed to install bridge dependencies." }

$envPath = Join-Path $repoRoot ".env"
$token = ""
if (Test-Path $envPath) {
    foreach ($line in Get-Content -LiteralPath $envPath) {
        if ($line -match '^BRIDGE_TOKEN=(.+)$') {
            $candidate = $matches[1].Trim().Trim('"')
            if ($candidate -and $candidate -ne "change-me-local") { $token = $candidate }
        }
    }
}

if ([string]::IsNullOrWhiteSpace($token)) {
    $bytes = New-Object byte[] 48
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $token = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
}

@(
    "BRIDGE_PROJECT_ID=$ProjectId"
    "BRIDGE_ROOT=$ProjectRoot"
    "BRIDGE_TOKEN=$token"
    "BRIDGE_ALLOW_WRITE=true"
    "BRIDGE_ALLOW_DELETE=false"
    "BRIDGE_ALLOW_COMMAND=false"
    "BRIDGE_COMMAND_ALLOWLIST="
    "BRIDGE_MAX_READ_BYTES=4194304"
    "BRIDGE_MAX_TEXT_BYTES=1048576"
    "BRIDGE_MAX_COMMAND_SECONDS=120"
    "BRIDGE_MAX_COMMAND_OUTPUT_BYTES=524288"
    "BRIDGE_AUDIT_LOG=$repoRoot\bridge-audit.log"
) | Set-Content -LiteralPath $envPath -Encoding UTF8

Write-Host "Configured allowed project: $ProjectRoot"

$localTunnel = Join-Path $env:LOCALAPPDATA "ChatGPT-Local-Bridge\tunnel-client\tunnel-client.exe"
if (-not $SkipTunnelInstall -and -not (Test-Path $localTunnel) -and -not (Get-Command tunnel-client -ErrorAction SilentlyContinue)) {
    try {
        Write-Host "Installing the Secure MCP Tunnel client..."
        & (Join-Path $PSScriptRoot "install-tunnel.ps1")
    }
    catch {
        Write-Warning "Tunnel client installation could not finish now: $($_.Exception.Message)"
        Write-Warning "The local filesystem bridge is still installed and will start normally."
    }
}

& (Join-Path $PSScriptRoot "register-autostart.ps1")
& (Join-Path $PSScriptRoot "start-background.ps1")

Write-Host ""
Write-Host "ChatGPT Local Bridge is installed and running."
Write-Host "Allowed root: $ProjectRoot"
Write-Host "Autostart: enabled for this Windows user"

$tunnelEnv = Join-Path $env:APPDATA "ChatGPT-Local-Bridge\tunnel.env"
if (-not (Test-Path $tunnelEnv)) {
    Write-Warning "Secure MCP Tunnel credentials are not configured yet. This is the only step that cannot be invented automatically. Run CONNECT CHATGPT.cmd once to enter the Tunnel ID and runtime API key."
}
