<#
.SYNOPSIS
  Cold-start each fleet webapp: parse-check start.ps1, probe backend + frontend + proxy, report.
.DESCRIPTION
  Reads scripts/fleet-webapp-manifest.json. Per entry:
  1) PowerShell parse-check on start script (catches instacrash before run)
  2) Start start.ps1 in background
  3) Backend health on port + healthPath
  4) Optional frontendPort + frontendPath (Vite up)
  5) Optional proxyHealthPath via frontend (backend connected through Vite proxy)
  6) When -RepoFilter is set: extra SPA route checks (frontendRoutes / probe-routes.json) for 404
  Writes scripts/out/fleet-webapp-report.json and .progress.json after each repo.
.EXAMPLE
  .\scripts\fleet-webapp-start-probe.ps1
  .\scripts\fleet-webapp-start-probe.ps1 -RepoFilter toolbench-mcp
#>
[CmdletBinding()]
param(
    [string]$ManifestPath = "scripts/fleet-webapp-manifest.json",
    [string]$ReportDir = "scripts/out",
    [int]$LogTailLines = 80,
    [string]$RepoFilter = "",
    [int]$CooldownBetweenSec = 5,
    [string[]]$ExcludeRepos = @("meta_mcp"),
    [switch]$IncludeProbeHost,
    [switch]$BrokenOnly
)

$ErrorActionPreference = "Stop"
$reposRoot = if ($env:FLEET_REPOS_ROOT) { $env:FLEET_REPOS_ROOT } else { "D:\Dev\repos" }

# Do not inherit MetaMCP / IDE Python env into probed repo start.ps1 children.
Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
Remove-Item Env:UV_PROJECT_ENVIRONMENT -ErrorAction SilentlyContinue

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
if (-not (Test-Path $repoRoot)) { $repoRoot = Get-Location }
$fleetStartMode = Join-Path $scriptRoot "FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $fleetStartMode)) {
    Write-Error "Missing FleetStartMode.ps1 beside probe script: $fleetStartMode"
    exit 1
}
. $fleetStartMode
$manifestFull = Join-Path $repoRoot $ManifestPath
$reportDirFull = Join-Path $repoRoot $ReportDir

if (-not (Test-Path $manifestFull)) {
    Write-Error "Manifest not found: $manifestFull"
    exit 1
}

function Test-StartScriptParses {
    param([string]$Path)
    $tokens = $null
    $errs = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errs)
    if ($errs -and $errs.Count -gt 0) {
        return @{ ok = $false; errors = @($errs | ForEach-Object { $_.ToString() }) }
    }
    return @{ ok = $true; errors = @() }
}

function Test-StartScriptRootOrder {
    param([string]$Path)
    $lines = Get-Content -LiteralPath $Path -Encoding UTF8
    $fleetLine = -1
    $rootLine = -1
    $rootVar = ""
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($line -match 'Join-Path\s+\$(ProjectRoot|RepoRoot)\s+[''"]scripts\\FleetStartMode') {
            $fleetLine = $i + 1
            $rootVar = $Matches[1]
        }
        if ($line -match '^\s*\$(ProjectRoot|RepoRoot)\s*=') {
            if ($rootLine -lt 0) { $rootLine = $i + 1 }
        }
    }
    if ($fleetLine -lt 0) {
        return @{ ok = $true; message = ""; line = $null; rootVar = "" }
    }
    if ($rootLine -lt 0 -or $rootLine -gt $fleetLine) {
        $msg = "At line ${fleetLine}: Join-Path `$$rootVar before `$$rootVar is assigned (FleetStartMode may resolve to fleet root\scripts\... instead of repo\scripts\...)"
        return @{ ok = $false; message = $msg; line = $fleetLine; rootVar = $rootVar }
    }
    return @{ ok = $true; message = ""; line = $null; rootVar = $rootVar }
}

function Get-ProbeSummaryCounts {
    param($ResultRows)
    return @{
        total             = @($ResultRows).Count
        stack_ok          = @($ResultRows | Where-Object { $_.outcome -eq "stack_ok" }).Count
        backend_ok        = @($ResultRows | Where-Object { $_.outcome -eq "backend_ok" }).Count
        parse_failed      = @($ResultRows | Where-Object { $_.outcome -eq "parse_failed" }).Count
        root_order_failed = @($ResultRows | Where-Object { $_.outcome -eq "root_order_failed" }).Count
        start_failed      = @($ResultRows | Where-Object { $_.outcome -eq "start_failed" }).Count
        skip              = @($ResultRows | Where-Object { $_.outcome -eq "skip" }).Count
        teardown_fail     = @($ResultRows | Where-Object { $_.teardownOk -eq $false }).Count
        pages_404         = @($ResultRows | Where-Object { $_.outcome -eq "pages_404" }).Count
        stack_degraded    = @($ResultRows | Where-Object { $_.outcome -eq "stack_degraded" }).Count
        dirty_log         = @($ResultRows | Where-Object { $_.dirtyLogOk -eq $false }).Count
    }
}

