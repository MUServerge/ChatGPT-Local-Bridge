$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$startupDir = [Environment]::GetFolderPath("Startup")
if ([string]::IsNullOrWhiteSpace($startupDir)) { throw "Windows Startup folder could not be resolved." }

$launcher = Join-Path $startupDir "ChatGPT Local Bridge.cmd"
$startScript = Join-Path $repoRoot "scripts\windows\start-background.ps1"
@(
    "@echo off"
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \`"$startScript\`""
) | Set-Content -LiteralPath $launcher -Encoding ASCII
Write-Host "Autostart registered: $launcher"
