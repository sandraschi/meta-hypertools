# meta-hypertools -- Product Requirements Document

**Version**: 0.5.0 (2026-08-02)
**Status**: ACTIVE - the fleet's central nervous system
**Owner**: Sandra Schipal
**One-liner**: The MCP server that builds, wraps, studies, probes, audits, and operates every other MCP server in the fleet.

---

## 1. Vision

The fleet is a living organism: 180+ FastMCP servers, webapps, robots,
schedulers, and documentation - each one born, grown, and retired. Most
fleet operators drown in that organism: scaffolding by hand, auditing by
grep, releases by prayer.

meta-hypertools is the organism's **meta layer**. It does not serve data. It
serves the fleet itself. Point it at any problem - "scaffold a server
like this repo", "wrap my script collection", "why is this webapp down",
"who is behind on standards", "ship ten releases safely" - and it turns
that into a repeatable, standards-compliant, verifiable process.

**The moonshot**: a fleet where no repo is ever hand-scaffolded, no
release is ever unprobed, no standard is ever silently violated, and the
meta-layer audits itself at 10/10 while promising the same for everyone
else.

## 2. Mission

Every fleet operation that is currently a dozen scripts, a wiki page, and
a prayer becomes a single MCP tool with a schema, a report, and a
recovery path. meta-hypertools is the operational API of the fleet: **scaffold,
inspire, wrap, probe, audit, operate** - all of it, all the time, all
against the current SOTA 2026 bar.

## 3. The Problem

| Pain | Today (without meta-hypertools) | With meta-hypertools |
|------|--------------------------|--------------|
| New server | Copy an old repo, rip out its soul, pray | `scaffold_mcp_server` - full SOTA repo in one pass |
| Imitate a GitHub project | Clone, grep, squint | `inspire_repo_workflow` - architecture study, no clone |
| Wrap existing code | Hand-write 40 tools | `harness_analyze` → `harness_generate` → `harness_refine` |
| Standards decay | "We should really..." | `analyze_mcp_runts` - scored work list, fix waves |
| Release wave | Manual smoke, manual prayer | `fleet_startup_probe` + `fleet_cold_install_probe` |
| IDE registration | Edit four JSON files by hand | `server_ops` - list/register/status/remove with backups |
| Machine health | Three terminal tabs | `heartbeat_ops` - status/processes/ports |
| LLM context | Paste a repo, blow the window | `pack_ops` + `token_ops` - bundle with budget |
| Toolchain switching | Disable 40 servers by hand | `toolchain_ops` - named presets, one apply |

## 4. Product Pillars

### Pillar 1 - Scaffold (the generation engine)

`scaffold_ops` generates complete, standards-compliant projects: MCP
servers (FastMCP 3.4+, portmanteau pattern, Prefab UI, MCPB packaging,
CI, tests, docs), fullstack webapps (React 18 + Vite + Tailwind + Bun
frontend, FastMCP backend, fleet-standard chat, roster, shop, onboarding,
scheduler, Tauri 2.0 wrapper), landing pages, Spec Kit SDD projects, and
specialized templates.

The fullstack builder is the fleet's monolithic joke and crown jewel: a
single 2768-line PowerShell file that emits a complete 50-file
application. It scaffolds SQLite, a membership roster, an onboarding
wizard, a fleet-standard chat, a webshop, an APScheduler job system, a
log ring buffer, Swagger UI, Playwright e2e, GitHub Actions CI, and an
optional Tauri wrapper - all wired to adjacent fleet-range ports.

### Pillar 2 - Inspire (the pattern miner)

`inspire_repo` studies any public GitHub repository without cloning:
README, tree, topics, languages, structure. `inspire_repo_workflow`
reasons about the architecture and produces a scaffold recommendation.
Inspiration feeds scaffolding: "build something like X" becomes a
two-call pipeline.

### Pillar 3 - Wrap (the harness)

`harness_analyze` parses any Python source tree into a tool spec.
`harness_generate` turns the spec into a FastMCP server.
`harness_refine` gap-checks the result. Three passes, existing code
becomes MCP surface.

### Pillar 4 - Probe (the certification engine)

`fleet_startup_probe` boots fleet backends and reports crashes, hangs,
and dirty logs. `fleet_cold_install_probe` validates INSTALL.md, `.mcpb`
assets, and per-IDE stdio smokes. Probes are the gate before every
release wave - they catch what unit tests never see.

### Pillar 5 - Audit (the honesty engine)

`analyze_mcp_runts` scores every repo against the SOTA bar (FastMCP 3.4
floor, MCPB 3-4-100 prompts, uv, CI, docs, tooling). `fleet_config_audit`
checks configuration artifacts fleet-wide. The diagnostics suite scrubs
Unicode, PowerShell, and stub-ware. And meta-hypertools audits itself: its own
standards checker scores it 10/10, its own tests are 65 green, its own
bundle ships to the 3-4-100 gate.

### Pillar 6 - Operate (the control plane)

`server_ops`, `scheduler_ops`, `toolchain_ops`, `heartbeat_ops`,
`pack_ops`, `token_ops`, `discovery_ops` - registration, jobs, presets,
health, context packing, and discovery. Every mutating path takes
backups and supports dry-runs. Fleet start/stop are auth-protected:
the kill-switch is not a free-for-all.

## 5. Capabilities Matrix (v0.5.0)