function Invoke-FleetProbePortSweep {
    param(
        [int[]]$Ports,
        [string]$Label = "probe"
    )
    $unique = @($Ports | Where-Object { $_ -gt 0 } | Sort-Object -Unique)
    if ($unique.Count -eq 0) { return @() }
    Stop-FleetPortSquatters -Ports $unique -Label $Label
    Start-Sleep -Milliseconds 500
    Stop-FleetPortSquatters -Ports $unique -Label "$Label-retry"
    Start-Sleep -Milliseconds 200
    $still = Get-FleetPortsStillListening -Ports $unique
    $stillPids = @()
    foreach ($entry in $still.GetEnumerator()) {
        foreach ($procId in $entry.Value) {
            $stillPids += "$($entry.Key):$procId"
        }
    }
    return @{
        portsClear     = ($still.Count -eq 0)
        stillListening = @($still.Keys | Sort-Object)
        stillPids      = $stillPids
    }
}

function Get-FleetProbeCapturedLogs {
    param([string]$LogDir, [int]$Tail = 120)
    if (-not $LogDir -or -not (Test-Path -LiteralPath $LogDir)) { return "" }
    $chunks = [System.Collections.Generic.List[string]]::new()
    Get-ChildItem -LiteralPath $LogDir -Filter "*.log" -ErrorAction SilentlyContinue | Sort-Object Name | ForEach-Object {
        $lines = @(Get-Content -LiteralPath $_.FullName -Tail $Tail -ErrorAction SilentlyContinue)
        if ($lines.Count -gt 0) {
            [void]$chunks.Add("--- $($_.Name) ---")
            [void]$chunks.AddRange($lines)
        }
    }
    return ($chunks -join [Environment]::NewLine)
}

function Test-FleetDirtyLog {
    param(
        [string]$LogText,
        [string[]]$ExtraIssues = @()
    )
    $issues = [System.Collections.Generic.List[string]]::new()
    foreach ($extra in $ExtraIssues) {
        if ($extra -and -not $issues.Contains($extra)) { [void]$issues.Add($extra) }
    }
    if (-not $LogText) {
        return @{
            issues     = @($issues)
            dirtyLogOk = ($issues.Count -eq 0)
            dirtyLog   = ""
        }
    }
    $httpPatterns = @(
        '(?:HTTP\s+|returned\s+HTTP\s+|status(?:\s*code)?\s*[=:]?\s*|Status\s+)(4\d{2}|5\d{2})\b',
        '(?i)(?:error|failed|exception).{0,60}\b(4\d{2}|5\d{2})\b',
        '(?i)\b(4\d{2}|5\d{2})\s+(?:Not Found|Forbidden|Unauthorized|Internal Server Error|Bad Gateway|Service Unavailable)'
    )
    $warnPatterns = @(
        'STARTUP PROBE:.*(?:missing|unreachable|timed out|degraded|fall back|not configured|returned HTTP)',
        'RAG enabled but missing packages',
        'semantic/hybrid search will fall back',
        'WARNING:.*OpenAPI schema has no paths',
        '^\s*WARN:',
        '^\[.*\]\s*WARN:',
        'WARNING - arxiv_mcp\.startup_probe',
        '(?i)http proxy error',
        'ECONNREFUSED',
        'Port \d+ is already in use'
    )
    foreach ($line in ($LogText -split "`r?`n")) {
        $trim = $line.Trim()
        if (-not $trim) { continue }
        $matched = $false
        foreach ($pat in $httpPatterns) {
            if ($trim -match $pat) {
                $code = if ($Matches[1]) { $Matches[1] } else { "?" }
                $snippet = if ($trim.Length -gt 100) { $trim.Substring(0, 100) + "..." } else { $trim }
                $msg = "HTTP $code  --  $snippet"
                if (-not $issues.Contains($msg)) { [void]$issues.Add($msg) }
                $matched = $true
                break
            }
        }
        if ($matched) { continue }
        foreach ($pat in $warnPatterns) {
            if ($trim -match $pat) {
                if (-not $issues.Contains($trim)) { [void]$issues.Add($trim) }
                break
            }
        }
    }
    $dirtyLog = ""
    if ($issues.Count -gt 0) {
        $httpHits = @($issues | Where-Object { $_ -like 'HTTP *' }).Count
        $parts = [System.Collections.Generic.List[string]]::new()
        if ($httpHits -gt 0) { [void]$parts.Add("HTTP ${httpHits}x") }
        if ($issues.Count -gt $httpHits) { [void]$parts.Add("warn $($issues.Count - $httpHits)x") }
        $preview = ($issues | Select-Object -First 2) -join "; "
        if ($preview.Length -gt 90) { $preview = $preview.Substring(0, 90) + "..." }
        $dirtyLog = "$(($parts -join ', ')): $preview"
    }
    return @{
        issues     = @($issues)
        dirtyLogOk = ($issues.Count -eq 0)
        dirtyLog   = $dirtyLog
    }
}

