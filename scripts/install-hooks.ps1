#Requires -Version 7.0
<#
.SYNOPSIS
    Install the MetaMCP pre-commit hook (relaxed biome: lint only).
.DESCRIPTION
    Writes .git/hooks/pre-commit: ruff check + ruff format --check on staged
    Python, biome lint (NOT format) on staged web_sota TS/TSX. Formatting is
    advisory on purpose - the web_sota tree is CRLF and biome enforces LF, so
    a format gate would block every commit. Run 'just fix' to format.
    Idempotent; use -Force to overwrite an existing hook.
#>
[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$hookPath = Join-Path $repoRoot '.git/hooks/pre-commit'

if ((Test-Path -LiteralPath $hookPath) -and (-not $Force)) {
    Write-Host 'Pre-commit hook already installed. Use -Force to overwrite.' -ForegroundColor Green
    exit 0
}

$hook = @'
#!/usr/bin/env bash
# MetaMCP pre-commit hook: ruff + biome-lint on staged files only.
# NOTE: biome runs `lint` (not `check`) - formatting is advisory
# (web_sota is CRLF, biome enforces LF). Run `just fix` to format.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

RUFF=""
if command -v ruff >/dev/null 2>&1; then
  RUFF="ruff"
elif [ -x ".venv/Scripts/ruff.exe" ]; then
  RUFF=".venv/Scripts/ruff.exe"
elif [ -x ".venv/bin/ruff" ]; then
  RUFF=".venv/bin/ruff"
else
  echo "pre-commit: ruff not found (install dev deps: uv sync --extra dev)"
  exit 1
fi

mapfile -t STAGED_PY < <(git diff --cached --name-only --diff-filter=ACMR | grep -E '\.py$' || true)
if [ "${#STAGED_PY[@]}" -gt 0 ]; then
  echo "=== Pre-commit: Ruff check (staged Python) ==="
  "$RUFF" check "${STAGED_PY[@]}"
  echo "=== Pre-commit: Ruff format check (staged Python) ==="
  "$RUFF" format --check "${STAGED_PY[@]}"
fi

mapfile -t STAGED_TS < <(git diff --cached --name-only --diff-filter=ACMR | grep -E '^web_sota/src/.*\.(ts|tsx|js|jsx)$' || true)
if [ -d "web_sota" ] && [ -f "web_sota/package.json" ] && [ "${#STAGED_TS[@]}" -gt 0 ]; then
  echo "=== Pre-commit: Biome lint (staged web_sota; format is advisory, run just fix to format) ==="
  BIOME_ARGS=()
  for f in "${STAGED_TS[@]}"; do
    BIOME_ARGS+=("${f#web_sota/}")
  done
  (
    cd web_sota
    npx @biomejs/biome lint "${BIOME_ARGS[@]}"
  )
fi

echo "=== Pre-commit: All checks passed ==="
'@

Set-Content -LiteralPath $hookPath -Value $hook -Encoding utf8NoBOM -NoNewline
Write-Host 'Pre-commit hook installed.' -ForegroundColor Green
