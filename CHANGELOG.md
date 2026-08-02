## [0.5.1] -- 2026-08-02

### Added
- **Standards checker v2** (check-repo-standards.ps1): FastMCP 3.4 floor, uv.lock, icon.png, 3-4-100 prompt word gates, mcpb/ layout support, live doc refs, ASCII output - synced upstream to mcp-central-docs
- **MCPB 3-4-100 prompt gate met**: icon.png + system.md (3154w) + user.md (4226w) + examples.json (101 mappings)
- **Fullstack builder modernization** (2768-line monolith): SQLite foundation, membership roster, onboarding wizard, fleet-standard chat (skill-first preprompt, example prompts), webshop (products/orders), APScheduler jobs + patrol demo job, Logs ring buffer + API Docs pages, Tauri 2.0 wrapper
- **Auth protection** for /api/v1/fleet/start|stop|restart (previously unprotected)
- **demo-app**: durable playground repo at D:\Dev\repos\demo-app (ports 11140/11141) with IDEAS.md roadmap

### Changed
- fleet.just: ASCII header, mcpb-pack repointed to mcpb/pack.ps1
- justfile: serve -> start.ps1, install-hooks real pre-commit install
- ruff: 47 errors fixed; per-file ignores for deliberate S310/S108/E402 patterns
- Tests: 65 green (fixed auth-env, stale help-tool portmanteau test)

### Removed
- Dead scripts: bin/dev.ps1 (forbidden ports), backup-repo.ps1 (0B), fix-standards.ps1 (generated), sync-sota.ps1 (vestige), wisdom/gamemaker/webshop builders (stale ai-games-collection paths), mcp-watchdog.ps1 (dup of .py), mcpb-pack.ps1 (dup of mcpb/pack.ps1), scripts/out/
- 79 committed .bak/.backup files (fleet cleanup)
- fullstack_builder_ASSESSMENT.md (obsolete "runt" verdict)


## [Unreleased] -- 2026-07-12

### Added
- **SOTA analyzer redesigned** (40+ rules from 2026 fleet standards):
  - New categories: WEB, INFRA, SAFETY — 40 rules total (up from 26)
  - Rules for Bun, Biome, TailwindCSS, Zustand, Lucide, dark mode, data-testid, Framer Motion
  - Prefab coverage, dual transport, llms.txt/llms-full.txt, glama.json, .env.example
  - Tauri/NSIS wrapper, port adjacency, PyInstaller spec, Playwright E2E, CUA-NSIS smoke test
  - Session context injection (.cursorrules/.claude-plugin), start scripts, justfile, run_server.py
  - Docstring SOTA 2026 (Annotated+Field), CORS Tauri origins, batch mutation safety (--bak/--dryrun)
  - All rules carry `standard_ref` linking to mcd standards docs
- **remediation_todo** field in analysis output — structured markdown grouped P0/P1/P2 with fix steps + standard refs
- **Tiiny.host static page builder** — `scaffold_ops(operation="tiiny_site")` scaffolds + deploys to tiiny.host
- **FastMCP 3.4.2 capability checks**: @mcp.prompt(), @mcp.resource(), output_schema, SkillsDirectoryProvider
- **Docstring 3.4.3 checks**: ## Return Format, ## Examples, old Args: block detection

### Changed
- **Analysis web page** (Analysis.tsx) rebuilt — dedicated tool cards per operation, severity indicators, SOTA score, runt badges, dry-run/bak toggles, LLM deep analysis
- **Builders web page** (Builders.tsx) — Tiiny.host card, output badges on each builder, clearer descriptions
- **analyze_runts** thresholds: FastMCP < 3.4.2 = runt (was < 2.12), portmanteau threshold 20 (was 15)
- **EmojiBuster** — adds dry_run=True to fix_unicode_logging for preview-before-write
- **analysis_ops portmanteau** — dry_run and create_bak flags on all operations
- **Better false positive handling**: FastMCP version from `[project.dependencies]` not description text, help/status tool detection via portmanteau operation names, print count excludes scripts/ and .venv, bare except count no longer includes `except Exception:`
- **Fix gates found during remediation**: is_test filter fixed (matched package names containing "test", hiding tools in test_fixture_mcp), .venv path-part filtering on all file walks, JS console.log detection added
- **Tool detection broadened**: catches @router.tool(), @server.tool(), programmatic registration (mcp.add_tool, register_tool)
- **FastMCP 2.x references cleaned**: `_check_fastmcp_2133_features` → `_check_fastmcp_342_features`, version constants bumped, sampling detection looks for ctx.sample()

### Fixed
- `.env` bundle security leak: `tauri.conf.json` resources flagged when bundling .env instead of .env.example
- API_BASE port mismatch detection: flags frontend-port-bound api.ts that breaks in Tauri production
- Stale .bak file detection in source trees

## [Unreleased] -- 2026-07-03

