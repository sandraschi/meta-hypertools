"""MCP Server Scaffolding Tool - SOTA 2026 (FastMCP 3.4+).

Creates new fleet-compliant MCP servers with all required components:
- FastMCP 3.4+ dual transport (stdio + HTTP)
- Sampling handler, CodeMode, Prefab UI cards
- Agentic workflow, prompts, skills resources
- Fleet files: justfile, llms.txt, llms-full.txt, glama.json
- PyInstaller-ready run_server.py, start.ps1, .env.example
- mcpb manifest, CI (Windows), tests, docs
- Optional: Tauri 2.0 + NSIS installer wrapper
"""

# ruff: noqa: E501, F541 - code generator templates; line length in generated output
# and f-strings with only escaped braces are inherent to the pattern.

import asyncio
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from .decorators import ToolCategory, tool
from .server_builder_sota import generate_sota_package_files, generate_sota_pyproject, generate_sota_readme

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------


def _kebab_to_snake(name: str) -> str:
    return name.replace("-", "_")


def _kebab_to_pascal(name: str) -> str:
    return "".join(word.capitalize() for word in name.split("-"))


# ---------------------------------------------------------------------------
# Fleet-standard file generators (not in server_builder_sota.py)
# ---------------------------------------------------------------------------


def _generate_justfile(server_name: str, package_name: str, dual_connect: bool = False) -> str:
    """Generate justfile with fleet-standard recipes."""
    http_recipe = (
        f"""
serve-http:
    uv run python -m {package_name} --http --port 10800
"""
        if dual_connect
        else ""
    )

    return f"""set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

default:
    @just --list

install:
    uv sync --extra dev
    pre-commit install

serve:
    uv run python -m {package_name}{http_recipe}

web:
    @powershell -ExecutionPolicy Bypass -File start.ps1

lint:
    ruff check .
    ruff format --check .

fix:
    ruff check . --fix
    ruff format .

test:
    uv run pytest tests/ -v

mcpb-pack:
    @pwsh -NoLogo -File scripts/pack.ps1

# Tauri NSIS (only works when native/ directory exists)
build-native:
    @if (Test-Path native) {{ Set-Location native; npx @tauri-apps/cli build --bundles nsis }}

cua-nsis-test:
    uv run python scripts/cua-smoke.py

ci: lint test
"""


def _generate_llms_txt(server_name: str, package_name: str, description: str) -> str:
    """Generate llms.txt - LLM index file."""
    return f"""# {server_name}

> {description}

## Docs
- [README.md](./README.md): Overview, install, run, API
- [llms-full.txt](./llms-full.txt): Full tool reference, architecture, LLM providers

## Tools
- `help`: List capabilities and fleet surface
- `status`: Server health and version
- `chat`: Multi-provider LLM chat (Ollama, LM Studio, OpenAI, Anthropic, Google)
- `agentic_{package_name}_workflow`: Multi-step sampling workflow
- `{server_name.replace("-", "_")}_status_card`: Prefab health card

## REST API (HTTP mode)
- `GET /health` · `GET /api/v1/diagnostics` · `GET /api/v1/tools`
- `GET /api/v1/providers` · `POST /api/v1/chat` (streaming supported)

## Optional
- [CHANGELOG.md](./CHANGELOG.md)
- [PRD.md](./PRD.md)
- [glama.json](./glama.json)
"""


def _generate_llms_full_txt(server_name: str, package_name: str, description: str, author: str) -> str:
    """Generate llms-full.txt - exhaustive LLM reference."""
    pascal = _kebab_to_pascal(server_name)
    return f"""# {pascal} - Full LLM Reference

{description}

## Stack
- Python 3.12+ · FastMCP 3.4+ · prefab-ui >= 0.18.0
- httpx, pydantic v2, structlog
- uv (package manager), ruff (lint), pytest (test)

## Server Entry Points

| Mode | Command |
|------|---------|
| stdio (Claude Desktop / Cursor) | `uv run python -m {package_name}` |
| HTTP (Tauri / webapp) | `uv run python -m {package_name} --http --port <port>` |
| CodeMode agentic | `uv run python -m {package_name} --agentic` |
| PyInstaller | `python run_server.py` |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `{package_name.upper()}_SAMPLING_BASE_URL` | `http://127.0.0.1:11434/v1` | Ollama / LM Studio base URL |
| `{package_name.upper()}_SAMPLING_MODEL` | `llama3.2` | Model name for sampling |
| `{package_name.upper()}_SAMPLING_API_KEY` | - | Optional API key for sampling endpoint |
| `MCP_PORT` | `10800` | HTTP transport port |
| `MCP_HOST` | `127.0.0.1` | HTTP transport bind address |
| `MCP_AGENTIC` | - | Set to `1` to enable CodeMode |

## Fleet Surface

### Tools
- `help` - List available tools and resources
- `status` - Server health, version, tool count
- `agentic_{package_name}_workflow` - Multi-step sampling workflow (SEP-1577)
- `{server_name.replace("-", "_")}_status_card` - Prefab UI health card

### Resources
- `resource://{server_name}/skills` - Agent skill instructions
- `resource://{server_name}/capabilities` - Server capability summary

### Prompts
- `{package_name}_session` - Session priming prompt

## Tool Registration Pattern

All tools use the FastMCP 3.4+ decorator pattern with Pydantic v2 annotations:

```python
from fastmcp import FastMCP, Context
from typing import Annotated
from pydantic import Field

mcp = FastMCP("{server_name}")

@mcp.tool(annotations={{"readOnlyHint": True}})
async def my_tool(
    param: Annotated[str, Field(description="Parameter description")],
    ctx: Context = None,
) -> dict:
    \"\"\"Tool description - no Args: section needed.

    ## Return Format
    {{"success": bool, "data": {{...}}}}

    ## Examples
    await my_tool(param="value")
    \"\"\"
    return {{"success": True, "data": {{"param": param}}}}
```

## Portmanteau Pattern

For servers with many related operations, use the portmanteau pattern:

```python
from typing import Literal

@mcp.tool()
async def domain_ops(
    operation: Annotated[Literal["list", "get", "create"], Field(description="Operation to perform")],
    item_id: Annotated[str | None, Field(description="Item ID")] = None,
) -> dict:
    \"\"\"Domain operations portmanteau.

    [RATIONALE] Consolidated 3 operations to stay under tool limits.

    ## Return Format
    {{"success": bool, "operation": str, "data": {{...}}}}
    \"\"\"
    ...
```

## Dependencies

```toml
[project]
dependencies = [
    "fastmcp>=3.2,<4",
    "prefab-ui>=0.18.0",
    "httpx>=0.27",
    "pydantic>=2.0",
    "structlog>=24.0",
]
```

## License

MIT © {datetime.now().year} {author}
"""


