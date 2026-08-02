# meta-hypertools

> **The MCP server that builds, wraps, probes, audits, and operates every other MCP server.** Scaffolding, GitHub inspiration, AST harness, fleet probes, standards analysis, diagnostics, and lifecycle ops - one toolbox, one pipeline, all SOTA-baked.

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://biomejs.dev/"><img src="https://img.shields.io/badge/Linted_with-Biome-60a5fa?style=flat-square&logo=biome&logoColor=white" alt="Biome"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.4-7c5cfc?style=flat-square" alt="FastMCP"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="MIT"></a>
  <a href="https://github.com/sandraschi/meta-hypertools/releases"><img src="https://img.shields.io/github/v/release/sandraschi/meta-hypertools?include_prereleases&label=release&style=flat-square" alt="Release"></a>
</p>

Exposed as **stdio MCP** (IDEs), **REST API** (HTTP mode), and a **web dashboard** (`web_sota`).

**Stack:** Python 3.12+ · [FastMCP](https://github.com/jlowin/fastmcp) 3.4+ · FastAPI · React/Vite · Tailwind

**Install:** [INSTALL.md](INSTALL.md) · **Help:** `help()` tool or dashboard `/help` · **Manifest:** [llms.txt](llms.txt) · **Vision:** [PRD.md](PRD.md)

---

## Reading ladder (the stack)

This repo is a leporello - it folds out. Read as deep as you need:

| Level | Doc | What you get |
|-------|-----|--------------|
| **L1 - 30 seconds** | This README | What it is + what you can do with it (below) |
| **L2 - 5 minutes** | [docs/README.md](docs/README.md) | The tour: suites, dashboard, probes, workflows |
| **L3 - tool deep dives** | [docs/TOOLS.md](docs/TOOLS.md) + `docs/tools/*.md` | Every tool, operation, and example |
| **L4 - architecture** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Server, API, MCP, UI internals |
| **L5 - the vision** | [PRD.md](PRD.md) | Where it is going (moonshots included) |
| **L6 - the scripts** | [scripts/README.md](scripts/README.md) | Every build script, with help entry points |

---

## The meta layer

The fleet is a living organism: 180+ MCP servers, webapps, robots, and
schedulers. meta-hypertools is the organism's **meta layer** - it does not
serve data, it serves the fleet itself.

```
scaffold → build servers & webapps (one-pass, SOTA-baked)
inspire  → study any GitHub repo, no clone
wrap     → harness: existing code becomes MCP surface
probe    → certify releases (boot + cold-install)
audit    → score every repo against the standards bar
operate  → register, schedule, switch presets, pack context
```

One server to rule the rest: scaffold what is missing, wrap what exists,
probe what ships, audit what decays, and operate what runs. The builder
is a proudly monolithic 2768-line PowerShell file that emits a complete
50-file fullstack app - roster, shop, onboarding, fleet-standard chat,
scheduler, Tauri wrapper - in one pass. And the meta-layer audits itself:
standards checker scores it **10/10**, tests are **65 green**, and its
MCPB bundle ships at the **3-4-100 prompt gate**.

---

## What you do with it (the leporello)

Fold out; pick your mission. Every row is a real, tested workflow.

### Build things

| You want... | Do this | In one line |
|-------------|---------|-------------|
| A new MCP server, standards-ready | `scaffold_ops(operation="mcp_server")` or dashboard Builders | Full SOTA repo in one pass - pyproject, uv.lock, llms.txt, glama, CI, MCPB layout |
| A fullstack webapp with backend | `scaffold_app_fullstack` or `scripts/fullstack-builder.ps1` | The 2768-line monolith emits a 50-file app: roster, shop, onboarding, chat, scheduler, Tauri wrapper |
| A dog care plane (really) | `scaffold_app_fullstack -AppName benny-the-dog-mcp` | Yes, the fleet dog has one - with Boomy patrol integration |
| A landing page | `scaffold_ops(operation="landing_page")` | Tailwind marketing scaffold |
| A spec-kit project | `scaffold_ops(operation="spec_kit")` | GitHub Spec-Driven Development with agent slash commands |
| A webshop / game / wisdom tree | `scaffold_ops(operation="webshop"\|"game"\|"wisdom_tree")` | Specialized templates |

### Learn from others

| You want... | Do this | In one line |
|-------------|---------|-------------|
| To study any GitHub repo without cloning | `inspire_repo(operation="structure\|files\|patterns")` | Architecture study: tree, README, topics, patterns |
| A deep agentic architecture review | `inspire_repo_workflow(goal=...)` | Multi-step reasoning + a scaffold recommendation |
| To wrap your script collection as MCP | `harness_analyze` → `harness_generate` → `harness_refine` | AST spec in, FastMCP server out, gaps checked |

### Certify & guard

| You want... | Do this | In one line |
|-------------|---------|-------------|
| To know which repos decayed | `analysis_ops(operation="runts")` | 40+ rules, P0/P1/P2 remediation, scored report |
| To verify releases actually boot | `fleet_startup_probe` | Cold-start probe: start.ps1, health, dirty logs |
| To validate install paths | `fleet_cold_install_probe` | INSTALL.md, .mcpb assets, per-IDE stdio smoke |
| To scrub Unicode from loggers | `diagnostics_ops(operation="unicode")` | EmojiBuster - Windows loggers stay ASCII |
| To scrub PowerShell Linux-isms | `diagnostics_ops(operation="pwsh")` | No grep/tail/&& in fleet scripts |
| To audit the repo's own honesty | `diagnostics_ops(operation="audit_impl")` | Stubs, mocks, TODO placeholders |

### Operate the machine

| You want... | Do this | In one line |
|-------------|---------|-------------|
| Servers registered in all IDEs | `server_ops` | list/register/status/remove with backups |
| Scheduled background jobs | `scheduler_ops` | add/list/run_now/pause/resume/remove |
| Toolchain presets | `toolchain_ops` | one apply switches the whole IDE config |
| Machine health | `heartbeat_ops` | status/processes/ports in the fleet range |
| A repo packed for LLM context | `pack_ops` | single bundle + token estimate |
| Token budgeting | `token_ops` | per-file/repo estimates before embedding |
| Fleet discovery | `discovery_ops` | local servers + IDE audit |

### The meta moves

| You want... | Do this |
|-------------|---------|
| The fleet audited automatically | schedule `analysis_ops(operation="runts")` via `scheduler_ops` |
| A server inspired by a repo you like | `inspire_repo_workflow` → `scaffold_mcp_server` - two calls |
| Your existing code exposed to Claude | `harness_analyze` → `harness_generate` - three calls total |
| To know it all still works | `just health` (self-audit 10/10), `just test` (65 green), `just mcpb-pack` (3-4-100 gate) |

---

## What it does

meta-hypertools is a single local hub for operations otherwise spread across a dozen scripts. All tools are **portmanteau** -- consolidated by domain with `operation: Literal[...]` discriminators.

| Area | Summary |
|------|---------|
| **Scaffolding** | Generate MCP servers, fullstack apps, landing pages, games, and **Spec Kit SDD projects** -- `scaffold_ops` |
| **Fleet lifecycle** | Start, stop, probe, and audit fleet apps -- `fleet_ops` |
| **Repo inspiration** | Study public GitHub repos without cloning -- `inspire_repo` |
| **Harness generation** | AST-analyze source code, generate FastMCP servers -- `harness_analyze`, `harness_generate` |
| **Config audit** | Scan fleet for CLAUDE.md, llms.txt, glama.json, .cursorrules -- `fleet_config_audit` |
| **Analysis** | SOTA compliance, runt detection, depot -- `analysis_ops` |
| **Diagnostics** | Tool discovery, Unicode/PowerShell/justfile validation -- `diagnostics_ops` |
| **Client management** | IDE config read/update/add/remove -- `client_ops` |
| **Server management** | MCP server start/stop/list/status -- `server_ops` |
| **Heartbeat** | Fleet health, ping, liveness checks -- `heartbeat_ops` |
| **Token analysis** | File/dir token counting, context limit checks -- `token_ops` |
| **Toolchains** | Preset management (list/create/delete/apply) -- `toolchain_ops` |
| **Scheduler** | Recurring task management -- `scheduler_ops` |
| **Meta dev** | Fleet helpers: diff, snippet, orphan detection, redact -- `meta_dev_ops` |
| **Repo packing** | LLM-optimized repo packing -- `pack_ops` |
| **Discovery** | Local server discovery, IDE audit -- `discovery_ops` |
| **Dashboard** | Tool Lab, Builders (incl. Spec Kit SDD), Analysis, Repo Inspiration, Config Audit, Fleet tabs |

### Portmanteau tools (16)

Every domain is consolidated into a single tool with `operation: Literal[...]`. Legacy individual tools are deprecated. The tool count went from 125 to **61** (16 portmanteau + 45 domain-specific tools including 5 routing tools).

| Portmanteau | Operations |
|-------------|------------|
| `scaffold_ops` | fullstack, landing_page, mcp_server, webshop, game, wisdom_tree, tauri_nsis, spec_kit, questionnaire, tiiny_site |
| `fleet_ops` | status, launch, stop, startup_probe, startup_report, install_probe, install_report |
| `analysis_ops` | runts, status, codebase, list_depot, get_depot_run, publish_mcd |
| `diagnostics_ops` | help, overview, unicode, pwsh, justfile, audit_impl, launcher, refresh |
| `server_ops` | start, stop, list, status |
| `heartbeat_ops` | pulse, ping, liveness, proactive |
| `client_ops` | read, update, add_server, remove_server, validate, list |
| `meta_dev_ops` | probe, diff, snippet, audit_surface, orphans, tail, env, summarize, changelog, redact |
| `token_ops` | analyze_file, analyze_dir, context_limits |
| `scheduler_ops` | schedule, list, cancel |
| `toolchain_ops` | list, create, delete, apply, available |
| `pack_ops` | pack, pack_ai |
| `discovery_ops` | servers, ide |
| (see below) | Dynamic routing: `meta_route_tool`, `meta_search_capabilities`, `meta_routing_status`, `meta_routing_reindex`, `meta_routing_servers` |

Call via MCP: `{"tool": "analysis_ops", "arguments": {"operation": "runts"}}` -- or use the web dashboard.

### Builders (scaffolding)

Generate new projects from fleet templates -- not just config, full repo trees.

| Tool / UI | Purpose |
|-----------|---------|
| **Dashboard → Builders → Spec Kit (SDD)** | GitHub Spec-Driven Development: `specify init` with `/speckit.*` slash commands for structured planning |
| **Dashboard → Builders** | Wizard UI for fullstack, landing page, MCP server, webshop, game |
| `scaffold_ops(operation='spec_kit')` | Runs `specify init` -- scaffolds a spec-kit project with AI agent integration (OpenCode/Claude/Copilot/Cursor/Gemini) |
| `scaffold_ops(operation='mcp_server')` | FastMCP 3.4 repo: sampling, agentic workflow, prompts/skills, CodeMode, prefab UI, mcpb |
| `scaffold_ops(operation='fullstack')` | FastAPI + React/Vite fullstack with MCP hooks |
| `scaffold_ops(operation='landing_page')` | Tailwind marketing page scaffold |
| `scaffold_ops(operation='webshop')` / `game` / `wisdom_tree` / `tauri_nsis` | Specialized app templates |

Docs: [docs/tools/scaffolding.md](docs/tools/scaffolding.md)

### Analyzers & scrubbers

**Analyze** fleet health and repo quality against 40+ 2026 fleet standards; **scrub** codebases before they bite you in production.

| Kind | Tools | What it catches |
|------|-------|-----------------|
| **SOTA compliance** | `analysis_ops(operation="runts"\|"status")` | 40+ rules: FastMCP version, web stack, Tauri/NSIS, docs, testing, safety — with **remediation_todo** output |
| **Fleet analysis** | `analyze_fleet`, `show_mcp_status` | Multi-dimensional: git, docker, web SOTA, AI infra, security |
| **Depot + export** | `list_analysis_depot`, `publish_analysis_to_mcd` | Persistent runs under `~/.meta_mcp/analysis/`; optional export when a handbook root is configured |
| **Deep pack** | `analyze_mcp_codebase` | Repomix-style codebase digest |
| **Unicode scrub** | `scan_mcp_unicode` (EmojiBuster) | Emoji literals that crash Windows loggers |
| **Shell scrub** | `validate_mcp_pwsh` | Linux-ism aliases in `.ps1` (`grep`, `&&`, …) |
| **Honesty scrub** | `audit_mcp_implementation` | Stubs, mocks, TODO placeholders |
| **Secret scrub** | `redact_secrets_audit` (`meta_dev`) | Keys/tokens before sharing scans |

All fix tools support `--dry-run` (preview) and `--bak` (timestamped backup) safety flags.
Results include structured **remediation_todo** markdown grouped P0/P1/P2 with actionable fix steps.

**Dashboard:** **SOTA Check** (dedicated tool cards) · **Fleet Status** (runtime audit) · **Scrubbers** (unicode/ps1/justfile)  
Docs: [docs/tools/analysis.md](docs/tools/analysis.md) · [docs/tools/diagnostics.md](docs/tools/diagnostics.md)

---

## Fleet probes

meta-hypertools **orchestrates** fleet-wide health checks. Probe scripts live in `fleet_probes/`; reports and manifests default to `~/.meta_mcp/fleet/`. No separate handbook repo is required at runtime.

### Cold-start probe

Answers: *does `start.ps1` bring up the stack, and is the console clean?*

- Runs `fleet-webapp-start-probe.ps1` against the webapp manifest
- Captures per-repo logs (`FLEET_PROBE_RUN=1`); flags HTTP 4xx/5xx, STARTUP PROBE warnings, proxy errors
- Outcomes include `stack_ok`, `stack_degraded` (up but dirty console), `start_failed`, `pages_404`
- Teardown uses `Stop-FleetPortSquatters` (port-based; no `taskkill`)
- **Phase 2c (planned):** Playwright UI smoke after `stack_ok` -- `ui_ok` / `ui_failed` on the cold-start report, not cold-install

**Dashboard:** Fleet → **Cold-start** tab  
**API:** `POST /api/v1/fleet/startup-probe/run`, `GET …/report`  
**MCP tools:** `fleet_startup_probe`, `fleet_startup_probe_report`

### Cold-install probe (Phase 2b)

Answers: *can a consumer follow `INSTALL.md` -- mcpb, stdio, or manual config?*

- Runs `fleet-cold-install-probe.ps1` against the cold-install manifest
- **Phase 2b (host):** **mcpb** outcomes apply to **Claude Desktop only**; other IDEs use **stdio** smoke (`stdio_mcp_smoke.py` + `Invoke-FleetStdioMcpSmoke.ps1`)
- Supports pilot batches, broken-only reruns, and multi-IDE client filters
- Preflight (default) checks doc structure and release assets without installing

**Dashboard:** Fleet → **Cold-install** tab  
**API:** `POST /api/v1/fleet/cold-install/run`, `GET …/report`  
**MCP tools:** `fleet_cold_install_probe`, `fleet_cold_install_probe_report`  
**Docs:** [FLEET_COLD_INSTALL_PROBE.md](docs/fleet/FLEET_COLD_INSTALL_PROBE.md) · [FLEET_COLD_INSTALL_PHASES_2B_2C.md](docs/fleet/FLEET_COLD_INSTALL_PHASES_2B_2C.md) · [FLEET_COLD_INSTALL_TODO.md](docs/fleet/FLEET_COLD_INSTALL_TODO.md)

### Runtime layout

```
meta_mcp/fleet_probes/scripts/     # vendored probe scripts (canonical)
~/.meta_mcp/fleet/
  manifests/                       # synced repo lists
  reports/                         # JSON + progress files
```

Path resolution: `src/meta_mcp/fleet_paths.py`. Override with `META_MCP_FLEET_PROBES_ROOT`, `META_MCP_FLEET_DEPOT`, etc. See [fleet_probes/README.md](fleet_probes/README.md) and [docs/fleet/FLEET_PROBE_ARCHITECTURE.md](docs/fleet/FLEET_PROBE_ARCHITECTURE.md).

**Planned (manifest flags, not separate programs yet):** Docker build/run, Tauri build smoke.

### Sandboxed cold-install (`-Execute`)

Beyond INSTALL.md preflight and host-side mcpb/stdio smoke (Phase 2b), meta-hypertools can generate **consumer-profile sandbox install scripts** for naked Windows validation via [virtualization-mcp](https://github.com/sandraschi/virtualization-mcp).

| Mode | What it checks | Status |
|------|----------------|--------|
| **Preflight** (default) | `INSTALL.md` structure, release `.mcpb` asset, doc gaps | Done |
| **Host smoke** (2b) | Claude mcpb config + multi-IDE stdio (`stdio_mcp_smoke.py`) | Done |
| **Sandbox execute** | Persist install script under `_sandbox_runs/` via virt-mcp | Script gen done; **guest execution pending** |

**Dashboard:** Fleet → **Cold-install** → enable **Execute** (requires virtualization-mcp on `10701`)  
**API:** `POST /api/v1/fleet/cold-install/run` with `execute=true`  
**CLI:** `fleet-cold-install-probe.ps1 -Execute` (see [fleet_probes/README.md](fleet_probes/README.md))

Options A/B/C in an isolated consumer sandbox -- see vendored [FLEET_COLD_INSTALL_PROBE.md](docs/fleet/FLEET_COLD_INSTALL_PROBE.md).

---

## Repo inspiration

**Study OSS repos from inside meta-hypertools** -- filtered trees, token-safe file fetches, and architecture prompts. Adapted from [Repomuse](https://www.npmjs.com/package/repomuse); implemented natively in Python (no `npx` sidecar).

| Surface | Entry |
|---------|--------|
| **Dashboard** | **Repo Inspiration** -- structure card, chapters, workflow |
| **MCP** | `inspire_repo(operation=structure\|files\|patterns\|help)` |
| **Prefab** | `inspire_repo_structure_card` |
| **Workflow** | `inspire_repo_workflow(goal=…)` -- multi-step agentic study |
| **Docs** | [docs/tools/repo-inspiration.md](docs/tools/repo-inspiration.md) |

Optional `GITHUB_TOKEN` raises GitHub API rate limits. Tree cache (~5 min) avoids repeat fetches in one session.

**Contrast:** local fleet repos → `pack_mcp_*`; live digest URLs → git-github-mcp `gitingest_*`.

---

## Quick start

```powershell
git clone https://github.com/sandraschi/meta-hypertools.git
cd meta-mcp
uv sync --group dev
```

| Mode | Command | URL / transport |
|------|---------|-----------------|
| Web + API | `.\start.bat` or `uv run meta-mcp` | http://127.0.0.1:10718 |
| stdio MCP | `uv run meta-mcp-server` | Cursor / Claude / etc. |
| Claude Desktop | `just mcpb-pack` → drag `dist/meta-mcp-v*.mcpb` | [Releases](https://github.com/sandraschi/meta-hypertools/releases) |
| Recipes | `just` | See [INSTALL.md](INSTALL.md) |
| Native desktop | `just build-native` | [docs/TAURI.md](docs/TAURI.md) -- installer + PyInstaller sidecar |

Install paths, IDE snippets, ports, troubleshooting: **[INSTALL.md](INSTALL.md)** and **[docs/INSTALL.md](docs/INSTALL.md)**.

**Discovery:** call `help()` for the full tool catalog (80+ tools), `show_mcp_overview` for suites, `inspire_repo_help` for GitHub study, Builders/Analysis pages in the dashboard.

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [INSTALL.md](INSTALL.md) | Install, IDE config, ports |
| [docs/INSTALL.md](docs/INSTALL.md) | Extended install and HTTP transport |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Server, API, MCP, UI |
| [docs/TOOLS.md](docs/TOOLS.md) | Tool suite index |
| [docs/fleet/FLEET_PROBE_ARCHITECTURE.md](docs/fleet/FLEET_PROBE_ARCHITECTURE.md) | Probe design, paths, phased roadmap |
| [docs/fleet/FLEET_COLD_INSTALL_PROBE.md](docs/fleet/FLEET_COLD_INSTALL_PROBE.md) | Cold-install probe spec (naked Windows) |
| [docs/fleet/FLEET_COLD_INSTALL_PHASES_2B_2C.md](docs/fleet/FLEET_COLD_INSTALL_PHASES_2B_2C.md) | mcpb/stdio (2b) and Playwright UI (2c) |
| [docs/fleet/FLEET_COLD_INSTALL_TODO.md](docs/fleet/FLEET_COLD_INSTALL_TODO.md) | Program tracker and phase checkboxes |
| [docs/TAURI.md](docs/TAURI.md) | Native desktop app -- sidecar + NSIS installer |
| [fleet_probes/README.md](fleet_probes/README.md) | Vendored scripts and env vars |
| [docs/tools/repo-inspiration.md](docs/tools/repo-inspiration.md) | `inspire_repo_*` tools |
| [docs/tools/scaffolding.md](docs/tools/scaffolding.md) | Builders (`scaffold_*`) |
| [docs/tools/analysis.md](docs/tools/analysis.md) | Runts, fleet analyzer, analysis depot |
| [docs/tools/diagnostics.md](docs/tools/diagnostics.md) | Scrubbers, `help`, EmojiBuster |
| [docs/tools/routing.md](docs/tools/routing.md) | Dynamic fleet routing, `meta_route_tool`, capability index |
| [llms.txt](llms.txt) | LLM/bot index (links + summary); see [llms-full.txt](llms-full.txt) for corpus |
| [docs/PRIVACY.md](docs/PRIVACY.md) | Sensitive data, local storage, scrub guidance |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |

---

## Requirements

- Python **3.10+** (3.12+ recommended)
- [uv](https://docs.astral.sh/uv/) for dependencies
- **Windows** for fleet probe scripts (PowerShell); core MCP tools are mostly cross-platform
- Optional: `GITHUB_TOKEN` for higher GitHub API rate limits (repo inspiration)
- Fleet probes: repos under `FLEET_REPOS_ROOT` (default: parent of meta_mcp checkout)

---

## Privacy and sensitive data

meta-hypertools runs **locally**. It does not host user accounts, but several tools read IDE configs, log directories, and fleet probe output that may contain **API keys, paths, or your machine hostname**.

- Reports and depot data live under `~/.meta_mcp/` (not committed).
- `data/tasks.json` is **gitignored**; seed from [data/tasks.example.json](data/tasks.example.json).
- Set `META_MCP_NODE_LABEL=local` to avoid emitting your hostname in heartbeat/pulse JSON.
- Set `WURST_AUTH_TOKEN` in `.env` before exposing the API beyond localhost.
- Use `redact_secrets_audit` before sharing file scans; scrub probe exports before posting issues.

Full detail: **[docs/PRIVACY.md](docs/PRIVACY.md)**.

---

## GitHub repository settings

Use these on [github.com/sandraschi/meta-hypertools](https://github.com/sandraschi/meta-hypertools) (About → Description & topics):

| Field | Value |
|-------|--------|
| **Description** | Swiss-army-knife MCP orchestrator: builders, analyzers/scrubbers, sandboxed cold-install probes, repo inspiration, fleet lifecycle, and web dashboard. |
| **Website** | `http://127.0.0.1:10718` (local dashboard; optional) |
| **Topics** | `mcp`, `model-context-protocol`, `fastmcp`, `fleet-management`, `github-api`, `devtools`, `python`, `windows`, `sandbox`, `orchestration` |

```powershell
gh repo edit sandraschi/meta-mcp `
  --description "Swiss-army-knife MCP orchestrator: builders, analyzers/scrubbers, sandboxed cold-install probes, repo inspiration, fleet lifecycle, and web dashboard." `
  --add-topic mcp --add-topic model-context-protocol --add-topic fastmcp `
  --add-topic fleet-management --add-topic github-api --add-topic devtools `
  --add-topic python --add-topic windows --add-topic sandbox --add-topic orchestration
```

---

## Attribution

Harness generation methodology adapted from [CLI-Anything](https://github.com/HKUDS/CLI-Anything)
(HKUDS, Apache 2.0, [arXiv:2606.03854](https://arxiv.org/abs/2606.03854)) -- the 7-phase
workflow for transforming applications into agent-controllable interfaces. Our adaptation
generates FastMCP 3.4+ servers with portmanteau tools instead of Click CLIs, and adds
curation rules, domain grouping, and Prefab UI surfaces for the fleet ecosystem.

Repo inspiration credit: [Repomuse](https://www.npmjs.com/package/repomuse) (MIT, praveene3127).

## License

MIT -- see [LICENSE](LICENSE).

