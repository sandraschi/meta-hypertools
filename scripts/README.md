# meta_mcp Scripts Reference

Every script in this repo, what it does, and how to get help. Run any
PowerShell script with `-?` for full comment-based help; Python scripts
with `--help`.

## The crown jewel

### `fullstack-builder.ps1` - SOTA Fullstack App Builder

**The 2768-line monolith.** One linear PowerShell file that generates a
complete 50-file fleet-standard web application in one pass: FastMCP 3.4
backend with SQLite (members/products/orders), APScheduler jobs, log ring
buffer; React 18 + Vite + Tailwind + Bun frontend with Dashboard, Tools,
Skills, Chat (skill-first, local LLM), Members, Shop, Cart, Jobs, Logs,
API Docs, Onboarding, Settings, Help; Playwright e2e, pytest, CI; optional
Tauri 2.0 wrapper, voice, PWA, upload, email, realtime.

```powershell
pwsh scripts/fullstack-builder.ps1 -?          # full help
pwsh scripts/fullstack-builder.ps1 -AppName my-app -Interactive
```

The generated app is a real SOTA scaffold - `uv sync` + `bun install` +
`start.ps1` and it runs. Demo: `D:\Dev\repos\demo-app` (ports 11140/11141).

## Fleet operations

| Script | What it does | Help |
|--------|--------------|------|
| `check-repo-standards.ps1` | **Standards checker v2** - scores a repo against the SOTA bar: FastMCP 3.4 floor, uv.lock, icon.png, 3-4-100 prompt word gates, CI, docs, tooling. Emits `docs/repository-analysis-{date}.md` + a dir-only fix script. `just health` | `-?` |
| `FleetStartMode.ps1` | Shared launch-mode helpers (port clearing, zombies, health poll, browser open) dot-sourced by `start.ps1` | `-?` |
| `kill-zombies.ps1` | Kill zombies on ports 10718/10719 + fleet dev process patterns. `just cleanup` | `-?` |
| `generate-tauri-icon.ps1` | Render the amber "M" Tauri icon (native/icons/icon.png) | `-?` |

## Packaging

| Script | What it does | Help |
|--------|--------------|------|
| `mcpb/pack.ps1` | **MCPB pack** - sync src into mcpb/, `uv export` requirements, validate manifest, pack to dist/, inspect. Ships icon.png + 3-4-100 prompts. `just mcpb-pack` | `-?` |
| `native/build.ps1` | Full Tauri release pipeline: tsc gate, frontend build, PyInstaller sidecar, NSIS installer. `just build-native` | - |
| `native/build-sidecar.ps1` | PyInstaller backend exe only. `just build-sidecar` | - |

## Quality gates

| Script | What it does | Help |
|--------|--------------|------|
| `cua-smoke.py` | **CUA-NSIS smoke test** - installs the real NSIS build, launches, walks the sidebar nav (title-matching), screenshots + OCR each page, uninstalls. `just cua-nsis-test` | `--help` |
| `cua-webapp-test.py` | **CUA webapp test** - pre-Tauri browser walk: stack start, Connected badge wait, nav click-through, per-page screenshots. `just cua-webapp-test` | `--help` |
| `just/emojibuster.ps1` | Scan Python files for emoji literals that crash Windows loggers. `just emojibuster` | `-?` |

## MCP tool bridges (Python CLI)

| Script | What it does | Help |
|--------|--------------|------|
| `meta-ops.py` | CLI bridge to MCP tools: `analyze-runts`, `emoji-buster`, `pack` | `--help` |
| `mcp-swapper.py` | Switch MCP server tiers in Antigravity config (tier1/2/3, dry-run, backups). `just pro/creative/core/swapper` | `--help` |
| `dump_mcp_tools.py` | Print all registered MCP tool names + first docstring line. `just tools` | - |
| `mcp-watchdog.py` | MCP server log health watchdog: scan/purge/rotate/task (Claude Desktop + IDEs) | `--help` |
| `audit_uv.py` | Fleet-wide uv setup audit (uv.lock/.venv presence per repo) | - |
| `autofix_uv.py` | Auto-fix uv gaps found by audit_uv | - |
| `repo_stats.py` | Repository stats (tools, FastMCP version, markdown) | - |
| `codemod_annotations.py` | Fleet-wide ToolBench annotation codemod (`_READ_ONLY` -> spec keys) | - |
| `log_rotate.py` | Truncate oversized log files to tail (used by mcp-watchdog) | - |

## Probes (fleet_probes/)

| Script | What it does | Help |
|--------|--------------|------|
| `fleet-cold-install-probe.ps1` | Cold-install validation: INSTALL.md, GitHub `.mcpb` asset, per-IDE stdio smoke | - |
| `fleet-webapp-start-probe.ps1` | Cold-start probe: start.ps1 boot, health, dirty-log parse | - |
| `sync-fleet-cold-install-manifest.ps1` | Refresh the cold-install manifest from GitHub releases | - |
| `Get-FleetMcpClientRegistry.ps1` | Enumerate MCP client configs (Claude/Cursor/Windsurf/Antigravity/Zed/OpenCode) | - |
| `Invoke-FleetStdioMcpSmoke.ps1` | stdio smoke helper for multi-IDE installs | - |
| `stdio_mcp_smoke.py` | Python stdio smoke (used by the probes) | - |

## Start / stop

| Script | What it does |
|--------|--------------|
| `start.ps1` | Stack start: kill squatters, backend :10718, frontend :10719, auto-open browser (`-Headless`, `-NoBrowser`) |
| `start.bat` / `stop.bat` | Double-click wrappers |
| `restart.ps1` | Restart via web_sota/start-dev.ps1 |
| `fleet-start.config.ps1` | Per-repo fleet start config (ports, backend target) |
| `web_sota/start.ps1` / `start-dev.ps1` / `stop.ps1` | Frontend-direct start/stop |
| `web_sota/start-dev.ps1` | Vite dev server launcher |

## Convention notes

- **ASCII only** in .ps1/.bat/justfile - no em dashes, no emoji literals
  (they crash Windows loggers). Checker: `just emojibuster`.
- **PowerShell 7+** - no `&&`, no `grep/tail/cat/ls`, use cmdlets.
- Destructive scripts support `-DryRun` / `--dry-run` previews.
- Ports: 10718 backend, 10719 frontend (fleet reservoir 10700-11500).
- `check-repo-standards.ps1` is synced with
  `mcp-central-docs/sota-scripts/repo-standards/` - update upstream first.