| Tool | Operations | Surface |
|------|-----------|---------|
| `scaffold_ops` | mcp_server, fullstack, landing_page, webshop, game, wisdom_tree, tauri_nsis, spec_kit, questionnaire, tiiny_site | MCP + Builders UI |
| `analysis_ops` | runts, status, codebase, list_depot, get_depot_run, publish_mcd | MCP + Analysis UI |
| `diagnostics_ops` | help, overview, unicode, pwsh, justfile, audit_impl, launcher, refresh | MCP + Tool Lab |
| `fleet_ops` | status, launch, stop, startup_probe, startup_report, install_probe, install_report | MCP + Fleet UI |
| `server_ops` / `client_ops` | start/stop/list/status; read/update/add/remove/validate | MCP |
| `heartbeat_ops` | pulse, ping, liveness, proactive | MCP |
| `meta_dev_ops` | probe, diff, snippet, audit_surface, orphans, tail, env, summarize, changelog, redact | MCP |
| `token_ops` / `pack_ops` | analyze_file, analyze_dir, context_limits; pack, pack_ai | MCP |
| `scheduler_ops` / `toolchain_ops` | schedule, list, cancel; list, create, delete, apply, available | MCP |
| `discovery_ops` / `inspire_repo*` | servers, ide; structure, files, patterns, help | MCP |
| `harness_*` | analyze, generate, refine | MCP |
| `demo_ops` | plan, record, render | MCP + demo-capture docs |

**Delivery surfaces**: stdio MCP (IDEs), REST API (`/api/v1`), web
dashboard (`web_sota`, ports 10718/10719), MCPB bundle (Claude Desktop).

## 6. Architecture

```
┌────────────────────────────────────────────────────────────┐
│  web_sota (React, :10719)  ←→  FastAPI /api/v1  ←→ FastMCP │
│  Tool Lab · Builders · Analysis · Fleet · Inspiration      │
└────────────────────────────────────────────────────────────┘
        │                    │                      │
        ▼                    ▼                      ▼
  Services (probe,     REST endpoints        MCP tools (stdio
  runtime, analysis,   (auth-protected       for Cursor/Claude/
  inspiration, ...)    write paths)          opencode)
        │
        ▼
  fleet_probes/scripts/ → PowerShell probes on the dev host
  ~/.meta_mcp/fleet/    → manifests, reports, runtime state
  mcp-central-docs/     → standards (read-only reference)
```

**Auth**: `X-Wurst-Auth` middleware protects mutating paths
(`/api/v1/fleet/start|stop|restart`, analysis, remediation, patch).
Token unset = local-dev bypass; token set = 403 without header.

## 7. Roadmap

### Shipped (v0.5.0, 2026-08)

- SOTA analyzer, 40+ rules with `standard_ref` and P0/P1/P2 remediation
- FastMCP 3.4.4 floor: sampling, prompts, skills, CodeMode, Prefab UI
- Cold-start and cold-install probes with dirty-log parsing
- Harness pipeline (analyze → generate → refine)
- No-clone repo inspiration (single + agentic workflow)
- Spec Kit SDD integration, Tiiny.host deployment
- Fullstack builder modernization: roster, shop, onboarding, scheduler,
  Logs/API-Docs/Jobs pages, Tauri 2.0, fleet-standard chat
- Standards checker v2 (FastMCP 3.4 floor, uv.lock, icon.png,
  3-4-100 word gates, mcpb/ layout support)
- MCPB bundle at the 3-4-100 prompt gate (system 3154w, user 4226w,
  101 examples)
- Auth protection for fleet lifecycle endpoints
- Test suite 65 green; ruff clean; self-audit 10/10

### Next (v0.6)

- `jobs.yaml`-driven scheduler with cron UI and SQLite job history
- `/fleet` page: live MCP client panel over the fleet port registry
- aiwatcher digest renderer as a scheduled chat message
- Learnbot personas as chat personalities
- Harness support for TypeScript and PowerShell sources
- Tauri NSIS pipeline for the dashboard itself

### Moonshot (v1.0+)

- **Fleet self-healing**: probes that fix what they find (restart
  crashed backends, re-register drifted configs) with human approval
- **The Fleet Brain**: a RAG depot over all fleet docs and llms-full.txt
  files, so agents can query the fleet in natural language
- **Cross-fleet orchestration**: one meta-hypertools instance in every fleet,
  gossiping health via the bridge URLs
- **Robot integration**: scheduled patrols dispatching to yahboom-mcp
  (the Boomy safety patrol), alert routing through aiwatcher-mcp
- **Self-scaffolding**: meta-hypertools that can regenerate parts of itself from
  its own harness spec - the ultimate dogfood

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| Self-audit score | 10/10 (maintained) |
| Test suite | 100% green on main |
| MCPB prompt gate | 3-4-100 always met |
| Time to scaffold a new server | < 5 minutes, one pass |
| Release wave failure rate | 0 user-facing failures (probe-gated) |
| Repos below the standards floor | trending to zero |

## 9. Non-Goals (for now)

- Cloud deployment / multi-tenant SaaS
- Data serving (this is not a database server)
- Modifying non-fleet applications
- Replacing the host applications it wraps (Blender, GIMP, robots)

## 10. Risks

| Risk | Mitigation |
|------|------------|
| Tool count grows unbounded | Portmanteau pattern; 61 tools today, capped by design |
| Generated code is subtly wrong | Harness refine loop; always review generated servers |
| Probes disturb the host | Scoped to fleet repos + registered ports; dry-runs |
| Auth bypass in local dev | Explicit: no token = dev mode; documented |
| Monolith builder (2768 lines) | Intentionally monolithic - the joke is the point; tested per release |

---

*"Build the meta layer and the fleet builds itself."*

