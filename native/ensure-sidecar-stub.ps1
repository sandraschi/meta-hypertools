#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$triple = "x86_64-pc-windows-msvc"
$dstDir = "$PSScriptRoot\binaries"
$dst = "$dstDir\meta_mcp-backend-$triple.exe"
$built = "$Root\dist\meta_mcp-backend.exe"

if (Test-Path $dst) { exit 0 }
New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
if (Test-Path $built) {
    Copy-Item $built $dst -Force
    exit 0
}
Copy-Item "$env:SystemRoot\System32\cmd.exe" $dst -Force
Write-Warning "Stub sidecar only. Run: just build-native"