def _generate_glama_json(server_name: str, description: str, author: str) -> str:
    """Generate glama.json for Glama MCP registry."""
    import json

    return json.dumps(
        {
            "name": server_name,
            "description": description,
            "version": "0.1.0",
            "author": author,
            "license": "MIT",
            "tags": ["mcp", "fastmcp", "python"],
            "repository": f"https://github.com/sandraschi/{server_name}",
        },
        indent=2,
    )


def _generate_env_example(package_name: str) -> str:
    """Generate .env.example with multi-provider LLM vars + fleet-standard env."""
    prefix = package_name.upper()
    return f"""# {package_name} - environment configuration

# ── LLM Provider ──
# Provider: ollama | lmstudio | openai | anthropic | google
# Local providers (ollama, lmstudio) are auto-detected - no config needed
{prefix}_LLM_PROVIDER=
# Override API base URL (e.g. for OpenRouter, custom endpoints)
{prefix}_LLM_BASE_URL=
# Override model name
{prefix}_LLM_MODEL=

# ── Cloud API Keys (only needed for cloud providers) ──
# {prefix}_LLM_API_KEY=           # OpenAI / OpenRouter / custom
# OPENAI_API_KEY=                 # Alternative for OpenAI
# ANTHROPIC_API_KEY=              # For Anthropic direct
# GOOGLE_API_KEY=                 # For Google Gemini

# ── HTTP Transport ──
MCP_PORT=10800
MCP_HOST=127.0.0.1
# MCP_AGENTIC=1                   # Enable CodeMode BM25 discovery

# ── PyInstaller / Tauri ──
# PORT=10800
# HOST=127.0.0.1
"""


def _generate_run_server_py(package_name: str, server_name: str) -> str:
    """Generate PyInstaller entry point with dual transport."""
    return f'''"""PyInstaller entry point - dual transport (HTTP when MCP_PORT set, else stdio)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from {package_name}.mcp_instance import get_mcp
from {package_name}.transport import run

if __name__ == "__main__":
    # Override MCP_PORT if PORT is set (PyInstaller / Tauri convention)
    if "PORT" in os.environ and "MCP_PORT" not in os.environ:
        os.environ["MCP_PORT"] = os.environ["PORT"]
    if "HOST" in os.environ and "MCP_HOST" not in os.environ:
        os.environ["MCP_HOST"] = os.environ["HOST"]

    mcp = get_mcp()
    run(mcp, "{server_name}")
'''


def _generate_pack_ps1(server_name: str) -> str:
    """Generate scripts/pack.ps1 - mcpb pack helper."""
    return f"""$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot
$ver = (Select-String '^version = "(.*)"' pyproject.toml).Matches.Groups[1].Value
$null = New-Item -ItemType Directory -Path dist -Force
npx --yes @anthropic-ai/mcpb@latest validate .
npx --yes @anthropic-ai/mcpb@latest pack . "dist/{server_name}-v$ver.mcpb"
Write-Host "Created dist/{server_name}-v$ver.mcpb" -ForegroundColor Green
"""


def _generate_start_ps1(server_name: str, package_name: str) -> str:
    """Generate start.ps1 - Windows dev launcher."""
    return f"""# {server_name} - dev launcher
param([switch]$Headless, [switch]$NoBrowser)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $PSCommandPath

# Kill any existing server on the port
$port = if ($env:MCP_PORT) {{ [int]$env:MCP_PORT }} else {{ 10800 }}
Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
    ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}

Write-Host "Starting {server_name} on http://127.0.0.1:$port" -ForegroundColor Cyan

if (-not $Headless) {{
    Start-Process "http://127.0.0.1:$port"
}}

Set-Location $ScriptRoot
uv run python -m {package_name} --http --port $port
"""


def _generate_start_bat(server_name: str) -> str:
    """Generate start.bat - Windows double-click launcher."""
    return '@echo off\ncd /d "%~dp0"\npowershell -ExecutionPolicy Bypass -File "%~dp0start.ps1"\n'


# ---------------------------------------------------------------------------
# Test, doc, example generators
# ---------------------------------------------------------------------------


