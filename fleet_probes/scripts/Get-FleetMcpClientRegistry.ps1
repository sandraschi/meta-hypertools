<#
.SYNOPSIS
  Registry of MCP stdio client config locations (Windows) for fleet cold-install smoke.
.DESCRIPTION
  Discovers command+args+env+cwd entries for a fleet repo across Claude Desktop, Cursor,
  Windsurf, Antigravity, Zed (custom context_servers), and OpenCode.

  **Note:** `mcpb install` (Option A) only updates Claude Desktop - not other IDEs.
  Non-Claude entries reflect uv/manual/clone installs; use stdio outcomes for those.
.NOTES
  Aligns with patterns/MCP_CLIENT_CONFIG_SNIPPETS.md - extend here when clients change paths.
#>

function Get-FleetMcpClientProfiles {
    $userHome = $env:USERPROFILE
    $app = $env:APPDATA
    return @(
        @{
            id         = 'claude'
            label      = 'Claude Desktop'
            paths      = @((Join-Path $app 'Claude\claude_desktop_config.json'))
            format     = 'mcpServers'
            serversKey = 'mcpServers'
        }
        @{
            id         = 'cursor'
            label      = 'Cursor'
            paths      = @(
                (Join-Path $userHome '.cursor\mcp.json')
                (Join-Path $app 'Cursor\User\globalStorage\cursor-storage\mcp_config.json')
            )
            format     = 'mcpServers'
            serversKey = 'mcpServers'
        }
        @{
            id         = 'windsurf'
            label      = 'Windsurf'
            paths      = @((Join-Path $userHome '.codeium\windsurf\mcp_config.json'))
            format     = 'mcpServers'
            serversKey = 'mcpServers'
        }
        @{
            id         = 'antigravity'
            label      = 'Antigravity'
            paths      = @(
                (Join-Path $userHome '.gemini\antigravity\mcp_config.json')
                (Join-Path $userHome '.gemini\config\mcp_config.json')
            )
            format     = 'mcpServers'
            serversKey = 'mcpServers'
        }
        @{
            id         = 'zed'
            label      = 'Zed'
            paths      = @((Join-Path $app 'Zed\settings.json'))
            format     = 'zedContext'
            serversKey = 'context_servers'
        }
        @{
            id         = 'opencode'
            label      = 'OpenCode'
            paths      = @(
                (Join-Path $userHome '.config\opencode\opencode.json')
                (Join-Path $userHome '.opencode\opencode.json')
            )
            format     = 'opencode'
            serversKey = 'mcp'
        }
    )
}

function Test-FleetMcpServerMatchesRepo {
    param(
        [string]$ServerName,
        $Entry,
        [string]$Repo,
        [string]$RepoPath
    )
    $repoLower = $Repo.ToLowerInvariant()
    $nameLower = $ServerName.ToLowerInvariant()
    if ($nameLower -eq $repoLower) { return $true }
    if ($nameLower -like "*$repoLower*") { return $true }
    $stem = $repoLower -replace '-mcp$', ''
    if ($stem -and ($nameLower -like "*$stem*")) { return $true }
    try {
        $blob = ($Entry | ConvertTo-Json -Depth 6 -Compress).ToLowerInvariant()
        $pathNorm = $RepoPath.Replace('\', '/').ToLowerInvariant()
        if ($blob -like "*$pathNorm*") { return $true }
        if ($blob -like "*repos/$repoLower*") { return $true }
    } catch { }
    return $false
}

function Convert-FleetMcpEntryToSmokeSpec {
    param(
        [string]$Format,
        $Entry
    )
    if (-not $Entry) { return $null }

    if ($Format -eq 'opencode') {
        if ($Entry.enabled -eq $false) { return $null }
        $parts = @($Entry.command)
        if ($parts.Count -lt 1) { return $null }
        return @{
            command = [string]$parts[0]
            args    = @($parts | Select-Object -Skip 1)
            env     = @{}
            cwd     = $null
        }
    }

    if ($Format -eq 'zedContext') {
        if ($Entry.source -and $Entry.source -ne 'custom') { return $null }
        if (-not $Entry.command) { return $null }
        if ($Entry.enabled -eq $false) { return $null }
        $envMap = @{}
        if ($Entry.env) {
            foreach ($k in $Entry.env.PSObject.Properties.Name) { $envMap[$k] = [string]$Entry.env.$k }
        }
        return @{
            command = [string]$Entry.command
            args    = @($Entry.args)
            env     = $envMap
            cwd     = if ($Entry.cwd) { [string]$Entry.cwd } else { $null }
        }
    }

    # mcpServers (Claude, Cursor, Windsurf, Antigravity)
    if ($Entry.disabled -eq $true) { return $null }
    if (-not $Entry.command) { return $null }
    $envMap = @{}
    if ($Entry.env) {
        foreach ($k in $Entry.env.PSObject.Properties.Name) { $envMap[$k] = [string]$Entry.env.$k }
    }
    return @{
        command = [string]$Entry.command
        args    = @($Entry.args)
        env     = $envMap
        cwd     = if ($Entry.cwd) { [string]$Entry.cwd } else { $null }
    }
}

function Get-FleetMcpStdioEntriesForRepo {
    param(
        [string]$Repo,
        [string]$ReposRoot = "D:\Dev\repos",
        [string[]]$ClientFilter = @()
    )
    $repoPath = Join-Path $ReposRoot $Repo
    $found = @()
    $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)

    foreach ($profile in Get-FleetMcpClientProfiles) {
        if ($ClientFilter.Count -gt 0 -and ($profile.id -notin $ClientFilter)) { continue }
        foreach ($cfgPath in $profile.paths) {
            if (-not (Test-Path -LiteralPath $cfgPath)) { continue }
            try {
                $cfg = Get-Content -LiteralPath $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
            } catch { continue }
            $servers = $cfg.($profile.serversKey)
            if (-not $servers) { continue }
            foreach ($name in $servers.PSObject.Properties.Name) {
                $entry = $servers.$name
                if (-not (Test-FleetMcpServerMatchesRepo -ServerName $name -Entry $entry -Repo $Repo -RepoPath $repoPath)) {
                    continue
                }
                $spec = Convert-FleetMcpEntryToSmokeSpec -Format $profile.format -Entry $entry
                if (-not $spec) { continue }
                $dedupe = "$($profile.id)|$name|$($spec.command)|$($spec.args -join ' ')"
                if ($seen.Contains($dedupe)) { continue }
                [void]$seen.Add($dedupe)
                $found += [PSCustomObject]@{
                    clientId   = $profile.id
                    client     = $profile.label
                    configPath = $cfgPath
                    serverName = $name
                    command    = $spec.command
                    args       = @($spec.args)
                    env        = $spec.env
                    cwd        = $spec.cwd
                }
            }
        }
    }
    return @($found)
}