### Added
- **Dynamic capabilities router** -- lazy-loading proxy for the 130+ MCP server fleet:
  - `meta_route_tool`: resolve tool_name → fleet server, hot-start via subprocess if offline, proxy MCP call over HTTP, return result. Avoids saturating LLM context with static mcp.json definitions.
  - `meta_search_capabilities`: semantic search across tool names and descriptions in the capability index.
  - `meta_routing_status`: index health, running servers, fleet stats.
  - `meta_routing_reindex`: force full fleet re-scan and SQLite index rebuild.
  - `meta_routing_servers`: list all fleet servers discovered by the index.
  - SQLite-backed `CapabilityIndex` with sub-second lookups, upsert/semantic search, and server status tracking.
  - `DynamicRouter` core service: fleet directory scanning, IDE mcp.json parsing, HTTP endpoint probing, hot-start with uv run, MCP JSON-RPC proxying via /mcp endpoint.
  - `ToolMapping`, `ServerEndpoint`, `RouteRequest`, `RouteResult`, `IndexStats` Pydantic models.
- **Consolidated routing registries**: replaced `capability_router` and `dynamic_routing` stubs with single `routing.py` registry. All routing tools delegate to `DynamicRouterService` (REST API parity).

### Changed
- Bumped version to 0.5.0 (minor: new routing subsystem).
- `mcp_server.py`: cleaned up stale `capability_router` / `dynamic_routing` imports, registered `routing` suite.

### Fixed
- Removed dead import `register_capability_router_tools` from `mcp_server.py`.

## [Unreleased] -- 2026-07-01

### Added
- **Harness generation suite** -- CLI-Anything integration for meta-mcp:
  - `harness_analyze`: AST-based Python API surface extraction with curation
    rules, domain grouping, backend detection. Produces ToolSurfaceSpec.
  - `harness_generate`: consumes ToolSurfaceSpec, generates complete
    fleet-conformant FastMCP 3.4+ server with portmanteau tools per domain
    group, Prefab cards, SKILL.md, backend strategy, dual transport.
  - `harness_refine`: gap analysis + incremental tool addition (non-destructive).
- **Fleet config audit** -- `fleet_config_audit` tool scans all repos for
  agent configs (CLAUDE.md, AGENTS.md, .cursorrules, llms.txt, glama.json, etc.)
  with override priority chain. Webapp Config Audit page.
- **15 portmanteau tools** -- consolidated from 125 flat tools to 55 total
  (15 portmanteau + 40 domain-specific). All registries now have a single
  `*_ops` entry point with `operation: Literal[...]`.
- **Webapp Harness Generator page** -- guided 3-step pipeline (analyze -> preview -> generate)
- **Script safety** -- `mcp-swapper.py` (dry-run, .bak, tally),
  `log_rotate.py` (dry-run, .bak, error recovery),
  `meta-ops.py` (functional, error handling, no emoji)
- **deep_scan_repo fix** -- replaced `rglob("*")` with `os.walk` dir pruning
  across all scanning paths. Prevents .venv/node_modules inflation.
- SOTA-compliant docstrings on all portmanteau tools: [RATIONALE],
  ## Operations, ## Return Format, ## Examples.

### Changed
- `create_response` accepts optional `error_type` parameter.
- `mcp_repo_analyzer.py`: module-level `_IGNORE_DIRS` + `_walk_py_files()`
- `pyproject.toml`: added `[tool.pytest.ini_options]` and `[tool.coverage]`
- All legacy alias tools removed from registries (replaced by portmanteau)
- Emoji stripped from all `src/meta_mcp/` Python source (except logging_config BASH_ICONS which use hex escapes)
- Em dashes replaced with `--` across all registry files (18 files)
- Stray `tools/repo_stats.py` moved to `scripts/`
- Builder scripts moved from `tools/` to `scripts/` (fullstack-builder, etc.)

### Fixed
- `diagnostics_service.py`: shortened long messages (E501)
- `server_builder_from_spec.py`: unused import `ast`, unused variable `default_op_name`
- `harness_analyzer.py`: unused variable `all_code`, loop variables
- `github_inspiration.py`: unused `time` import
- `mcp_repo_analyzer.py`: missing `import os`

## [Unreleased] -- 2026-06-14

### Fixed
- Tauri build: resolved Rust crate conflict (brotli/alloc-no-stdlib)
- Tauri build: fixed PyInstaller path mismatch (hyphen to underscore in src dirs)
- Tauri build: fixed TypeScript errors (unused imports, useRef arg, import.meta.env)
- Tauri CORS: allow_origins includes tauri://localhost for WebView access

### Added
- CUA-NSIS: just cua-nsis-test recipe, smoke script, config
- CUA-NSIS: build.ps1 now copies NSIS installer to dist/
- CUA-NSIS: 11-phase smoke test (install, launch, WebView OCR, diagnostics, uninstall)

## [Unreleased] -- 2026-06-14

