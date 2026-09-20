$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Virtual environment not found. Run setup-local.bat first."
}

$serverArgs = @("-m", "uvicorn", "bridge.app:app", "--host", "127.0.0.1", "--port", "8765")
$server = Start-Process -FilePath $python -ArgumentList $serverArgs -WorkingDirectory $repoRoot -PassThru

try {
    $ready = $false

    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500

        try {
            $health = Invoke-RestMethod "http://127.0.0.1:8765/health"

            if ($health.ok) {
                $ready = $true
                break
            }
        }
        catch {
        }
    }

    if (-not $ready) {
        throw "Local bridge did not become ready on 127.0.0.1:8765."
    }

    Write-Host "Local bridge is ready."
    & (Join-Path $PSScriptRoot "run-tunnel.ps1")
}
finally {
    if (-not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
}
