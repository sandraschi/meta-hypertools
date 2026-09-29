# Meta Hypertools desktop app (Tauri 2.0 + NSIS)

One installer, one shortcut: `Meta Hypertools_0.5.1_x64-setup.exe`
installs the operator window plus an embedded Python backend. No Python,
Node, `uv`, or git clone needed on the target machine.

- UI: Rust shell (WebView2) + `web_sota/dist`, bundle id
  `com.sandraschi.meta-mcp`, currentUser install.
- Backend: PyInstaller onefile `meta-mcp-backend.exe`, embedded in bundle
  resources, copied to the app cache on launch and spawned on port 11220
  (`META_MCP_TAURI=1`, dedicated operator port registered as
  `meta-mcp-native` backend - clear of the 10718 dev backend so both can
  run side by side). Killed with the window on exit.
- First run seeds `.env` from the bundled `.env.example` into
  `%LOCALAPPDATA%`; the real `.env` is never bundled.

## Build (build machine only)

Prerequisites: Rust (`cargo`), Node 22+, `uv`, WebView2 runtime for
testing. Python deps via `uv sync --group dev` (pyinstaller included).

```powershell
cd D:\Dev\repos\meta_mcp
just build-native
```

Pipeline (`web_sota/src-tauri/build.ps1`): Step-0 API port check, tsc +
vite build with `VITE_API_BASE_URL=http://127.0.0.1:10718`, PyInstaller
from the project venv, frozen smoke (`/health` + a real JSON route),
5 MB size gate, embed to `resources/`, `tauri build --bundles nsis`,
stage the setup exe to `dist/`. Partial runs: `just build-sidecar`
stops after embedding (same script, full pipeline today).

The bundle entry (`mcpb/run_server.py`) speaks
MCP stdio by default and HTTP with `--http`; frozen builds translate
`MCP_PORT`/`PORT` env into flags before argparse. Claude Desktop config
uses `uv run meta-mcp-server` against source; the installed app serves
`http://127.0.0.1:10718` while running.

## Frozen-build fixes record (all in-repo)

- `meta-mcp-backend.spec`: `collect_all` 2-tuple TOC normalization,
  dist-info keep list (mcp/fastmcp/fastapi/pydantic/opentelemetry/email
  variants), tomli mypyc hashed runtime, docket + burner_redis for
  FastMCP tasks, joserfc/pydantic/cachetools/key_value hiddenimports,
  OTEL runtime hook, `console=True` (uvicorn logging crashes on None
  stderr), `noarchive=True`, standard SKIP list.
- NSIS hooks kill both `meta-mcp-backend.exe` and `meta-mcp-native.exe`
  pre-install and pre-uninstall (backend file lock hangs installs).
- CSP `connect-src` covers the backend origin; CORS already lists Tauri
  origins with an unconditional regex.
- Frontend: Ctrl+scroll zoom ladder (persisted), backend-status dot
  (Tauri event + backoff HTTP poll).

## Verify before release

1. No `*-native.exe` / `*-backend.exe` in Task Manager.
2. Install (uninstall old first on upgrade path).
3. `%LOCALAPPDATA%\com.sandraschi.meta-mcp\logs\backend-spawn.log` shows
   the resources backend path + Uvicorn running.
4. `Invoke-WebRequest http://127.0.0.1:11220/health` returns 200.
5. Dashboard plus one secondary route render with data; Settings
   connection test works.
6. Uninstall removes binaries; no orphans in Task Manager.

Build history: [BUILD_LOG.md](../BUILD_LOG.md). Install-verify on a
clean box is still pending as of 2026-09-29 (dev stack owns 10718 here).
