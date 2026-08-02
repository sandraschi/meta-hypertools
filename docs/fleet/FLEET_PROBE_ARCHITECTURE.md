# Fleet probe architecture — MCD-free runtime

**Problem:** Cold-start, cold-install, and future Docker/Tauri probes currently live under
`mcp-central-docs` (private). Consumers (Fritz, sandbox, CI, other devs) must not need
that repo cloned.

**Answer:** **meta_mcp owns orchestration + vendored probe assets.** virtualization-mcp
owns sandbox execution only. MCD is an optional **docs/export mirror**, not a runtime dep.

---

## Three planes

| Plane | Repo | Role | MCD required? |
|-------|------|------|---------------|
| **Orchestration** | `meta_mcp` (public) | UI, API, MCP tools, manifests, reports, probe scripts | No |
| **Execution** | `virtualization-mcp` (public) | Consumer sandbox, install scripts, mcpb download | No |
| **Handbook** | `mcp-central-docs` (private) | Specs, CHANGELOG narrative, memops import | Optional |

Same pattern as **analysis depot**: canonical data under `~/.meta_mcp/`, optional
`publish_*_to_mcd` for Sandra's private handbook.

---

## Runtime layout (target)

```
meta_mcp/
  fleet_probes/                    # vendored scripts (canonical source of truth)
    scripts/
      fleet-cold-install-probe.ps1
      fleet-webapp-start-probe.ps1
      sync-*-manifest.ps1
      Get-FleetMcpClientRegistry.ps1
      stdio_mcp_smoke.py
      ...
    README.md

~/.meta_mcp/fleet/                 # machine-local generated state
  manifests/
    fleet-cold-install-manifest.json
    fleet-webapp-manifest.json
  reports/
    fleet-cold-install-report.json
    fleet-webapp-report.json
    *.progress.json
  runs/                            # sandbox artifact pointers
```

**Path resolution:** `meta_mcp.fleet_paths` (see `src/meta_mcp/fleet_paths.py`)

1. `META_MCP_FLEET_PROBES_ROOT` → vendored `fleet_probes/scripts`
2. Else `meta_mcp/fleet_probes/scripts` next to package
3. Legacy fallback: `MCP_CENTRAL_DOCS_ROOT/scripts` (dev machine only)

Reports always default to `~/.meta_mcp/fleet/reports/` unless overridden.

---

## Probe programs (phased)

| Program | Question | Host |
|---------|----------|------|
| **Cold-start** | Does `start.ps1` + stack work? Dirty console clean? | Dev host |
| **Cold-install** | Does `INSTALL.md` / mcpb / stdio work? | Consumer sandbox |
| **Multi-IDE stdio** | Does uv/manual config in Cursor/Windsurf/… smoke? | Dev host |
| *(mcpb = Claude only)* | Option A `mcpb install` writes `claude_desktop_config.json` only | |
| **Playwright** (2c) | Does SPA render after `stack_ok`? | Dev host |
| **Docker** (Phase 6) | `docker build` / `compose up` / health? | Host or sandbox w/ Docker |
| **Tauri** (Phase 7) | `tauri build` / native installer smoke? | Host (Rust toolchain) |

Docker and Tauri are **manifest flags**, not separate probes:

```json
{
  "repo": "foo-mcp",
  "hasDocker": true,
  "dockerComposeFile": "docker-compose.yml",
  "hasTauri": true,
  "tauriDir": "src-tauri"
}
```

Sync script sets flags from repo tree (`Dockerfile`, `compose.yaml`, `src-tauri/`).

### Docker outcomes (planned)

| Outcome | Meaning |
|---------|---------|
| `docker_build_ok` | `docker build` succeeded |
| `docker_run_ok` | `compose up` + health endpoint OK |
| `docker_skip` | No Docker instrumentation |
| `docker_failed` | Build or run failed |

### Tauri outcomes (planned)

| Outcome | Meaning |
|---------|---------|
| `tauri_build_ok` | `cargo tauri build` or `just build-native` OK |
| `tauri_run_ok` | Built artifact launches (headless or short-lived) |
| `tauri_skip` | No Tauri project |
| `tauri_failed` | Build/run failed |

