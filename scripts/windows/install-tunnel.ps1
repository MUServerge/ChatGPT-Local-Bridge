$ErrorActionPreference = "Stop"

$Release = Invoke-RestMethod -Headers @{ "User-Agent" = "ChatGPT-Local-Bridge" } "https://api.github.com/repos/openai/tunnel-client/releases/latest"
$Asset = $Release.assets | Where-Object { $_.name -match "^tunnel-client-v.*-windows-amd64\.zip$" } | Select-Object -First 1

if (-not $Asset) {
    throw "Could not find the official Windows amd64 tunnel-client asset."
}

$Expected = [string]$Asset.digest

if (-not $Expected.StartsWith("sha256:")) {
    throw "Latest tunnel-client release did not publish a SHA-256 digest."
}

$ExpectedHash = $Expected.Substring(7).ToLowerInvariant()
$InstallDir = Join-Path $env:LOCALAPPDATA "ChatGPT-Local-Bridge\tunnel-client"
$TempRoot = Join-Path $env:TEMP ("chatgpt-local-bridge-" + [Guid]::NewGuid().ToString("N"))
$Zip = Join-Path $TempRoot $Asset.name
$Extract = Join-Path $TempRoot "extract"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $Extract | Out-Null

try {
    Write-Host ("Downloading official OpenAI tunnel-client " + $Release.tag_name + "...")
    Invoke-WebRequest -UseBasicParsing -Uri $Asset.browser_download_url -OutFile $Zip

    $ActualHash = (Get-FileHash -Algorithm SHA256 $Zip).Hash.ToLowerInvariant()

    if ($ActualHash -ne $ExpectedHash) {
        throw "SHA-256 verification failed."
    }

    Expand-Archive -Path $Zip -DestinationPath $Extract -Force
    $Exe = Get-ChildItem -Path $Extract -Filter "tunnel-client.exe" -Recurse | Select-Object -First 1

    if (-not $Exe) {
        throw "tunnel-client.exe was not found in the official archive."
    }

    Copy-Item $Exe.FullName (Join-Path $InstallDir "tunnel-client.exe") -Force

    Write-Host "Installed:"
    Write-Host (Join-Path $InstallDir "tunnel-client.exe")
    Write-Host ("Verified SHA-256: " + $ActualHash)
}
finally {
    if (Test-Path $TempRoot) {
        Remove-Item $TempRoot -Recurse -Force
    }
}
