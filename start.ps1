<#
.SYNOPSIS
    Start the meta_mcp stack: backend (uvicorn, :10718) + frontend
    (Vite, :10719) with port-zombie clearing and auto-open browser.

.DESCRIPTION
    1. Kills port squatters on 10718/10719
    2. Starts the backend via FleetStartMode helpers
    3. Starts the Vite frontend in web_sota
    4. Opens the browser when the frontend responds

.PARAMETER Headless
    Start hidden (no console window).

.PARAMETER NoBrowser
    Do not auto-open the browser.

.EXAMPLE
    .\start.ps1
    .\start.ps1 -Headless -NoBrowser
#>
Param([switch]$Headless, [switch]$NoBrowser)

# --- SOTA Headless Standard ---
if ($Headless -and ($Host.UI.RawUI.WindowTitle -notmatch 'Hidden')) {
    Start-Process pwsh -ArgumentList '-NoProfile', '-File', $PSCommandPath, '-Headless' -WindowStyle Hidden
    exit
}
$WindowStyle = if ($Headless) { 'Hidden' } else { 'Normal' }
# ------------------------------

$env:FASTMCP_LOG_LEVEL = 'WARNING'
$WebPort = 10719
$BackendPort = 10718
$FleetStartPath = Join-Path $ProjectRoot "scripts\FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $FleetStartPath)) {
    Write-Host "ERROR: Missing vendored launcher helper: $FleetStartPath" -ForegroundColor Red
    exit 1
}
. $FleetStartPath


Write-Host 'Starting meta_mcp...' -ForegroundColor Cyan

# 1. Kill port squatters
Write-Host "Checking for port squatters on $BackendPort and $WebPort..." -ForegroundColor Yellow
$pids = Get-NetTCPConnection -LocalPort $BackendPort, $WebPort -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 4 } | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($p in $pids) {
    Write-Host "Found squatter (PID: $p). Terminating..." -ForegroundColor Red
    try { Stop-Process -Id $p -Force -ErrorAction Stop } catch { Write-Host "Warning: Could not terminate PID $p." -ForegroundColor Gray }
}

# 2. Launch backend
Set-Location $PSScriptRoot
Write-Host "Starting backend on port $BackendPort ..." -ForegroundColor Green
Start-Process pwsh -ArgumentList '-NoProfile', '-Command', "uv run -m meta_mcp $BackendPort" -WindowStyle Hidden

# 3. Launch frontend
Set-Location web_sota
Write-Host "Starting frontend on port $WebPort ..." -ForegroundColor Cyan

# 4. Auto-open browser when frontend is ready
$frontendUrl = "http://127.0.0.1:$WebPort/"
if (-not $NoBrowser) {
    $pollAndOpen = "for (`$i = 0; `$i -lt 60; `$i++) { try { `$null = Invoke-WebRequest -Uri '$frontendUrl' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; Start-Process '$frontendUrl'; exit } catch { Start-Sleep -Seconds 1 } }"
    Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Hidden", "-Command", $pollAndOpen
    Write-Host "Browser will open automatically when Vite is ready." -ForegroundColor Gray
}
npm run dev -- --port $WebPort --host
