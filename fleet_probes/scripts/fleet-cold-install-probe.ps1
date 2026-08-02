<#
.SYNOPSIS
  Fleet cold-install probe - INSTALL.md preflight, mcpb release check, optional sandbox/mcpb smoke.
.DESCRIPTION
  Phase 1: preflight (INSTALL.md structure, GitHub .mcpb asset from manifest).
  Phase 2b (-TestMcpb): mcpb release check (Option A - Claude Desktop only; mcpb CLI writes
  claude_desktop_config.json). -HostMcpbSmoke: Claude mcpb config smoke + optional multi-IDE
  stdio smoke for uv/manual installs (Cursor, Windsurf, Antigravity, Zed, OpenCode).
  Phase 2 (-Execute): dispatch to virtualization-mcp sandbox APIs when available.

  See docs/operations/FLEET_COLD_INSTALL_PROBE.md
.EXAMPLE
  .\scripts\fleet-cold-install-probe.ps1 -PreflightOnly
  .\scripts\fleet-cold-install-probe.ps1 -RepoFilter docker-mcp -TestMcpb -HostMcpbSmoke
  .\scripts\fleet-cold-install-probe.ps1 -BrokenOnly -BatchSize 10
#>
[CmdletBinding()]
param(
    [string]$ManifestPath = "scripts/fleet-cold-install-manifest.json",
    [string]$ReportDir = "scripts/out",
    [string]$SandboxRunsRoot = "D:\Dev\repos\_sandbox_runs",
    [string]$VirtMcpBase = "http://127.0.0.1:10701",
    [string]$RepoFilter = "",
    [int]$BatchSize = 0,
    [switch]$BrokenOnly,
    [switch]$PreflightOnly,
    [switch]$Execute,
    [switch]$TestMcpb,
    [switch]$HostMcpbSmoke,
    [string]$McpClients = ""
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$manifestFull = Join-Path $repoRoot $ManifestPath
$reportDirFull = Join-Path $repoRoot $ReportDir
$reposRoot = if ($env:FLEET_REPOS_ROOT) { $env:FLEET_REPOS_ROOT } else { "D:\Dev\repos" }
$smokeHelper = Join-Path $scriptRoot "Invoke-FleetStdioMcpSmoke.ps1"
$clientRegistry = Join-Path $scriptRoot "Get-FleetMcpClientRegistry.ps1"
if (Test-Path -LiteralPath $clientRegistry) { . $clientRegistry }

$clientFilter = @()
if ($McpClients.Trim()) {
    $clientFilter = @($McpClients.Split(',') | ForEach-Object { $_.Trim().ToLowerInvariant() } | Where-Object { $_ })
}

function Get-ColdInstallSummary {
    param($Rows)
    return @{
        total               = @($Rows).Count
        install_ok          = @($Rows | Where-Object { $_.outcome -eq "install_ok" }).Count
        install_failed      = @($Rows | Where-Object { $_.outcome -eq "install_failed" }).Count
        doc_gap             = @($Rows | Where-Object { $_.outcome -eq "doc_gap" }).Count
        verify_failed       = @($Rows | Where-Object { $_.outcome -eq "verify_failed" }).Count
        preflight_ok        = @($Rows | Where-Object { $_.outcome -eq "preflight_ok" }).Count
        skip                = @($Rows | Where-Object { $_.outcome -eq "skip" }).Count
        mcpb_ok             = @($Rows | Where-Object { $_.mcpbOutcome -eq "mcpb_ok" }).Count
        mcpb_install_failed = @($Rows | Where-Object { $_.mcpbOutcome -eq "mcpb_install_failed" }).Count
        mcpb_smoke_failed   = @($Rows | Where-Object { $_.mcpbOutcome -eq "mcpb_smoke_failed" }).Count
        mcpb_no_package     = @($Rows | Where-Object { $_.mcpbOutcome -eq "mcpb_no_package" }).Count
        stdio_ok            = @($Rows | Where-Object { $_.stdioOutcome -eq "stdio_ok" }).Count
        stdio_failed        = @($Rows | Where-Object { $_.stdioOutcome -eq "stdio_failed" }).Count
        stdio_no_config     = @($Rows | Where-Object { $_.stdioOutcome -eq "stdio_no_config" }).Count
    }
}

function Build-ColdInstallComparison {
    param($Prior, $Rows, [string]$Mode, [int]$Probed)
    if (-not $Prior) { return $null }
    $priorSummary = if ($Prior.summary) { $Prior.summary } else { Get-ColdInstallSummary -Rows $Prior.results }
    $nowSummary = Get-ColdInstallSummary -Rows $Rows
    $failPrior = [int]($priorSummary.install_failed + $priorSummary.doc_gap + $priorSummary.verify_failed)
    $failNow = [int]($nowSummary.install_failed + $nowSummary.doc_gap + $nowSummary.verify_failed)
    return @{
        priorGeneratedAt       = $Prior.generatedAt
        probeMode              = $Mode
        reposProbed            = $Probed
        install_failed_prior   = $failPrior
        install_failed_now     = $failNow
        install_failed_delta   = $failNow - $failPrior
        mcpb_ok_prior          = [int]$priorSummary.mcpb_ok
        mcpb_ok_now            = [int]$nowSummary.mcpb_ok
        mcpb_ok_delta          = [int]$nowSummary.mcpb_ok - [int]$priorSummary.mcpb_ok
    }
}

function Write-ColdInstallProgress {
    param($Rows, [string]$GeneratedAt, [string]$Status, [int]$Total, [string]$CurrentRepo = "")
    $progress = @{
        generatedAt   = $GeneratedAt
        status        = $Status
        reposRoot     = $reposRoot
        completed     = $Rows.Count
        totalExpected = $Total
        currentRepo   = $CurrentRepo
        results       = @($Rows)
    }
    $path = Join-Path $reportDirFull "fleet-cold-install-report.progress.json"
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($path, ($progress | ConvertTo-Json -Depth 6), $utf8)
}

function Write-ColdInstallMarkdown {
    param($Rows, $Summary, $Comparison, [string]$GeneratedAt, [string]$Path)
    $lines = [System.Collections.Generic.List[string]]::new()
    [void]$lines.Add("# Fleet cold-install probe report")
    [void]$lines.Add("")
    [void]$lines.Add("Generated: $GeneratedAt")
    [void]$lines.Add("Repos root: $reposRoot")
    if ($Comparison) {
        $d = $Comparison.install_failed_delta
        $dl = if ($d -gt 0) { "+$d" } else { "$d" }
        [void]$lines.Add("Install/doc failures: $($Comparison.install_failed_now) (was $($Comparison.install_failed_prior), $dl since prior run)")
        if ($Comparison.mcpb_ok_now -gt 0 -or $Comparison.mcpb_ok_prior -gt 0) {
            [void]$lines.Add("mcpb ok: $($Comparison.mcpb_ok_now) (was $($Comparison.mcpb_ok_prior))")
        }
    }
    [void]$lines.Add("")
    [void]$lines.Add("## Summary")
    [void]$lines.Add("")
    [void]$lines.Add("| Metric | Count |")
    [void]$lines.Add("| --- | ---: |")
    foreach ($k in @('total','preflight_ok','install_ok','install_failed','doc_gap','verify_failed','skip','mcpb_ok','mcpb_install_failed','mcpb_smoke_failed','mcpb_no_package')) {
        if ($Summary.ContainsKey($k)) { [void]$lines.Add("| $k | $($Summary[$k]) |") }
    }
    [void]$lines.Add("")
    [void]$lines.Add("## Results")
    [void]$lines.Add("")
    [void]$lines.Add("| Repo | Outcome | mcpb | stdio | Option | Error |")
    [void]$lines.Add("| --- | --- | --- | --- | --- | --- |")
    foreach ($r in $Rows) {
        $err = ([string]$r.errorMessage).Replace("|", '\|').Replace([Environment]::NewLine, " ")
        $mcpb = if ($r.mcpbOutcome) { $r.mcpbOutcome } else { "" }
        $stdio = if ($r.stdioOutcome) { $r.stdioOutcome } else { "" }
        [void]$lines.Add("| $($r.repo) | $($r.outcome) | $(if ($mcpb) { $mcpb } else { '-' }) | $(if ($stdio) { $stdio } else { '-' }) | $($r.primaryOption) | $(if ($err) { $err } else { '-' }) |")
    }
    foreach ($r in $Rows) {
        if (-not $r.logExcerpt) { continue }
        [void]$lines.Add("")
        [void]$lines.Add("### $($r.repo)")
        [void]$lines.Add('```text')
        [void]$lines.Add([string]$r.logExcerpt)
        [void]$lines.Add('```')
    }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, ($lines -join [Environment]::NewLine) + [Environment]::NewLine, $utf8)
}

