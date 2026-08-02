<#
.SYNOPSIS
  Build fleet-cold-install-manifest.json from fleet repos with INSTALL.md.
.DESCRIPTION
  Scans FLEET_REPOS_ROOT for INSTALL.md, detects Option A/B/C hints, probes GitHub
  releases API for .mcpb assets (mcpbAvailable, mcpbReleasesUrl, mcpbAssetName).
  Preserves manual edits when repo id matches.
.EXAMPLE
  .\scripts\sync-fleet-cold-install-manifest.ps1
  .\scripts\sync-fleet-cold-install-manifest.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [string]$ReposRoot = "",
    [string]$ManifestPath = "scripts/fleet-cold-install-manifest.json",
    [string]$WebappManifestPath = "scripts/fleet-webapp-manifest.json",
    [switch]$DryRun,
    [switch]$SkipGithubApi
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$mcdRoot = Split-Path -Parent $scriptRoot
if (-not $ReposRoot) {
    $ReposRoot = if ($env:FLEET_REPOS_ROOT) { $env:FLEET_REPOS_ROOT } else { "D:\Dev\repos" }
}
$manifestFull = Join-Path $mcdRoot $ManifestPath
$webappManifestFull = Join-Path $mcdRoot $WebappManifestPath

$defaultSkip = @('meta_mcp', 'mcp-central-docs', 'pinokio-mcp', '_legacy_junk', 'external', 'sandraschi')

function Find-InstallMd {
    param([string]$RepoPath)
    foreach ($rel in @('INSTALL.md', 'docs\INSTALL.md', 'docs\install.md', 'docs\readme\INSTALL.md')) {
        $p = Join-Path $RepoPath $rel
        if (Test-Path -LiteralPath $p) { return $rel.Replace('\', '/') }
    }
    return $null
}

function Get-InstallOptions {
    param([string]$Content)
    $opts = @()
    if ($Content -match '(?i)option\s+a|\.mcpb|drag.*claude') { $opts += 'A' }
    if ($Content -match '(?i)npx\s+@anthropic-ai/mcpb|option\s+b') { $opts += 'B' }
    if ($Content -match '(?i)uv\s+sync|option\s+c|winget.*git') { $opts += 'C' }
    return @($opts | Select-Object -Unique)
}

function Get-GithubRepoSlug {
    param([string]$RepoPath, [string]$RepoName)
    Push-Location $RepoPath
    try {
        $url = $null
        try {
            $url = git remote get-url origin 2>$null
        } catch {
            $url = $null
        }
        if ($url -and ($url -match 'github\.com[:/]([^/]+)/([^/.]+)')) {
            return @{ owner = $Matches[1]; repo = $Matches[2] -replace '\.git$', '' }
        }
    } finally { Pop-Location }
    return @{ owner = 'sandraschi'; repo = $RepoName }
}

function Get-McpbReleaseInfo {
    param([string]$Owner, [string]$Repo)
    if ($SkipGithubApi) {
        return @{ available = $false; url = "https://github.com/$Owner/$Repo/releases"; asset = $null }
    }
    $api = "https://api.github.com/repos/$Owner/$Repo/releases/latest"
    try {
        $headers = @{ 'User-Agent' = 'fleet-cold-install-manifest-sync' }
        if ($env:GITHUB_TOKEN) { $headers['Authorization'] = "Bearer $env:GITHUB_TOKEN" }
        $release = Invoke-RestMethod -Uri $api -Headers $headers -TimeoutSec 20
        $asset = $null
        foreach ($a in @($release.assets)) {
            if ($a.name -match '\.mcpb$') { $asset = $a.name; break }
        }
        return @{
            available = [bool]$asset
            url       = "https://github.com/$Owner/$Repo/releases"
            asset     = $asset
        }
    } catch {
        return @{ available = $false; url = "https://github.com/$Owner/$Repo/releases"; asset = $null }
    }
}

$existing = @{}
if (Test-Path -LiteralPath $manifestFull) {
    $old = Get-Content $manifestFull -Raw | ConvertFrom-Json
    foreach ($row in @($old)) {
        $existing[$row.repo] = $row
    }
}

$webappRepos = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
if (Test-Path -LiteralPath $webappManifestFull) {
    $wm = Get-Content $webappManifestFull -Raw | ConvertFrom-Json
    foreach ($w in @($wm)) { if ($w.repo) { [void]$webappRepos.Add([string]$w.repo) } }
}

$entries = [System.Collections.Generic.List[object]]::new()
Get-ChildItem -Path $ReposRoot -Directory | Where-Object { $_.Name -notmatch '^_' } | ForEach-Object {
    $repo = $_.Name
    if ($repo -in $defaultSkip) { return }
    $repoPath = $_.FullName
    $installRel = Find-InstallMd -RepoPath $repoPath
    if (-not $installRel) { return }

    $installFull = Join-Path $repoPath ($installRel.Replace('/', '\'))
    $content = Get-Content -LiteralPath $installFull -Raw -Encoding UTF8
    $options = Get-InstallOptions -Content $content
    $slug = Get-GithubRepoSlug -RepoPath $repoPath -RepoName $repo
    $mcpb = Get-McpbReleaseInfo -Owner $slug.owner -Repo $slug.repo

    $prior = $existing[$repo]
    $entry = [ordered]@{
        repo              = $repo
        installPath       = $installRel
        installOptions    = $options
        githubOwner       = $slug.owner
        githubRepo        = $slug.repo
        mcpbAvailable     = $mcpb.available
        mcpbReleasesUrl   = $mcpb.url
        mcpbAssetName     = $mcpb.asset
        studioSmokeArgs   = $null
        hasWebapp         = $webappRepos.Contains($repo)
        probeSkip         = $false
        primaryOption     = if ($options -contains 'C') { 'C' } elseif ($options -contains 'A') { 'A' } else { 'unknown' }
        note              = ''
    }

    if ($prior) {
        foreach ($key in @('probeSkip', 'studioSmokeArgs', 'note', 'primaryOption')) {
            if ($prior.PSObject.Properties.Name -contains $key -and $null -ne $prior.$key -and "$($prior.$key)" -ne '') {
                $entry[$key] = $prior.$key
            }
        }
    }

    [void]$entries.Add([PSCustomObject]$entry)
}

$sorted = @($entries | Sort-Object { $_.repo })
Write-Host "Manifest entries: $($sorted.Count) (repos with INSTALL.md under $ReposRoot)"

if ($DryRun) {
    $sorted | Select-Object repo, installPath, primaryOption, mcpbAvailable, mcpbAssetName | Format-Table -AutoSize
    exit 0
}

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($manifestFull, ($sorted | ConvertTo-Json -Depth 5), $utf8NoBom)
Write-Host "Wrote $manifestFull"
