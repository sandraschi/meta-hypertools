param(
    [string]$Title = "Fleet Webapp Demo",
    [string]$Subtitle = "",
    [string]$Output = "..\..\docs\screenshots\demo.mp4"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path "public\source.webm")) {
    throw "public\source.webm not found - run demo_ops record first or copy a Playwright .webm here"
}

if (-not (Test-Path "node_modules")) {
    npm install
}

$props = @{ title = $Title; subtitle = $Subtitle } | ConvertTo-Json -Compress
npx remotion render src/index.ts DemoComposition $Output --props=$props
