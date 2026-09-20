param(
    [string]$LocalUrl = "http://127.0.0.1:8765",
    [string]$RelayUrl = ""
)

$ErrorActionPreference = "Stop"

Write-Host "Checking local bridge..."
$local = Invoke-RestMethod "$LocalUrl/health"

if (-not $local.ok) {
    throw "Local bridge health check failed."
}

Write-Host "Local bridge OK."
Write-Host ("Projects: " + ($local.projects -join ", "))

if ($RelayUrl) {
    $relayBase = $RelayUrl.TrimEnd("/")
    Write-Host "Checking relay..."
    $relay = Invoke-RestMethod "$relayBase/healthz"

    if (-not $relay.ok) {
        throw "Relay health check failed."
    }

    Write-Host "Relay OK."

    if ($relay.machines.Count -eq 0) {
        Write-Warning "Relay is healthy, but no local agent is connected."
    }
    else {
        foreach ($machine in $relay.machines) {
            Write-Host ("Machine: " + $machine.machine)
            Write-Host ("Projects: " + ($machine.projects -join ", "))
        }
    }
}