Run Tauri on **host** by default (Rust + WebView2 SDK); sandbox only with dev-infra snapshot.

---

## Cold-start dirty log (2026-06-07)

Do not treat `stack_ok` as sufficient if console output shows warnings.

| Field | Meaning |
|-------|---------|
| `dirtyLogOk` | `false` when any parsed issue found |
| `dirtyLog` | Short summary for MD **Dirty log** column |
| `consoleIssues[]` | Full issue lines (HTTP 4xx/5xx, STARTUP PROBE, proxy errors) |
| `stack_degraded` | Outcome when stack is up but `dirtyLogOk` is false |

**Capture:** probe sets `FLEET_PROBE_RUN=1`; start scripts use `Start-FleetDetachedShell` to write `probe-logs/<repo>/*.log`. **Teardown:** two-pass `Stop-FleetPortSquatters` only (no `taskkill`).

---

## virtualization-mcp decoupling

Today virt-mcp reads `mcp-central-docs/scripts/stdio_mcp_smoke.py` — **remove that**.

| Approach | Detail |
|----------|--------|
| **Bundle** | Ship `assets/fleet/stdio_mcp_smoke.py` inside virtualization-mcp |
| **API body** | meta_mcp POSTs script content or runs smoke on host (current host path) |
| **Registry** | `FLEET_REPOS_ROOT` only — never `MCP_CENTRAL_DOCS_ROOT` |

virt-mcp `install-mcpb` uses GitHub API + `FLEET_REPOS_ROOT` manifest path from request body
or `~/.meta_mcp/fleet/manifests/`.

---

## What moves out of MCD

| Asset | New canonical home |
|-------|-------------------|
| Probe PS1/py scripts | `meta_mcp/fleet_probes/scripts/` |
| Manifest sync | meta_mcp tool + `sync_fleet_manifests` MCP tool |
| Reports | `~/.meta_mcp/fleet/reports/` |
| Fleet Dashboard tabs | Already in meta_mcp |
| Ops spec (markdown) | Copy summary to `meta_mcp/docs/fleet/`; MCD keeps full handbook |

MCD keeps: narrative CHANGELOG, memops imports, cross-repo program pages (optional).

---

## Migration steps

1. [x] `fleet_paths.py` — meta_mcp-first path resolution (this PR)
2. [ ] Vendor scripts into `meta_mcp/fleet_probes/scripts/`
3. [ ] Point `Fleet*ProbeService` at `fleet_paths` only
4. [ ] `sync_fleet_manifests` MCP tool writes to `~/.meta_mcp/fleet/manifests/`
5. [ ] virt-mcp: bundle smoke helper; drop MCD paths
6. [ ] `fleet_runtime_service`: registry from `~/.meta_mcp/fleet/registry.json` or env
7. [ ] Optional `publish_fleet_report_to_mcd` (like analysis depot)
8. [ ] Phase 6 Docker + Phase 7 Tauri blocks in cold-install probe

---

## CI / Fritz without MCD

```yaml
# fleet-agent-mcp — needs only public repos
env:
  FLEET_REPOS_ROOT: /fleet
  META_MCP_FLEET_PROBES_ROOT: /meta_mcp/fleet_probes/scripts
steps:
  - run: meta-mcp fleet_cold_install_probe preflight_only=true batch_size=20
```

No `git clone mcp-central-docs`.

---

## Decision

**Yes — put the shebang in meta_mcp** (orchestration + vendored probes + local depot).
Keep virtualization-mcp as execution subcontractor. Optional handbook export only —
not a runtime dependency.

## Vendored program docs (canonical)

| Doc | Purpose |
|-----|---------|
| [FLEET_COLD_INSTALL_PROBE.md](FLEET_COLD_INSTALL_PROBE.md) | Cold-install probe spec |
| [FLEET_COLD_INSTALL_PHASES_2B_2C.md](FLEET_COLD_INSTALL_PHASES_2B_2C.md) | mcpb/stdio (2b) + Playwright (2c) |
| [FLEET_COLD_INSTALL_TODO.md](FLEET_COLD_INSTALL_TODO.md) | Phase tracker |
| [../../fleet_probes/README.md](../../fleet_probes/README.md) | Scripts and env vars |
