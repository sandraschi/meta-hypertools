
<#
.SYNOPSIS
    SOTA Fullstack App Builder - generates a complete fleet-standard web
    application in one pass. This is the 2768-line monolith: one script,
    one linear flow, a whole repo.

.DESCRIPTION
    Generates a fleet-compliant fullstack application:
      - Backend:  FastMCP 3.4+ server (Python, uv) with FastAPI HTTP app,
                  SQLite (members/products/orders), APScheduler jobs,
                  log ring buffer, /api/health + /api/v1/diagnostics
      - Frontend: React 18 + Vite + TypeScript + TailwindCSS (dark Zinc
                  theme) + Lucide + Zustand + Bun, with Dashboard, Tools,
                  Skills, Chat (skill-first, local LLM), Members, Shop,
                  Cart, Jobs, Logs, API Docs, Onboarding, Settings, Help
      - Quality:  data-testid everywhere, Playwright e2e, pytest,
                  GitHub Actions CI, README + llms.txt
      - Optional: Tauri 2.0 desktop wrapper, Web Speech voice, PWA,
                  file upload, email, WebSocket realtime
    Ports are adjacent and validated against the fleet range 10700-11500.

.PARAMETER AppName
    Required. Lowercase hyphenated name (2-30 chars). Becomes the repo
    directory and the Python package name.

.PARAMETER Description
    One-line description used in README, pyproject, and the dashboard hero.

.PARAMETER Author
    Author name for pyproject and README. Default: sandraschi.

.PARAMETER OutputPath
    Parent directory for the generated app. Default: current directory.

.PARAMETER Interactive
    Show the feature-selection menu instead of using defaults/flags.

.PARAMETER BackendPort
    Backend port (10700-11500). Must be adjacent to FrontendPort.

.PARAMETER FrontendPort
    Frontend port (10700-11500). Must be adjacent to BackendPort.

.PARAMETER IncludeAI
    Local LLM chat (Ollama/LM Studio/vLLM probe). Default: on.

.PARAMETER IncludeMCP
    MCP streamable HTTP endpoint (/mcp). Default: on.

.PARAMETER IncludeScheduler
    APScheduler jobs + Jobs page + patrol demo job. Default: on.

.PARAMETER IncludeCI
    GitHub Actions workflow. Default: on.

.PARAMETER IncludeTesting
    pytest + Playwright e2e. Default: on.

.PARAMETER IncludeFileUpload
    Multipart upload endpoint + UI. Default: off.

.PARAMETER IncludeVoice
    Web Speech TTS/STT (browser API). Default: off.

.PARAMETER IncludePWA
    PWA manifest + service worker. Default: off.

.PARAMETER IncludeEmail
    SMTP contact endpoint. Default: off.

.PARAMETER IncludeRealtime
    WebSocket event channel. Default: off.

.PARAMETER IncludeTauri
    Tauri 2.0 desktop wrapper scaffold (native/). Default: off.

.EXAMPLE
    .\scripts\fullstack-builder.ps1 -AppName my-app

    Scaffolds my-app with all default features on ports 10700/10701.

.EXAMPLE
    .\scripts\fullstack-builder.ps1 -AppName control-room -Interactive
        -BackendPort 11200 -FrontendPort 11201

    Interactive feature selection, adjacent ports 11200/11201.

.EXAMPLE
    .\scripts\fullstack-builder.ps1 -AppName demo-app -IncludeTauri
        -IncludeVoice -IncludeScheduler

    Adds the desktop wrapper, voice, and scheduler.

.NOTES
    - Register the chosen ports in mcp-central-docs/operations/WEBAPP_PORTS.md
    - Run `uv sync` and `bun --prefix webapp install` in the generated
      project before start.ps1
    - The generated Chat page loads the server SKILL.md as its preprompt
    - This file is intentionally monolithic. Do not refactor it.
#>
# =============================================================================
# SOTA FULLSTACK APP BUILDER - Fleet-standards Web Application Generator
# =============================================================================
# Generates a fleet-compliant fullstack application:
#   - Backend:  FastMCP 3.4+ server (Python, uv) with FastAPI HTTP app
#   - Frontend: React 18 + Vite + TypeScript + TailwindCSS (dark Zinc theme)
#              + Lucide icons + Zustand + Bun
#   - Local:    SQLite (local-first), local LLM chat (Ollama/LM Studio probe)
#   - Native:   Optional Tauri 2.0 wrapper (replaces retired Electron)
#   - Quality:  data-testid, Playwright e2e, pytest, GitHub Actions CI
#   - Ports:    Fleet range 10700-11500, backend/frontend adjacent
#
# Usage:
#   .\scripts\fullstack-builder.ps1 -AppName my-app
#   .\scripts\fullstack-builder.ps1 -AppName my-app -IncludeVoice -IncludeTauri
#   .\scripts\fullstack-builder.ps1 -Interactive
#
# Notes:
#   - Register the chosen ports in mcp-central-docs/operations/WEBAPP_PORTS.md
#   - Run `uv sync` and `bun install` in the generated project before start.ps1
# =============================================================================

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidatePattern('^[a-z][a-z0-9-]{2,29}$')]
    [string]$AppName,

    [Parameter(Mandatory = $false)]
    [string]$Description = "A fleet-standard fullstack application",

    [Parameter(Mandatory = $false)]
    [string]$Author = "sandraschi",

    [Parameter(Mandatory = $false)]
    [string]$OutputPath = ".",

    [Parameter(Mandatory = $false)]
    [switch]$Interactive,

    [Parameter(Mandatory = $false)]
    [ValidateRange(10700, 11500)]
    [int]$BackendPort = 10700,

    [Parameter(Mandatory = $false)]
    [ValidateRange(10700, 11500)]
    [int]$FrontendPort = 10701,

    # Feature flags
    [switch]$IncludeAI,          # Local LLM chat (Ollama/LM Studio probe)
    [switch]$IncludeMCP,         # MCP streamable HTTP endpoint (/mcp)
    [switch]$IncludeFileUpload,  # Multipart upload endpoint + UI
    [switch]$IncludeVoice,       # Web Speech TTS/STT (browser API)
    [switch]$IncludePWA,         # PWA manifest + service worker
    [switch]$IncludeEmail,       # SMTP contact endpoint
    [switch]$IncludeRealtime,    # WebSocket event channel
    [switch]$IncludeScheduler,   # APScheduler periodic jobs (/api/jobs)
    [switch]$IncludeTauri,       # Tauri 2.0 desktop wrapper (native/)
    [switch]$IncludeCI,          # GitHub Actions workflow
    [switch]$IncludeTesting      # pytest + Playwright e2e
)

$ErrorActionPreference = "Stop"

# =============================================================================
# DEFAULTS (non-interactive mode)
# =============================================================================
if (-not $Interactive) {
    $IncludeAI = if ($PSBoundParameters.ContainsKey('IncludeAI')) { $IncludeAI } else { $true }
    $IncludeMCP = if ($PSBoundParameters.ContainsKey('IncludeMCP')) { $IncludeMCP } else { $true }
    $IncludeScheduler = if ($PSBoundParameters.ContainsKey('IncludeScheduler')) { $IncludeScheduler } else { $true }
    $IncludeCI = if ($PSBoundParameters.ContainsKey('IncludeCI')) { $IncludeCI } else { $true }
    $IncludeTesting = if ($PSBoundParameters.ContainsKey('IncludeTesting')) { $IncludeTesting } else { $true }
}

# =============================================================================
# INTERACTIVE FEATURE SELECTION
# =============================================================================
function Show-FeatureMenu {
    Write-Host ""
    Write-Host "=============================================================" -ForegroundColor Cyan
    Write-Host "  SOTA FULLSTACK APP BUILDER - Feature Selection" -ForegroundColor Cyan
    Write-Host "=============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Building: $AppName" -ForegroundColor White
    Write-Host ""

    $features = @(
        @{ Id = 1;  Name = "AI Chat (local LLM)";        Default = $true;  Var = "IncludeAI" },
        @{ Id = 2;  Name = "MCP streamable HTTP";        Default = $true;  Var = "IncludeMCP" },
        @{ Id = 3;  Name = "File upload";                Default = $false; Var = "IncludeFileUpload" },
        @{ Id = 4;  Name = "Voice input/output";         Default = $false; Var = "IncludeVoice" },
        @{ Id = 5;  Name = "PWA (offline manifest)";     Default = $false; Var = "IncludePWA" },
        @{ Id = 6;  Name = "Email (SMTP)";               Default = $false; Var = "IncludeEmail" },
        @{ Id = 7;  Name = "Realtime (WebSocket)";       Default = $false; Var = "IncludeRealtime" },
        @{ Id = 8;  Name = "Scheduler (cron jobs)";     Default = $true;  Var = "IncludeScheduler" },
        @{ Id = 9;  Name = "Tauri 2.0 desktop wrapper";  Default = $false; Var = "IncludeTauri" },
        @{ Id = 10; Name = "CI (GitHub Actions)";        Default = $true;  Var = "IncludeCI" },
        @{ Id = 11; Name = "Tests (pytest + Playwright)"; Default = $true; Var = "IncludeTesting" }
    )

    foreach ($f in $features) {
        $mark = if ($f.Default) { "[x]" } else { "[ ]" }
        Write-Host ("  {0,2}. {1,-32} {2}" -f $f.Id, $f.Name, $mark) -ForegroundColor Gray
    }
    Write-Host "  all. Enable all features"
    Write-Host "  done. Proceed with current selection"
    Write-Host ""

    $state = @{}
    foreach ($f in $features) { $state[$f.Var] = $f.Default }

    while ($true) {
        $answer = Read-Host "Toggle feature (number), 'all', or 'done'"
        if ($answer -eq "done") { break }
        if ($answer -eq "all") {
            foreach ($f in $features) { $state[$f.Var] = $true }
            Write-Host "  All features enabled." -ForegroundColor Yellow
            continue
        }
        $num = 0
        if ([int]::TryParse($answer, [ref]$num)) {
            $f = $features | Where-Object { $_.Id -eq $num }
            if ($f) {
                $state[$f.Var] = -not $state[$f.Var]
                $mark = if ($state[$f.Var]) { "[x]" } else { "[ ]" }
                Write-Host ("  {0}. {1,-32} {2}" -f $f.Id, $f.Name, $mark) -ForegroundColor Gray
            } else {
                Write-Host "  Unknown feature: $num" -ForegroundColor DarkYellow
            }
        } else {
            Write-Host "  Invalid input: $answer" -ForegroundColor DarkYellow
        }
    }

    $script:IncludeAI = $state.IncludeAI
    $script:IncludeMCP = $state.IncludeMCP
    $script:IncludeFileUpload = $state.IncludeFileUpload
    $script:IncludeVoice = $state.IncludeVoice
    $script:IncludePWA = $state.IncludePWA
    $script:IncludeEmail = $state.IncludeEmail
    $script:IncludeRealtime = $state.IncludeRealtime
    $script:IncludeScheduler = $state.IncludeScheduler
    $script:IncludeTauri = $state.IncludeTauri
    $script:IncludeCI = $state.IncludeCI
    $script:IncludeTesting = $state.IncludeTesting
}