function Invoke-FleetPostStackApiChecks {
    param(
        [string]$Repo,
        [int]$Port,
        [string]$HealthPath
    )
    $issues = [System.Collections.Generic.List[string]]::new()
    if ($Repo -eq 'arxiv-mcp' -and $Port -gt 0) {
        $capUri = "http://127.0.0.1:$Port/api/capabilities"
        try {
            $resp = Invoke-RestMethod -Uri $capUri -TimeoutSec 8 -ErrorAction Stop
            $ragOk = $resp.features.rag_available
            if ($resp.features.rag_enabled -and -not $ragOk) {
                [void]$issues.Add("API: rag_enabled=true but rag_available=false (uv sync --extra rag)")
            }
        } catch {
            [void]$issues.Add("API: capabilities check failed ($($_.Exception.Message))")
        }
    }
    return @($issues)
}

function Build-ProbeComparison {
    param($PriorReport, $CurrentRows, [string]$ProbeMode, [int]$ReposProbed)
    if (-not $PriorReport) { return $null }
    $priorRows = @($PriorReport.results)
    $priorSummary = if ($PriorReport.summary) { $PriorReport.summary } else { Get-ProbeSummaryCounts -ResultRows $priorRows }
    $nowSummary = Get-ProbeSummaryCounts -ResultRows $CurrentRows
    $parsePrior = [int]($priorSummary.parse_failed)
    if ($priorSummary.PSObject.Properties.Name -contains "parse_failed" -and $null -ne $priorSummary.parse_failed) {
        $parsePrior = [int]$priorSummary.parse_failed
    }
    $parseNow = [int]$nowSummary.parse_failed
    $rootPrior = 0
    if ($priorSummary.PSObject.Properties.Name -contains "root_order_failed") {
        $rootPrior = [int]$priorSummary.root_order_failed
    } else {
        $rootPrior = @($priorRows | Where-Object { $_.outcome -eq "root_order_failed" }).Count
    }
    $rootNow = [int]$nowSummary.root_order_failed
    return @{
        priorGeneratedAt    = $PriorReport.generatedAt
        probeMode           = $ProbeMode
        reposProbed         = $ReposProbed
        parse_failed_prior  = $parsePrior
        parse_failed_now    = $parseNow
        parse_failed_delta  = $parseNow - $parsePrior
        root_order_failed_prior = $rootPrior
        root_order_failed_now   = $rootNow
        root_order_failed_delta = $rootNow - $rootPrior
    }
}

