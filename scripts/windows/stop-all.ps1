$ErrorActionPreference = "Stop"
$stateDir = Join-Path $env:APPDATA "ChatGPT-Local-Bridge"

function Stop-OwnedProcess([string]$Name, [string]$Needle) {
    $pidPath = Join-Path $stateDir "$Name.pid"
    if (-not (Test-Path -LiteralPath $pidPath)) { return }

    $processId = 0
    if (-not [int]::TryParse((Get-Content -LiteralPath $pidPath -Raw).Trim(), [ref]$processId)) {
        Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
        return
    }

    $owned = $false
    try {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction Stop
        $owned = $process -and $process.CommandLine -and ($process.CommandLine.IndexOf($Needle, [StringComparison]::OrdinalIgnoreCase) -ge 0)
    }
    catch {}

    if ($owned) {
        & taskkill.exe /PID $processId /T /F | Out-Null
        Write-Host "Stopped $Name (PID $processId)"
    }
    else {
        Write-Warning "Ignored stale $Name PID file; the PID no longer belongs to this bridge."
    }

    Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
}

Stop-OwnedProcess "tunnel" "run-tunnel.ps1"
Stop-OwnedProcess "bridge" "bridge.app:app"