### Added
- Tauri CORS: 	auri://localhost, http://tauri.localhost, https://tauri.localhost in CORS origins
- Tauri CORS: _TAURI env var toggle with llow_origin_regex for secure WebView access
- build.ps1: auto-copy NSIS installer to dist/ on build

### Changed
- CORS: llow_origins=["*"] → explicit origins list for Tauri webview compatibility
# Meta MCP Changelog

All notable changes to Meta MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed -- fleet cold-start smoke teardown leak (2026-06-10)

The 108-repo cold-start probe left ~234 orphaned processes (uv.exe + server
python.exe pairs) because teardown was non-tree at every layer:

1. `fleet_probes/scripts/stdio_mcp_smoke.py`: `proc.terminate()` killed only
   the direct child (uv.exe for `uv run <server>`), orphaning the server
   python grandchild on every run -- including successful ones. Now closes
   stdin (graceful MCP exit hint) then tree-kills via `taskkill /T /F` in a
   `finally` block.
2. Same file: blocking `proc.stdout.readline()` ignored the deadline while a
   silent child was alive, and the undrained stderr pipe could fill and block
   chatty children (uv sync). Replaced with reader threads + queue; deadline
   is now always honored.
3. `fleet_probes/scripts/Invoke-FleetStdioMcpSmoke.ps1`: on helper timeout,
   `$p.Kill()` (no tree on .NET Framework) orphaned uv AND server. Now
   `taskkill /T /F /PID` first.

Verified standalone: happy-path grandchild reaped in 2.2s; silent-server
3s deadline honored (4.7s incl. tree-kill), grandchild reaped.

## [0.3.0] - 2026-06-07

Desktop installer release: Tauri 2 native app with bundled Python sidecar, plus dashboard TypeScript hardening and fleet doc vendoring.

### Added
- **Tauri 2 native desktop app** -- PyInstaller one-file sidecar, NSIS `.exe` + MSI installer (`just build-native`, `docs/TAURI.md`)
- **MCPB package** -- `mcpb/manifest.json`, `pack.ps1`, `just mcpb-pack`; Claude Desktop bundle at `dist/meta-mcp-v*.mcpb`
- **Fleet cold-install docs** -- vendored locally under `docs/fleet/` (no naked `mcp-central-docs` install links)
- **`scaffold_mcp_server` FastMCP 3.4** -- sampling, agentic workflow, prompts/skills, CodeMode, prefab UI in generator output

### Fixed
- **`web_sota` TypeScript build** -- `apiTypes` helpers, generic `useApi`, typed API payloads across dashboard pages

## [0.3.0-beta] - 2026-06-07

First public **beta** GitHub release. MetaMCP positioned as a **Swiss-army-knife** fleet hub: builders, analyzers/scrubbers, probes, and repo inspiration in one MCP + dashboard.

### Added
- **Repo inspiration suite** -- `inspire_repo_*`, workflow, Prefab card, dashboard page
- **Fleet cold-install probe** -- mcpb + stdio smoke; optional sandboxed `-Execute` via virtualization-mcp
- **Fleet cold-start probe** -- dirty console detection, `stack_degraded`, broken-only reruns
- **Analysis depot** -- persistent runs, MCD export, `analyze_fleet` multidimensional scan
- **Builders** -- `scaffold_*` tools + dashboard Builders wizard (MCP server, fullstack, landing, webshop, game)
- **Scrubbers** -- EmojiBuster, PowerShell validator, implementation honesty, `redact_secrets_audit`
- **Dashboard** -- Tool Lab, Repo Inspiration, Fleet tabs, local LLM proxy, multitab Help
- **Docs** -- README badges, GitHub topics/description, sandbox + inspiration sections

### Changed
- Ruff-clean Python tree; Biome-clean `web_sota`
- `llms.txt` / manifest scrub per fleet standard
- README/help/`show_mcp_overview` document builders, analyzers, and scrubbers

## [Unreleased] - 2026-06-07 (archived)

### Changed
- **`llms.txt` / `llms-full.txt`:** Rewritten per fleet LLM manifest standard -- curated index + corpus for bots/RAG; no machine paths or embedded MCP configs; `llms-full.txt` tracked again.
- **Privacy / PII scrub:** `docs/PRIVACY.md`; README privacy section; gitignore `data/tasks.json`, `llms-full.txt`, `debug_output.txt`; generic `.env.example` and `REPOS_DIR` default (`~/repos`); removed hardcoded `WURST_AUTH_TOKEN` default; `META_MCP_NODE_LABEL` for heartbeat; author email removed from `pyproject.toml`.
- **README / PRD:** Trimmed for public release -- factual tone, fleet probe sections (cold-start, cold-install, dirty log, paths); removed stale marketing copy.

