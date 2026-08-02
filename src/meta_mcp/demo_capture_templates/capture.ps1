param(
    [switch]$Screenshots,
    [switch]$Video,
    [string]$E2eDir = "."
)

$ErrorActionPreference = "Stop"
Set-Location $E2eDir

if (-not (Test-Path "config.json")) {
    throw "config.json not found in $E2eDir"
}

$targets = @()
if ($Screenshots) { $targets += "demo-screenshots.ts" }
if ($Video) { $targets += "demo-video.ts" }
if ($targets.Count -eq 0) {
    $targets = @("demo-screenshots.ts", "demo-video.ts")
}

npx playwright test $targets --config playwright.demo.config.ts