def _generate_example_tool() -> str:
    """Generate a SOTA 2026 example portmanteau tool."""
    return '''"""Example portmanteau tool - demonstrates the fleet 2026 pattern."""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from pydantic import Field

from example_package.mcp_instance import mcp  # noqa: F811  - replaced at scaffold time

logger = logging.getLogger(__name__)


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
async def example_portmanteau(
    operation: Annotated[
        Literal["list", "get", "search"],
        Field(description="Operation to perform."),
    ],
    query: Annotated[str | None, Field(description="Search query for 'search' operation.")] = None,
    item_id: Annotated[str | None, Field(description="Item ID for 'get' operation.")] = None,
) -> dict:
    """Demonstrate the SOTA 2026 portmanteau pattern.

    [RATIONALE] Consolidates 3 related example operations into a single tool
    to demonstrate the fleet pattern without polluting the tool namespace.

    Operations:
    - list: Return example items.
    - get: Get a single example item by ID.
    - search: Search example items by query.

    ## Return Format
    {"success": bool, "operation": str, "data": [...]}

    ## Examples
    await example_portmanteau(operation="list")
    await example_portmanteau(operation="search", query="test")
    await example_portmanteau(operation="get", item_id="example-1")
    """
    if operation == "list":
        return {
            "success": True,
            "operation": "list",
            "data": [{"id": "example-1", "name": "First example"}],
        }
    if operation == "get":
        return {
            "success": True,
            "operation": "get",
            "data": {"id": item_id or "unknown", "name": "Example item"},
        }
    return {
        "success": True,
        "operation": "search",
        "data": [{"id": "example-1", "name": f"Result for: {query}"}],
    }
'''


def _generate_test_files(package_name: str, server_name: str) -> dict[str, str]:
    """Generate SOTA 2026 test file templates."""
    return {
        "tests/__init__.py": "",
        "tests/conftest.py": f'''"""Pytest configuration and initialization."""

from {package_name}.mcp_instance import get_mcp

# Initialize the FastMCP singleton so that top-level tool imports during test collection do not crash
get_mcp()
''',
        "tests/test_imports.py": f'''"""Verify the package imports and initializes cleanly."""


def test_package_imports():
    """All core modules should be importable."""
    import {package_name}
    assert {package_name}.__version__ == "0.1.0"


def test_config_loads():
    """Config should load with defaults."""
    from {package_name}.config import get_llm_config
    cfg = get_llm_config()
    assert cfg.base_url
    assert cfg.model
''',
        "tests/test_tools.py": f'''"""Verify tools register and return expected shapes."""

import asyncio


def test_help_tool():
    """Help tool should return tools list."""
    from {package_name}.tools.help_tools import help
    result = asyncio.run(help())
    assert result["success"]
    assert "tools" in result


def test_status_tool():
    """Status tool should report healthy."""
    from {package_name}.tools.help_tools import status
    result = asyncio.run(status())
    assert result["success"]
    assert result["healthy"]
    assert "version" in result
''',
    }


def _generate_docs(server_name: str, description: str) -> dict[str, str]:
    """Generate fleet-accurate documentation files."""
    package_name = _kebab_to_snake(server_name)
    return {
        "docs/TOOLS.md": f"""# {server_name} - Tool Reference

## Core Tools

### `help`
List available tools, resources, and CodeMode status.

### `status`
Server health, version, and tool count.

### `agentic_{package_name}_workflow`
Multi-step sampling workflow. Requires a sampling-capable MCP client
(Claude Desktop, Cursor with sampling support).

### `{server_name.replace("-", "_")}_status_card`
Prefab UI health card rendered in supporting MCP clients.

## Fleet Surface

| Feature | Entry |
|---------|-------|
| Prompts | `{package_name}_session` |
| Skills | `resource://{server_name}/skills` |
| Capabilities | `resource://{server_name}/capabilities` |
| CodeMode | `--agentic` flag or `MCP_AGENTIC=1` |
""",
        "docs/ARCHITECTURE.md": f"""# {server_name} - Architecture

## Package Layout

```
src/{package_name}/
├── __init__.py          # Version
├── __main__.py          # python -m entry
├── server.py            # Top-level runner
├── config.py            # Sampling config
├── sampling.py          # OpenAI-compatible handler
├── mcp_instance.py      # FastMCP singleton
├── tool_registration.py # Import all tools
├── fleet_surface.py     # Prompts, resources, prefab card
├── prefabs.py           # Prefab UI card builders
├── transport.py         # Dual transport (stdio/HTTP) + CodeMode
└── tools/
    ├── __init__.py
    ├── help_tools.py    # help + status
    └── agentic_workflow.py  # SEP-1577 sampling workflow
```

## Transport

- **stdio**: Default - for Claude Desktop, Cursor, Windsurf
- **HTTP**: Via `--http --port <port>` - for Tauri/webapp integration
- **PyInstaller**: `run_server.py` - detects `MCP_PORT`/`PORT` for HTTP, falls back to stdio

## Sampling

Configured via `{package_name.upper()}_SAMPLING_BASE_URL` (default: Ollama on localhost:11434).
Also works with LM Studio (`http://localhost:1234/v1`) and any OpenAI-compatible endpoint.
""",
    }


def _generate_ci_workflow() -> str:
    """Generate GitHub Actions CI workflow (Windows)."""
    return """name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: uv sync --group dev
      - name: Lint with ruff
        run: uv run ruff check .
      - name: Run tests
        run: uv run pytest tests/ -v
"""