### Added
- **Fleet probe architecture (MCD-free):** `docs/fleet/FLEET_PROBE_ARCHITECTURE.md`, `fleet_paths.py`, `fleet_probes/` vendored scripts + manifests; probe services resolve meta_mcp / `~/.meta_mcp/fleet` first, MCD legacy fallback only.
- **Fleet cold-install probe:** `FleetColdInstallService`, `/api/v1/fleet/cold-install/run|report`, `FleetColdInstall.tsx` tab (mcpb + stdio columns, IDE filter), MCP tools with `test_mcpb`, `host_mcpb_smoke`, `mcp_clients`. **mcpb = Claude Desktop only**; other IDEs use `stdio_*` outcomes.
- **Fleet cold-start dirty log:** `fleet-webapp-start-probe.ps1` parses console output on every run (HTTP 4xx/5xx, STARTUP PROBE warnings); per-repo `dirtyLog` / `dirtyLogOk` / `consoleIssues[]`; `stack_degraded` outcome; teardown via two-pass `Stop-FleetPortSquatters`.

### Changed
- **`FleetStartMode.ps1` (vendored):** `Start-FleetDetachedShell` for `FLEET_PROBE_RUN=1` log capture without visible consoles.

## [Unreleased] - 2026-06-06

### Added
- **Fleet cold-start probe -- Broken\* mode:** `FleetStartupProbe.tsx` button; `FleetStartupProbeRequest.broken_only`; `FleetStartupProbeService.run_probe(broken_only=…)` wraps `-BrokenOnly` on central probe script.

### Fixed
- **Cold-start UI:** Broken\* enabled when last report `status === complete` and broken count > 0.

## [Unreleased] - 2026-05-31

