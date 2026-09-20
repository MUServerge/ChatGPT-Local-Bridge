$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Bridge is not installed. Run INSTALL AND START.cmd first." }

$stateDir = Join-Path $env:APPDATA "ChatGPT-Local-Bridge"
$logDir = Join-Path $stateDir "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-BridgeReady {
    try {
        $health = Invoke-RestMethod "http://127.0.0.1:8765/health" -TimeoutSec 2
        return [bool]$health.ok
    }
    catch { return $false }
}

function Test-OwnedProcess([string]$PidPath, [string]$Needle) {
    if (-not (Test-Path -LiteralPath $PidPath)) { return $false }

    $processId = 0
    if (-not [int]::TryParse((Get-Content -LiteralPath $PidPath -Raw).Trim(), [ref]$processId)) {
        Remove-Item -LiteralPath $PidPath -Force -ErrorAction SilentlyContinue
        return $false
    }

    try {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction Stop
        if ($process -and $process.CommandLine -and $process.CommandLine.IndexOf($Needle, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
            return $true
        }
    }
    catch {}

    Remove-Item -LiteralPath $PidPath -Force -ErrorAction SilentlyContinue
    return $false
}

$bridgePidPath = Join-Path $stateDir "bridge.pid"
if (-not (Test-BridgeReady)) {
    if (Test-OwnedProcess $bridgePidPath "bridge.app:app") {
        for ($i = 0; $i -lt 20; $i++) {
            Start-Sleep -Milliseconds 250
            if (Test-BridgeReady) { break }
        }
    }

    if (-not (Test-BridgeReady)) {
        $stdout = Join-Path $logDir "bridge.out.log"
        $stderr = Join-Path $logDir "bridge.err.log"
        $serverArgs = @("-m", "uvicorn", "bridge.app:app", "--host", "127.0.0.1", "--port", "8765")
        $server = Start-Process -FilePath $python -ArgumentList $serverArgs -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        Set-Content -LiteralPath $bridgePidPath -Value $server.Id -Encoding ASCII

        $ready = $false
        for ($i = 0; $i -lt 40; $i++) {
            Start-Sleep -Milliseconds 250
            if (Test-BridgeReady) { $ready = $true; break }
            if ($server.HasExited) { break }
        }
        if (-not $ready) {
            throw "Bridge failed to start. See $stderr"
        }
    }
}

$tunnelEnv = Join-Path $stateDir "tunnel.env"
$tunnelPidPath = Join-Path $stateDir "tunnel.pid"
if (Test-Path $tunnelEnv) {
    $tunnelReady = $false
    try {
        Invoke-RestMethod "http://127.0.0.1:8766/readyz" -TimeoutSec 2 | Out-Null
        $tunnelReady = $true
    }
    catch {}

    if (-not $tunnelReady -and -not (Test-OwnedProcess $tunnelPidPath "run-tunnel.ps1")) {
        $runTunnel = Join-Path $PSScriptRoot "run-tunnel.ps1"
        $stdout = Join-Path $logDir "tunnel.out.log"
        $stderr = Join-Path $logDir "tunnel.err.log"
        $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runTunnel`""
        $tunnel = Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        Set-Content -LiteralPath $tunnelPidPath -Value $tunnel.Id -Encoding ASCII
    }
}

Write-Host "Bridge ready: http://127.0.0.1:8765/health"
