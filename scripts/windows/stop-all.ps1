$ErrorActionPreference = "Stop"
$stateDir = Join-Path $env:APPDATA "ChatGPT-Local-Bridge"
foreach ($name in @("tunnel", "bridge")) {
    $pidPath = Join-Path $stateDir "$name.pid"
    if (Test-Path $pidPath) {
        $processId = 0
        [void][int]::TryParse((Get-Content -LiteralPath $pidPath -Raw).Trim(), [ref]$processId)
        if ($processId -gt 0) {
            $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                Write-Host "Stopped $name (PID $processId)"
            }
        }
        Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
    }
}