if ($Interactive) {
    Show-FeatureMenu
    Write-Host ""
    Write-Host "Selected features:" -ForegroundColor Yellow
    Write-Host "  AI: $IncludeAI | MCP: $IncludeMCP | Upload: $IncludeFileUpload | Voice: $IncludeVoice | PWA: $IncludePWA"
    Write-Host "  Email: $IncludeEmail | Realtime: $IncludeRealtime | Scheduler: $IncludeScheduler | Tauri: $IncludeTauri | CI: $IncludeCI | Tests: $IncludeTesting"
    Write-Host ""
}

# =============================================================================
# CONFIGURATION & VALIDATION
# =============================================================================
$PkgName = $AppName -replace '-', '_'
$AppDir = Join-Path $OutputPath $AppName

if (Test-Path $AppDir) {
    throw "Target directory already exists: $AppDir"
}
if (Test-Path (Join-Path $OutputPath $PkgName)) {
    throw "Python package directory already exists: $(Join-Path $OutputPath $PkgName)"
}
if ([Math]::Abs($BackendPort - $FrontendPort) -ne 1) {
    throw "Ports must be adjacent (Adjacency Rule): backend $BackendPort, frontend $FrontendPort"
}

New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
Write-Host "Scaffolding $AppName at $AppDir" -ForegroundColor Cyan
Write-Host "  Backend port: $BackendPort  Frontend port: $FrontendPort" -ForegroundColor Gray

# =============================================================================
# FILE WRITER HELPER
# =============================================================================
function Write-Scaffold {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string]$Content
    )
    $resolved = $Content
    $resolved = $resolved.Replace('__APPNAME__', $AppName)
    $resolved = $resolved.Replace('__PKG__', $PkgName)
    $resolved = $resolved.Replace('__DESC__', $Description)
    $resolved = $resolved.Replace('__AUTHOR__', $Author)
    $resolved = $resolved.Replace('__BPORT__', $BackendPort.ToString())
    $resolved = $resolved.Replace('__FPORT__', $FrontendPort.ToString())
    $resolved = $resolved.Replace('__SCHEDULER_DEFAULT__', $(if ($IncludeScheduler) { '1' } else { '0' }))

    $target = Join-Path $AppDir ($RelativePath.Replace('__PKG__', $PkgName).Replace('__APPNAME__', $AppName))
    $dir = Split-Path -Parent $target
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Set-Content -Path $target -Value $resolved -Encoding utf8NoBOM -NoNewline
}

