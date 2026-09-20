$ErrorActionPreference = "Stop"

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Repo ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run setup-local.bat first."
}

$HealthUrl = "http://127.0.0.1:8765/readyz"

$Bridge = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "bridge.app:app", "--host", "127.0.0.1", "--port", "8765" -WorkingDirectory $Repo -PassThru

try {
    $Ready = $false

    for ($Index = 0; $Index -lt 40; $Index++) {
        try {
            $Result = Invoke-RestMethod $HealthUrl -TimeoutSec 2

            if ($Result.ready) {
                $Ready = $true
                break
            }
        }
        catch {
        }

        Start-Sleep -Milliseconds 500
    }

    if (-not $Ready) {
        throw "Local MCP bridge did not become ready."
    }

    Write-Host "Local MCP bridge ready at http://127.0.0.1:8765/mcp"
    Write-Host "Starting Secure MCP Tunnel..."
    & (Join-Path $PSScriptRoot "run-tunnel.ps1")
}
finally {
    if ($Bridge -and -not $Bridge.HasExited) {
        Stop-Process -Id $Bridge.Id -Force
    }
}
