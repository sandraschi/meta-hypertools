<#
.SYNOPSIS
  Run MCP stdio initialize smoke via stdio_mcp_smoke.py.
#>
function Resolve-FleetPythonExe {
    $pyExe = $env:FLEET_PYTHON_EXE
    if ($pyExe -and (Test-Path -LiteralPath $pyExe)) { return $pyExe }
    if (Get-Command python -ErrorAction SilentlyContinue) { return (Get-Command python).Source }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $resolved = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($resolved -and (Test-Path -LiteralPath $resolved.Trim())) { return $resolved.Trim() }
    }
    return "python"
}

function Invoke-FleetStdioMcpSmoke {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [string[]]$SmokeArgs = @(),
        [hashtable]$Env = @{},
        [string]$WorkingDirectory = "",
        [int]$TimeoutSec = 10
    )

    $ErrorActionPreference = "Stop"
    $pyScript = Join-Path (Split-Path -Parent $PSCommandPath) "stdio_mcp_smoke.py"
    if (-not (Test-Path -LiteralPath $pyScript)) {
        return @{ ok = $false; error = "Missing $pyScript"; log = "" }
    }

    $pyExe = Resolve-FleetPythonExe
    $argList = @($pyScript, "--timeout", "$TimeoutSec")
    if ($WorkingDirectory) { $argList += @("--cwd", $WorkingDirectory) }
    foreach ($k in $Env.Keys) {
        $argList += @("--env", "$k=$($Env[$k])")
    }
    $argList += @("--", $Command) + $SmokeArgs

    $outFile = [System.IO.Path]::GetTempFileName()
    $errFile = [System.IO.Path]::GetTempFileName()
    $waitMs = ([int]$TimeoutSec + 20) * 1000

    $prevEnv = @{}
    foreach ($k in $Env.Keys) {
        $prevEnv[$k] = [Environment]::GetEnvironmentVariable($k, 'Process')
        [Environment]::SetEnvironmentVariable($k, [string]$Env[$k], 'Process')
    }
    try {
        $psi = @{
            FilePath               = $pyExe
            ArgumentList           = $argList
            NoNewWindow            = $true
            PassThru               = $true
            RedirectStandardOutput = $outFile
            RedirectStandardError  = $errFile
        }
        if ($WorkingDirectory) { $psi.WorkingDirectory = $WorkingDirectory }
        $p = Start-Process @psi
        if (-not $p.WaitForExit($waitMs)) {
            # TREE kill: $p.Kill() alone orphans the smoke helper's children
            # (uv.exe AND the server python). .NET Framework Process.Kill()
            # has no tree overload, so use taskkill /T /F.
            try { & taskkill /T /F /PID $p.Id 2>$null | Out-Null } catch { }
            try { $p.Kill() } catch { }
            return @{ ok = $false; error = "Smoke helper timed out after ${waitMs}ms"; log = "" }
        }
        $stdout = if (Test-Path -LiteralPath $outFile) { Get-Content -LiteralPath $outFile -Raw } else { "" }
        $stderr = if (Test-Path -LiteralPath $errFile) { Get-Content -LiteralPath $errFile -Raw } else { "" }
        try {
            $parsed = $stdout | ConvertFrom-Json
            return @{
                ok       = [bool]$parsed.ok
                error    = if ($parsed.error) { [string]$parsed.error } else { "" }
                log      = if ($parsed.log) { [string]$parsed.log } else { $stderr }
                response = $parsed.response
            }
        } catch {
            return @{ ok = $false; error = $_.Exception.Message; log = "$stdout`n$stderr" }
        }
    } finally {
        foreach ($k in $prevEnv.Keys) {
            if ($null -eq $prevEnv[$k]) {
                [Environment]::SetEnvironmentVariable($k, $null, 'Process')
            } else {
                [Environment]::SetEnvironmentVariable($k, $prevEnv[$k], 'Process')
            }
        }
        Remove-Item -LiteralPath $outFile -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $errFile -Force -ErrorAction SilentlyContinue
    }
}