# =============================================================================
# PROJECT ROOT FILES
# =============================================================================
$gitignore = @'
.venv/
__pycache__/
*.pyc
.ruff_cache/
.pytest_cache/
.coverage
reports/
dist/
build/
*.bak
*.backup
webapp/node_modules/
webapp/dist/
webapp/.vite/
native/target/
native/resources/*.exe
native/binaries/*.exe
data/
.env
'@
Write-Scaffold ".gitignore" $gitignore

$pyproject = @'
[project]
name = "__PKG__"
version = "0.1.0"
description = "__DESC__"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastmcp[tasks]>=3.4.4,<4",
    "prefab-ui>=0.14.0",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "httpx>=0.27",
    "APScheduler>=3.10,<4",
]

[project.scripts]
__PKG__-server = "__PKG__.server:main"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.6",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
ignore = ["E501"]

[tool.pytest.ini_options]
pythonpath = ["src"]
asyncio_mode = "auto"
testpaths = ["tests"]
'@
Write-Scaffold "pyproject.toml" $pyproject

$justfile = @'
# __APPNAME__ - fleet justfile
serve port="__BPORT__":
    uv run uvicorn __PKG__.server:app --host 127.0.0.1 --port {{port}}

mcp-stdio:
    uv run __PKG__-server

dev:
    pwsh -NoProfile -File start.ps1

lint:
    uv run ruff check .
    uv run ruff format . --check

fix:
    uv run ruff check . --fix
    uv run ruff format .

test:
    uv run pytest tests/ -q

e2e:
    Set-Location webapp
    npx playwright test

bootstrap:
    uv sync
    Set-Location webapp
    bun install
'@
Write-Scaffold "justfile" $justfile

$envExample = @'
# Copy to .env and adjust. Never commit .env.
WEB_PORT=__BPORT__
LLM_PROVIDER=ollama
OLLAMA_URL=http://127.0.0.1:11434
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
'@
Write-Scaffold ".env.example" $envExample

$llmsTxt = @'
# __APPNAME__

__DESC__

## Links

- llms-full.txt: ./llms-full.txt
- Source: ./src/__PKG__/

## Quick start

uv sync && bun --prefix webapp install && ./start.ps1
'@
Write-Scaffold "llms.txt" $llmsTxt

$llmsFull = @'
# __APPNAME__ - LLM Reference

__DESC__

## Stack

- Backend: FastMCP 3.4+ (Python, uv), served by uvicorn on 127.0.0.1:__BPORT__
- Frontend: React 18 + Vite + TailwindCSS (dark), Bun, served on 127.0.0.1:__FPORT__
- Storage: SQLite (local-first) - members, products, orders
- Scheduler: APScheduler periodic jobs (patrol demo job)
- Desktop: optional Tauri 2.0 wrapper under native/

## Endpoints

- GET /api/health - server name, version, uptime, tool_count
- GET /api/v1/diagnostics - tool list + system info
- GET /api/skills - registered skills
- GET /api/tools - registered MCP tools
- GET /api/logs - in-memory log ring buffer
- GET /api/jobs - scheduler jobs (APScheduler)
- GET/POST /api/members, DELETE /api/members/{id} - roster (SQLite)
- GET /api/products, POST /api/orders - webshop (SQLite)
- /mcp - MCP streamable HTTP endpoint (when enabled)
- /docs - FastAPI Swagger UI

## Start

pwsh -File start.ps1        # clears ports, starts backend + frontend, opens browser
uv run pytest tests/        # backend tests
npx --prefix webapp playwright test   # e2e tests

## Ports

Backend __BPORT__, frontend __FPORT__ (fleet registry 10700-11500).
'@
Write-Scaffold "llms-full.txt" $llmsFull

# =============================================================================
# BACKEND (FastMCP 3.4 + FastAPI)
# =============================================================================
$dbPy = @'
"""SQLite local-first storage for __APPNAME__ (members, products, orders)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "__PKG__.sqlite3"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL DEFAULT 'member',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price_cents INTEGER NOT NULL,
                description TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                items TEXT NOT NULL,
                total_cents INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )


def seed_products() -> None:
    with _conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO products (name, price_cents, description) VALUES (?, ?, ?)",
                [
                    ("Robot patrol sticker", 499, "Boomy approved, weatherproof"),
                    ("Fleet keycap", 1299, "Cherry MX, amber accent"),
                    ("MCP mug", 1599, "Hot tools in a hot mug"),
                    ("Scheduler t-shirt", 2499, "Every 5 minutes, on time"),
                ],
            )


def list_members() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM members ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def add_member(name: str, email: str, role: str = "member") -> dict:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO members (name, email, role) VALUES (?, ?, ?)",
            (name, email, role),
        )
        row = conn.execute(
            "SELECT * FROM members WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


def delete_member(member_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    return cur.rowcount > 0


def list_products() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def create_order(items: str, total_cents: int) -> dict:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO orders (items, total_cents) VALUES (?, ?)",
            (items, total_cents),
        )
        row = conn.execute(
            "SELECT * FROM orders WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)
'@
Write-Scaffold "src/__PKG__/db.py" $dbPy

$serverPy = @'
"""FastMCP 3.4 server with FastAPI HTTP app for __APPNAME__.

Run: uv run uvicorn __PKG__.server:app --host 127.0.0.1 --port __BPORT__
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Context, FastMCP

from . import db as _db

_db.init_db()
_db.seed_products()

mcp = FastMCP(
    "__APPNAME__",
    instructions="Fleet-standard __APPNAME__ MCP server.",
)

_tauri_desktop = os.environ.get("__PKG__TAURI", "").lower() in ("1", "true", "yes")


@mcp.tool()
async def app_info(ctx: Context = None) -> dict:
    """Return metadata about this server.

    ## Return Format
    {"success": bool, "name": str, "version": str, "tool_count": int}

    ## Examples
    app_info()
    """
    tools = await mcp.list_tools()
    return {
        "success": True,
        "name": "__APPNAME__",
        "version": "0.1.0",
        "tool_count": len(tools),
    }


@mcp.tool()
async def example_op(
    operation: str = "hello",
    name: str = "world",
    ctx: Context = None,
) -> dict:
    """Example portmanteau tool - demonstrates the fleet operation pattern.

    ## Return Format
    {"success": bool, "message": str, "data": dict}

    ## Examples
    example_op(operation="hello", name="Sandra")
    example_op(operation="echo", name="ping")
    """
    if operation == "hello":
        return {"success": True, "message": f"Hello, {name}!", "data": {"name": name}}
    if operation == "echo":
        return {"success": True, "message": name, "data": {"echo": name}}
    return {"success": False, "error": f"Unknown operation: {operation}"}


@mcp.resource("skill://__PKG__/SKILL.md")
def get_skill() -> str:
    """Expose the bundled skill as an MCP resource."""
    from pathlib import Path

    skill_path = Path(__file__).parent / "skills" / "__PKG__" / "SKILL.md"
    return skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""


# ---------------------------------------------------------------------------
# FastAPI app (webapp backend + CORS + health endpoints)
# ---------------------------------------------------------------------------
_mcp_http = mcp.http_app(path="/")
app = FastAPI(title="__APPNAME__", version="0.1.0", lifespan=_mcp_http.lifespan)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    tools = await mcp.list_tools()
    return {
        "status": "ok",
        "server": "__APPNAME__",
        "version": "0.1.0",
        "uptime_seconds": 0,
        "tool_count": len(tools),
    }


@app.get("/api/v1/diagnostics")
async def diagnostics() -> dict[str, Any]:
    tools = await mcp.list_tools()
    return {
        "status": "ok",
        "server": "__APPNAME__",
        "version": "0.1.0",
        "uptime_seconds": 0,
        "tool_count": len(tools),
        "tools": [{"name": t.name} for t in tools],
        "system": {"windows": os.name == "nt"},
        "errors": [],
    }


@app.get("/api/tools")
async def api_tools() -> dict[str, Any]:
    tools = await mcp.list_tools()
    return {
        "success": True,
        "tools": [
            {
                "name": t.name,
                "description": (t.description or "").splitlines()[0],
            }
            for t in tools
        ],
    }


@app.get("/api/skills")
async def api_skills() -> dict[str, Any]:
    return {"success": True, "skills": ["__PKG__"]}


@app.get("/skill/{skill_name}")
async def get_skill(skill_name: str) -> str:
    """Return the raw SKILL.md content for a skill name."""
    from pathlib import Path

    skill_path = Path(__file__).parent / "skills" / skill_name / "SKILL.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return "not found"


# ---------------------------------------------------------------------------
# In-memory log ring buffer (fleet UiLog pattern)
# ---------------------------------------------------------------------------
from collections import deque

_LOG_RING: deque[dict] = deque(maxlen=200)


def ring_log(source: str, level: str, message: str) -> None:
    _LOG_RING.appendleft(
        {"ts": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
         "source": source, "level": level, "message": message}
    )


@app.get("/api/logs")
async def api_logs(limit: int = 50) -> dict[str, Any]:
    return {"success": True, "entries": list(_LOG_RING)[:limit], "count": min(limit, len(_LOG_RING))}


# ---------------------------------------------------------------------------
# Membership roster (SQLite)
# ---------------------------------------------------------------------------
@app.get("/api/members")
async def api_members() -> dict[str, Any]:
    members = _db.list_members()
    return {"success": True, "members": members, "count": len(members)}


@app.post("/api/members")
async def api_members_add(payload: dict[str, Any]) -> dict[str, Any]:
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()
    if not name or not email:
        return {"success": False, "error": "name and email required"}
    try:
        member = _db.add_member(name, email, (payload.get("role") or "member").strip())
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    ring_log("roster", "INFO", f"member added: {name} <{email}>")
    return {"success": True, "member": member}


@app.delete("/api/members/{member_id}")
async def api_members_delete(member_id: int) -> dict[str, Any]:
    ok = _db.delete_member(member_id)
    if ok:
        ring_log("roster", "INFO", f"member removed: id {member_id}")
    return {"success": ok, "id": member_id}


# ---------------------------------------------------------------------------
# Webshop (products + orders, SQLite)
# ---------------------------------------------------------------------------
@app.get("/api/products")
async def api_products() -> dict[str, Any]:
    return {"success": True, "products": _db.list_products()}


@app.post("/api/orders")
async def api_orders_create(payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("items")
    total = payload.get("total_cents")
    if not isinstance(items, str) or not isinstance(total, int):
        return {"success": False, "error": "items (str) and total_cents (int) required"}
    order = _db.create_order(items, total)
    ring_log("shop", "INFO", f"order {order['id']} placed for {total / 100:.2f} EUR")
    return {"success": True, "order": order}


# ---------------------------------------------------------------------------
# Scheduler (APScheduler periodic jobs) - the robot patrol foundation
# ---------------------------------------------------------------------------
if os.environ.get("ENABLE_SCHEDULER", "__SCHEDULER_DEFAULT__") == "1":
    from apscheduler.schedulers.background import BackgroundScheduler

    _JOBS: dict[str, dict] = {}
    _scheduler = BackgroundScheduler()


    def _patrol_tick() -> None:
        _JOBS["patrol"] = {
            "name": "patrol",
            "last_run": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
            "status": "ok",
            "message": "periodic safety patrol completed",
        }
        ring_log("scheduler", "INFO", "patrol tick")


    _scheduler.add_job(_patrol_tick, "interval", minutes=5, id="patrol")
    _scheduler.start()
    ring_log("scheduler", "INFO", "scheduler started")


    @app.get("/api/jobs")
    async def api_jobs() -> dict[str, Any]:
        jobs = [
            {"id": j.id, "next_run": str(j.next_run_time or ""), "enabled": not j.next_run_time is None}
            for j in _scheduler.get_jobs()
        ]
        return {"success": True, "jobs": jobs, "runs": _JOBS}


    @app.post("/api/jobs/{job_id}/run")
    async def run_job(job_id: str) -> dict[str, Any]:
        if job_id == "patrol":
            _patrol_tick()
            return {"success": True, "message": "patrol dispatched"}
        return {"success": False, "error": f"unknown job: {job_id}"}


    @app.on_event("shutdown")
    async def _stop_scheduler() -> None:
        _scheduler.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Optional feature endpoints
# ---------------------------------------------------------------------------
if os.environ.get("ENABLE_UPLOAD", "0") == "1":
    from pathlib import Path

    _UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "data/uploads"))
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    @app.post("/api/upload")
    async def upload(file: Any = None) -> dict[str, Any]:
        return {"success": False, "error": "multipart body expected"}

if os.environ.get("ENABLE_EMAIL", "0") == "1":
    @app.post("/api/contact")
    async def contact(subject: str = "", body: str = "") -> dict[str, Any]:
        if not subject or not body:
            return {"success": False, "error": "subject and body required"}
        return {"success": True, "message": "email queued (configure SMTP in .env)"}

if os.environ.get("ENABLE_REALTIME", "0") == "1":
    from fastapi import WebSocket

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                await websocket.send_text(f"echo: {data}")
        except Exception:
            pass


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{os.environ.get('WEB_PORT', '__FPORT__')}",
        f"http://127.0.0.1:{os.environ.get('WEB_PORT', '__FPORT__')}",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    ],
    allow_origin_regex=(
        r"https?://(?:[a-zA-Z0-9-]+\.ts\.net|.*?\.tail-[a-f0-9]+\.ts\.net|"
        r"tauri\.localhost|localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?$"
        r"|^tauri://localhost$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/mcp", _mcp_http)


def main() -> None:
    import uvicorn

    port = int(os.environ.get("WEB_PORT", "__BPORT__"))
    host = os.environ.get("WEB_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
'@
Write-Scaffold "src/__PKG__/server.py" $serverPy

$initPy = @'
"""__APPNAME__ package."""
'@
Write-Scaffold "src/__PKG__/__init__.py" $initPy

$skillMd = @'
# __APPNAME__ Skill

This server exposes FastMCP tools for the __APPNAME__ webapp.

## Tools

- `app_info` - server metadata, version, tool count
- `example_op` - portmanteau example: hello, echo

## Usage

Call `app_info()` first to discover the server state, then use
`example_op(operation=..., name=...)` for demonstration.
'@
Write-Scaffold "src/__PKG__/skills/__PKG__/SKILL.md" $skillMd

$testPy = @'
"""Backend smoke tests for __APPNAME__."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_health_endpoint():
    from __PKG__.server import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["tool_count"] >= 1


@pytest.mark.asyncio
async def test_tools_endpoint():
    from __PKG__.server import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/tools")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()["tools"]]
        assert "app_info" in names
'@
Write-Scaffold "tests/test_server.py" $testPy

# =============================================================================
# FRONTEND (React + Vite + Tailwind + Bun)
# =============================================================================
$packageJson = @'
{
  "name": "__APPNAME__",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --port __FPORT__ --host",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "e2e": "playwright test"
  },
  "dependencies": {
    "@tauri-apps/api": "^2.2.0",
    "lucide-react": "^0.469.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-markdown": "^9.0.1",
    "react-router-dom": "^6.28.0",
    "zustand": "^5.0.2"
  },
  "devDependencies": {
    "@playwright/test": "^1.49.0",
    "@tailwindcss/vite": "^4.0.0",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.7.2",
    "vite": "^6.0.0",
    "vitest": "^2.1.8"
  }
}
'@
Write-Scaffold "webapp/package.json" $packageJson

$viteConfig = @'
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const BACKEND = "http://127.0.0.1:__BPORT__";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: __FPORT__,
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true },
      "/mcp": { target: BACKEND, changeOrigin: true },
      "/docs": { target: BACKEND, changeOrigin: true },
      "/ws": { target: BACKEND, ws: true },
    },
  },
});
'@
Write-Scaffold "webapp/vite.config.ts" $viteConfig

$tsConfig = @'
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
'@
Write-Scaffold "webapp/tsconfig.json" $tsConfig

$indexHtml = @'
<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>__APPNAME__</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
'@
Write-Scaffold "webapp/index.html" $indexHtml

$indexCss = @'
@import "tailwindcss";

:root {
  color-scheme: dark;
}

body {
  margin: 0;
  background-color: #09090b;
  color: #f4f4f5;
  font-family: "Inter", ui-sans-serif, system-ui, sans-serif;
}

select, input, textarea {
  color-scheme: dark;
}
'@
Write-Scaffold "webapp/src/index.css" $indexCss

$mainTsx = @'
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
'@
Write-Scaffold "webapp/src/main.tsx" $mainTsx

$apiTs = @'
export const API_BASE = "http://127.0.0.1:__BPORT__";

export interface HealthInfo {
  status: string;
  server: string;
  version: string;
  uptime_seconds: number;
  tool_count: number;
}

export async function fetchHealth(): Promise<HealthInfo> {
  const r = await fetch(`${API_BASE}/api/health`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function fetchTools() {
  const r = await fetch(`${API_BASE}/api/tools`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return (await r.json()).tools as { name: string; description: string }[];
}

export async function fetchSkills() {
  const r = await fetch(`${API_BASE}/api/skills`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return (await r.json()).skills as string[];
}
'@
Write-Scaffold "webapp/src/lib/api.ts" $apiTs

$providerTs = @'
export interface Provider {
  name: string;
  port: number;
  base: string;
}

export const PROVIDERS: Provider[] = [
  { name: "Ollama", port: 11434, base: "http://127.0.0.1:11434" },
  { name: "LM Studio", port: 1234, base: "http://127.0.0.1:1234" },
  { name: "vLLM", port: 8000, base: "http://127.0.0.1:8000" },
];

export async function probeProvider(p: Provider): Promise<boolean> {
  try {
    const url = p.name === "Ollama" ? `${p.base}/api/tags` : `${p.base}/v1/models`;
    const r = await fetch(url, { signal: AbortSignal.timeout(3000) });
    return r.ok;
  } catch {
    return false;
  }
}

export async function listModels(p: Provider): Promise<string[]> {
  try {
    const url = p.name === "Ollama" ? `${p.base}/api/tags` : `${p.base}/v1/models`;
    const r = await fetch(url, { signal: AbortSignal.timeout(3000) });
    if (!r.ok) return [];
    const j = await r.json();
    if (p.name === "Ollama") return (j.models ?? []).map((m: { name: string }) => m.name);
    return (j.data ?? []).map((m: { id: string }) => m.id);
  } catch {
    return [];
  }
}
'@
Write-Scaffold "webapp/src/lib/provider.ts" $providerTs

$llmStore = @'
import { create } from "zustand";

interface LlmState {
  provider: string;
  model: string;
  setProvider: (p: string) => void;
  setModel: (m: string) => void;
}

const KEY = "__APPNAME__-llm";

function load(): { provider: string; model: string } {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* ignore */
  }
  return { provider: "Ollama", model: "" };
}

