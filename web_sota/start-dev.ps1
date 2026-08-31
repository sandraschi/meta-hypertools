Write-Host "Starting MetaMCP Development Environment..." -ForegroundColor Magenta

$WebSotaDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $WebSotaDir

# 1. Kill Zombies (ports 10718, 10719 per WEBAPP_PORTS.md)
$KillScript = Join-Path $RepoRoot "scripts\kill-zombies.ps1"
if (Test-Path $KillScript) {
    & $KillScript
}

# 2. Start Backend (Port 10718)
Write-Host "Starting Backend on Port 10718..." -ForegroundColor Green
$backendCmd = "Set-Location '$RepoRoot'; `$env:PYTHONPATH = 'src'; uv run uvicorn meta_mcp.main:create_fastapi_app --factory --reload --host 127.0.0.1 --port 10718"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# 3. Start Frontend (Port 10719)
Write-Host "Starting Frontend on Port 10719..." -ForegroundColor Cyan
$frontendCmd = "Set-Location '$WebSotaDir'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "Dev environment started." -ForegroundColor Green
Write-Host "Webapp: http://localhost:10719"
Write-Host "Backend: http://localhost:10718"