function Test-InstallDocPreflight {
    param([string]$RepoPath, [string]$InstallRel, $Entry)
    $full = Join-Path $RepoPath ($InstallRel.Replace('/', '\'))
    if (-not (Test-Path -LiteralPath $full)) {
        return @{ ok = $false; outcome = "doc_gap"; message = "INSTALL.md missing at $InstallRel" }
    }
    $text = Get-Content -LiteralPath $full -Raw -Encoding UTF8
    $gaps = @()
    if ($text -notmatch '(?i)option\s+[abc]|##\s+install|##\s+option') { $gaps += "no Option A/B/C structure" }
    if ($Entry.primaryOption -eq 'C' -and $text -notmatch '(?i)uv\s+sync') { $gaps += "primary Option C but no uv sync documented" }
    if ($Entry.installOptions -contains 'A' -and $text -notmatch '(?i)\.mcpb') { $gaps += "Option A listed but no .mcpb mention" }
    if ($gaps.Count -gt 0) {
        return @{ ok = $false; outcome = "doc_gap"; message = ($gaps -join "; ") }
    }
    return @{ ok = $true; outcome = "preflight_ok"; message = "" }
}

function Invoke-FleetMcpStdioSmokeEntry {
    param($DiscoveredEntry, [int]$TimeoutSec = 12)
    $envMap = @{}
    if ($DiscoveredEntry.env) {
        foreach ($k in $DiscoveredEntry.env.Keys) { $envMap[$k] = $DiscoveredEntry.env[$k] }
    }
    $body = @{
        command     = $DiscoveredEntry.command
        args        = @($DiscoveredEntry.args)
        timeout_sec = $TimeoutSec
        env         = $envMap
        cwd         = $DiscoveredEntry.cwd
    }
    if ($HostMcpbSmoke -and (Test-Path -LiteralPath $smokeHelper)) {
        . $smokeHelper
        return Invoke-FleetStdioMcpSmoke -Command $DiscoveredEntry.command -SmokeArgs @($DiscoveredEntry.args) `
            -Env $envMap -WorkingDirectory ([string]$DiscoveredEntry.cwd) -TimeoutSec $TimeoutSec
    }
    $apiSmoke = Invoke-VirtMcpPost -Path "/api/v1/fleet/stdio-smoke" -Body $body
    if ($apiSmoke.ok) {
        return @{ ok = $true; log = if ($apiSmoke.result.log) { [string]$apiSmoke.result.log } else { "" } }
    }
    return @{
        ok    = $false
        error = if ($apiSmoke.result.error) { [string]$apiSmoke.result.error } elseif ($apiSmoke.error) { [string]$apiSmoke.error } else { "stdio-smoke API failed" }
        log   = if ($apiSmoke.result.log) { [string]$apiSmoke.result.log } else { [string]$apiSmoke.stderr }
    }
}

function Invoke-VirtMcpPost {
    param([string]$Path, $Body)
    $uri = "$VirtMcpBase$Path"
    try {
        $json = if ($Body) { $Body | ConvertTo-Json -Depth 5 } else { "{}" }
        return Invoke-RestMethod -Uri $uri -Method Post -Body $json -ContentType "application/json" -TimeoutSec 120
    } catch {
        return @{ success = $false; error = $_.Exception.Message }
    }
}

if (-not (Test-Path -LiteralPath $manifestFull)) {
    Write-Error "Manifest missing: $manifestFull. Run sync-fleet-cold-install-manifest.ps1 first."
    exit 1
}

$priorPath = Join-Path $reportDirFull "fleet-cold-install-report.json"
$priorSnapshot = $null
if (Test-Path -LiteralPath $priorPath) {
    $priorSnapshot = Get-Content $priorPath -Raw | ConvertFrom-Json
}

$manifestRaw = Get-Content $manifestFull -Raw -Encoding UTF8 | ConvertFrom-Json
$manifest = @()
foreach ($row in @($manifestRaw)) {
    if ($row -is [System.Array]) {
        foreach ($inner in $row) { $manifest += $inner }
    } else {
        $manifest += $row
    }
}

if ($BrokenOnly) {
    if ($RepoFilter) { Write-Error "Cannot combine -RepoFilter with -BrokenOnly."; exit 1 }
    if (-not $priorSnapshot) { Write-Error "No prior report at $priorPath"; exit 1 }
    $broken = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($row in @($priorSnapshot.results)) {
        $oc = [string]$row.outcome
        $mc = [string]$row.mcpbOutcome
        if ($oc -and $oc -notin @('install_ok', 'preflight_ok', 'skip')) { [void]$broken.Add([string]$row.repo) }
        if ($mc -and $mc -notin @('mcpb_ok', 'mcpb_no_package', '')) { [void]$broken.Add([string]$row.repo) }
    }
    if ($broken.Count -eq 0) { Write-Host "BrokenOnly: nothing to re-probe."; exit 0 }
    $manifest = @($manifest | Where-Object { $broken.Contains($_.repo) })
    Write-Host "BrokenOnly: $($manifest.Count) repos"
}
elseif ($RepoFilter) {
    $manifest = @($manifest | Where-Object { $_.repo -eq $RepoFilter })
    if ($manifest.Count -eq 0) { Write-Error "No manifest entry for $RepoFilter"; exit 1 }
}

if ($BatchSize -gt 0) { $manifest = @($manifest | Select-Object -First $BatchSize) }

if (-not $Execute -and -not $PreflightOnly) { $PreflightOnly = $true }

$runId = Get-Date -Format "yyyyMMdd_HHmmss"
$runDir = Join-Path $SandboxRunsRoot $runId
New-Item -ItemType Directory -Force -Path $reportDirFull | Out-Null
if ($Execute) { New-Item -ItemType Directory -Force -Path $runDir | Out-Null }

$results = @()
$total = $manifest.Count
$generatedAt = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$probeMode = if ($BrokenOnly) { "broken_only" } elseif ($RepoFilter) { "single" } else { "full" }
Write-ColdInstallProgress -Rows $results -GeneratedAt $generatedAt -Status "running" -Total $total

foreach ($entry in $manifest) {
    $repo = [string]$entry.repo
    Write-ColdInstallProgress -Rows $results -GeneratedAt $generatedAt -Status "running" -Total $total -CurrentRepo $repo
    $repoPath = Join-Path $reposRoot $repo

    $r = [PSCustomObject]@{
        repo            = $repo
        installPath     = $entry.installPath
        primaryOption   = $entry.primaryOption
        outcome         = "skip"
        mcpbOutcome     = ""
        mcpbAssetName   = $entry.mcpbAssetName
        mcpbConfigEntry   = ""
        stdioOutcome      = ""
        stdioSmokeResults = @()
        errorMessage      = ""
        logExcerpt        = ""
        durationSec       = 0
    }

    if ($entry.probeSkip) {
        $r.outcome = "skip"
        $r.errorMessage = "probeSkip"
        $results += $r
        Write-Host "[$repo] skip"
        continue
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    if (-not (Test-Path -LiteralPath $repoPath)) {
        $r.outcome = "skip"
        $r.errorMessage = "Repo path not found"
        $results += $r
        Write-Host "[$repo] skip (missing path)"
        continue
    }

    $pf = Test-InstallDocPreflight -RepoPath $repoPath -InstallRel $entry.installPath -Entry $entry
    $r.outcome = $pf.outcome
    $r.errorMessage = $pf.message

    if ($TestMcpb) {
        if ($entry.mcpbAvailable) {
            if ($Execute) {
                $mcpbBody = @{
                    repo         = $repo
                    releases_url = $entry.mcpbReleasesUrl
                    asset_name   = $entry.mcpbAssetName
                    run_dir      = $runDir
                }
                $mcpbResp = Invoke-VirtMcpPost -Path "/api/v1/fleet/install-mcpb" -Body $mcpbBody
                if ($mcpbResp.success) {
                    $r.logExcerpt = "mcpb script: $($mcpbResp.script_path)"
                    $r.mcpbOutcome = "mcpb_pending"
                }
                else {
                    $r.mcpbOutcome = "mcpb_install_failed"
                    if ($r.errorMessage) { $r.errorMessage += "; " }
                    $r.errorMessage += "install-mcpb: $($mcpbResp.error)"
                }
            }
            else {
                $r.mcpbOutcome = "mcpb_pending"
            }
        }
        else {
            $r.mcpbOutcome = "mcpb_no_package"
        }
    }

    if ($HostMcpbSmoke) {
        $discovered = @()
        if (Get-Command Get-FleetMcpStdioEntriesForRepo -ErrorAction SilentlyContinue) {
            $discovered = @(Get-FleetMcpStdioEntriesForRepo -Repo $repo -ReposRoot $reposRoot -ClientFilter $clientFilter)
        }
        if ($discovered.Count -eq 0) {
            $r.stdioOutcome = "stdio_no_config"
            if ($entry.mcpbAvailable -and $r.mcpbOutcome -eq "mcpb_pending") {
                $r.mcpbOutcome = "mcpb_install_failed"
                if ($r.errorMessage) { $r.errorMessage += "; " }
                $r.errorMessage += "No MCP config entry found (mcpb path requires Claude Desktop config)"
            }
        }
        else {
            $smokeRows = @()
            $anyStdioOk = $false
            $claudeOk = $false
            $claudeRow = $null
            foreach ($d in $discovered) {
                if ($entry.studioSmokeArgs) { $d.args = @($entry.studioSmokeArgs) }
                $smoke = Invoke-FleetMcpStdioSmokeEntry -DiscoveredEntry $d -TimeoutSec 12
                $row = [ordered]@{
                    clientId   = $d.clientId
                    client     = $d.client
                    serverName = $d.serverName
                    command    = "$($d.command) $($d.args -join ' ')"
                    ok         = [bool]$smoke.ok
                    error      = if ($smoke.error) { [string]$smoke.error } else { "" }
                }
                $smokeRows += [PSCustomObject]$row
                if ($smoke.ok) { $anyStdioOk = $true }
                if ($d.clientId -eq 'claude') {
                    $claudeRow = $row
                    if ($smoke.ok) { $claudeOk = $true }
                    $r.mcpbConfigEntry = $row.command
                }
                if (-not $smoke.ok -and $smoke.log) { $r.logExcerpt = $smoke.log }
            }
            $r.stdioSmokeResults = $smokeRows
            if ($anyStdioOk) { $r.stdioOutcome = "stdio_ok" }
            else {
                $r.stdioOutcome = "stdio_failed"
                $failedClients = @($smokeRows | Where-Object { -not $_.ok } | ForEach-Object { "$($_.client):$($_.error)" }) -join "; "
                if ($r.errorMessage) { $r.errorMessage += "; " }
                $r.errorMessage += "stdio smoke failed ($($discovered.Count) configs): $failedClients"
            }
            # mcpb outcomes: Claude Desktop only (mcpb install does not write other IDE configs)
            if ($entry.mcpbAvailable -and $TestMcpb) {
                if (-not $claudeRow) {
                    if ($r.mcpbOutcome -eq "mcpb_pending") {
                        $r.mcpbOutcome = "mcpb_install_failed"
                        if ($r.errorMessage) { $r.errorMessage += "; " }
                        $r.errorMessage += "mcpb path needs Claude Desktop config entry (other IDEs are uv/manual only)"
                    }
                }
                elseif ($claudeOk) { $r.mcpbOutcome = "mcpb_ok" }
                else {
                    $r.mcpbOutcome = "mcpb_smoke_failed"
                    if ($r.errorMessage) { $r.errorMessage += "; " }
                    $r.errorMessage += "Claude Desktop stdio smoke failed: $($claudeRow.error)"
                }
            }
        }
    }

    if ($Execute -and $pf.ok) {
        $body = @{
            repos       = @($repo)
            install_dir = "C:\Fleet"
            setup_venv  = $true
            setup_npm   = $true
        }
        $scriptResp = Invoke-VirtMcpPost -Path "/api/v1/fleet/install-script" -Body $body
        if ($scriptResp.script) {
            $scriptFile = Join-Path $runDir "$repo-install.ps1"
            Set-Content -LiteralPath $scriptFile -Value $scriptResp.script -Encoding UTF8
            $r.logExcerpt = "Generated install script at $scriptFile (sandbox execution pending virt-mcp install-run API)"
            $r.outcome = "install_pending"
        }
        else {
            $r.outcome = "install_failed"
            if ($r.errorMessage) { $r.errorMessage += "; " }
            $r.errorMessage += "virt-mcp install-script failed: $($scriptResp.error)"
        }
    }

    $sw.Stop()
    $r.durationSec = [int]$sw.Elapsed.TotalSeconds
    $results += $r
    Write-Host "[$repo] $($r.outcome) mcpb=$($r.mcpbOutcome)"
    Write-ColdInstallProgress -Rows $results -GeneratedAt $generatedAt -Status "running" -Total $total
}

$finalResults = @($results)
if ($BrokenOnly -and $priorSnapshot) {
    $probed = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($row in $results) { [void]$probed.Add([string]$row.repo) }
    foreach ($priorRow in @($priorSnapshot.results)) {
        if (-not $probed.Contains([string]$priorRow.repo)) { $finalResults += $priorRow }
    }
    $finalResults = @($finalResults | Sort-Object { $_.repo })
}

$summary = Get-ColdInstallSummary -Rows $finalResults
$comparison = Build-ColdInstallComparison -Prior $priorSnapshot -Rows $finalResults -Mode $probeMode -Probed $results.Count

$report = @{
    generatedAt    = $generatedAt
    reposRoot      = $reposRoot
    probeMode      = $probeMode
    sandboxProfile = "consumer"
    runId          = $runId
    preflightOnly  = [bool]$PreflightOnly
    execute        = [bool]$Execute
    testMcpb       = [bool]$TestMcpb
    summary        = $summary
    comparison     = $comparison
    results        = @($finalResults)
}

$utf8 = New-Object System.Text.UTF8Encoding $false
$reportJson = Join-Path $reportDirFull "fleet-cold-install-report.json"
[System.IO.File]::WriteAllText($reportJson, ($report | ConvertTo-Json -Depth 6), $utf8)
Write-ColdInstallProgress -Rows $finalResults -GeneratedAt $generatedAt -Status "complete" -Total $finalResults.Count

$stamp = $generatedAt.Replace(":", "-")
$mdPath = Join-Path $reportDirFull "fleet-cold-install-$stamp.md"
Write-ColdInstallMarkdown -Rows $finalResults -Summary $summary -Comparison $comparison -GeneratedAt $generatedAt -Path $mdPath
Write-ColdInstallMarkdown -Rows $finalResults -Summary $summary -Comparison $comparison -GeneratedAt $generatedAt -Path (Join-Path $reportDirFull "fleet-cold-install-report.md")

Write-Host "Report: $reportJson"
if ($comparison) {
    Write-Host "Install/doc failures: $($comparison.install_failed_now) (delta $($comparison.install_failed_delta))"
}
