# Scaffolding Suite

**The generation engine.** One portmanteau, nine operations, complete
SOTA-baked project trees out. This suite is why no fleet repo is ever
hand-scaffolded.

## The makers, each with its own page

| Builder | Page | Generates |
|---------|------|-----------|
| **MCP Server** | [scaffolding/mcp-server.md](scaffolding/mcp-server.md) | Full FastMCP 3.4+ server repo (New Repo Gate) |
| **Fullstack App** | [scaffolding/fullstack.md](scaffolding/fullstack.md) | React 18 + Vite + Tailwind + Bun webapp paired with FastMCP backend - the 2768-line monolith |
| **Landing Page** | [scaffolding/landing-page.md](scaffolding/landing-page.md) | Tailwind marketing page |
| **Webshop / Game / Wisdom Tree** | [scaffolding/webshop-game-wisdom.md](scaffolding/webshop-game-wisdom.md) | Specialized templates |
| **Tauri NSIS wrapper** | [scaffolding/tauri-nsis.md](scaffolding/tauri-nsis.md) | Native desktop wrapper for an existing repo |
| **Spec Kit / Tiiny / Questionnaire** | [scaffolding/spec-kit-tiiny.md](scaffolding/spec-kit-tiiny.md) | SDD projects, static deploys, interactive config |

## Entry points

| Surface | How |
|---------|-----|
| **MCP** | `scaffold_ops(operation=...)` - the portmanteau (primary) |
| **Dashboard** | Builders page - wizard UI, one card per builder |
| **Questionnaire** | `scaffold_ops(operation="questionnaire")` - interactive config card in chat |
| **PowerShell** | `scripts/fullstack-builder.ps1` - the monolith for fullstack apps |
| **Legacy** | `create_tauri_nsis` (alias for `operation="tauri_nsis"`) |

![Builders page](../../screenshots/builders-page.png)
*The Builders page: one card per maker tool.*

## The portmanteau: `scaffold_ops`

```
scaffold_ops(operation=..., name=..., description=..., repository_path=...,
             backend_port=..., frontend_port=..., include_mcpb=true, ...)
```

| Parameter | Meaning |
|-----------|---------|
| `operation` | Which generator to run (`fullstack`, `landing_page`, `mcp_server`, `webshop`, `game`, `wisdom_tree`, `tauri_nsis`, `questionnaire`, `tiiny_site`) |
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

## Shared limits (read before scaffolding)

- **`name` is required** for `mcp_server`; `config` is required for
  `fullstack`, `landing_page`, `webshop`, `game`, `wisdom_tree`. The
  tool returns `success: false` with the exact missing field - it never
  guesses defaults.
- **Target directory must not exist** - generators refuse to overwrite.
- **Ports must be adjacent** and inside 10700-11500 (fleet reservoir).
  Register chosen ports in `mcp-central-docs/operations/WEBAPP_PORTS.md`.
- **Generated code is a starting point, not a finish line**: the example
  tools/pages are placeholders to replace; the SOTA structure around them
  is the deliverable. Harness-refine or code review before committing.
- **Template updates propagate forward, not backward** - existing
  generated repos do not auto-update when the builder changes.

## After scaffolding - the verification flow

```powershell
cd <generated-repo>
just bootstrap        # uv sync + bun install
just lint             # ruff check + format
just test             # pytest (backend)
just e2e              # Playwright (webapp)
just mcpb-pack        # MCPB bundle at the 3-4-100 gate
```

Then register the ports and `server_ops(operation="register")` to wire it
into your IDE.

## Philosophy

- **Batteries included**: linting (Ruff), formatting, tests, CI, and
  docs ship in the first pass - no "scaffold, then add quality" stages.
- **SOTA by default**: templates encode the current standards bar
  (FastMCP 3.4 floor, uv.lock, icon.png, 3-4-100 prompts, portmanteau
  pattern, data-testid, dark mode).
- **One pass or not at all**: the New Repo Gate exists so the first
  version is the real version.
- **The monolith stays a monolith**: the 2768-line fullstack builder is
  intentionally one file. It is the joke, and the joke works.

## Related

- [spec-kit-integration.md](../spec-kit-integration.md)
- [../README.md](../README.md) - tour + leporello
- [../TAURI.md](../TAURI.md) - Tauri/NSIS pipeline
- [scripts/README.md](../../scripts/README.md) - the build scripts behind the suite