function Write-ProbeMarkdownReport {
    param(
        $ResultRows,
        [string]$GeneratedAt,
        [string]$ReposRoot,
        $Summary,
        $Comparison,
        [string]$ReportPath
    )
    $lines = [System.Collections.Generic.List[string]]::new()
    [void]$lines.Add("# Fleet cold-start probe report")
    [void]$lines.Add("")
    [void]$lines.Add("Generated: $GeneratedAt")
    [void]$lines.Add("Repos root: $ReposRoot")
    if ($Comparison) {
        $delta = $Comparison.parse_failed_delta
        $deltaLabel = if ($delta -lt 0) { "$delta" } elseif ($delta -gt 0) { "+$delta" } else { "0" }
        [void]$lines.Add("Parse failures: $($Comparison.parse_failed_now) (was $($Comparison.parse_failed_prior), $deltaLabel since prior run)")
        if ($Comparison.root_order_failed_now -gt 0 -or $Comparison.root_order_failed_prior -gt 0) {
            $rd = $Comparison.root_order_failed_delta
            $rdLabel = if ($rd -lt 0) { "$rd" } elseif ($rd -gt 0) { "+$rd" } else { "0" }
            [void]$lines.Add("Root-order failures: $($Comparison.root_order_failed_now) (was $($Comparison.root_order_failed_prior), $rdLabel since prior run)")
        }
        if ($Comparison.probeMode -eq "broken_only") {
            [void]$lines.Add("Mode: broken_only ($($Comparison.reposProbed) repos re-probed; prior rows merged for fleet-wide summary)")
        }
    }
    [void]$lines.Add("")
    [void]$lines.Add("## Summary")
    [void]$lines.Add("")
    [void]$lines.Add("| Metric | Count |")
    [void]$lines.Add("| --- | ---: |")
    foreach ($key in @("total", "stack_ok", "stack_degraded", "backend_ok", "parse_failed", "root_order_failed", "start_failed", "skip", "teardown_fail", "pages_404", "dirty_log")) {
        if ($Summary.PSObject.Properties.Name -contains $key) {
            [void]$lines.Add("| $key | $($Summary.$key) |")
        }
    }
    [void]$lines.Add("")
    [void]$lines.Add("## Results")
    [void]$lines.Add("")
    [void]$lines.Add("| Repo | Outcome | Backend | Frontend | Proxy | Teardown | Dirty log | Error |")
    [void]$lines.Add("| --- | --- | :---: | :---: | :---: | :---: | --- | --- |")
    foreach ($r in $ResultRows) {
        $be = if ($r.backendOk -eq $true) { "yes" } elseif ($r.backendOk -eq $false) { "no" } else { "" }
        $fe = if ($r.frontendOk -eq $true) { "yes" } elseif ($r.frontendOk -eq $false) { "no" } else { "" }
        $px = if ($r.proxyOk -eq $true) { "yes" } elseif ($r.proxyOk -eq $false) { "no" } else { "" }
        $td = if ($r.teardownOk -eq $true) { "yes" } elseif ($r.teardownOk -eq $false) { "no" } else { "" }
        $dirty = if ($r.dirtyLogOk -eq $false -and $r.dirtyLog) {
            [string]$r.dirtyLog
        } elseif ($r.dirtyLogOk -eq $false) {
            "yes"
        } else {
            ""
        }
        $dirty = $dirty.Replace("|", '\|').Replace([Environment]::NewLine, " ")
        $err = [string]$r.errorMessage
        $err = $err.Replace("|", '\|').Replace([Environment]::NewLine, " ")
        if (-not $err) { $err = "" }
        [void]$lines.Add("| $($r.repo) | $($r.outcome) | $(if ($be) { $be } else { ' -- ' }) | $(if ($fe) { $fe } else { ' -- ' }) | $(if ($px) { $px } else { ' -- ' }) | $(if ($td) { $td } else { ' -- ' }) | $(if ($dirty) { $dirty } else { ' -- ' }) | $(if ($err) { $err } else { ' -- ' }) |")
    }
    foreach ($r in $ResultRows) {
        if (-not $r.logExcerpt -and -not $r.teardownDetail -and $r.dirtyLogOk -ne $false) { continue }
        [void]$lines.Add("")
        [void]$lines.Add("### $($r.repo)")
        [void]$lines.Add("")
        if ($r.rootOrderOk -eq $false) { [void]$lines.Add("- Root order: FAILED") }
        if ($r.teardownDetail) { [void]$lines.Add("- Teardown: $($r.teardownDetail)") }
        if ($r.dirtyLogOk -eq $false) {
            [void]$lines.Add("- Dirty log: $($r.dirtyLog)")
            if ($r.consoleIssues -and $r.consoleIssues.Count -gt 0) {
                foreach ($w in $r.consoleIssues) { [void]$lines.Add("  - $w") }
            }
        }
        if ($r.errorMessage) { [void]$lines.Add("- Error: $($r.errorMessage)") }
        if ($r.logExcerpt) {
            [void]$lines.Add("")
            [void]$lines.Add('```text')
            [void]$lines.Add([string]$r.logExcerpt)
            [void]$lines.Add('```')
        }
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    $nl = [Environment]::NewLine
    [System.IO.File]::WriteAllText($ReportPath, ($lines -join $nl) + $nl, $utf8NoBom)
}

function Test-HttpOk {
    param([string]$Uri, [int]$TimeoutSec = 5)
    $st = Test-HttpStatus -Uri $Uri -TimeoutSec $TimeoutSec
    return @{ ok = $st.ok; status = $st.status; error = $st.error }
}

function Test-HttpStatus {
    param([string]$Uri, [int]$TimeoutSec = 5)
    try {
        $resp = Invoke-WebRequest -Uri $Uri -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        $code = [int]$resp.StatusCode
        return @{ ok = ($code -ge 200 -and $code -lt 400); status = $code; error = "" }
    } catch {
        $code = $null
        if ($_.Exception.Response) {
            try { $code = [int]$_.Exception.Response.StatusCode.value__ } catch { }
        }
        $ok = ($null -ne $code -and $code -ge 200 -and $code -lt 400)
        return @{ ok = $ok; status = $code; error = $_.Exception.Message }
    }
}

function Normalize-ProbeRoutePath {
    param([string]$Path)
    if (-not $Path) { return "/" }
    if ($Path -notmatch '^/') { return "/$Path" }
    return $Path
}

function Get-ProbeFrontendRoutes {
    param($Entry, [string]$RepoPath)
    $routes = [System.Collections.Generic.List[string]]::new()
    if ($Entry.PSObject.Properties.Name -contains "frontendRoutes" -and $Entry.frontendRoutes) {
        foreach ($p in $Entry.frontendRoutes) {
            $norm = Normalize-ProbeRoutePath -Path ([string]$p)
            if (-not $routes.Contains($norm)) { [void]$routes.Add($norm) }
        }
        return @($routes)
    }
    foreach ($rel in @("web_sota/probe-routes.json", "webapp/probe-routes.json", "web-sota/probe-routes.json", "probe-routes.json")) {
        $f = Join-Path $RepoPath $rel
        if (-not (Test-Path $f)) { continue }
        try {
            $j = Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json
            $arr = if ($j.PSObject.Properties.Name -contains "routes") { $j.routes } elseif ($j -is [array]) { $j } else { @() }
            foreach ($p in $arr) {
                $norm = Normalize-ProbeRoutePath -Path ([string]$p)
                if (-not $routes.Contains($norm)) { [void]$routes.Add($norm) }
            }
            if ($routes.Count -gt 0) { return @($routes) }
        } catch { }
    }
    return @("/", "/index.html")
}

function Test-ProbeFrontendPages {
    param(
        [int]$FrontendPort,
        [string[]]$Routes
    )
    $checks = @()
    $failed404 = @()
    $failedOther = @()
    foreach ($path in $Routes) {
        $uri = "http://127.0.0.1:$FrontendPort$path"
        $st = Test-HttpStatus -Uri $uri -TimeoutSec 8
        $pageOk = $st.ok
        $checks += [PSCustomObject]@{
            path   = $path
            status = $st.status
            ok     = $pageOk
        }
        if ($st.status -eq 404) { $failed404 += $path }
        elseif (-not $pageOk) { $failedOther += $path }
    }
    return @{
        checks      = $checks
        pagesOk     = ($failed404.Count -eq 0 -and $failedOther.Count -eq 0)
        failed404   = $failed404
        failedOther = $failedOther
    }
}

function Stop-FleetProbeTeardown {
    param(
        [int[]]$Ports,
        $StartProcess = $null,
        [string]$Label = "probe-teardown"
    )
    $killed = @()
    if ($StartProcess -and -not $StartProcess.HasExited) {
        Stop-Process -Id $StartProcess.Id -Force -ErrorAction SilentlyContinue
        $killed += "starter:$($StartProcess.Id)"
        Start-Sleep -Milliseconds 200
    }
    $sweep = Invoke-FleetProbePortSweep -Ports $Ports -Label $Label
    if ($sweep.stillPids.Count -gt 0) {
        $killed += @($sweep.stillPids | ForEach-Object { "still:$_" })
    }
    return @{
        killed         = $killed
        portsClear     = $sweep.portsClear
        stillListening = $sweep.stillListening
    }
}

function Write-ProgressReport {
    param($Results, [string]$GeneratedAt, [string]$Status, [int]$TotalExpected, [string]$CurrentRepo = "")
    $progress = @{
        generatedAt   = $GeneratedAt
        status        = $Status
        reposRoot     = $reposRoot
        completed     = $Results.Count
        totalExpected = $TotalExpected
        currentRepo   = $CurrentRepo
        results       = @($Results)
    }
    $progressPath = Join-Path $reportDirFull "fleet-webapp-report.progress.json"
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($progressPath, ($progress | ConvertTo-Json -Depth 6), $utf8NoBom)
}

$manifest = Get-Content $manifestFull -Raw | ConvertFrom-Json

$excludeSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($r in $ExcludeRepos) {
    if ($r -and $r.Trim()) { [void]$excludeSet.Add($r.Trim()) }
}
if ($env:FLEET_PROBE_EXCLUDE_REPOS) {
    foreach ($r in ($env:FLEET_PROBE_EXCLUDE_REPOS -split '[,;]')) {
        if ($r -and $r.Trim()) { [void]$excludeSet.Add($r.Trim()) }
    }
}

function Test-ProbeRepoExcluded {
    param($Entry)
    if ($excludeSet.Contains($Entry.repo)) { return $true }
    if ($Entry.PSObject.Properties.Name -contains 'probeSkip' -and $Entry.probeSkip) { return $true }
    return $false
}

$priorReportPath = Join-Path $reportDirFull "fleet-webapp-report.json"
$priorReportSnapshot = $null
if (Test-Path $priorReportPath) {
    $priorReportSnapshot = Get-Content $priorReportPath -Raw | ConvertFrom-Json
}

if ($BrokenOnly) {
    if ($RepoFilter) {
        Write-Error "Cannot combine -RepoFilter with -BrokenOnly."
        exit 1
    }
    if (-not $priorReportSnapshot) {
        Write-Error "No prior report at $priorReportPath - run a full fleet probe first."
        exit 1
    }
    $priorReport = $priorReportSnapshot
    $brokenSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($row in @($priorReport.results)) {
        $oc = [string]$row.outcome
        if ($oc -and $oc -notin @("stack_ok", "skip")) {
            [void]$brokenSet.Add([string]$row.repo)
        }
    }
    if ($brokenSet.Count -eq 0) {
        Write-Host "BrokenOnly: no non-ok repos in last report (stack_ok + skip only)."
        exit 0
    }
    $manifest = @($manifest | Where-Object { $brokenSet.Contains($_.repo) })
    Write-Host "BrokenOnly: $($manifest.Count) repos from prior report ($($brokenSet.Count) broken entries)"
    if ($manifest.Count -eq 0) {
        Write-Error "BrokenOnly: broken repos from report not found in manifest."
        exit 1
    }
}
elseif ($RepoFilter) {
    if (-not $IncludeProbeHost -and $excludeSet.Contains($RepoFilter)) {
        Write-Error "Repo '$RepoFilter' is the probe host (excluded). Pass -IncludeProbeHost to cold-start it anyway."
        exit 1
    }
    $manifest = @($manifest | Where-Object { $_.repo -eq $RepoFilter })
    if ($manifest.Count -eq 0) { Write-Error "RepoFilter '$RepoFilter' matched no manifest entry."; exit 1 }
    Write-Host "Filtering to repo: $RepoFilter"
}
elseif (-not $IncludeProbeHost) {
    $skippedHosts = @($manifest | Where-Object { Test-ProbeRepoExcluded $_ })
    $manifest = @($manifest | Where-Object { -not (Test-ProbeRepoExcluded $_) })
    foreach ($s in $skippedHosts) {
        Write-Host "[$($s.repo)] SKIP (probe host - already running; use -IncludeProbeHost to include)"
    }
}
if ([System.IO.Path]::IsPathRooted($ReportDir)) { $reportDirFull = $ReportDir }
New-Item -ItemType Directory -Force -Path $reportDirFull | Out-Null

$results = @()
$totalExpected = @($manifest).Count
$generatedAt = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$preSweepPorts = @()
foreach ($m in $manifest) {
    if ($m.port) { $preSweepPorts += [int]$m.port }
    if ($m.frontendPort) { $preSweepPorts += [int]$m.frontendPort }
    if ($m.teardownPorts) { foreach ($tp in $m.teardownPorts) { $preSweepPorts += [int]$tp } }
}
# Skip pre-sweep (too slow with zombie PIDs; per-repo teardowns handle cleanup)
Write-ProgressReport -Results $results -GeneratedAt $generatedAt -Status "running" -TotalExpected $totalExpected

foreach ($entry in $manifest) {
    $repo = $entry.repo
    Write-ProgressReport -Results $results -GeneratedAt $generatedAt -Status "running" -TotalExpected $totalExpected -CurrentRepo $repo
    $startPath = $entry.startPath
    $port = [int]$entry.port
    $healthPath = $entry.healthPath
    $timeoutSec = if ($entry.timeoutSec) { [int]$entry.timeoutSec } else { 90 }
    $frontendPort = if ($entry.PSObject.Properties.Name -contains "frontendPort" -and $entry.frontendPort) { [int]$entry.frontendPort } else { 0 }
    $frontendPath = if ($entry.frontendPath) { $entry.frontendPath } else { "/" }
    $proxyHealthPath = if ($entry.proxyHealthPath) { $entry.proxyHealthPath } else { "" }

    $r = [PSCustomObject]@{
        repo            = $repo
        startPath       = $startPath
        port            = $port
        healthPath      = $healthPath
        frontendPort    = $frontendPort
        proxyHealthPath = $proxyHealthPath
        outcome         = "skip"
        parseOk         = $null
        rootOrderOk     = $null
        rootOrderLine   = $null
        backendOk       = $false
        frontendOk      = $null
        proxyOk         = $null
        healthStatus    = $null
        errorMessage    = ""
        logExcerpt      = ""
        dirtyLog        = ""
        dirtyLogOk      = $true
        consoleIssues   = @()
        teardownOk      = $null
        teardownDetail  = ""
        pagesOk         = $null
        pageChecks      = @()
    }

    if ($port -le 0) {
        $r.errorMessage = "Port not set (fill from repo start.ps1 BackendPort)"
        $results += $r
        Write-Host "[$repo] SKIP (port not set)"
        Write-ProgressReport -Results $results -GeneratedAt $generatedAt -Status "running" -TotalExpected $totalExpected
        continue
    }

    $repoPath = Join-Path $reposRoot $repo
    $startScriptPath = Join-Path $repoPath $startPath
    if (-not (Test-Path $repoPath)) {
        $r.errorMessage = "Repo path not found: $repoPath"
        $results += $r
        Write-Host "[$repo] SKIP (repo not found)"
        Write-ProgressReport -Results $results -GeneratedAt $generatedAt -Status "running" -TotalExpected $totalExpected
        continue
    }
    if (-not (Test-Path $startScriptPath)) {
        $r.errorMessage = "Start script not found: $startScriptPath"
        $results += $r
        Write-Host "[$repo] SKIP (start script not found)"
        Write-ProgressReport -Results $results -GeneratedAt $generatedAt -Status "running" -TotalExpected $totalExpected
        continue
    }

    $startScriptPath = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $startScriptPath).Path)
    $workDir = Split-Path -Parent $startScriptPath

    $parse = Test-StartScriptParses -Path $startScriptPath
    $r.parseOk = $parse.ok
    if (-not $parse.ok) {
        $r.outcome = "parse_failed"
        $r.errorMessage = ($parse.errors -join "; ")
        $r.logExcerpt = ($parse.errors -join "`n")
        $results += $r
        Write-Host "[$repo] parse_failed"
        Write-ProgressReport -Results $results -GeneratedAt $generatedAt -Status "running" -TotalExpected $totalExpected
        continue
    }

    $rootOrder = Test-StartScriptRootOrder -Path $startScriptPath
    $r.rootOrderOk = $rootOrder.ok
    $r.rootOrderLine = $rootOrder.line
    if (-not $rootOrder.ok) {
        $r.outcome = "root_order_failed"
        $r.errorMessage = $rootOrder.message
        $r.logExcerpt = $rootOrder.message
        $results += $r
        Write-Host "[$repo] root_order_failed (line $($rootOrder.line))"
        Write-ProgressReport -Results $results -GeneratedAt $generatedAt -Status "running" -TotalExpected $totalExpected
        continue
    }

    $teardownPorts = @($port)
    if ($frontendPort -gt 0) { $teardownPorts += $frontendPort }
    if ($entry.PSObject.Properties.Name -contains "teardownPorts" -and $entry.teardownPorts) {
        foreach ($extra in $entry.teardownPorts) { $teardownPorts += [int]$extra }
    }

    $outFile = [System.IO.Path]::GetTempFileName()
    $errFile = [System.IO.Path]::GetTempFileName()
    $probeLogDir = Join-Path $reportDirFull "probe-logs\$repo"
    if (Test-Path -LiteralPath $probeLogDir) {
        Remove-Item -LiteralPath $probeLogDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Force -Path $probeLogDir | Out-Null
    $prevProbeRun = $env:FLEET_PROBE_RUN
    $prevProbeLogDir = $env:FLEET_PROBE_LOG_DIR
    $env:FLEET_PROBE_RUN = '1'
    $env:FLEET_PROBE_LOG_DIR = $probeLogDir
    $p = $null
    try {
        $p = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$startScriptPath`"", "-NoBrowser" -WorkingDirectory $workDir -RedirectStandardOutput $outFile -RedirectStandardError $errFile -PassThru -NoNewWindow

        $backendDeadline = (Get-Date).AddSeconds($timeoutSec)
        $backendOk = $false
        while ((Get-Date) -lt $backendDeadline) {
            Start-Sleep -Seconds 3
            $backendUri = "http://127.0.0.1:$port$healthPath"
            $bh = Test-HttpOk -Uri $backendUri
            if ($bh.ok) {
                $r.backendOk = $true
                $r.healthStatus = $bh.status
                $backendOk = $true
                break
            }
        }

        $frontendDeadline = (Get-Date).AddSeconds($timeoutSec)
        while ((Get-Date) -lt $frontendDeadline) {
            $allFeOk = $true
            if ($frontendPort -gt 0) {
                $feUri = "http://127.0.0.1:$frontendPort$frontendPath"
                $fh = Test-HttpOk -Uri $feUri -TimeoutSec 8
                $r.frontendOk = $fh.ok
                if (-not $fh.ok) { $allFeOk = $false }
            }
            if ($proxyHealthPath -and $frontendPort -gt 0) {
                $pxUri = "http://127.0.0.1:$frontendPort$proxyHealthPath"
                $ph = Test-HttpOk -Uri $pxUri -TimeoutSec 8
                $r.proxyOk = $ph.ok
                if (-not $ph.ok) { $allFeOk = $false }
            }
            if ($frontendPort -le 0 -or $allFeOk) { break }
            Start-Sleep -Seconds 3
        }

        if ($frontendPort -gt 0 -and $r.frontendOk -eq $false) {
            if (-not $r.errorMessage) { $r.errorMessage = "Frontend: not ready before timeout" }
        }
        if ($proxyHealthPath -and $frontendPort -gt 0 -and $r.proxyOk -eq $false) {
            if ($r.errorMessage) { $r.errorMessage += "; " }
            $r.errorMessage += "Proxy: not ready before timeout"
        }

        if ($RepoFilter -and $frontendPort -gt 0 -and $r.frontendOk) {
            $repoPath = Join-Path $reposRoot $repo
            $pageRoutes = Get-ProbeFrontendRoutes -Entry $entry -RepoPath $repoPath
            $fePathNorm = Normalize-ProbeRoutePath -Path $frontendPath
            $pageRoutes = @($pageRoutes | Where-Object { $_ -ne $fePathNorm })
            if ($pageRoutes.Count -gt 0) {
                $pageProbe = Test-ProbeFrontendPages -FrontendPort $frontendPort -Routes $pageRoutes
                $r.pageChecks = $pageProbe.checks
                $r.pagesOk = $pageProbe.pagesOk
                if ($pageProbe.failed404.Count -gt 0) {
                    if ($r.errorMessage) { $r.errorMessage += "; " }
                    $r.errorMessage += "SPA routes 404: $($pageProbe.failed404 -join ', ')"
                }
                if ($pageProbe.failedOther.Count -gt 0) {
                    if ($r.errorMessage) { $r.errorMessage += "; " }
                    $r.errorMessage += "SPA routes failed: $($pageProbe.failedOther -join ', ')"
                }
            }
        }

        if ($backendOk -and ($frontendPort -le 0 -or $r.frontendOk) -and (-not $proxyHealthPath -or $r.proxyOk)) {
            $r.outcome = "stack_ok"
        } elseif ($backendOk) {
            $r.outcome = "backend_ok"
        } else {
            $r.outcome = "start_failed"
            if (-not $r.errorMessage) { $r.errorMessage = "Backend port $port did not respond within $timeoutSec s" }
        }

        if ($r.pagesOk -eq $false -and $r.pageChecks -and @($r.pageChecks | Where-Object { $_.status -eq 404 }).Count -gt 0) {
            if ($r.outcome -eq "stack_ok" -or $r.outcome -eq "backend_ok") {
                $r.outcome = "pages_404"
            }
        }

        if ($r.outcome -eq "stack_ok" -or $r.outcome -eq "backend_ok") {
            $apiIssues = Invoke-FleetPostStackApiChecks -Repo $repo -Port $port -HealthPath $healthPath
            if ($apiIssues.Count -gt 0) {
                $r.consoleIssues = @($r.consoleIssues + $apiIssues | Select-Object -Unique)
            }
        }
    } catch {
        $r.outcome = "start_failed"
        $r.errorMessage = $_.Exception.Message
    } finally {
        $errContent = @(Get-Content $errFile -Tail $LogTailLines -ErrorAction SilentlyContinue)
        $outContent = @(Get-Content $outFile -Tail $LogTailLines -ErrorAction SilentlyContinue)
        $captured = Get-FleetProbeCapturedLogs -LogDir $probeLogDir -Tail $LogTailLines
        $mergedLog = (($outContent + $errContent) -join [Environment]::NewLine)
        if ($captured) {
            $mergedLog = if ($mergedLog) { "$mergedLog`n$captured" } else { $captured }
        }
        $dirty = Test-FleetDirtyLog -LogText $mergedLog -ExtraIssues $r.consoleIssues
        $r.consoleIssues = $dirty.issues
        $r.dirtyLogOk = $dirty.dirtyLogOk
        $r.dirtyLog = $dirty.dirtyLog
        if (-not $r.dirtyLogOk) {
            if ($r.outcome -eq "stack_ok") {
                $r.outcome = "stack_degraded"
                if (-not $r.errorMessage) {
                    $r.errorMessage = "Dirty log: $($r.dirtyLog)"
                }
            }
            if (-not $r.logExcerpt) {
                $r.logExcerpt = ($r.consoleIssues -join [Environment]::NewLine)
            }
        } elseif ($r.outcome -ne "stack_ok" -and $r.outcome -ne "backend_ok" -and $mergedLog) {
            $r.logExcerpt = $mergedLog.Trim()
        }

        $td = Stop-FleetProbeTeardown -Ports $teardownPorts -StartProcess $p -Label "$repo-teardown"
        $r.teardownOk = $td.portsClear
        $r.teardownDetail = "killed=$($td.killed.Count); clear=$($td.portsClear)"
        if (-not $td.portsClear) {
            $r.teardownDetail += "; still=$($td.stillListening -join ',')"
        }
        if ($prevProbeRun) { $env:FLEET_PROBE_RUN = $prevProbeRun } else { Remove-Item Env:FLEET_PROBE_RUN -ErrorAction SilentlyContinue }
        if ($prevProbeLogDir) { $env:FLEET_PROBE_LOG_DIR = $prevProbeLogDir } else { Remove-Item Env:FLEET_PROBE_LOG_DIR -ErrorAction SilentlyContinue }
        Remove-Item $outFile -Force -ErrorAction SilentlyContinue
        Remove-Item $errFile -Force -ErrorAction SilentlyContinue
        Write-Host "[$repo] teardown ports=$($teardownPorts -join ',') ok=$($r.teardownOk) dirtyLog=$(if ($r.dirtyLogOk) { 'clean' } else { 'yes' })"
    }

    $results += $r
    Write-Host "[$repo] $($r.outcome)"
    Write-ProgressReport -Results $results -GeneratedAt $generatedAt -Status "running" -TotalExpected $totalExpected
    if ($CooldownBetweenSec -gt 0) { Start-Sleep -Seconds $CooldownBetweenSec }
}

