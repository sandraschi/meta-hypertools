set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]
import 'scripts/just/fleet.just'

REPO := justfile_directory()
NAME := "meta_mcp"

# --- Dashboard ---

# Open the interactive recipe dashboard in the browser
default:
    @powershell.exe -NoProfile -ExecutionPolicy Bypass -File ../mcp-central-docs/scripts/just-industrial-dashboard.ps1 -Path . -Title meta-hypertools -Version 0.5.1 -Subtitle "meta-hypertools Orchestrator"

# --- Sovereign ---

# Load Tier 1 + 2 (High Priority / Pro Mode)
pro:
    uv run py scripts/mcp-swapper.py tier1 tier2

# Load Tier 1 + 3 (Creative / Rendering Mode)
creative:
    uv run py scripts/mcp-swapper.py tier1 tier3

# Load Tier 1 only (Minimalist / Core Mode)
core:
    uv run py scripts/mcp-swapper.py tier1

# Full manual tier swapper switch
swapper *tiers:
    uv run py scripts/mcp-swapper.py {{tiers}}

# List available server tiers
tiers:
    uv run py scripts/mcp-swapper.py --list

# --- Maintenance ---

# Check repository for SOTA Industrial Standards
health:
    powershell.exe scripts/check-repo-standards.ps1

# Apply automated repository fixes
doctor:
    if (Test-Path "scripts/fix-standards.ps1") { pwsh scripts/fix-standards.ps1 } else { Write-Host "No fix script found. Run 'just health' first." -ForegroundColor Yellow }

# Kill zombie MCP processes and cleanup
cleanup:
    if (Test-Path "scripts/kill-zombies.ps1") { pwsh scripts/kill-zombies.ps1 }
    uv run py scripts/meta-ops.py emoji-buster .

# --- Discovery ---

# Analyze MCP fleet and find "runts" (outdated servers)
analyze:
    uv run py scripts/meta-ops.py analyze-runts

# Deep scan of all MCP repositories
deep-scan:
    uv run py scripts/meta-ops.py analyze-runts --deep

# Dump all registered MCP tool names
tools:
    uv run py scripts/dump_mcp_tools.py

# --- MCPB  Claude Desktop bundle ---

# --- Quality ---

# Execute Ruff linting
lint:
    uv run ruff check .

# Execute Ruff fix + format + Biome + pre-commit install
fix:
    uv run ruff check . --fix --unsafe-fixes
    uv run ruff format .
    if (Test-Path "web_sota") { Set-Location web_sota; npx @biomejs/biome check --write --unsafe src/ }
    if (-not (Test-Path ".git/hooks/pre-commit")) { Write-Host "Pre-commit hook not installed. Run 'just install-hooks'." -ForegroundColor Yellow }

# Install pre-commit hook (relaxed biome: lint only, format advisory)
install-hooks:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File '{{REPO}}/scripts/install-hooks.ps1'

# Run all tests
test:
    uv run pytest tests/ -v

# Run frontend unit tests (vitest)
vitest:
    Set-Location web_sota; npx vitest run

# Install Playwright browsers
playwright-install:
    Set-Location web_sota; npx playwright install chromium

# Run Playwright e2e tests (starts backend automatically)
e2e:
    Set-Location web_sota; npx playwright test

# Run all test suites: backend + frontend + e2e
test-all: test vitest e2e

# --- Operations ---

# Launch the full stack (API + Frontend) via the fleet start script
serve:
    powershell.exe -NoProfile -File start.ps1

# MCP stdio transport
mcp-stdio:
    uv run meta_mcp-server

# Refresh dependencies
sync:
    uv sync --group dev

# --- Utilities ---

# Pack repository for large context sharing
pack path=".":
    uv run py scripts/meta-ops.py pack {{path}}

# --- Native ---

# Full Tauri release: Vite + PyInstaller sidecar + NSIS/MSI installer (see docs/TAURI.md)
build-native:
    powershell.exe -NoProfile -File '{{REPO}}\native\build.ps1'

# Build the PyInstaller backend .exe only
build-sidecar:
    powershell.exe -NoProfile -File '{{REPO}}\native\build-sidecar.ps1'

# Restart Ollama engine (kill + launch serve detached)
ollama-restart:
    taskkill /F /IM ollama.exe 2>nul; taskkill /F /IM "ollama app.exe" 2>nul
    Start-Sleep -Seconds 2
    $ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (Test-Path $ollama) { Start-Process $ollama -ArgumentList serve -WindowStyle Hidden }
    for ($i = 0; $i -lt 15; $i++) { Start-Sleep -Seconds 1; try { $r = Invoke-WebRequest -Uri http://127.0.0.1:11434/api/version -TimeoutSec 1 -UseBasicParsing -ErrorAction SilentlyContinue; if ($r.StatusCode -eq 200) { Write-Host "Ollama ready on port 11434" -ForegroundColor Green; break } } catch {} }
    if ($i -ge 14) { Write-Host "Ollama did not start within 15s" -ForegroundColor Red }

# Tauri dev (Vite on :10719, stub sidecar if missing)
tauri-dev:
    Set-Location '{{justfile_directory()}}\native'; $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"; powershell.exe -NoProfile -File ensure-sidecar-stub.ps1; npm install; npx @tauri-apps/cli dev

# PyInstaller sidecar only
tauri-sidecar:
    powershell.exe -NoProfile -File '{{justfile_directory()}}\native\build-sidecar.ps1'

# Tauri bundle only (requires prior frontend + sidecar builds)
build-native-debug:
	Set-Location '{{justfile_directory()}}\native'; $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"; powershell.exe -NoProfile -File ensure-sidecar-stub.ps1; npm install; npx @tauri-apps/cli build --debug


# Bootstrap: install dev deps + pre-commit hook
bootstrap:
    uv sync --group dev
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File '{{REPO}}/scripts/install-hooks.ps1'
    Write-Host "Pre-commit hooks installed." -ForegroundColor Green
