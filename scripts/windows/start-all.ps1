$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "start-background.ps1")
& (Join-Path $PSScriptRoot "status.ps1")
