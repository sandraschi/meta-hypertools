Write-Host "Restarting MetaMCP..." -ForegroundColor Yellow
$StartScript = Join-Path $PSScriptRoot "start.ps1"
& $StartScript