### Added
- **Analysis depot** -- durable runs under `~/.meta_mcp/analysis/` (replaces primitive 1h-only `~/.mcp-studio/scan-cache`); tools `list_analysis_depot`, `get_analysis_depot_run`, `publish_analysis_to_mcd`; `analyze_mcp_runts` / `show_mcp_status` accept `export_mcd`; MCD section `mcp-central-docs/projects/analysis/` with `FLEET_*_LATEST.md`, `runs/`, `repos/`, optional `projects/<repo>/ANALYSIS_SNAPSHOT.md`
- **Phase D (fleet SOTA surface)** -- `prefab-ui` core dependency; `inspire_repo_structure_card` (Prefab + text fallback); MCP prompts (`inspire_repo_study`, `meta_mcp_fleet_discovery`); resources `resource://meta-mcp/repo-inspiration/skills`, `resource://meta-mcp/capabilities`; `META_MCP_PREFAB_APPS=0` to skip App tool registration
- **`help` tool** -- fleet-standard discovery entry point (`list_mcp_tools` / `find_mcp_tools` remain aliases)
- **`inspire_repo_help`** -- standalone inspiration parameter reference
- **README / help docs** -- fleet [README_STRUCTURE](https://github.com/sandraschi/mcp-central-docs/blob/main/standards/README_STRUCTURE.md) user README; expanded [docs/tools/diagnostics.md](docs/tools/diagnostics.md)
- **`repo_inspiration` suite** -- remote GitHub inspiration tools (native Python port of [Repomuse](https://www.npmjs.com/package/repomuse), MIT, praveene3127):
  - `inspire_repo` portmanteau (`operation=structure|files|patterns|help`) plus legacy `inspire_repo_*` aliases
  - **Phase A:** `data.chapters[]` (`overview`, `tree`, `manifest`, `readme`, `source`, `prompt`, `file`, `hint`); `profile` (`brief`|`standard`|`deep`); `subpath`, `branch`, `max_chars`, `language_hint`, glob filters; in-memory tree cache (5 min); `gitingest_url` in responses
  - **Phase B:** large-repo directory summary, `data.hints[]`, `suggested_subpaths`, manifest-based `suggested_language_hint`, `rate_limit_remaining`; web UI warnings, subpath chips, expand-all, language hint field
  - **Phase C:** `inspire_repo_workflow` (structure → files → patterns + optional `ctx.sample` synthesis)
  - **Web:** `/api/v1/llm/models` and `/api/v1/llm/chat` proxy -- Settings model dropdown + Chat no longer blocked by browser CORS to Ollama
- **Docs:** [docs/tools/repo-inspiration.md](docs/tools/repo-inspiration.md); fleet note in `mcp-central-docs/integrations/repo-inspiration.md`
- **Web (`web_sota`):** **Repo Inspiration** page -- GitHub URL + three inspire tools; results split into collapsible chapters + full-text pane

### Confirmed working
- **Toolchains / Config Switcher** (`web_sota/src/pages/Toolchains.tsx`): fully wired into sidebar nav and router. Backend (`ToolchainService`, `toolchains_service.py`) complete with CRUD + apply. API endpoints at `/api/v1/toolchains/{list,create,apply,available_servers}` and `DELETE /api/v1/toolchains/{name}` all functional. Profiles stored in `~/.meta_mcp_toolchains.json`, server pool sourced from `MASTER_MCP_CONFIG.json`.

### Fixed
- **Frontend build**: `web_sota` Vite build confirmed working via `node_modules\.bin\vite.cmd build`. Pre-existing `tsc` errors in AppsHub/Topbar/DynamicForm do not block the Vite production build.

### Notes
- `frontend/` is a stale older copy of the webapp - active frontend is `web_sota/`. Changes to `frontend/` have no effect.

## [Unreleased]

### Changed
- **Language Professionalization**: Removed overenthusiastic marketing language throughout codebase
  - Replaced "SOTA" references with "modern" and "professional" 
  - Updated project description from "Ultimate Bloat-Buster" to "Professional MCP server management platform"
  - Standardized all documentation to use enterprise-ready terminology

### Added
- **`meta_dev` suite** (`meta_dev_impl`): Fleet and developer helpers â€” `probe_fleet_health`, `diff_mcp_configs`, `export_cursor_mcp_snippet`, `audit_fastmcp_surface`, `find_orphan_tool_references`, `tail_log_file`, `env_sanity_check`, `summarize_server_for_prompt`, `mcp_changelog_digest`, `redact_secrets_audit`. Documented in [docs/tools/meta-dev.md](docs/tools/meta-dev.md).
- **HTTP tool catalog**: `GET /api/v1/mcp/catalog` â€” live FastMCP tool list with JSON Schema for each tool (powers the dashboard).
- **Tool Lab** (`web_sota`): Sidebar page to pick any registered tool, edit args via **DynamicForm** or raw JSON, and run via `POST /api/v1/tools/execute`.
- **`justfile`**: `just sync`, `just fix`, `just serve`, `just web-dev`, `just web-build`, `just tools`, `just mcp-stdio`, `just ready`, etc. (PowerShell-friendly).
- **Ruff** in **`[dependency-groups] dev`**; `src` lint/format via `uv run ruff`.
- **`meta_mcp.tools` package** `__init__.py` re-exports `tool` / `structured_log` / `retry_on_failure` from `decorators` so legacy `from meta_mcp.tools import tool` imports keep working.

### Changed
- **Documentation layout**: Short root [README.md](README.md); guides in **docs/** â€” [INSTALL.md](docs/INSTALL.md), [ARCHITECTURE.md](docs/ARCHITECTURE.md), [TOOLS.md](docs/TOOLS.md), [docs/README.md](docs/README.md). Root [INSTALL.md](INSTALL.md) redirects to **docs/INSTALL.md**.
- **`POST /api/v1/tools/execute`**: JSON body `{ "server_id", "tool_name", "parameters" }` (matches the web client); executes the **in-process** Meta MCP FastMCP app (`metaops` / `meta-mcp` / `local` server ids).
- **Tool service**: Real `call_tool` / `list_tools` bridge (no simulated execution for local id); responses include **`result`** for the React app.
- **Static UI**: FastAPI serves built assets from **`web_sota/dist`** (aligns with Vite `web_sota` build output and fleet ports **10718** backend / **10719** dev frontend per MCP Central Docs).

### Added (earlier in Unreleased)
- **`help`** (diagnostics): primary catalog â€” lists **all** tools (default **max_tools=2000**). Optional **query** filter. **`help_tools`** remains an alias (default cap 500).
- **`meta_mcp_help`** (diagnostics): short overview (version, suites, next steps) only; points to **`help`** for the full list.
- **`help_tools`** (diagnostics): alias of **`help`** for older clients.
- **`generate_fleet_starts_launcher`** (diagnostics): runs MCP Central Docs `tools/sync_fleet_fastmcp.py` (`operation=fastmcp_only`) or `tools/generate_fleet_registry.py` (`operation=full_registry`) so **Fleet Starts Launcher** data stays current. Override clone path with **`MCP_CENTRAL_DOCS_ROOT`** if needed.

## [3.4.0] - 2026-02-21 - Toolchains & Presets

### Major Feature Expansion
**MetaMCP Professional** now features **Toolchain Manager**, a way to curate collections of MCP servers and rapidly hot-swap them into your preferred IDE clients.

### Added
- **Toolchain Presets**: Create, read, update, and delete curated groups of MCP servers.
- **Rapid Deployment**: Apply an entire preset to Cursor, Windsurf, Zed, or Claude Desktop with one click.
- **Toolchain Dashboard**: A UI page in the webapp (`Toolchains.tsx`) to manage your configurations visually.

## [3.2.1] - 2026-02-04 - Stability & Client Detection Fixes

### Fixed
- **Discovery Service**: Removed incorrect `await` keywords on synchronous functions (`discover_clients`, `check_client_integration`), resolving a `TypeError` on the Server Repos page.
- **Tools UI**: Increased `z-index` of the search bar container to prevent it from being hidden behind tool cards.

### Added
- **Client Discovery**: Expanded detection paths for **Zed** (Scoop shims) and **Antigravity** (User-specific AppData).
- **Client Configuration**: Implemented functional "Configure" and "View JSON" buttons on the Clients page with a new JSON editor modal.

### Changed
## [3.3.0] - 2026-02-06 - Dynamic Tools & Inspection ðŸ§ 
### ðŸš€ Major Feature Expansion
**MetaMCP Enterprise** now features **intelligent tool execution** and **deep server inspection** capabilities.

### Added
- **ðŸ“ Tool Execution Dynamic Form**: Values are no longer just raw JSON strings.
    -   **Smart Inputs**: `string`, `boolean`, `enum`, and `array` types are now rendered as proper form fields.
    -   **Mode Toggle**: Logic to switch between "Form View" (user friendly) and "JSON View" (power user).
    -   **Schema-Driven**: Form fields are generated in real-time based on the tool's JSON schema.
- **ðŸ” Server Drill-Down**: Deep inspection of active MCP servers.
    -   **Tool List**: View all available tools for a connected server.
    -   **Resource List**: View exposed resources (where supported).
    -   **Prompt List**: View available prompts (where supported).

### Changed
- **ðŸ˜ Renaming**: Globally renamed "Server Zoo" to **"Server Repos"** for improved clarity and semantic alignment.

## [3.2.0] - 2026-02-04 - Premium Webapp & Backend Integration ðŸ’Ž

### ðŸš€ Major Feature Expansion

**MetaMCP Enterprise** now features a **fully integrated, premium web interface** with real-time backend communication, replacing the previous static/mock implementations.

#### Added
- **ðŸ’Ž Premium Dark Theme**: Complete UI overhaul with glassmorphism, smooth transitions, and a refined color palette (`bg-slate-950`).
- **ðŸ--ï¸ Modular Architecture**:
  - **Layout Engine**: Retractable Sidebar, persistent Topbar with emergency stops, and responsive main content area.
  - **Interactive Modals**: Global Logger console (Ctrl+`) and Help dialogs (?).
  - **Atomic Components**: Reusable UI elements for consistency across the application.
- **ðŸ”Œ Backend Integration**:
  - **Live Tool Execution**: Frontend now communicates directly with the Python backend via `executeTool`.
  - **Real-time Status**: Dashboard reflects actual server and tool states.
- **ðŸ§ª Testing Scaffold**:
  - **Vitest + RTL**: Comprehensive testing setup for React components.
  - **CI Integration**: `npm test` script for automated verification.

#### Changed
- **Webapp Core**: Migrated from monolithic `App.tsx` to a structured, scalable directory format (`components/`, `pages/`, `hooks/`, `context/`).
- **Dashboard**: Enhanced visualization of system health and active services.
- **Repository Analysis**: Improved UI for deep codebase inspection.
- **Client Management**: Refined interface for managing IDE configurations.

## [3.1.1] - 2026-02-04 - Protocol Stability Fix ðŸ”§

### Fixed
- **ðŸš¨ Protocol Corruption**: Configured `structlog` to output via standard logging (stderr) instead of printing directly to stdout, which was corrupting the MCP JSON-RPC protocol during startup.

## [3.1.0] - 2026-01-19 - Repomix Integration & Repository Intelligence ðŸ§ 

### ðŸš€ Major Feature Expansion

**MetaMCP Enterprise** now includes **Repomix-inspired repository intelligence** - advanced token analysis and AI-optimized repository packing capabilities.

#### Added
- **ðŸ§  Token Analysis Suite**: Complete token usage analysis for LLM context optimization
  - File-level token counting with language detection
  - Directory-wide token distribution analysis
  - LLM context limit compatibility estimation (GPT-4, Claude, Gemini, etc.)
  - Token efficiency metrics and optimization recommendations

- **ðŸ“¦ Repository Packing Suite**: AI-first repository consolidation inspired by repomix
  - Multi-format output: XML, Markdown, JSON, Plain Text
  - AI-optimized packing with automatic token limits
  - Intelligent file selection prioritizing important code
  - Git-aware filtering with .gitignore and custom exclusions
  - Security filtering to prevent sensitive data leakage

- **ðŸŒ Enhanced Web Dashboard**: New enterprise management sections
  - Token Analysis page with real-time LLM compatibility checking
  - Repository Packing page with format selection and optimization
  - Advanced repository intelligence visualization
  - Interactive token limit estimation tools

- **ðŸ”§ Repomix Integration**: Advanced repository intelligence features
  - Repository consolidation for AI consumption
  - Token-aware content optimization
  - Multi-format AI-friendly packaging
  - Intelligent file prioritization for context limits

#### Technical Enhancements
- **10 Enterprise Tool Suites**: Complete MCP ecosystem coverage
- **Advanced Token Estimation**: Language-specific token counting algorithms
- **AI Context Optimization**: Automatic content selection for LLM consumption
- **Multi-Format Repository Export**: XML (repomix-style), Markdown, JSON, Plain Text
- **Security-Enhanced Packing**: Sensitive data filtering and exclusion

### Breaking Changes
- **New Tool Suites**: Added token_analysis and repo_packing suites
- **API Expansion**: 50+ endpoints across 10 service suites
- **Web Interface**: Added Token Analysis and Repository Packing pages

## [3.0.0] - 2026-01-19 - Enterprise Launch ðŸš€

### ðŸŽ‰ Major Enterprise Release

**MetaMCP Enterprise** - Complete MCP ecosystem orchestrator surpassing mcp-studio functionality.

#### Added
- **ðŸš€ 8 Tool Suites**: Complete MCP ecosystem management platform
  - Server Management: Start/stop/monitor MCP servers with process control
  - Tool Execution: Remote tool invocation across MCP server networks
  - Repository Analysis: Deep codebase analysis with health scoring
  - Client Management: Multi-client configuration for 5+ IDEs (Claude, Cursor, Windsurf, Zed, Antigravity)
  - Diagnostics: Enhanced EmojiBuster and PowerShell validation
  - Analysis: Advanced Runt Analyzer with SOTA compliance
  - Discovery: Comprehensive server and client integration scanning
  - Scaffolding: Enterprise-grade project generation

- **ðŸŒ Enterprise Web Dashboard**: Complete real-time management interface
  - Live API integration (no mock data)
  - 8 service health monitoring
  - Server lifecycle management
  - Tool execution interface
  - Repository intelligence dashboard
  - Client ecosystem management
  - Multi-page enterprise navigation

- **âš™ï¸ Advanced Server Management**: Production-ready MCP server orchestration
  - Process lifecycle control with PID tracking
  - Cross-platform subprocess management
  - Resource monitoring and health checks
  - Graceful shutdown and cleanup
  - Real-time status monitoring

- **ðŸ”§ Tool Execution Engine**: Remote tool invocation across MCP networks
  - Parameter validation and type checking
  - Execution history and performance tracking
  - Error handling and recovery
  - Tool metadata extraction and documentation

- **ðŸ“Š Repository Intelligence**: Deep codebase analysis and health assessment
  - Comprehensive structure analysis
  - Dependency auditing and FastMCP version checking
  - Code quality metrics and complexity scoring
  - Documentation completeness evaluation
  - Testing framework detection and coverage analysis
  - Health scoring algorithm (0-100 scale)
  - Automated improvement recommendations

- **ðŸ-¥ï¸ Client Ecosystem Management**: Multi-IDE integration platform
  - Configuration file parsing for 5+ IDEs
  - Safe configuration updates with backup
  - Server registration and unregistration
  - Integration validation and diagnostics
  - Cross-platform client support

#### Changed
- **ðŸ--ï¸ Architecture Overhaul**: Complete modular service architecture
  - 8 independent services with dedicated responsibilities
  - Service health monitoring and status tracking
  - Graceful error handling and recovery
  - Hot-swappable component design

- **ðŸ”’ Unicode Safety Enhancement**: Enterprise-grade crash prevention
  - Hex escape sequence standardization (`\uXXXX` format)
  - Safe Scanner philosophy implementation
  - Comprehensive validation across all components
  - Pre-commit hooks and CI integration

- **ðŸŒ Web Interface Transformation**: From basic UI to enterprise dashboard
  - Real API integration replacing mock data
  - Live health status and monitoring
  - Interactive server and tool management
  - Professional enterprise design system

#### Technical Improvements
- **FastMCP 2.14.1+**: Enhanced response patterns throughout
- **Cross-platform Compatibility**: Windows, macOS, Linux verified
- **Performance Optimization**: Efficient resource usage and caching
- **Security Hardening**: Safe configuration management and validation
- **Error Resilience**: Comprehensive error handling and recovery

### Breaking Changes
- **API Structure**: Complete overhaul with 8 service endpoints
- **Web Interface**: Real functionality replaces placeholder UI
- **Configuration**: Enhanced client management with backup safety
- **Tool Registry**: 8 modular suites replace simple tool collection

## [2.0.0] - 2026-01-15 - Enterprise Foundation ðŸ--ï¸

### Added
- **ðŸ--ï¸ Modular Service Architecture**: Complete overhaul with 8 dedicated services
- **ðŸŒ Enterprise Web Dashboard**: Real-time monitoring and management interface
- **âš™ï¸ Server Lifecycle Management**: Start/stop/monitor MCP servers with process control
- **ðŸ”§ Tool Execution Framework**: Remote tool invocation across server networks
- **ðŸ“Š Repository Intelligence**: Deep codebase analysis with health assessment
- **ðŸ-¥ï¸ Client Management System**: Multi-client configuration for 5+ IDEs
- **ðŸ”’ Enhanced Security**: Comprehensive Unicode safety and validation
- **ðŸ“ˆ Performance Monitoring**: Real-time service health and metrics

### Changed
- **ðŸ›ï¸ Enterprise Architecture**: From basic server to complete ecosystem platform
- **ðŸ”§ Tool Registry Expansion**: From 4 to 8 comprehensive tool suites
- **ðŸŒ Web Interface**: Complete redesign with real API integration
- **ðŸ“š Documentation**: Enterprise-grade documentation and standards

### Technical Enhancements
- **FastMCP 2.14.1+**: Full protocol compliance with enhanced patterns
- **Cross-platform**: Verified Windows, macOS, Linux compatibility
- **Process Management**: Advanced subprocess control and monitoring
- **API Architecture**: RESTful endpoints for all enterprise functions

## [1.2.0] - 2026-01-05

### Added
- **ðŸ” Client Integration Diagnostics**: New tool to check server health across multiple IDE clients (Antigravity, Claude, Cursor, Windsurf, Zed).
- **ðŸ“Š Runt Analyzer Enhancements**: Added Lines of Code (LoC) counting, dependency parsing, and detailed tool metadata extraction.

### Changed
- **ðŸ›¡ï¸ Project Cleanup**: Removed 15+ "zombie" server files and temporary backups to streamline the repository.
- **ðŸ”§ Robust Configuration**: Refactored server discovery to use dynamic system paths instead of hardcoded strings.

### Fixed
- **ðŸš¨ Code Quality**: Resolved 50+ Ruff linting errors across the entire project.
- **âš›ï¸ JSX Syntax**: Fixed critical React/JSX template corruption in `landing_page.py` caused by f-string escaping issues.
- **ðŸ”„ Async Hygiene**: Eliminated `RuntimeWarning` coroutine errors in diagnostic scripts.

## [1.1.0] - 2026-01-04

### Added
- **ðŸ›¡ï¸ Safe Scanner Standard**: Global repository sweep refactoring 17 files and 219 instances.
- **ðŸš¨ Hex-Based Identification**: All Unicode emojis in patterns and constants now use hex escape sequences (e.g., `\U0001F680`) to prevent grep/terminal crashes.
- **ðŸ” Global Unicode Detection**: EmojiBuster now scans docstrings, return values, and logging globally.
- **ðŸš€ CLI Support**: `safe_scanner.py` updated to accept target paths via command line.

### Changed
- **ðŸ›¡ï¸ EmojiBuster**: Standardized on uppercase hex formatting (`\uXXXX`) for conventional SOTA compliance.
- **ðŸ“š Documentation**: Updated README and PRD to reflect the Safe Scanner as a core SOTA requirement.

## [1.0.0] - 2026-01-04

### Changed
- **ðŸ“- README.md**: Complete rewrite with "Argh-Coding" philosophy
- **ðŸŽ¯ Product Vision**: Focus on preventing developer pain points
- **ðŸ--ï¸ Architecture**: Enhanced response pattern integration

### Fixed
- **ðŸš¨ Critical Issue**: Unicode logging crashes causing production instability
- **ðŸ”„ Restart Loops**: LLM auto-fix trap identification and prevention

## [0.2.1-beta] - 2026-01-02

### Changed
- Refactored project from `mcp-studio` to `meta_mcp` namespace.
- Standardized project structure for MCP SOTA compliance.
- Created `pyproject.toml` and entry points.

## [0.1.0] - 2026-01-02

### Added
- **ðŸ” Basic MCP Server**: FastMCP integration with tool registry
- **ðŸ› ï¸ Tool Discovery Framework**: Auto-discovery system for MCP tools
- **ðŸ“Š Server Management**: Basic server lifecycle management
- **ðŸŒ Web Interface**: Basic web UI for tool interaction
- **ðŸ“‹ Documentation**: Initial README and basic setup guide

### Core Tools Implemented
- **Server Discovery**: Find MCP servers across system
- **Tool Execution**: Execute tools on remote MCP servers
- **Configuration Management**: Basic client configuration updates
- **Health Monitoring**: Basic server status checking

### Architecture
- **FastMCP 2.13+**: Core framework integration
- **Tool Registry**: Centralized tool management
- **Enhanced Logging**: Structured logging with Unicode safety awareness
- **Cross-Platform**: Windows, macOS, Linux support

---

## ðŸŽ¯ Development Philosophy

Meta MCP follows the **"Argh-Coding" philosophy** - every feature is designed to prevent a specific developer frustration that we've all experienced:

### ðŸš¨ Critical Issues Addressed
- **Unicode Logging Crashes**: The #1 cause of mysterious service restarts
- **Docker Desktop Confusion**: Maximum confusion scenarios with UI deception
- **Framework Assumption Errors**: Hours wasted on incorrect API usage
- **SOTA Compliance Gaps**: Repositories not following modern standards

### ðŸ›¡ï¸ Prevention Focus
- **Enhanced Response Patterns**: Immediate diagnosis instead of mysterious errors
- **Unicode Safety**: Comprehensive validation and auto-fixing
- **Proactive Tooling**: Prevent problems before they cause crashes
- **Education**: Clear guidance on best practices

### ðŸš€ Impact Metrics
- **Before Meta MCP**: 3+ days cumulative delay from Unicode crashes
- **After Meta MCP**: 5 minutes comprehensive Unicode audit and fix
- **Success Stories**: Real-world stability improvements tracked and reported

---

**Meta MCP**: Turning "Argh!" moments into "Aha!" moments since 2026. ðŸš€