export const useLlm = create<LlmState>((set) => ({
  ...load(),
  setProvider: (provider) =>
    set((s) => {
      const next = { ...s, provider, model: "" };
      localStorage.setItem(KEY, JSON.stringify(next));
      return next;
    }),
  setModel: (model) =>
    set((s) => {
      const next = { ...s, model };
      localStorage.setItem(KEY, JSON.stringify(next));
      return next;
    }),
}));
'@
Write-Scaffold "webapp/src/store/llm.ts" $llmStore

$appTsx = @'
import { Routes, Route } from "react-router-dom";
import Layout from "./Layout";
import Dashboard from "./pages/Dashboard";
import Tools from "./pages/Tools";
import Skills from "./pages/Skills";
import Chat from "./pages/Chat";
import Settings from "./pages/Settings";
import Help from "./pages/Help";
import Logs from "./pages/Logs";
import ApiDocs from "./pages/ApiDocs";
import Jobs from "./pages/Jobs";
import Members from "./pages/Members";
import Shop from "./pages/Shop";
import Cart from "./pages/Cart";
import Onboarding from "./pages/Onboarding";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/tools" element={<Tools />} />
        <Route path="/skills" element={<Skills />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="/api-docs" element={<ApiDocs />} />
        <Route path="/members" element={<Members />} />
        <Route path="/shop" element={<Shop />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/help" element={<Help />} />
      </Route>
    </Routes>
  );
}
'@
Write-Scaffold "webapp/src/App.tsx" $appTsx

