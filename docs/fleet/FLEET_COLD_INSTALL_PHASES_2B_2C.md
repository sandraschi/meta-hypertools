# Fleet cold-install program — phases 2b and 2c

**Date:** 2026-06-07  
**Status:** Incorporated into [FLEET_COLD_INSTALL_TODO.md](FLEET_COLD_INSTALL_TODO.md)  
**Vendored in:** meta_mcp (canonical runtime copy)

---

## Context

The fleet cold-install program covers Phases 0–8: scaffolding, the PowerShell probe script,
the virtualization-mcp execution layer, meta_mcp orchestration, fix wave, and optional CI.
Two significant validation surfaces were added as **2b** and **2c**:

1. **mcpb package install + stdio smoke** — repos that ship a built `.mcpb` need a separate
   install path validated: download from GitHub releases, install via mcpb CLI, verify stdio.

2. **Playwright webapp smoke** — repos with a frontend need UI validation beyond cold-start
   health polls. **This attaches to the cold-start probe, not cold-install.**

---

## Phase 2b — mcpb package install + stdio smoke

### What it is

For repos that publish a `.mcpb` on GitHub releases: validate that `mcpb install` works
and the installed server responds to a minimal JSON-RPC `initialize` on stdio. This is
Option A — the most important path for Claude Desktop end users.

### Why separate from Option C

Option C is winget git + uv → clone → `uv sync`. Option A has different failure modes
(wrong entrypoint, mcpb CLI mismatch, malformed config). Outcomes must stay separate in
the report (`mcpbOutcome` vs `outcome`).

### Manifest fields

Per `fleet-cold-install-manifest.json`:

```json
{
  "repo": "calibre-mcp",
  "mcpbAvailable": true,
  "mcpbReleasesUrl": "https://github.com/sandraschi/calibre-mcp/releases",
  "studioSmokeArgs": null
}
```

### Per-repo flow

1. Fetch latest `.mcpb` from GitHub releases API
2. Install via `mcpb install` (Claude Desktop config only)
3. Verify `claude_desktop_config.json` entry
4. Stdio smoke — spawn command+args, send `initialize`, expect response within 10s
5. Record `mcpb_*` and `stdio_*` outcomes (stdio uses multi-IDE registry for uv/manual)

### Outcomes

| Outcome | Meaning |
|---------|---------|
| `mcpb_ok` | Install + config + smoke passed |
| `mcpb_install_failed` | Install failed or no config entry |
| `mcpb_smoke_failed` | Installed but stdio failed |
| `mcpb_no_package` | No `.mcpb` artifact — skip (not failure) |

**Decision:** mcpb = **Claude Desktop only**. Cursor, Windsurf, Antigravity, Zed, OpenCode
use `stdio_*` on host configs only.

### Status in meta_mcp

| Item | Status |
|------|--------|
| Probe `-TestMcpb`, `-HostMcpbSmoke`, `-McpClients` | Done |
| Dashboard mcpb + stdio columns | Done |
| `fleet_cold_install_probe` MCP tool | Done |
| Consumer sandbox mcpb matrix | Pending |
| INSTALL.md Option A/B snippets per IDE | Pending |

---

## Phase 2c — Playwright webapp smoke (cold-start only)

### What it is

After cold-start reports `stack_ok`, optionally run Playwright headless against
`127.0.0.1:{frontendPort}`. Catches SPA 404s, console errors, blank pages, broken Vite proxy.

### Architecture

- Runs on the **host**, not in sandbox — stack already up locally
- Manifest: `fleet-webapp-manifest.json` (cold-start), **not** cold-install manifest
- Probe: `fleet-webapp-start-probe.ps1` + future `run-playwright-smoke.ps1`

```
cold-start → stack_ok → (optional) Playwright → ui_ok / ui_failed
```

### Outcomes

| Outcome | Meaning |
|---------|---------|
| `ui_ok` | Routes loaded, no console errors |
| `ui_failed` | Route/console/assertion failure |
| `ui_skip` | No routes/spec declared |

A repo can be `stack_ok` + `ui_failed` — independent dimensions.

### Status in meta_mcp

| Item | Status |
|------|--------|
| `playwrightRoutes` in webapp manifest | Pending |
| `run-playwright-smoke.ps1` | Pending |
| Dashboard UI chip on cold-start tab | Pending |
| `fleet_startup_probe(run_playwright=…)` | Pending |

---

## Priority

**2b before 2c.** A broken mcpb package is worse UX than a broken UI — users hit install
before they have a running stack.

Both phases start opt-in; mandatory in Phase 5 CI gate once stable.
