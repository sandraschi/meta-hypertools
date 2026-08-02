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
$patterns = @("*meta_mcp*", "*uvicorn*", "*watchfiles*", "*vite*", "*node*")

Write-Host "🧟 Checking for zombie processes on ports $ports..." -ForegroundColor Cyan

# 1. Kill by port (Listener focus)
foreach ($port in $ports) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
        if ($conns) {
            foreach ($conn in $conns) {
                $procId = $conn.OwningProcess
                if ($procId -gt 0) {
                    $process = Get-Process -Id $procId -ErrorAction SilentlyContinue
                    if ($process) {
                        Write-Host "💥 Terminating squatter: $($process.ProcessName) (PID: $procId) on port $port" -ForegroundColor Red
                        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                    }
                }
            }
        }
    }
    catch {
        Write-Host "⚠️ Error checking port $port" -ForegroundColor Yellow
    }
}

# 2. Kill by pattern (General cleanup)
foreach ($pattern in $patterns) {
    $processes = Get-Process | Where-Object { $_.CommandLine -like $pattern -or $_.ProcessName -like $pattern -or $_.Path -like $pattern } -ErrorAction SilentlyContinue
    if ($processes) {
        foreach ($p in $processes) {
            try {
                $id = $p.Id
                $name = $p.ProcessName
                Write-Host "💨 Cleaning up $name (PID: $id) matching '$pattern'" -ForegroundColor Red
                Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
            }
            catch { }
        }
    }
}

Write-Host "✨ Ready for a clean start." -ForegroundColor Green