$layoutTsx = @'
import { useEffect, useState } from "react";
import { Link, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Wrench,
  BookOpen,
  MessageSquare,
  CalendarClock,
  Terminal,
  Code2,
  Users,
  Store,
  ShoppingCart,
  Rocket,
  Settings as SettingsIcon,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { fetchHealth } from "./lib/api";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/tools", label: "Tools", icon: Wrench },
  { to: "/skills", label: "Skills", icon: BookOpen },
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/members", label: "Members", icon: Users },
  { to: "/shop", label: "Shop", icon: Store },
  { to: "/cart", label: "Cart", icon: ShoppingCart },
  { to: "/jobs", label: "Jobs", icon: CalendarClock },
  { to: "/logs", label: "Logs", icon: Terminal },
  { to: "/api-docs", label: "API Docs", icon: Code2 },
  { to: "/onboarding", label: "Onboarding", icon: Rocket },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
  { to: "/help", label: "Help", icon: HelpCircle },
];

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        await fetchHealth();
        if (!cancelled) setBackendOk(true);
      } catch {
        if (!cancelled) setBackendOk(false);
      }
    };
    poll();
    const interval = setInterval(poll, 10_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100" data-testid="app-layout">
      <aside
        className={`flex flex-col border-r border-zinc-800 bg-zinc-900 transition-all ${
          collapsed ? "w-16" : "w-56"
        }`}
        data-testid="sidebar"
      >
        <div className="flex items-center justify-between p-3">
          {!collapsed && (
            <span className="font-bold text-amber-500" data-testid="app-logo">
              __APPNAME__
            </span>
          )}
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="rounded p-1 text-zinc-400 hover:text-white"
            aria-label="Toggle sidebar"
            data-testid="sidebar-toggle"
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
        <nav className="flex-1 space-y-1 px-2" data-testid="sidebar-nav">
          {NAV.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              aria-label={label}
              data-testid={`nav-${label.toLowerCase()}`}
              className="flex items-center gap-3 rounded px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-800 hover:text-white"
              title={label}
            >
              <Icon size={18} />
              {!collapsed && <span>{label}</span>}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/80 px-4 py-2 backdrop-blur">
          <h1 className="text-sm font-medium text-zinc-200">__APPNAME__</h1>
          <div className="flex items-center gap-2">
            <span
              data-testid="backend-dot"
              className={`h-2 w-2 rounded-full ${
                backendOk === null
                  ? "bg-zinc-500"
                  : backendOk
                    ? "bg-green-500"
                    : "bg-red-500"
              } animate-pulse`}
            />
            <span className="text-xs text-zinc-400">
              {backendOk === null ? "Connecting..." : backendOk ? "Connected" : "Offline"}
            </span>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
'@
Write-Scaffold "webapp/src/Layout.tsx" $layoutTsx

$dashboardTsx = @'
import { useEffect, useState } from "react";
import { Activity, Cpu, Server, Wrench } from "lucide-react";
import { fetchHealth, type HealthInfo } from "../lib/api";

function Kpi({
  testid,
  label,
  value,
  icon: Icon,
}: {
  testid: string;
  label: string;
  value: string;
  icon: typeof Server;
}) {
  return (
    <div
      data-testid={testid}
      className="rounded-lg border border-zinc-800 bg-zinc-900 p-4"
    >
      <div className="flex items-center gap-2 text-zinc-400">
        <Icon size={16} />
        <span className="text-xs uppercase tracking-wide">{label}</span>
      </div>
      <div className="mt-2 text-2xl font-bold text-amber-500">{value}</div>
    </div>
  );
}

export default function Dashboard() {
  const [health, setHealth] = useState<HealthInfo | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  return (
    <div data-testid="dashboard" className="space-y-6">
      {localStorage.getItem("__APPNAME__-onboarded") !== "1" && (
        <div className="flex items-center justify-between rounded-lg border border-amber-800/50 bg-amber-950/30 p-4">
          <span className="text-sm text-amber-300">
            Welcome! Finish the quick onboarding to get the most out of __APPNAME__.
          </span>
          <a
            href="/onboarding"
            className="rounded bg-amber-500 px-3 py-1 text-sm font-medium text-zinc-950 hover:bg-amber-400"
          >
            Start
          </a>
        </div>
      )}
      <section className="rounded-xl border border-zinc-800 bg-gradient-to-br from-zinc-900 to-zinc-950 p-8">
        <h2 className="text-3xl font-bold text-white">__APPNAME__</h2>
        <p className="mt-2 max-w-xl text-zinc-400">
          __DESC__
        </p>
        <div className="mt-4 flex gap-2">
          <a
            href="/tools"
            className="rounded bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400"
          >
            Explore tools
          </a>
        </div>
      </section>
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi testid="kpi-server" label="Server" value={health?.server ?? "..."} icon={Server} />
        <Kpi testid="kpi-tools" label="Tools" value={String(health?.tool_count ?? "-")} icon={Wrench} />
        <Kpi testid="kpi-status" label="Status" value={health?.status ?? "..."} icon={Activity} />
        <Kpi testid="kpi-version" label="Version" value={health?.version ?? "..."} icon={Cpu} />
      </section>
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/Dashboard.tsx" $dashboardTsx

$toolsTsx = @'
import { useEffect, useState } from "react";
import { fetchTools } from "../lib/api";

export default function Tools() {
  const [tools, setTools] = useState<{ name: string; description: string }[]>([]);

  useEffect(() => {
    fetchTools().then(setTools).catch(() => setTools([]));
  }, []);

  return (
    <div data-testid="tools-page" className="space-y-4">
      <h2 className="text-xl font-semibold text-white">Tools</h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {tools.map((t) => (
          <div key={t.name} className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <div className="font-mono text-sm text-amber-500">{t.name}</div>
            <div className="mt-1 text-sm text-zinc-400">{t.description}</div>
          </div>
        ))}
      </div>
      {tools.length === 0 && (
        <p className="text-zinc-500">No tools discovered. Is the backend running?</p>
      )}
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/Tools.tsx" $toolsTsx

$skillsTsx = @'
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { fetchSkills } from "../lib/api";

const API_BASE = "http://127.0.0.1:__BPORT__";

export default function Skills() {
  const [skills, setSkills] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");

  useEffect(() => {
    fetchSkills().then(setSkills).catch(() => setSkills([]));
  }, []);

  useEffect(() => {
    if (!selected) return;
    fetch(`${API_BASE}/api/skills`).catch(() => undefined);
    fetch(`${API_BASE}/skill/${selected}`)
      .then((r) => r.text())
      .then(setContent)
      .catch(() => setContent("(skill content unavailable)"));
  }, [selected]);

  return (
    <div data-testid="skills-page" className="space-y-4">
      <h2 className="text-xl font-semibold text-white">Skills</h2>
      <div className="flex gap-2">
        {skills.map((s) => (
          <button
            key={s}
            onClick={() => setSelected(s)}
            className={`rounded px-3 py-1 text-sm ${
              selected === s
                ? "bg-amber-500 text-zinc-950"
                : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
            }`}
          >
            {s}
          </button>
        ))}
      </div>
      {selected && (
        <article className="rounded-lg border border-zinc-800 bg-zinc-900 p-6 prose prose-invert max-w-none">
          <ReactMarkdown>{content}</ReactMarkdown>
        </article>
      )}
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/Skills.tsx" $skillsTsx

$chatTsx = @'
import { useEffect, useRef, useState } from "react";
import { Send, Download, Eraser } from "lucide-react";
import { useLlm } from "../store/llm";
import { listModels, PROVIDERS, probeProvider } from "../lib/provider";
import { API_BASE, fetchSkills } from "../lib/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
  ts?: string;
}

const HISTORY_KEY = "__APPNAME__-chat-history";
const PERSONALITIES = [
  { id: "assistant", name: "Assistant", prompt: "You are a helpful assistant." },
  { id: "expert", name: "Expert Reviewer", prompt: "You are a rigorous expert reviewer. Be concise and critical." },
  { id: "summarizer", name: "Quick Summarizer", prompt: "You summarize content into clear, short bullet points." },
];

const EXAMPLES = [
  { group: "General", items: ["What can this app do?", "How is the backend health?"] },
  { group: "Roster", items: ["How do I add a member?", "Summarize the membership roster"] },
  { group: "Operations", items: ["Check the last patrol run", "Explain the scheduler jobs"] },
];

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]");
    } catch {
      return [];
    }
  });
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [personality, setPersonality] = useState("assistant");
  const [providerOk, setProviderOk] = useState<boolean | null>(null);
  const { provider, model, setProvider, setModel } = useLlm();
  const [models, setModels] = useState<string[]>([]);
  const [skillName, setSkillName] = useState<string | null>(null);
  const [skillContent, setSkillContent] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(messages.slice(-100)));
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    let alive = true;
    probeProvider(PROVIDERS[0]).then((ok) => {
      if (alive) setProviderOk(ok);
    });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const p = PROVIDERS.find((x) => x.name === provider);
    if (!p) return;
    listModels(p).then((m) => {
      setModels(m);
      if (!model && m.length > 0) setModel(m[0]);
    });
  }, [provider, model, setModel]);

  useEffect(() => {
    fetchSkills()
      .then(async (names) => {
        if (names.length > 0) {
          setSkillName(names[0]);
          const r = await fetch(`${API_BASE}/skill/${names[0]}`);
          if (r.ok) setSkillContent(await r.text());
        }
      })
      .catch(() => undefined);
  }, []);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    const p = PROVIDERS.find((x) => x.name === provider);
    if (!p) return;
    const next: Msg[] = [...messages, { role: "user", content: text, ts: new Date().toISOString() }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const persona = PERSONALITIES.find((x) => x.id === personality);
      const role = persona?.prompt ?? "";
      const system = skillContent ? `${skillContent}\n\n---\n\n## Role\n${role}` : role;
      const r = await fetch(`${p.base}/v1/chat/completions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model,
          messages: [
            { role: "system", content: system },
            ...next.map(({ role: rl, content }) => ({ role: rl, content })),
          ],
        }),
      });
      const j = await r.json();
      const reply = j?.choices?.[0]?.message?.content ?? "(no response)";
      setMessages((m) => [...m, { role: "assistant", content: reply, ts: new Date().toISOString() }]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `Error: ${e instanceof Error ? e.message : "network"}`, ts: new Date().toISOString() },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const exportChat = () => {
    const body = messages.map((m) => `[${m.ts ?? ""}] ${m.role}: ${m.content}`).join("\n");
    const blob = new Blob([body], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `__APPNAME__-chat-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const clearChat = () => {
    setMessages([]);
    localStorage.removeItem(HISTORY_KEY);
  };

  return (
    <div data-testid="chat-page" className="flex h-full flex-col space-y-3">
      <div data-testid="chat-controls" className="flex flex-wrap items-center gap-2">
        <select
          data-testid="personality-select"
          value={personality}
          onChange={(e) => setPersonality(e.target.value)}
          className="rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-sm text-zinc-100"
        >
          {PERSONALITIES.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <select
          data-testid="llm-provider-select"
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          className="rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-sm text-zinc-100"
        >
          {PROVIDERS.map((p) => (
            <option key={p.name} value={p.name}>{p.name}</option>
          ))}
        </select>
        <select
          data-testid="llm-model-select"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-sm text-zinc-100"
        >
          {models.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <span
          data-testid="llm-status"
          className={`text-xs ${providerOk ? "text-green-500" : "text-red-500"}`}
        >
          {providerOk === null ? "Detecting..." : providerOk ? "Ollama on :11434" : "Not detected"}
        </span>
        {skillName && (
          <span className="rounded bg-zinc-900 px-2 py-1 text-xs text-amber-500" data-testid="skill-indicator">
            skill:{skillName}
          </span>
        )}
        <div className="ml-auto flex gap-1">
          <button
            data-testid="chat-export"
            onClick={exportChat}
            disabled={messages.length === 0}
            className="rounded bg-zinc-800 p-2 text-zinc-300 hover:bg-zinc-700 disabled:opacity-40"
            title="Export chat"
          >
            <Download size={16} />
          </button>
          <button
            data-testid="chat-clear"
            onClick={clearChat}
            disabled={messages.length === 0}
            className="rounded bg-zinc-800 p-2 text-zinc-300 hover:bg-zinc-700 disabled:opacity-40"
            title="Clear chat"
          >
            <Eraser size={16} />
          </button>
        </div>
      </div>
      <div data-testid="chat-messages" className="flex-1 space-y-3 overflow-y-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] whitespace-pre-wrap rounded-lg px-4 py-2 text-sm ${
                m.role === "user"
                  ? "bg-amber-500 text-zinc-950"
                  : "bg-zinc-800 text-zinc-100"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        {busy && <div className="text-sm text-zinc-500">Thinking...</div>}
        <div ref={bottomRef} />
      </div>
      <div data-testid="example-prompts" className="flex flex-wrap gap-2">
        {EXAMPLES.map((g) => (
          <div key={g.group} className="flex items-center gap-1">
            <span className="text-xs text-zinc-600">{g.group}:</span>
            {g.items.map((e) => (
              <button
                key={e}
                onClick={() => setInput(e)}
                className="rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1 text-xs text-zinc-300 hover:border-amber-500 hover:text-amber-400"
              >
                {e}
              </button>
            ))}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
          placeholder="Ask something..."
          className="flex-1 rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-amber-500"
        />
        <button
          data-testid="chat-send"
          onClick={send}
          disabled={busy || !providerOk}
          className="rounded bg-amber-500 px-4 text-zinc-950 hover:bg-amber-400 disabled:opacity-40"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/Chat.tsx" $chatTsx

$settingsTsx = @'
import { useEffect, useState } from "react";
import { PROVIDERS, probeProvider, listModels } from "../lib/provider";
import { useLlm } from "../store/llm";
import { fetchHealth } from "../lib/api";

export default function Settings() {
  const [providerStatus, setProviderStatus] = useState<Record<string, string>>({});
  const [models, setModels] = useState<string[]>([]);
  const { provider, model, setProvider, setModel } = useLlm();
  const [health, setHealth] = useState<string>("checking");

  useEffect(() => {
    fetchHealth()
      .then((h) => setHealth(`${h.server} ${h.version} (${h.tool_count} tools)`))
      .catch(() => setHealth("backend unreachable"));

    const checks: Record<string, string> = {};
    PROVIDERS.forEach((p) => {
      checks[p.name] = "probing";
      probeProvider(p).then((ok) => {
        setProviderStatus((s) => ({ ...s, [p.name]: ok ? "detected" : "not_found" }));
      });
    });
    setProviderStatus(checks);
  }, []);

  useEffect(() => {
    const p = PROVIDERS.find((x) => x.name === provider);
    if (!p) return;
    listModels(p).then((m) => {
      setModels(m);
      if (!model && m.length > 0) setModel(m[0]);
    });
  }, [provider, model, setModel]);

  return (
    <div data-testid="settings-page" className="max-w-2xl space-y-6">
      <h2 className="text-xl font-semibold text-white">Settings</h2>
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h3 className="text-sm font-medium text-zinc-300">Backend health</h3>
        <p className="mt-1 text-sm text-zinc-400">{health}</p>
      </section>
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h3 className="text-sm font-medium text-zinc-300">Local LLM providers</h3>
        <div className="mt-3 space-y-2">
          {PROVIDERS.map((p) => {
            const st = providerStatus[p.name] ?? "probing";
            const ok = st === "detected";
            return (
              <div key={p.name} className="flex items-center justify-between text-sm">
                <span className="text-zinc-200">{p.name} (:{(p as { port: number }).port})</span>
                <span className={ok ? "text-green-500" : "text-zinc-500"}>
                  {st === "probing" ? "Probing..." : ok ? "Detected" : "Not found"}
                </span>
              </div>
            );
          })}
        </div>
        <div className="mt-4 flex gap-2">
          <select
            data-testid="llm-provider-select"
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-sm text-zinc-100"
          >
            {PROVIDERS.map((p) => (
              <option key={p.name} value={p.name}>{p.name}</option>
            ))}
          </select>
          <select
            data-testid="llm-model-select"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-sm text-zinc-100"
          >
            {models.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
        {Object.values(providerStatus).every((s) => s === "not_found") && (
          <p className="mt-3 text-sm text-amber-500">
            No local LLM detected. Install Ollama or LM Studio to enable AI features.
          </p>
        )}
      </section>
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/Settings.tsx" $settingsTsx

$helpTsx = @'
export default function Help() {
  return (
    <div data-testid="help-page" className="max-w-3xl space-y-4">
      <h2 className="text-xl font-semibold text-white">Help</h2>
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h3 className="text-sm font-medium text-zinc-300">Architecture</h3>
        <p className="mt-1 text-sm text-zinc-400">
          __APPNAME__ is a fleet-standard fullstack app: FastMCP 3.4 backend (uvicorn),
          React + Vite + Tailwind frontend (Bun), optional Tauri 2.0 desktop wrapper.
        </p>
      </section>
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h3 className="text-sm font-medium text-zinc-300">Ports</h3>
        <p className="mt-1 font-mono text-sm text-zinc-400">
          Backend: __BPORT__ (API, docs at /docs) | Frontend: __FPORT__
        </p>
      </section>
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h3 className="text-sm font-medium text-zinc-300">Troubleshooting</h3>
        <ul className="mt-1 list-inside list-disc space-y-1 text-sm text-zinc-400">
          <li>Backend offline: run start.ps1 (clears port zombies first)</li>
          <li>Chat disabled: start Ollama (http://127.0.0.1:11434)</li>
          <li>Ports in use: check mcp-central-docs/operations/WEBAPP_PORTS.md</li>
        </ul>
      </section>
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/Help.tsx" $helpTsx

$logsTsx = @'
import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";

interface LogEntry {
  ts: string;
  source: string;
  level: string;
  message: string;
}

export default function Logs() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [level, setLevel] = useState("all");

  useEffect(() => {
    let alive = true;
    const load = () => {
      fetch(`${API_BASE}/api/logs?limit=100`)
        .then((r) => r.json())
        .then((j) => {
          if (alive) setEntries(j.entries ?? []);
        })
        .catch(() => undefined);
    };
    load();
    const interval = setInterval(load, 5000);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, []);

  const shown = level === "all" ? entries : entries.filter((e) => e.level === level);

  return (
    <div data-testid="logs-page" className="space-y-4">
      <div className="flex items-center gap-2">
        <h2 className="text-xl font-semibold text-white">Logs</h2>
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          className="ml-auto rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-sm text-zinc-100"
        >
          {["all", "INFO", "WARNING", "ERROR"].map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
      </div>
      <div className="rounded-lg border border-zinc-800 bg-black/40 p-3 font-mono text-xs text-zinc-300">
        {shown.map((e, i) => (
          <div key={i} className={`flex gap-2 ${e.level === "ERROR" ? "text-red-400" : ""}`}>
            <span className="text-zinc-600">{e.ts}</span>
            <span className="text-zinc-500">{e.source}</span>
            <span className="text-amber-500">{e.level}</span>
            <span className="break-all">{e.message}</span>
          </div>
        ))}
        {shown.length === 0 && <div className="text-zinc-600">No log entries yet.</div>}
      </div>
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/Logs.tsx" $logsTsx

$apiDocsTsx = @'
import { API_BASE } from "../lib/api";

export default function ApiDocs() {
  return (
    <div data-testid="api-docs-page" className="flex h-full flex-col space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">API Docs</h2>
        <a
          href={`${API_BASE}/docs`}
          target="_blank"
          rel="noreferrer"
          className="rounded bg-zinc-800 px-3 py-1 text-sm text-zinc-200 hover:bg-zinc-700"
        >
          Open in browser
        </a>
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        {["GET /api/health", "GET /api/v1/diagnostics", "GET /api/tools", "GET /api/skills", "GET /api/logs", "GET /api/jobs", "POST /api/jobs/{id}/run", "/mcp"].map(
          (ep) => (
            <span key={ep} className="rounded bg-zinc-900 px-2 py-1 font-mono text-amber-500">
              {ep}
            </span>
          ),
        )}
      </div>
      <iframe
        src={`${API_BASE}/docs`}
        title="Swagger UI"
        className="min-h-0 flex-1 rounded-lg border border-zinc-800 bg-white"
      />
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/ApiDocs.tsx" $apiDocsTsx

$jobsTsx = @'
import { useEffect, useState } from "react";
import { Play } from "lucide-react";
import { API_BASE } from "../lib/api";

export default function Jobs() {
  const [jobs, setJobs] = useState<{ id: string; next_run: string; enabled: boolean }[]>([]);
  const [runs, setRuns] = useState<Record<string, Record<string, string>>>({});
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => {
    fetch(`${API_BASE}/api/jobs`)
      .then((r) => r.json())
      .then((j) => {
        setJobs(j.jobs ?? []);
        setRuns(j.runs ?? {});
      })
      .catch(() => undefined);
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 10_000);
    return () => clearInterval(interval);
  }, []);

  const run = async (id: string) => {
    setBusy(id);
    try {
      await fetch(`${API_BASE}/api/jobs/${id}/run`, { method: "POST" });
      load();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div data-testid="jobs-page" className="space-y-4">
      <h2 className="text-xl font-semibold text-white">Jobs</h2>
      {jobs.length === 0 && (
        <p className="text-zinc-500">Scheduler disabled. Set ENABLE_SCHEDULER=1 and restart the backend.</p>
      )}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {jobs.map((j) => (
          <div key={j.id} className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm text-amber-500">{j.id}</span>
              <button
                onClick={() => run(j.id)}
                disabled={busy !== null}
                className="rounded bg-zinc-800 p-2 text-zinc-300 hover:bg-zinc-700 disabled:opacity-40"
                title="Run now"
              >
                <Play size={14} />
              </button>
            </div>
            <div className="mt-2 text-xs text-zinc-400">
              next run: {j.next_run || "disabled"}
            </div>
            {runs[j.id] && (
              <div className="mt-2 text-xs text-zinc-500">
                last: {runs[j.id].last_run} - {runs[j.id].status} - {runs[j.id].message}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/Jobs.tsx" $jobsTsx

$cartStore = @'
import { create } from "zustand";

export interface CartItem {
  id: number;
  name: string;
  price_cents: number;
  qty: number;
}

interface CartState {
  items: CartItem[];
  add: (p: { id: number; name: string; price_cents: number }) => void;
  remove: (id: number) => void;
  clear: () => void;
  total: () => number;
}

const KEY = "__APPNAME__-cart";

function load(): CartItem[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]");
  } catch {
    return [];
  }
}

export const useCart = create<CartState>((set, get) => ({
  items: load(),
  add: (p) =>
    set((s) => {
      const found = s.items.find((i) => i.id === p.id);
      const items = found
        ? s.items.map((i) => (i.id === p.id ? { ...i, qty: i.qty + 1 } : i))
        : [...s.items, { ...p, qty: 1 }];
      localStorage.setItem(KEY, JSON.stringify(items));
      return { items };
    }),
  remove: (id) =>
    set((s) => {
      const items = s.items.filter((i) => i.id !== id);
      localStorage.setItem(KEY, JSON.stringify(items));
      return { items };
    }),
  clear: () => {
    localStorage.removeItem(KEY);
    set({ items: [] });
  },
  total: () => get().items.reduce((sum, i) => sum + i.price_cents * i.qty, 0),
}));
'@
Write-Scaffold "webapp/src/store/cart.ts" $cartStore

$membersTsx = @'
import { useEffect, useState } from "react";
import { UserPlus, Trash2 } from "lucide-react";
import { API_BASE } from "../lib/api";

interface Member {
  id: number;
  name: string;
  email: string;
  role: string;
  created_at: string;
}

export default function Members() {
  const [members, setMembers] = useState<Member[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  const load = () => {
    fetch(`${API_BASE}/api/members`)
      .then((r) => r.json())
      .then((j) => setMembers(j.members ?? []))
      .catch(() => setMembers([]));
  };

  useEffect(() => {
    load();
  }, []);

  const add = async () => {
    if (!name.trim() || !email.trim()) return;
    await fetch(`${API_BASE}/api/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim(), email: email.trim() }),
    });
    setName("");
    setEmail("");
    load();
  };

  const remove = async (id: number) => {
    await fetch(`${API_BASE}/api/members/${id}`, { method: "DELETE" });
    load();
  };

  return (
    <div data-testid="members-page" className="space-y-4">
      <h2 className="text-xl font-semibold text-white">Members</h2>
      <div className="flex gap-2">
        <input
          data-testid="member-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name"
          className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-amber-500"
        />
        <input
          data-testid="member-email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-amber-500"
        />
        <button
          data-testid="member-add"
          onClick={add}
          disabled={!name.trim() || !email.trim()}
          className="rounded bg-amber-500 px-3 text-zinc-950 hover:bg-amber-400 disabled:opacity-40"
          title="Add member"
        >
          <UserPlus size={16} />
        </button>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-zinc-500">
            <th className="pb-2">Name</th>
            <th className="pb-2">Email</th>
            <th className="pb-2">Role</th>
            <th className="pb-2">Joined</th>
            <th className="pb-2"></th>
          </tr>
        </thead>
        <tbody>
          {members.map((m) => (
            <tr key={m.id} className="border-t border-zinc-800">
              <td className="py-2 text-zinc-200">{m.name}</td>
              <td className="text-zinc-400">{m.email}</td>
              <td className="text-zinc-400">{m.role}</td>
              <td className="text-zinc-500">{m.created_at}</td>
              <td>
                <button
                  onClick={() => remove(m.id)}
                  className="text-zinc-600 hover:text-red-400"
                  title="Remove"
                >
                  <Trash2 size={14} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {members.length === 0 && (
        <p className="text-zinc-500">No members yet. Add the first one above.</p>
      )}
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/Members.tsx" $membersTsx

$shopTsx = @'
import { useEffect, useState } from "react";
import { ShoppingCart, Plus } from "lucide-react";
import { API_BASE } from "../lib/api";
import { useCart } from "../store/cart";

interface Product {
  id: number;
  name: string;
  price_cents: number;
  description: string;
}

export default function Shop() {
  const [products, setProducts] = useState<Product[]>([]);
  const { items, add } = useCart();

  useEffect(() => {
    fetch(`${API_BASE}/api/products`)
      .then((r) => r.json())
      .then((j) => setProducts(j.products ?? []))
      .catch(() => setProducts([]));
  }, []);

  return (
    <div data-testid="shop-page" className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Shop</h2>
        <a
          href="/cart"
          className="flex items-center gap-2 rounded bg-zinc-800 px-3 py-1 text-sm text-zinc-200 hover:bg-zinc-700"
        >
          <ShoppingCart size={16} /> Cart ({items.length})
        </a>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {products.map((p) => (
          <div key={p.id} className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <div className="text-sm font-medium text-zinc-100">{p.name}</div>
            <div className="mt-1 text-xs text-zinc-500">{p.description}</div>
            <div className="mt-3 flex items-center justify-between">
              <span className="text-amber-500">{(p.price_cents / 100).toFixed(2)} EUR</span>
              <button
                data-testid={`add-${p.id}`}
                onClick={() => add(p)}
                className="rounded bg-zinc-800 p-2 text-zinc-300 hover:bg-zinc-700"
                title="Add to cart"
              >
                <Plus size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/Shop.tsx" $shopTsx

$cartTsx = @'
import { useState } from "react";
import { Trash2, CheckCircle2 } from "lucide-react";
import { API_BASE } from "../lib/api";
import { useCart } from "../store/cart";

export default function Cart() {
  const { items, remove, clear, total } = useCart();
  const [placed, setPlaced] = useState(false);

  const checkout = async () => {
    const r = await fetch(`${API_BASE}/api/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items: JSON.stringify(items), total_cents: total() }),
    });
    if (r.ok) {
      setPlaced(true);
      clear();
    }
  };

  if (placed) {
    return (
      <div data-testid="cart-page" className="space-y-4">
        <h2 className="text-xl font-semibold text-white">Cart</h2>
        <div className="flex items-center gap-2 rounded-lg border border-green-800 bg-green-950/40 p-4 text-green-400">
          <CheckCircle2 size={18} /> Order placed. Thanks!
        </div>
      </div>
    );
  }

  return (
    <div data-testid="cart-page" className="max-w-2xl space-y-4">
      <h2 className="text-xl font-semibold text-white">Cart</h2>
      {items.map((i) => (
        <div key={i.id} className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900 p-3">
          <div>
            <div className="text-sm text-zinc-200">{i.name}</div>
            <div className="text-xs text-zinc-500">
              qty {i.qty} x {(i.price_cents / 100).toFixed(2)} EUR
            </div>
          </div>
          <button onClick={() => remove(i.id)} className="text-zinc-600 hover:text-red-400" title="Remove">
            <Trash2 size={14} />
          </button>
        </div>
      ))}
      {items.length === 0 && <p className="text-zinc-500">Cart is empty. Head to the Shop.</p>}
      <div className="flex items-center justify-between">
        <span className="text-sm text-zinc-300">
          Total: <span className="text-amber-500">{(total() / 100).toFixed(2)} EUR</span>
        </span>
        <button
          data-testid="checkout"
          onClick={checkout}
          disabled={items.length === 0}
          className="rounded bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400 disabled:opacity-40"
        >
          Checkout
        </button>
      </div>
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/Cart.tsx" $cartTsx

$onboardingTsx = @'
import { useState } from "react";
import { ArrowRight, CheckCircle2 } from "lucide-react";

const ONBOARDED_KEY = "__APPNAME__-onboarded";

export default function Onboarding() {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [done, setDone] = useState(() => localStorage.getItem(ONBOARDED_KEY) === "1");

  const finish = () => {
    localStorage.setItem(ONBOARDED_KEY, "1");
    localStorage.setItem("__APPNAME__-member", name);
    setDone(true);
  };

  if (done) {
    return (
      <div data-testid="onboarding-page" className="max-w-xl space-y-4">
        <h2 className="text-xl font-semibold text-white">Onboarding</h2>
        <div className="flex items-center gap-2 rounded-lg border border-green-800 bg-green-950/40 p-4 text-green-400">
          <CheckCircle2 size={18} /> All set, {name || "friend"}. Welcome aboard!
        </div>
      </div>
    );
  }

  return (
    <div data-testid="onboarding-page" className="max-w-xl space-y-6">
      <h2 className="text-xl font-semibold text-white">Welcome to __APPNAME__</h2>
      {step === 0 && (
        <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <p className="text-sm text-zinc-300">Step 1 of 3 - Tell us who you are.</p>
          <input
            data-testid="onboarding-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            className="w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-amber-500"
          />
          <button
            onClick={() => setStep(1)}
            disabled={!name.trim()}
            className="flex items-center gap-1 rounded bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400 disabled:opacity-40"
          >
            Next <ArrowRight size={14} />
          </button>
        </div>
      )}
      {step === 1 && (
        <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <p className="text-sm text-zinc-300">
            Step 2 of 3 - The app lives at http://127.0.0.1:__FPORT__ (frontend) and
            http://127.0.0.1:__BPORT__ (API + Swagger).
          </p>
          <button
            onClick={() => setStep(2)}
            className="rounded bg-zinc-800 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-700"
          >
            Next
          </button>
        </div>
      )}
      {step === 2 && (
        <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <p className="text-sm text-zinc-300">
            Step 3 of 3 - Start Ollama for the AI chat, or browse Tools, Jobs, Members and the Shop.
          </p>
          <button
            data-testid="onboarding-finish"
            onClick={finish}
            className="rounded bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400"
          >
            Finish
          </button>
        </div>
      )}
    </div>
  );
}
'@
Write-Scaffold "webapp/src/pages/Onboarding.tsx" $onboardingTsx

# =============================================================================
# START SCRIPTS (fleet standard: port clearing + auto-open browser)
# =============================================================================
$startPs1 = @'
param([switch]$Headless, [switch]$NoBrowser)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSCommandPath
$BackendPort = __BPORT__
$FrontendPort = __FPORT__

foreach ($port in @($BackendPort, $FrontendPort)) {
    Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

$backend = Start-Job -Name "__PKG__-backend" -ScriptBlock {
    param($Root, $Port)
    Set-Location $Root
    uv run uvicorn __PKG__.server:app --host 127.0.0.1 --port $Port
} -ArgumentList $Root, $BackendPort

for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) { break }
    } catch {}
    Start-Sleep -Seconds 1
}

$frontend = Start-Process -FilePath "bun" -ArgumentList "run", "dev" -WorkingDirectory (Join-Path $Root "webapp") -PassThru -WindowStyle Hidden

if (-not $NoBrowser) {
    $url = "http://127.0.0.1:$FrontendPort"
    Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Hidden", "-Command",
        "for (`$i = 0; `$i -lt 60; `$i++) { try { `$null = Invoke-WebRequest -Uri '$url' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; Start-Process '$url'; exit } catch { Start-Sleep -Seconds 1 } }"
}

Write-Host "Backend: http://127.0.0.1:$BackendPort/docs" -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:$FrontendPort" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray

try {
    while ($true) {
        if ($backend.State -eq "Failed") { Receive-Job $backend; break }
        Start-Sleep -Seconds 2
    }
} finally {
    Stop-Job $backend -ErrorAction SilentlyContinue
    Remove-Job $backend -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
}
'@
Write-Scaffold "start.ps1" $startPs1

$startBat = @'
@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1"
'@
Write-Scaffold "start.bat" $startBat

# =============================================================================
# PLAYWRIGHT E2E
# =============================================================================
$playwrightConfig = @'
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  retries: 1,
  use: {
    baseURL: "http://127.0.0.1:__FPORT__",
    headless: true,
    screenshot: "only-on-failure",
  },
});
'@
Write-Scaffold "webapp/playwright.config.ts" $playwrightConfig

$e2eSpec = @'
import { test, expect } from "@playwright/test";

const BE = "http://127.0.0.1:__BPORT__";
const FE = "http://127.0.0.1:__FPORT__";

test.describe("Fleet Audit", () => {
  test("Backend health", async ({ request }) => {
    const resp = await request.get(`${BE}/api/health`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe("ok");
  });

  test("Frontend loads without console errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto(FE, { timeout: 15000 });
    await expect(page.locator("#root")).toBeAttached();
    await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("Sidebar navigation works", async ({ page }) => {
    await page.goto(FE, { timeout: 15000 });
    await page.getByTestId("nav-tools").click();
    await expect(page.locator('[data-testid="tools-page"]')).toBeVisible();
    await page.getByTestId("nav-settings").click();
    await expect(page.locator('[data-testid="settings-page"]')).toBeVisible();
  });
});
'@
Write-Scaffold "webapp/e2e/fleet-audit.spec.ts" $e2eSpec

# =============================================================================
# CI (GitHub Actions)
# =============================================================================
$ciYml = @'
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --group dev
      - run: uv run ruff check .
      - run: uv run pytest tests/ -q

  frontend:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v2
      - run: bun install
        working-directory: webapp
      - run: bunx tsc --noEmit
        working-directory: webapp
      - run: bun run build
        working-directory: webapp
'@
Write-Scaffold ".github/workflows/ci.yml" $ciYml

# =============================================================================
# README
# =============================================================================
$readme = @'
# __APPNAME__

__DESC__

Fleet-standard fullstack app: FastMCP 3.4 backend, React + Vite + Tailwind frontend, Bun, optional Tauri 2.0 desktop wrapper.

## Quick start

```powershell
uv sync
bun --prefix webapp install
.\start.ps1          # clears ports, starts backend + frontend, opens browser
```

- Backend API + Swagger: http://127.0.0.1:__BPORT__/docs
- Frontend: http://127.0.0.1:__FPORT__
- MCP endpoint (when enabled): http://127.0.0.1:__BPORT__/mcp

## Tests

```powershell
uv run pytest tests/        # backend
bun --prefix webapp run e2e # Playwright
```

## Ports

Registered in the fleet reservoir: backend __BPORT__, frontend __FPORT__ (see `mcp-central-docs/operations/WEBAPP_PORTS.md`).
'@
Write-Scaffold "README.md" $readme

# =============================================================================
# OPTIONAL FEATURES
# =============================================================================
if ($IncludeVoice) {
    $speechTs = @'
export function stripMarkdown(md: string): string {
  return md
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[*_`#~]/g, "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/\n+/g, " ")
    .trim();
}

export function speak(text: string, onEnd?: () => void): () => void {
  if (typeof window === "undefined" || !window.speechSynthesis) return () => {};
  const plain = stripMarkdown(text);
  if (!plain) return () => {};
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(plain);
  u.rate = 1;
  u.pitch = 1;
  if (onEnd) u.onend = onEnd;
  window.speechSynthesis.speak(u);
  return () => window.speechSynthesis.cancel();
}

export function isTTSSupported(): boolean {
  return typeof window !== "undefined" && !!window.speechSynthesis;
}
'@
    Write-Scaffold "webapp/src/lib/speech.ts" $speechTs
}

if ($IncludePWA) {
    $pwaManifest = @'
{
  "name": "__APPNAME__",
  "short_name": "__APPNAME__",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#09090b",
  "theme_color": "#09090b"
}
'@
    Write-Scaffold "webapp/public/manifest.webmanifest" $pwaManifest
    Write-Scaffold "webapp/src/pwa.ts" "navigator.serviceWorker?.register('/sw.js').catch(() => undefined);
"
}

if ($IncludeTauri) {
    $cargoToml = @'
[package]
name = "__PKG__-native"
version = "0.1.0"
description = "Tauri 2.0 desktop app for __APPNAME__"
edition = "2021"

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-shell = "2"
tauri-plugin-fs = "2"
tauri-plugin-process = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"

[features]
default = ["custom-protocol"]
custom-protocol = ["tauri/custom-protocol"]
'@
    Write-Scaffold "native/Cargo.toml" $cargoToml

    $tauriConf = @'
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "__APPNAME__",
  "version": "0.1.0",
  "identifier": "ai.fleet.__PKG__",
  "build": {
    "frontendDist": "../webapp/dist",
    "devUrl": "http://localhost:__FPORT__",
    "beforeDevCommand": "bun --prefix ../webapp run dev",
    "beforeBuildCommand": "bun --prefix ../webapp install && bun --prefix ../webapp run build"
  },
  "app": {
    "windows": [{
      "label": "main",
      "title": "__APPNAME__",
      "width": 1100,
      "height": 750,
      "minWidth": 700,
      "minHeight": 500
    }],
    "security": { "csp": null }
  },
  "bundle": {
    "active": true,
    "targets": ["nsis"],
    "icon": ["icons/icon.ico", "icons/icon.png"],
    "resources": ["resources/.env.example"],
    "windows": {
      "webviewInstallMode": { "type": "skip" },
      "nsis": { "installMode": "currentUser" }
    }
  }
}
'@
    Write-Scaffold "native/src-tauri/tauri.conf.json" $tauriConf

    $buildRs = @'
fn main() {
    tauri_build::build()
}
'@
    Write-Scaffold "native/src-tauri/build.rs" $buildRs

    $mainRs = @'
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_process::init())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
'@
    Write-Scaffold "native/src-tauri/src/main.rs" $mainRs

    $capsJson = @'
{
  "identifier": "default",
  "description": "Default capability set for the main window",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "shell:allow-open",
    "shell:allow-spawn",
    "shell:allow-execute",
    "fs:default",
    "process:default"
  ]
}
'@
    Write-Scaffold "native/src-tauri/capabilities/default.json" $capsJson

    $nativeGitignore = @'
target/
gen/
resources/*.exe
binaries/*.exe
'@
    Write-Scaffold "native/.gitignore" $nativeGitignore

    $buildSidecar = @'
# Build the PyInstaller backend exe and copy into Tauri resources.
# See mcp-central-docs/standards/rules/tauri_nsis_building.md
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RepoName = Split-Path -Leaf $Root
$Triple = "x86_64-pc-windows-msvc"
$ResourceDir = "$PSScriptRoot\resources"
$DevDir = "$PSScriptRoot\binaries"
New-Item -ItemType Directory -Force -Path $ResourceDir, $DevDir | Out-Null

Push-Location $Root
$pyi = "$Root\.venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $pyi)) { uv add --dev pyinstaller }
& $pyi "$Root\__PKG__-backend.spec" --clean --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
Pop-Location

$src = "$Root\dist\__PKG__-backend.exe"
if (-not (Test-Path $src)) { throw "Backend exe not found at $src" }
Copy-Item $src "$ResourceDir\__PKG__-backend.exe" -Force
Copy-Item $src "$DevDir\__PKG__-backend-$Triple.exe" -Force
if (Test-Path "$Root\.env.example") { Copy-Item "$Root\.env.example" "$ResourceDir\.env.example" -Force }
Write-Host "Backend exe staged into Tauri resources." -ForegroundColor Green
'@
    Write-Scaffold "native/build-sidecar.ps1" $buildSidecar
}

# =============================================================================
# SUMMARY
# =============================================================================
Write-Host ""
Write-Host "=============================================================" -ForegroundColor Green
Write-Host "  $AppName scaffolded at $AppDir" -ForegroundColor Green
Write-Host "=============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Register ports $BackendPort/$FrontendPort in mcp-central-docs/operations/WEBAPP_PORTS.md"
Write-Host "  2. cd $AppDir"
Write-Host "  3. uv sync"
Write-Host "  4. bun --prefix webapp install"
Write-Host "  5. .\start.ps1"
Write-Host ""
Write-Host "Backend: http://127.0.0.1:$BackendPort/docs"
Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
Write-Host ""
Write-Host "Features: AI=$IncludeAI MCP=$IncludeMCP Upload=$IncludeFileUpload Voice=$IncludeVoice PWA=$IncludePWA Email=$IncludeEmail Realtime=$IncludeRealtime Scheduler=$IncludeScheduler Tauri=$IncludeTauri CI=$IncludeCI Tests=$IncludeTesting" -ForegroundColor Gray



