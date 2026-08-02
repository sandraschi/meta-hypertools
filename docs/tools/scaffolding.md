# Scaffolding Suite

**The generation engine.** One portmanteau, nine operations, complete
SOTA-baked project trees out. This suite is why no fleet repo is ever
hand-scaffolded: `scaffold_ops` emits a full standards-compliant
repository - source, tests, CI, docs, packaging - in one pass, and the
`fullstack-builder.ps1` monolith goes one step further for webapps.

## Entry points

| Surface | How |
|---------|-----|
| **MCP** | `scaffold_ops(operation=...)` - the portmanteau (primary) |
| **Dashboard** | Builders page - wizard UI per operation |
| **Questionnaire** | `scaffold_ops(operation="questionnaire")` - interactive config card in chat |
| **PowerShell** | `scripts/fullstack-builder.ps1` - the 2768-line monolith for fullstack apps |
| **Legacy** | `create_tauri_nsis` (alias for `operation="tauri_nsis"`) |

## The portmanteau: `scaffold_ops`

```
scaffold_ops(operation=..., name=..., description=..., repository_path=...,
             backend_port=..., frontend_port=..., include_mcpb=true, ...)
```

| Parameter | Meaning |
|-----------|---------|
| `operation` | Which generator to run (enum below) |
| `name` / `description` | Project identity - become package name, README title, hero copy |
| `author` | pyproject/README author (default "MCP Studio") |
| `repository_path` | Parent directory for the generated repo |
| `license_type` | Default MIT |
| `include_mcpb` / `build_mcpb` | Scaffold the MCPB layout and pack the bundle |
| `include_prd` / `include_changelog` / `include_prompts` | SOTA doc set (default on) |
| `include_frontend` / `frontend_type` | Add a React webapp to the generated server |
| `include_nsis` | Add the Tauri 2.0 NSIS wrapper scaffold |
| `dual_connect` | Wire stdio + HTTP dual transport |
| `backend_port` / `frontend_port` | Seed ports (fleet range 10700-11500, adjacent) |

## Operations

### `mcp_server` - the flagship

Generates a complete FastMCP 3.4+ server repository following the New
Repo Gate: `pyproject.toml` with uv + committed `uv.lock`, `justfile`
with discoverable recipes, `llms.txt` + `llms-full.txt`, `glama.json`,
MCPB packaging layout with the 3-4-100 prompts, `.github/workflows/ci.yml`,
README + INSTALL, portmanteau tool pattern, Prefab UI for list/status
tools, and pytest scaffold.

```python
scaffold_ops(operation="mcp_server", name="weather-mcp",
             description="Weather forecast server", include_frontend=True)
```

### `fullstack` - webapp + backend pair

Generates a React 18 + Vite + Tailwind + Bun frontend paired with a
FastMCP 3.4 backend. The webapp ships the mandatory SOTA page set:
Dashboard (KPI cards, data-testid), Tools (dynamic discovery), Skills,
Chat (skill-first preprompt, local LLM probe), Settings (Ollama/LM
Studio/vLLM), Help, Logs, API Docs - plus Jobs, roster, shop, and
onboarding in the monolith variant. Ports are adjacent.

### The `fullstack-builder.ps1` monolith

The same `fullstack` operation is also available as a 2768-line
PowerShell script - intentionally monolithic, one linear flow, a whole
repo:

```powershell
pwsh scripts/fullstack-builder.ps1 -?                    # full help
pwsh scripts/fullstack-builder.ps1 -AppName my-app       # defaults
pwsh scripts/fullstack-builder.ps1 -AppName my-app -Interactive -IncludeTauri
```

| Flag | What it adds |
|------|--------------|
| `-Interactive` | Feature-selection menu (11 toggles) |
| `-IncludeAI` | Local LLM chat (default on) |
| `-IncludeMCP` | MCP streamable HTTP endpoint `/mcp` (default on) |
| `-IncludeScheduler` | APScheduler jobs + patrol demo job (default on) |
| `-IncludeCI` / `-IncludeTesting` | GitHub Actions + pytest/Playwright (default on) |
| `-IncludeFileUpload` / `-IncludeVoice` / `-IncludePWA` / `-IncludeEmail` / `-IncludeRealtime` | Feature blocks |
| `-IncludeTauri` | Tauri 2.0 desktop wrapper scaffold (`native/`) |
| `-BackendPort` / `-FrontendPort` | Adjacent fleet-range ports |

It emits a 50-file app: SQLite (members/products/orders), membership
roster, dog-grade onboarding wizard, webshop with cart + orders, Logs
ring buffer, API Docs page, Playwright e2e, CI, README + llms.txt.
Dogfood proof: `benny-the-dog-mcp` was built with it.

### `landing_page`

Tailwind marketing page with the fleet design language (dark zinc,
amber accents, lucide icons). `scaffold_ops(operation="landing_page",
name="fleet-landing")`.

### `webshop`, `game`, `wisdom_tree`

Specialized templates: e-commerce foundation, browser game bootstrap,
and knowledge-tree interface. Each scaffolds the repo structure; the
domain logic is yours to grow.

### `tauri_nsis`

Adds the Tauri 2.0 NSIS wrapper to an existing repo: `native/` with
`Cargo.toml`, `tauri.conf.json` (embedded backend via `bundle.resources`,
not `externalBin`), capabilities, and `build-sidecar.ps1` (PyInstaller
pipeline). See `docs/TAURI.md` for the full NSIS build rules.

### `questionnaire`

Interactive scaffold config card - renders in chat (Prefab) so the user
picks features without reading the schema. `scaffold_ops(operation="questionnaire")`.

### `tiiny_site`

Static page scaffold + deploy to tiiny.host.

## After scaffolding - the verification flow

Every generated repo is self-contained and verifiable:

```powershell
cd <generated-repo>
just bootstrap        # uv sync + bun install
just lint             # ruff check + format
just test             # pytest (backend)
just e2e              # Playwright (webapp)
just mcpb-pack        # MCPB bundle at the 3-4-100 gate
```

Then register the ports in `mcp-central-docs/operations/WEBAPP_PORTS.md`
(backend + frontend adjacent) and `server_ops(operation="register")` to
wire it into your IDE.

## Philosophy

- **Batteries included**: linting (Ruff), formatting, tests, CI, and
  docs ship in the first pass - no "scaffold, then add quality" stages.
- **SOTA by default**: templates encode the current standards bar
  (FastMCP 3.4 floor, uv.lock, icon.png, 3-4-100 prompts, portmanteau
  pattern, data-testid, dark mode). Template updates propagate to every
  new project automatically.
- **One pass or not at all**: the New Repo Gate exists so the first
  version is the real version. No runt iterations.
- **The monolith stays a monolith**: the 2768-line builder is
  intentionally one file. It is the joke, and the joke works.

## Related

- [spec-kit-integration.md](../spec-kit-integration.md) - Spec Kit (SDD) operation
- [../README.md](../README.md) - tour + leporello
- [../TAURI.md](../TAURI.md) - Tauri/NSIS pipeline
- [scripts/README.md](../../scripts/README.md) - the build scripts behind the suite