def _generate_native(
    server_name: str, package_name: str, description: str, author: str, backend_port: int = 10800
) -> dict[str, str]:
    """Generate the full native/ Tauri 2.0 + NSIS directory contents.

    Returns dict of relative path -> file content.
    """
    pascal = _kebab_to_pascal(server_name)
    identifier = f"ai.fleet.{server_name}"
    frontend_dist = "../webapp/dist"

    return {
        "native/.gitignore": """resources/*.exe
binaries/*.exe
target/
gen/
""",
        "native/Cargo.toml": f'''[package]
name = "{server_name}-native"
version = "0.1.0"
description = "Tauri 2.0 desktop app for {server_name}"
edition = "2021"

[build-dependencies]
tauri-build = {{ version = "2", features = [] }}

[dependencies]
tauri = {{ version = "2", features = ["tray-icon"] }}
tauri-plugin-shell = "2"
tauri-plugin-fs = "2"
tauri-plugin-process = "2"
serde = {{ version = "1", features = ["derive"] }}
serde_json = "1"

[features]
default = ["custom-protocol"]
custom-protocol = ["tauri/custom-protocol"]
''',
        "native/tauri.conf.json": json.dumps(
            {
                "productName": pascal,
                "version": "0.1.0",
                "identifier": identifier,
                "build": {
                    "frontendDist": frontend_dist,
                    "devUrl": f"http://localhost:{backend_port}",
                    "beforeDevCommand": f"npm --prefix ../webapp run dev",
                    "beforeBuildCommand": "pwsh -NoProfile -File ./scripts/build-desktop.ps1",
                },
                "app": {
                    "windows": [
                        {
                            "label": "main",
                            "title": pascal,
                            "width": 1100,
                            "height": 750,
                            "minWidth": 700,
                            "minHeight": 500,
                        }
                    ],
                    "security": {"csp": None},
                },
                "bundle": {
                    "active": True,
                    "targets": ["nsis"],
                    "icon": ["icons/icon.ico", "icons/icon.png"],
                    "resources": [
                        f"resources/{server_name}-backend.exe",
                    ],
                    "windows": {
                        "webviewInstallMode": {"type": "skip"},
                        "nsis": {
                            "installMode": "currentUser",
                            "installerHooks": "./windows/hooks.nsh",
                        },
                    },
                },
            },
            indent=2,
        ),
        "native/src/main.rs": f"""mod backend;
use backend::{{BackendProcess, spawn_backend}};
use tauri::{{Emitter, Manager}};

#[tauri::command]
async fn start_backend(app: tauri::AppHandle, state: tauri::State<'_, BackendProcess>) -> Result<String, String> {{
    spawn_backend(app, &state)
}}

fn main() {{
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_process::init())
        .manage(BackendProcess(std::sync::Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![start_backend])
        .setup(|app| {{
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {{
                if let Err(e) = start_backend(handle.clone(), handle.state::<BackendProcess>()).await {{
                    let _ = handle.emit("backend-status", format!("error: {{e}}"));
                }}
            }});
            Ok(())
        }})
        .build(tauri::generate_context!())
        .expect("error building tauri application")
        .run(|app, event| {{
            if let tauri::RunEvent::Exit = event {{
                if let Some(mut child) = app.state::<BackendProcess>().0.lock().unwrap().take() {{
                    let _ = child.kill();
                }}
            }}
        }});
}}
""",
        "native/src/backend.rs": f'''use std::fs::{{self, OpenOptions}};
use std::io::{{BufRead, BufReader, Write}};
use std::net::{{SocketAddr, TcpStream}};
use std::path::PathBuf;
use std::process::{{Child, Command, Stdio}};
use std::str::FromStr;
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use tauri::path::BaseDirectory;
use tauri::{{AppHandle, Emitter, Manager}};

pub struct BackendProcess(pub Mutex<Option<Child>>);

const BACKEND_NAME: &str = "{server_name}-backend.exe";
const BACKEND_PORT: u16 = {backend_port};
const ENV_PORT: &str = "MCP_PORT";
const ENV_HOST: &str = "MCP_HOST";
const ENV_TAURI: &str = "{package_name.upper()}_TAURI";

fn log_line(app: &AppHandle, message: &str) {{
    eprintln!("[backend] {{message}}");
    if let Ok(dir) = app.path().app_log_dir() {{
        let _ = fs::create_dir_all(&dir);
        let log_path = dir.join("backend-spawn.log");
        if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_path) {{
            let _ = writeln!(file, "{{message}}");
        }}
    }}
}}

fn resolve_bundled_backend(app: &AppHandle) -> Result<PathBuf, String> {{
    let mut tried = Vec::new();
    let resources_path = format!("resources/{{BACKEND_NAME}}");
    if let Ok(path) = app.path().resolve(&resources_path, BaseDirectory::Resource) {{
        tried.push(path.display().to_string());
        if path.exists() {{ return Ok(path); }}
    }}
    if let Ok(path) = app.path().resolve(BACKEND_NAME, BaseDirectory::Resource) {{
        tried.push(path.display().to_string());
        if path.exists() {{ return Ok(path); }}
    }}
    Err(format!("bundled backend missing (tried: {{}})", tried.join("; ")))
}}

pub fn materialize_backend(app: &AppHandle) -> Result<PathBuf, String> {{
    let bundled = resolve_bundled_backend(app)?;
    log_line(app, &format!("using bundled backend: {{}}", bundled.display()));
    Ok(bundled)
}}

fn free_port(port: u16) {{
    let script = format!(
        "Get-NetTCPConnection -LocalPort {{port}} -ErrorAction SilentlyContinue \
        | ForEach-Object {{ taskkill /F /PID `$_.OwningProcess /T 2>$null }}"
    );
    let _ = Command::new("powershell.exe")
        .args(["-NoProfile", "-Command", &script])
        .stdout(Stdio::null()).stderr(Stdio::null())
        .status();
    thread::sleep(Duration::from_millis(500));
}}

pub fn spawn_backend(app: AppHandle, state: &BackendProcess) -> Result<String, String> {{
    if let Some(mut child) = state.0.lock().unwrap().take() {{
        let _ = child.kill();
        let _ = child.wait();
    }}
    free_port(BACKEND_PORT);

    let backend_path = materialize_backend(&app)?;
    log_line(&app, &format!("spawning {{}} on port {{}}", backend_path.display(), BACKEND_PORT));

    let mut command = Command::new(&backend_path);
    command
        .env(ENV_PORT, BACKEND_PORT.to_string())
        .env(ENV_HOST, "127.0.0.1")
        .env(ENV_TAURI, "1")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    #[cfg(windows)]
    {{
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }}

    let mut child = command.spawn()
        .map_err(|e| format!("Failed to spawn {{}}: {{e}}", backend_path.display()))?;

    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    state.0.lock().unwrap().replace(child);

    if let Some(out) = stdout {{
        let handle = app.clone();
        thread::spawn(move || watch_backend_stream(out, handle));
    }}
    if let Some(err) = stderr {{
        let handle = app.clone();
        thread::spawn(move || watch_backend_stream(err, handle));
    }}

    let addr = SocketAddr::from_str(&format!("127.0.0.1:{{BACKEND_PORT}}")).unwrap();
    let app_health = app.clone();
    thread::spawn(move || {{
        for attempt in 0..30 {{
            thread::sleep(Duration::from_secs(2));
            match TcpStream::connect_timeout(&addr, Duration::from_secs(2)) {{
                Ok(_) => {{
                    log_line(&app_health, &format!("Backend health check PASSED on port {{BACKEND_PORT}} (attempt {{}})", attempt + 1));
                    let _ = app_health.emit("backend-status", "ready");
                    return;
                }}
                Err(e) => log_line(&app_health, &format!("Backend health check: {{e}} (attempt {{}})", attempt + 1)),
            }}
        }}
        log_line(&app_health, &format!("Backend health check FAILED"));
        let _ = app_health.emit("backend-status", "error: backend not reachable");
    }});

    Ok(format!("Backend starting on port {{BACKEND_PORT}}"))
}}

fn watch_backend_stream<R: std::io::Read + Send + 'static>(stream: R, app: AppHandle) {{
    let reader = BufReader::new(stream);
    for line in reader.lines().map_while(Result::ok) {{
        log_line(&app, &line);
    }}
}}
''',
        "native/windows/hooks.nsh": f'''; -- native/windows/hooks.nsh --
; Kill UI + backend before install/uninstall.
!macro KillFleetProcesses
  DetailPrint "Stopping {server_name} processes..."
  ExecWait 'taskkill /F /IM {server_name}-backend.exe /T' $0
  ExecWait 'taskkill /F /IM {server_name}-native.exe /T' $0
  !if "${{INSTALLMODE}}" == "currentUser"
    nsis_tauri_utils::KillProcessCurrentUser "{server_name}-backend.exe"
    Pop $0
    nsis_tauri_utils::KillProcessCurrentUser "{server_name}-native.exe"
    Pop $0
  !else
    nsis_tauri_utils::KillProcess "{server_name}-backend.exe"
    Pop $0
    nsis_tauri_utils::KillProcess "{server_name}-native.exe"
    Pop $0
  !endif
  Sleep 2000
!macroend

!macro UninstallPrevious
  DetailPrint "Checking for previous installation..."
  !if "${{INSTALLMODE}}" == "currentUser"
    ReadRegStr $R0 HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{IDENTIFIER}}" "UninstallString"
  !else
    ReadRegStr $R0 HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{IDENTIFIER}}" "UninstallString"
  !endif
  ${{If}} $R0 != ""
    DetailPrint "Removing previous installation..."
    ExecWait '"$R0" /S' $0
    DetailPrint "Previous uninstall exit code: $0"
    Sleep 1500
  ${{EndIf}}
!macroend

!macro NSIS_HOOK_PREINSTALL
  !insertmacro KillFleetProcesses
  !insertmacro UninstallPrevious
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  !insertmacro KillFleetProcesses
!macroend
''',
        "native/capabilities/default.json": json.dumps(
            {
                "identifier": "default",
                "description": "Default capability set for the main window",
                "windows": ["main"],
                "permissions": [
                    "core:default",
                    "shell:allow-open",
                    "shell:allow-spawn",
                    "fs:default",
                    "process:default",
                ],
            },
            indent=2,
        ),
        "native/build.ps1": f"""$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RepoName = Split-Path -Leaf $Root
$ResourceDir = "$PSScriptRoot\\resources"
$DevDir = "$PSScriptRoot\\binaries"
New-Item -ItemType Directory -Force -Path $ResourceDir, $DevDir | Out-Null

Write-Host "=== ${{RepoName}} Tauri Release Build ===" -ForegroundColor Cyan

# Step 1: TypeScript lint + frontend build
$frontendDirs = @("web_sota", "webapp/frontend", "webapp")
foreach ($dir in $frontendDirs) {{
    $frontend = Join-Path $Root $dir
    if (Test-Path "$frontend\\package.json") {{
        Write-Host "-> [1/4] Building frontend ($dir)..." -ForegroundColor Yellow
        Push-Location $frontend
        npm install --silent 2>$null
        npx tsc --noEmit 2>&1
        if ($LASTEXITCODE -ne 0) {{ throw "TypeScript compilation failed" }}
        npm run build
        Pop-Location
        break
    }}
}}

# Step 2: PyInstaller backend
Write-Host "-> [2/4] PyInstaller backend..." -ForegroundColor Yellow
$specFile = "$Root\\${{RepoName}}-backend.spec"
if (Test-Path $specFile) {{
    Push-Location $Root
    $pyi = "$Root\\.venv\\Scripts\\pyinstaller.exe"
    Remove-Item "$Root\\dist\\${{RepoName}}-backend.exe" -Force -ErrorAction SilentlyContinue
    & $pyi "$specFile" --clean --noconfirm
    if ($LASTEXITCODE -ne 0) {{ throw "PyInstaller failed" }}
    Pop-Location
}}

# Step 3: Embed backend in Tauri resources
Write-Host "-> [3/4] Embedding backend..." -ForegroundColor Yellow
$src = "$Root\\dist\\${{RepoName}}-backend.exe"
if (Test-Path $src) {{
    Copy-Item $src "$ResourceDir\\${{RepoName}}-backend.exe" -Force
    Write-Host "  Backend exe: $((Get-Item $src).Length / 1MB) MB" -ForegroundColor Green
}}

$envExample = "$Root\\.env.example"
if (Test-Path $envExample) {{ Copy-Item $envExample "$ResourceDir\\.env.example" -Force }}

# Step 4: NSIS build
Write-Host "-> [4/4] Tauri NSIS bundle..." -ForegroundColor Yellow
Push-Location $PSScriptRoot
$env:Path = "$env:USERPROFILE\\.cargo\\bin;$env:Path"
npx @tauri-apps/cli build --bundles nsis
Pop-Location
Write-Host "=== Build complete ===" -ForegroundColor Green
""",
        f"{server_name}-backend.spec": f"""# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['run_server.py'], pathex=['src'],
    datas=[('src/{package_name}', '{package_name}')],
    hiddenimports=['uvicorn.logging','uvicorn.loops','uvicorn.loops.asyncio','uvicorn.protocols','uvicorn.protocols.http','uvicorn.protocols.http.httptools_impl','uvicorn.protocols.http.h11_impl','uvicorn.lifespan','uvicorn.lifespan.on'],
    excludes=['tkinter','setuptools','pip','wheel','test','tests','unittest','_distutils_hack'],
    noarchive=True,
)
_keep_dist = ['fastmcp-', 'mcp-', 'prefab_ui-', 'opentelemetry-']
_saved = [e for e in a.datas if isinstance(e, tuple) and any(k in str(e[0]) for k in _keep_dist) and '.dist-info' in str(e[0])]
for _list in [a.datas, a.binaries, a.zipfiles, a.scripts]:
    _list[:] = [e for e in _list if not (isinstance(e, tuple) and '.dist-info' in str(e[0]))]
a.datas.extend(_saved)
SKIP = ['torch','playwright','bitsandbytes','llvmlite','pyarrow','pymupdf','grpc','numba','Cython','google','azure','boto3','botocore','matplotlib','PIL','pandas','scipy','sklearn','onnxruntime']
a.binaries = [b for b in a.binaries if not any(s in b[0].lower() for s in SKIP)]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, name='{server_name}-backend', debug=False, strip=False, upx=False, upx_exclude=[], runtime_tmpdir=None, console=False)
""",
    }

    """Generate .gitignore."""
    return """# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
.ruff_cache/
.pytest_cache/
.python-version

# Node (webapp)
node_modules/

# Secrets
.env

# OS
.DS_Store
Thumbs.db
*.bak
"""