$probeMode = if ($BrokenOnly) { "broken_only" } elseif ($RepoFilter) { "single" } else { "full" }
$reposProbed = $results.Count
$finalResults = @($results)

if ($BrokenOnly -and $priorReportSnapshot) {
    $probedSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($row in $results) { [void]$probedSet.Add([string]$row.repo) }
    foreach ($priorRow in @($priorReportSnapshot.results)) {
        if (-not $probedSet.Contains([string]$priorRow.repo)) {
            $finalResults += $priorRow
        }
    }
    $finalResults = @($finalResults | Sort-Object { $_.repo })
}

$summary = Get-ProbeSummaryCounts -ResultRows $finalResults
$comparison = Build-ProbeComparison -PriorReport $priorReportSnapshot -CurrentRows $finalResults -ProbeMode $probeMode -ReposProbed $reposProbed
$stackOk = [int]$summary.stack_ok

$report = @{
    generatedAt   = $generatedAt
    reposRoot     = $reposRoot
    probeMode     = $probeMode
    totalExpected = if ($BrokenOnly) { @($finalResults).Count } else { $totalExpected }
    reposProbed   = $reposProbed
    summary       = $summary
    comparison    = $comparison
    results       = @($finalResults)
}
$reportJson = Join-Path $reportDirFull "fleet-webapp-report.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($reportJson, ($report | ConvertTo-Json -Depth 6), $utf8NoBom)
Write-ProgressReport -Results $finalResults -GeneratedAt $generatedAt -Status "complete" -TotalExpected $report.totalExpected

$reportMd = Join-Path $reportDirFull "fleet-webapp-report.md"
Write-ProbeMarkdownReport -ResultRows $finalResults -GeneratedAt $generatedAt -ReposRoot $reposRoot -Summary $summary -Comparison $comparison -ReportPath $reportMd

$coldStamp = $generatedAt.Replace(":", "-")
$coldMd = Join-Path $reportDirFull "fleet-cold-start-$coldStamp.md"
Write-ProbeMarkdownReport -ResultRows $finalResults -GeneratedAt $generatedAt -ReposRoot $reposRoot -Summary $summary -Comparison $comparison -ReportPath $coldMd

# Skip post-sweep (too slow)

Write-Host "Report: $reportJson"
Write-Host "Stack OK: $stackOk / $($finalResults.Count)"
if ($summary.dirty_log -gt 0) {
    Write-Host "Dirty log: $($summary.dirty_log) repo(s) (see dirtyLog column / stack_degraded)" -ForegroundColor Yellow
}
if ($comparison) {
    Write-Host "Parse failures: $($comparison.parse_failed_now) (was $($comparison.parse_failed_prior), delta $($comparison.parse_failed_delta))"
}
