<#
.SYNOPSIS
    Kill zombie processes on the meta_mcp ports and by process pattern.

.DESCRIPTION
    1. Kills any process listening on ports 10718/10719 (fleet registry).
    2. Kills processes matching *meta_mcp*, *uvicorn*, *watchfiles*,
       *vite*, *node* by command line, name, or path.
    Run before starting the stack so start.ps1 binds cleanly.

.EXAMPLE
    .\scripts\kill-zombies.ps1

.NOTES
    Runs via `just cleanup`. Only touches fleet dev processes.
#>
$ports = @(10718, 10719)
$repoRoot = (Split-Path -Parent $PSScriptRoot)

Write-Host "🧟 Checking for zombie processes on ports $ports..." -ForegroundColor Cyan

# 1. Kill by port (Listener focus with process tree termination)
foreach ($port in $ports) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" -and $_.OwningProcess -gt 4 }
        if ($conns) {
            foreach ($conn in $conns) {
                $procId = $conn.OwningProcess
                $process = Get-Process -Id $procId -ErrorAction SilentlyContinue
                if ($process) {
                    Write-Host "💥 Terminating squatter: $($process.ProcessName) (PID: $procId) on port $port" -ForegroundColor Red
                    taskkill.exe /F /T /PID $procId 2>$null | Out-Null
                }
            }
        }
    }
    catch {
        Write-Host "⚠️ Error checking port $port" -ForegroundColor Yellow
    }
}

# 2. Kill by repo path (Target only processes spawned for this repo)
try {
    $repoWmiProcs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and ($_.CommandLine -like "*$repoRoot*" -or $_.CommandLine -like "*meta_mcp*") -and
        $_.ProcessId -ne $PID
    }
    foreach ($p in $repoWmiProcs) {
        try {
            Write-Host "💨 Cleaning up $($p.Name) (PID: $($p.ProcessId)) matching repo context" -ForegroundColor Red
            taskkill.exe /F /T /PID $p.ProcessId 2>$null | Out-Null
        }
        catch { }
    }
}
catch { }

Write-Host "✨ Ready for a clean start." -ForegroundColor Green