def _generate_gitignore() -> str:
    """Generate .gitignore."""
    return """# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
.ruff_cache/
.pytest_cache/
.python-version

# Node (webapp)
node_modules/

# Secrets
.env

# OS
.DS_Store
Thumbs.db
*.bak

# Rust / Tauri
native/target/
native/resources/*.exe
native/binaries/*.exe
native/gen/
"""


def _generate_prd_md(server_name: str, description: str, dual_connect: bool = False) -> str:
    """Generate PRD.md."""
    transport_info = "stdio + HTTP" if dual_connect else "stdio (HTTP optional)"
    return f"""# Product Requirements Document: {server_name}

## Overview
{description}

## Target Audience
- AI agents (Claude Desktop, Cursor, Windsurf)
- Fleet MCP servers consuming this server
- Developers integrating via MCP protocol

## Core Features
1. **FastMCP 3.4+**: Full MCP protocol with tools, prompts, resources
2. **Transport**: {transport_info}
3. **Sampling**: OpenAI-compatible endpoint (Ollama, LM Studio)
4. **Prefab UI**: Rich in-chat cards for status/discovery
5. **CodeMode**: BM25 agentic discovery via `--agentic`
6. **Fleet integration**: Glama registry, llms.txt, mcpb packaging

## Success Metrics
- All tools return structured dicts with success/data/error
- Sampling fallback works when client lacks sampling support
- mcpb pack produces valid .mcpb bundle
"""


