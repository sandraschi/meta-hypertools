
<#
.SYNOPSIS
    Fleet MCP Server Standards Checker (SOTA 2026)

.DESCRIPTION
    Analyzes an MCP server repository for compliance with current fleet
    standards (mcp-central-docs):
      - FastMCP 3.4+ (pyproject version floor, no description= in @mcp.tool)
      - MCPB packaging (manifest.json, assets/icon.png, prompts 3-4-100)
      - CI/CD workflow (GitHub Actions ci.yml)
      - Test scaffold (pytest configured in pyproject.toml)
      - Folder structure (src/, docs/, tests/)
      - Documentation (README, CHANGELOG, llms.txt, llms-full.txt, glama.json)
      - Repo root cleanliness
      - Modern tooling (uv + uv.lock, ruff, justfile)

    Generates two outputs:
      1. docs/repository-analysis-{date}.md - Detailed report
      2. scripts/fix-standards.ps1 - Auto-remediation script (dirs only)

.PARAMETER GenerateFixScript
    Generate the remediation script (default: true)

.PARAMETER Verbose
    Show detailed checking progress

.EXAMPLE
    .\scripts\check-repo-standards.ps1

.EXAMPLE
    .\scripts\check-repo-standards.ps1 -Verbose
#>

param(
    [switch]$GenerateFixScript = $true,
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=============================================================" -ForegroundColor Magenta
Write-Host "  Fleet MCP Server Standards Checker (SOTA 2026)" -ForegroundColor Magenta
Write-Host "=============================================================" -ForegroundColor Magenta
Write-Host ""

# Check we are in a repo
if (-not (Test-Path "pyproject.toml") -and -not (Test-Path ".git")) {
    Write-Host "Error: Must run from repository root" -ForegroundColor Red
    exit 1
}

$repoName = (Get-Item .).Name
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$date = Get-Date -Format "yyyy-MM-dd"

Write-Host "Analyzing Repository: $repoName" -ForegroundColor Cyan
Write-Host "   Timestamp: $timestamp" -ForegroundColor Gray
Write-Host ""

$results = @{
    RepoName   = $repoName
    Timestamp  = $timestamp
    Scores     = @{}
    Issues     = @()
    Fixes      = @()
    Summary    = @{}
}

function Add-Issue {
    param([string]$Category, [string]$Message, [int]$Penalty)
    $script:results.Issues += $Message
    $script:results.Scores[$Category] = [Math]::Max(0, $script:results.Scores[$Category] - $Penalty)
    if ($Verbose) {
        Write-Host "  [ISSUE] $Message" -ForegroundColor DarkYellow
    }
}

# ============================================================================
# SECTION 1: FastMCP 3.4+ Compliance
# ============================================================================
Write-Host "Checking FastMCP 3.4+ compliance..." -ForegroundColor Yellow
$results.Scores["FastMCP"] = 10

$pyproject = if (Test-Path "pyproject.toml") { Get-Content "pyproject.toml" -Raw } else { "" }

if ($pyproject -match 'fastmcp\s*(?:\[[^\]]*\])?\s*[>=~]=\s*([0-9.]+)') {
    $fmVersion = [version]$Matches[1]
    if ($fmVersion -lt [version]"3.4.0") {
        Add-Issue -Category "FastMCP" -Message "FastMCP $fmVersion is below the 3.4+ floor (pyproject.toml)" -Penalty 4
    } else {
        Write-Host "  FastMCP $fmVersion OK (3.4+ floor met)" -ForegroundColor Green
    }
} else {
    Add-Issue -Category "FastMCP" -Message "No fastmcp>=3.4 dependency found in pyproject.toml" -Penalty 5
}

# Obsolete decorator pattern: @mcp.tool(description=...) (pre-3.x)
if (Test-Path "src") {
    $toolFiles = Get-ChildItem -Path "src" -Filter "*.py" -Recurse -ErrorAction SilentlyContinue
    $descHits = 0
    foreach ($file in $toolFiles) {
        $content = Get-Content $file.FullName -Raw
        if ($content -match '@mcp\.tool\([^)]*description\s*=') {
            $descHits++
        }
    }
    if ($descHits -gt 0) {
        Add-Issue -Category "FastMCP" -Message "$descHits @mcp.tool(description=) decorators - use docstring + Annotated[Field] instead" -Penalty 3
    } else {
        Write-Host "  No obsolete description= decorators" -ForegroundColor Green
    }
}

# ============================================================================
# SECTION 2: MCPB Packaging
# ============================================================================
Write-Host "Checking MCPB packaging..." -ForegroundColor Yellow
$results.Scores["MCPB"] = 10

function Get-McpbPath {
    param([string]$Relative)
    foreach ($base in @(".", "mcpb")) {
        $candidate = Join-Path $base $Relative
        if (Test-Path $candidate) { return $candidate }
    }
    return (Join-Path "." $Relative)
}

$mcpbChecks = @(
    @{ File = "manifest.json";              Label = "MCPB manifest" },
    @{ File = "assets/icon.png";            Label = "Icon asset (png 256x256)" },
    @{ File = "assets/prompts/system.md";   Label = "System prompt (3000+ words)" },
    @{ File = "assets/prompts/user.md";     Label = "User prompt (4000+ words)" },
    @{ File = "assets/prompts/examples.json"; Label = "Examples (100+ mappings)" }
)

foreach ($c in $mcpbChecks) {
    $resolved = Get-McpbPath $c.File
    if (-not (Test-Path $resolved)) {
        Add-Issue -Category "MCPB" -Message "Missing: $($c.File) ($($c.Label))" -Penalty 2
    }
}

# Prompt word-count gates (3-4-100 rule)
$sysPrompt = Get-McpbPath "assets/prompts/system.md"
if (Test-Path $sysPrompt) {
    $words = ((Get-Content $sysPrompt -Raw -ErrorAction SilentlyContinue) -split "\s+" | Where-Object { $_ }).Count
    if ($words -lt 3000) {
        Add-Issue -Category "MCPB" -Message "assets/prompts/system.md is $words words (need 3000+)" -Penalty 2
    }
}
$userPrompt = Get-McpbPath "assets/prompts/user.md"
if (Test-Path $userPrompt) {
    $words = ((Get-Content $userPrompt -Raw -ErrorAction SilentlyContinue) -split "\s+" | Where-Object { $_ }).Count
    if ($words -lt 4000) {
        Add-Issue -Category "MCPB" -Message "assets/prompts/user.md is $words words (need 4000+)" -Penalty 2
    }
}
$examplesFile = Get-McpbPath "assets/prompts/examples.json"
if (Test-Path $examplesFile) {
    try {
        $examples = Get-Content $examplesFile -Raw | ConvertFrom-Json
        $count = @($examples).Count
        if ($count -lt 100) {
            Add-Issue -Category "MCPB" -Message "examples.json has $count entries (need 100+)" -Penalty 2
        }
    } catch {
        Add-Issue -Category "MCPB" -Message "examples.json is not valid JSON" -Penalty 3
    }
}

# ============================================================================
# SECTION 3: CI/CD
# ============================================================================
Write-Host "Checking CI/CD..." -ForegroundColor Yellow
$results.Scores["CICD"] = 10

if (-not (Test-Path ".github/workflows/ci.yml")) {
    Add-Issue -Category "CICD" -Message "Missing .github/workflows/ci.yml" -Penalty 4
} else {
    Write-Host "  ci.yml present" -ForegroundColor Green
}

# ============================================================================
# SECTION 4: Test Scaffold
# ============================================================================
Write-Host "Checking test scaffold..." -ForegroundColor Yellow
$results.Scores["Tests"] = 10

if (-not (Test-Path "tests")) {
    Add-Issue -Category "Tests" -Message "Missing tests/ directory" -Penalty 5
} else {
    $testFiles = Get-ChildItem -Path "tests" -Filter "test_*.py" -Recurse -ErrorAction SilentlyContinue
    if ($testFiles.Count -eq 0) {
        Add-Issue -Category "Tests" -Message "No test_*.py files in tests/" -Penalty 3
    }
}
if ($pyproject -notmatch 'pytest') {
    Add-Issue -Category "Tests" -Message "pytest not configured in pyproject.toml" -Penalty 2
}

# ============================================================================
# SECTION 5: Folder Structure
# ============================================================================
Write-Host "Checking folder structure..." -ForegroundColor Yellow
$results.Scores["Structure"] = 10

foreach ($dir in @("src", "docs", "tests")) {
    if (-not (Test-Path $dir)) {
        Add-Issue -Category "Structure" -Message "Missing directory: $dir/" -Penalty 3
    }
}

# ============================================================================
# SECTION 6: Documentation
# ============================================================================
Write-Host "Checking documentation..." -ForegroundColor Yellow
$results.Scores["Documentation"] = 10

$docFiles = @("README.md", "CHANGELOG.md", "llms.txt", "llms-full.txt", "glama.json")
foreach ($doc in $docFiles) {
    if (-not (Test-Path $doc)) {
        Add-Issue -Category "Documentation" -Message "Missing: $doc" -Penalty 2
    }
}

# ============================================================================
# SECTION 7: Repo Root Cleanliness
# ============================================================================
Write-Host "Checking repo root cleanliness..." -ForegroundColor Yellow
$results.Scores["Cleanliness"] = 10

$rubbishPatterns = @("*.dxt", "*.old", "*.bak", "*.backup", "*.tmp", "*.temp", "*_backup.*", "*_old.*", "*.log")
$rootFiles = Get-ChildItem -File -ErrorAction SilentlyContinue
foreach ($file in $rootFiles) {
    foreach ($pattern in $rubbishPatterns) {
        if ($file.Name -like $pattern) {
            Add-Issue -Category "Cleanliness" -Message "Rubbish in root: $($file.Name)" -Penalty 1
            break
        }
    }
}

# ============================================================================
# SECTION 8: Modern Tooling
# ============================================================================
Write-Host "Checking modern tooling..." -ForegroundColor Yellow
$results.Scores["Tooling"] = 10

if (-not (Test-Path "pyproject.toml")) {
    Add-Issue -Category "Tooling" -Message "Missing pyproject.toml" -Penalty 5
}
if (-not (Test-Path "uv.lock")) {
    Add-Issue -Category "Tooling" -Message "Missing uv.lock (uv package manager)" -Penalty 2
}
if ($pyproject -notmatch 'ruff') {
    Add-Issue -Category "Tooling" -Message "No ruff configuration in pyproject.toml" -Penalty 2
}
if (-not (Test-Path "justfile")) {
    Add-Issue -Category "Tooling" -Message "Missing justfile" -Penalty 1
}

# ============================================================================
# Overall score
# ============================================================================
$overallScore = ($results.Scores.Values | Measure-Object -Average).Average
$results.Summary["OverallScore"] = [Math]::Round($overallScore, 1)
$results.Summary["TotalIssues"] = $results.Issues.Count

$grade = switch ($overallScore) {
    { $_ -ge 9.0 } { "EXCELLENT"; break }
    { $_ -ge 8.0 } { "GOOD"; break }
    { $_ -ge 7.0 } { "NEEDS WORK"; break }
    { $_ -ge 6.0 } { "POOR"; break }
    default        { "CRITICAL"; break }
}
$results.Summary["Grade"] = $grade

# ============================================================================
# Generate Report
# ============================================================================
Write-Host "Generating report..." -ForegroundColor Cyan

$reportPath = "docs/repository-analysis-$date.md"
if (-not (Test-Path "docs")) {
    New-Item -ItemType Directory -Path "docs" -Force | Out-Null
}

$scoreRows = ($results.Scores.Keys | Sort-Object | ForEach-Object {
    "| $($_) | $($results.Scores[$_])/10 |"
}) -join "`n"

$issueList = if ($results.Issues.Count -eq 0) { "None - repository is compliant." } else {
    ($results.Issues | ForEach-Object { "- $_" }) -join "`n"
}

$report = @"
# Repository Standards Analysis - $repoName

**Date:** $timestamp
**Overall Score:** $($results.Summary.OverallScore)/10
**Grade:** $grade

---

## Scores by Category

| Category | Score |
|----------|-------|
$scoreRows

---

## Issues Found ($($results.Issues.Count))

$issueList

---

## References

- Standards: mcp-central-docs/standards/SOTA_REQUIREMENTS.md
- FastMCP: mcp-central-docs/standards/SOTA_REQUIREMENTS.md (3.4+ floor)
- MCPB: mcp-central-docs/standards/MCPB_PACKAGING_STANDARDS.md
- Tool design: mcp-central-docs/standards/TOOL_DESIGN_STANDARDS.md
- Ports: mcp-central-docs/operations/WEBAPP_PORTS.md
- Verification: mcp-central-docs/standards/VERIFICATION_STANDARDS.md

---

**Generated by:** check-repo-standards.ps1 (SOTA 2026)
**Report saved to:** $reportPath
"@

Set-Content -Path $reportPath -Value $report -Encoding utf8
Write-Host "  Report saved: $reportPath" -ForegroundColor Green

# ============================================================================
# Generate Fix Script (directories only - no dead template copies)
# ============================================================================
if ($GenerateFixScript -and $results.Fixes.Count -gt 0) {
    $fixScriptPath = "scripts/fix-standards.ps1"
    if (-not (Test-Path "scripts")) {
        New-Item -ItemType Directory -Path "scripts" -Force | Out-Null
    }
    $lines = @(
        "#!/usr/bin/env pwsh",
        "# Auto-generated remediation for $repoName",
        "# Generated: $timestamp",
        "param([switch]`$DryRun = `$false)",
        "Write-Host 'Creating missing directories...' -ForegroundColor Cyan",
        "foreach (`$dir in @('src','docs','tests','assets','assets/prompts')) {",
        "    if (-not (Test-Path `$dir)) {",
        "        if (`$DryRun) { Write-Host ('[DRY-RUN] Would create ' + `$dir) -ForegroundColor Yellow }",
        "        else { New-Item -ItemType Directory -Path `$dir -Force | Out-Null; Write-Host ('Created ' + `$dir) -ForegroundColor Green }",
        "    }",
        "}",
        "Write-Host 'Content fixes (prompts, docs, config) are manual - see docs/repository-analysis-$date.md' -ForegroundColor Yellow"
    )
    Set-Content -Path $fixScriptPath -Value $lines -Encoding utf8
    Write-Host "  Fix script saved: $fixScriptPath" -ForegroundColor Green
}

# ============================================================================
# Display Summary
# ============================================================================
Write-Host ""
Write-Host "=============================================================" -ForegroundColor Magenta
Write-Host "  Analysis Complete!" -ForegroundColor Magenta
Write-Host "=============================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Overall Score: $($results.Summary.OverallScore)/10 - $grade" -ForegroundColor $(if ($overallScore -ge 8) { "Green" } else { "Yellow" })
Write-Host ""
Write-Host "Category Scores:" -ForegroundColor White
foreach ($category in $results.Scores.Keys | Sort-Object) {
    $score = $results.Scores[$category]
    $color = if ($score -ge 8) { "Green" } elseif ($score -ge 6) { "Yellow" } else { "Red" }
    Write-Host ("  {0,-15} {1}/10" -f $category, $score) -ForegroundColor $color
}
Write-Host ""
Write-Host "Issues: $($results.Issues.Count)" -ForegroundColor $(if ($results.Issues.Count -eq 0) { "Green" } else { "Yellow" })
Write-Host "Report: $reportPath" -ForegroundColor White
Write-Host ""