def _generate_changelog_md(server_name: str) -> str:
    """Generate CHANGELOG.md."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return f"""# Changelog: {server_name}

## [0.1.0] - {date_str} - Initial Scaffold
- FastMCP 3.4+ dual transport (stdio + HTTP)
- Sampling handler (Ollama/LM Studio compatible)
- Agentic workflow, Prefab UI card, prompts, skills
- Fleet files: justfile, llms.txt, glama.json
- PyInstaller entry point (run_server.py)
- CI (Windows), tests, docs
"""


# ---------------------------------------------------------------------------
# Frontend generation (optional)
# ---------------------------------------------------------------------------


def _generate_frontend(
    server_dir: Path,
    server_name: str,
    description: str,
    author: str,
    frontend_type: str = "fullstack",
) -> dict[str, Any]:
    """Generate frontend by copying fullstack-builder when available."""
    try:
        source_builder = Path("D:/Dev/repos/fullstack-builder-script")
        dest_webapp = server_dir / "webapp"

        if source_builder.exists():
            shutil.copytree(
                source_builder,
                dest_webapp,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules", "dist"),
            )
            logger.info(f"Fullstack builder copied to {dest_webapp}")
            return {
                "success": True,
                "frontend_path": str(dest_webapp),
                "message": "Frontend scaffolded from fullstack-builder-script",
            }
        return {"success": False, "error": f"fullstack-builder-script not found at {source_builder}"}
    except Exception as e:
        logger.error(f"Frontend generation failed: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Main scaffold tool
# ---------------------------------------------------------------------------


@tool(
    name="create_mcp_server",
    description="""Create a new SOTA-compliant MCP server from scratch.

    Scaffolds a fleet 2026 MCP server:
    - FastMCP 3.4+ (sampling, prompts, skills resources)
    - Agentic workflow tool (SEP-1577) + CodeMode (--agentic)
    - Prefab-UI status card
    - Fleet files: justfile, llms.txt, llms-full.txt, glama.json, .env.example
    - PyInstaller entry point (run_server.py), start.ps1
    - mcpb/manifest.json, CI (Windows), tests, docs
    - Optional: fullstack webapp via fullstack-builder-script""",
    category=ToolCategory.DISCOVERY,
    tags=["server", "scaffold", "create", "sota"],
    estimated_runtime="15-20s",
)
async def create_mcp_server(
    server_name: str,
    description: str,
    author: str = "MCP Studio",
    license_type: str = "MIT",
    target_path: str = "D:/Dev/repos",
    include_examples: bool = True,
    make_git: bool = True,
    init_git: bool | None = None,
    include_frontend: bool = False,
    frontend_type: str = "fullstack",
    include_nsis: bool = False,
    include_mcpb: bool = True,
    build_mcpb: bool = True,
    dual_connect: bool = False,
    include_prd: bool = True,
    include_changelog: bool = True,
    include_prompts: bool = True,
) -> dict[str, Any]:
    """Create a new SOTA-compliant MCP server.

    Args:
        server_name: Kebab-case server name (e.g., "my-server")
        description: Server description
        author: Author name (default: "MCP Studio")
        license_type: License type (default: "MIT")
        target_path: Parent directory (default: "D:/Dev/repos")
        include_examples: Include example portmanteau tool (default: True)
        make_git: Initialize git repository and create initial commit (default: True)
        init_git: Deprecated alias for make_git
        include_frontend: Copy fullstack-builder webapp scaffold (default: False)
        frontend_type: "fullstack" or "minimal" (default: "fullstack")
        include_nsis: Generate native/ Tauri 2.0 + NSIS installer wrappers (default: False)
        include_mcpb: Include mcpb/manifest.json (default: True)
        build_mcpb: Build .mcpb bundle in dist/ after scaffold (default: True)
        dual_connect: Support both stdio and HTTP transport (default: False)
        include_prd: Include PRD.md template (default: True)
        include_changelog: Include CHANGELOG.md (default: True)
        include_prompts: Include prompt templates (default: True)

    Returns:
        Dictionary with creation status, server path, and next steps
    """
    try:
        # Validate server name
        if not server_name or not server_name.replace("-", "").replace("_", "").isalnum():
            return {"success": False, "error": "Server name must be alphanumeric with hyphens/underscores only"}

        package_name = _kebab_to_snake(server_name)
        # Portable default: honour FLEET_REPOS_ROOT/REPOS_DIR when caller left the stock default
        if target_path in ("D:/Dev/repos", r"D:\Dev\repos", "d:/Dev/repos", "d:\\Dev\\repos"):
            _env_root = os.environ.get("FLEET_REPOS_ROOT") or os.environ.get("REPOS_DIR")
            if _env_root:
                target_path = _env_root
        target_dir = Path(target_path).expanduser().resolve()
        server_dir = target_dir / server_name

        if server_dir.exists():
            return {"success": False, "error": f"Directory already exists: {server_dir}"}

        server_dir.mkdir(parents=True, exist_ok=False)
        logger.info(f"Scaffolding {server_name} at {server_dir}")

        # Directory structure
        (server_dir / "src" / package_name / "tools").mkdir(parents=True, exist_ok=True)
        (server_dir / "skills" / server_name).mkdir(parents=True, exist_ok=True)
        (server_dir / "mcpb").mkdir(parents=True, exist_ok=True)
        (server_dir / "tests").mkdir(parents=True, exist_ok=True)
        (server_dir / "docs").mkdir(parents=True, exist_ok=True)
        (server_dir / "scripts").mkdir(parents=True, exist_ok=True)
        (server_dir / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        (server_dir / "assets").mkdir(parents=True, exist_ok=True)

        files_created: list[str] = []

        def _write(rel_path: str, content: str) -> None:
            out = server_dir / rel_path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content, encoding="utf-8")
            files_created.append(rel_path)

        # ── Core SOTA Python files ──
        sota_files = generate_sota_package_files(
            server_name,
            package_name,
            description,
            author,
            dual_connect=dual_connect,
        )
        for rel_path, content in sota_files.items():
            _write(rel_path, content)

        # ── pyproject.toml ──
        _write("pyproject.toml", generate_sota_pyproject(package_name, description, author, license_type))

        # ── README.md ──
        _write("README.md", generate_sota_readme(server_name, package_name, description, author))

        # ── Fleet standard files ──
        _write("justfile", _generate_justfile(server_name, package_name, dual_connect))
        _write("llms.txt", _generate_llms_txt(server_name, package_name, description))
        _write("llms-full.txt", _generate_llms_full_txt(server_name, package_name, description, author))
        _write("glama.json", _generate_glama_json(server_name, description, author))
        _write(".env.example", _generate_env_example(package_name))
        _write(".gitignore", _generate_gitignore())
        _write("assets/.gitkeep", "")
        _write("run_server.py", _generate_run_server_py(package_name, server_name))
        _write("start.ps1", _generate_start_ps1(server_name, package_name))
        _write("start.bat", _generate_start_bat(server_name))
        _write("scripts/pack.ps1", _generate_pack_ps1(server_name))

        # ── CI workflow (Windows) ──
        _write(".github/workflows/ci.yml", _generate_ci_workflow())

        # ── Tauri 2.0 + NSIS installer (optional) ──
        if include_nsis:
            native_files = _generate_native(server_name, package_name, description, author)
            for rel_path, content in native_files.items():
                _write(rel_path, content)

        # ── Example tool ──
        if include_examples:
            content = _generate_example_tool().replace("example_package", package_name)
            _write(f"src/{package_name}/tools/example_portmanteau.py", content)

        # ── Tests ──
        test_files = _generate_test_files(package_name, server_name)
        for rel_path, content in test_files.items():
            _write(rel_path, content)

        # ── Documentation ──
        doc_files = _generate_docs(server_name, description)
        for rel_path, content in doc_files.items():
            _write(rel_path, content)

        # ── PRD.md ──
        if include_prd:
            _write("PRD.md", _generate_prd_md(server_name, description, dual_connect))

        # ── CHANGELOG.md ──
        if include_changelog:
            _write("CHANGELOG.md", _generate_changelog_md(server_name))

        # ── LICENSE ──
        if license_type == "MIT":
            _write(
                "LICENSE",
                (
                    f"MIT License\n\nCopyright (c) {datetime.now().year} {author}\n\n"
                    "Permission is hereby granted, free of charge, to any person obtaining a copy "
                    'of this software and associated documentation files (the "Software"), to deal '
                    "in the Software without restriction, including without limitation the rights "
                    "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
                    "copies of the Software, and to permit persons to whom the Software is "
                    "furnished to do so, subject to the following conditions:\n\n"
                    "The above copyright notice and this permission notice shall be included in all "
                    "copies or substantial portions of the Software.\n\n"
                    'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR '
                    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, "
                    "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE "
                    "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER "
                    "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, "
                    "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n"
                ),
            )

        # ── mcpb cleanup (if disabled) ──
        if not include_mcpb:
            mcpb_manifest = server_dir / "mcpb" / "manifest.json"
            if mcpb_manifest.exists():
                mcpb_manifest.unlink()
                files_created = [p for p in files_created if p != "mcpb/manifest.json"]

        # ── Git init ──
        git_initialized = False
        final_make_git = make_git if init_git is None else init_git
        if final_make_git:
            try:
                git_path = shutil.which("git") or "git"
                await asyncio.to_thread(
                    subprocess.run, [git_path, "init"], cwd=server_dir, check=True, capture_output=True
                )
                await asyncio.to_thread(
                    subprocess.run, [git_path, "add", "."], cwd=server_dir, check=True, capture_output=True
                )
                await asyncio.to_thread(
                    subprocess.run,
                    [git_path, "commit", "-m", f"Initial scaffold: {server_name} (FastMCP 3.4+ fleet 2026)"],
                    cwd=server_dir,
                    check=True,
                    capture_output=True,
                )
                git_initialized = True
                logger.info(f"Git repo initialized for {server_name}")
            except Exception as e:
                logger.warning(f"Git init failed (non-fatal): {e}")

        # ── mcpb build ──
        mcpb_built = False
        if include_mcpb and build_mcpb:
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    [sys.executable, "-m", "pip", "install", "mcpb"],
                    check=True,
                    capture_output=True,
                )
                mcpb_path = shutil.which("mcpb") or "mcpb"
                await asyncio.to_thread(
                    subprocess.run, [mcpb_path, "build"], cwd=server_dir, check=True, capture_output=True
                )
                mcpb_built = True
                files_created.append("dist/*.mcpb")
                logger.info(f"MCP bundle built for {server_name}")
            except Exception as e:
                logger.warning(f"mcpb build failed (non-fatal): {e}")

        # ── Frontend scaffold ──
        frontend_generated = False
        webapp_path = None
        if include_frontend:
            result = _generate_frontend(server_dir, server_name, description, author, frontend_type)
            frontend_generated = result.get("success", False)
            webapp_path = result.get("frontend_path")
            if frontend_generated:
                files_created.append("webapp/**/*")

        # ── Next steps ──
        next_steps = [
            f"cd {server_dir}",
            "uv sync --group dev",
            f"uv run python -m {package_name}",
            f"uv run python -m {package_name} --agentic  # CodeMode",
            f"# Add tools under src/{package_name}/tools/",
            "uv run pytest",
        ]
        if frontend_generated and webapp_path:
            next_steps.extend(["", "cd webapp && npm install && npm run dev"])

        return {
            "success": True,
            "server_name": server_name,
            "server_path": str(server_dir),
            "package_name": package_name,
            "files_created": files_created,
            "file_count": len(files_created),
            "git_initialized": git_initialized,
            "mcpb_built": mcpb_built,
            "sota_compliant": True,
            "fastmcp_version": "3.4",
            "features": [
                "sampling",
                "agentic_workflow",
                "prefab_ui",
                "codemode",
                "dual_transport",
                "run_server_py",
                "justfile",
                "llms_txt",
                "glama_json",
                "env_example",
                "start_ps1",
                "ci_windows",
            ]
            + (["nsis", "tauri"] if include_nsis else []),
            "frontend_generated": frontend_generated,
            "frontend_path": webapp_path,
            "next_steps": next_steps,
        }

    except Exception as e:
        logger.error(f"Scaffold failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
