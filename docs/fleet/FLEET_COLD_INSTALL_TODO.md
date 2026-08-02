# Fleet cold-install probe — program tracker

**Program:** meta_mcp + virtualization-mcp  
**Started:** 2026-06-07  
**Work doc:** check boxes as you land PRs; link commit/PR in Notes column.

**Spec:** [FLEET_COLD_INSTALL_PROBE.md](FLEET_COLD_INSTALL_PROBE.md)  
**Phases 2b / 2c:** [FLEET_COLD_INSTALL_PHASES_2B_2C.md](FLEET_COLD_INSTALL_PHASES_2B_2C.md)

---

## Phase 0 — Docs & scaffolding

- [x] Ops spec vendored as `docs/fleet/FLEET_COLD_INSTALL_PROBE.md`
- [x] Program tracker (this file) + phases spec
- [x] Stub `fleet_probes/scripts/fleet-cold-install-probe.ps1`
- [x] meta_mcp CHANGELOG + PRD fleet sections

---

## Phase 1 — Probe script

- [x] `fleet_probes/manifests/fleet-cold-install-manifest.json` — repos with `INSTALL.md`
- [x] `sync-fleet-cold-install-manifest.ps1` — scan `FLEET_REPOS_ROOT\*\INSTALL.md` + GitHub mcpb API
- [x] `fleet-cold-install-probe.ps1` — modes: full, `-RepoFilter`, `-BrokenOnly`, `-BatchSize`, `-PreflightOnly`, `-Execute`
- [x] Outcomes: `install_ok`, `install_failed`, `doc_gap`, `verify_failed`, `skip`, `preflight_ok`, `install_pending`
- [x] `comparison` block (install_failed delta vs prior report)
- [x] Progress JSON after each repo
- [x] Markdown report `fleet-cold-install-{stamp}.md`
- [x] Write artifacts to `_sandbox_runs/<run_id>/` + depot reports dir
- [x] Pilot batch: 10 repos alphabetically (doc_gap findings — many INSTALL.md lack Option A/B/C headers)

---

## Phase 2 — virtualization-mcp execution layer

- [ ] Align `POST /api/v1/fleet/install-script` with INSTALL.md (uv sync, no `&&`, PS 5.1)
- [ ] Add `POST /api/v1/fleet/install-run` — execute generated script inside running sandbox (or document manual flow)
- [ ] Consumer sandbox log capture API or documented path `Desktop\consumer-sandbox-launch.log`
- [ ] Optional: VB `NakedWin11` + `clean-base` snapshot restore for faster iteration
- [ ] Document env: `FLEET_REPOS_ROOT`, sandbox memory, networking (online required for winget)

---

## Phase 2b — mcpb package install + stdio smoke

> Validates Option A (`.mcpb` / `mcpb install`) — separate outcomes from Option C.
> **mcpb = Claude Desktop only**; other IDEs use `stdio_*` on host configs.

**meta_mcp:**
- [x] `sync-fleet-cold-install-manifest.ps1` — GitHub releases API for `*.mcpb`
- [x] `fleet-cold-install-probe.ps1` — `-TestMcpb`, `-HostMcpbSmoke`, virt-mcp stdio-smoke fallback
- [x] `stdio_mcp_smoke.py` + `Invoke-FleetStdioMcpSmoke.ps1`
- [x] Report schema: `mcpbOutcome`, `stdioOutcome`, `stdioSmokeResults[]`
- [x] Dashboard cold-install tab: mcpb + stdio columns
- [x] `fleet_cold_install_probe` MCP tool with `test_mcpb`, `host_mcpb_smoke`, `mcp_clients`
- [x] Export: mcpb + stdio in MD/CSV

**virt-mcp:**
- [x] `POST /api/v1/fleet/install-mcpb`
- [x] `POST /api/v1/fleet/stdio-smoke`
- [x] `POST /api/v1/fleet/install-run` — persist script to `_sandbox_runs/<run_id>/`
- [ ] Restart virt-mcp backend after route changes
- [ ] In-sandbox guest execution (consumer logon extension) — pending Phase 2

**Remaining:**
- [ ] Consumer sandbox IDE matrix (winget Claude for mcpb; host stdio for other IDEs)
- [ ] INSTALL.md Option A/B per-client snippets (`snippets/mcp-config-*.json`)
- [ ] Zed extensions vs custom smoke strategy
- [ ] HTTP/SSE transports — separate `transport_not_stdio` outcome
- [ ] Fleet run guardrails (parallel smoke cap, uvx pre-warm)
- [ ] Manifest optional `stdioClients[]` override per repo

**Pilot:** 5 repos with `.mcpb`; host stdio pilot: `docker-mcp` → `stdio_ok` (Cursor).

---

## Phase 2c — Playwright webapp smoke (cold-start only)

> Host-side UI validation after `stack_ok`. **Not** part of cold-install.

- [ ] `fleet-webapp-manifest.json`: `playwrightRoutes`, optional `playwrightSpec`
- [ ] `fleet-webapp-start-probe.ps1`: call `run-playwright-smoke.ps1` after `stack_ok`
- [ ] `run-playwright-smoke.ps1` — npx playwright wrapper
- [ ] Report: `ui_outcome`, `ui_failed_routes`, `ui_console_errors`
- [ ] Dashboard cold-start tab: UI chip column
- [ ] `fleet_startup_probe(run_playwright=…)` parameter

**Pilot:** calibre-mcp, arxiv-mcp, git-github-mcp, aiwatcher-mcp, meta_mcp.

---

## Phase 3 — meta_mcp orchestration

- [x] `FleetColdInstallService`
- [x] API: `POST /api/v1/fleet/cold-install/run`, `GET …/report`
- [x] Dashboard **Cold install** tab + export
- [x] MCP tools: `fleet_cold_install_probe`, `fleet_cold_install_probe_report`
- [ ] Exclude `meta_mcp` from sandbox install target

---

## Phase 4 — Fix wave + reinstall

- [ ] First full baseline report
- [ ] Fix wave 1: INSTALL.md, winget ids, Option C standardization
- [ ] **Broken\*** reinstall-after-fix until pilot set clean
- [ ] Expand pilot 10 → full fleet in batches of 20

---

## Phase 5 — CI / Fritz (optional)

- [ ] Weekly Broken\* on INSTALL.md regressions
- [ ] Gate release: new MCP repos require `install_ok` in last report

---

## Phase 6 — Docker instrumentation (later)

- [ ] Manifest flags: `hasDocker`, `dockerComposeFile`, `dockerHealthPath`
- [ ] Probe: `docker build` + `compose up -d` + health poll
- [ ] Outcomes: `docker_build_ok`, `docker_run_ok`, `docker_failed`, `docker_skip`

---

## Phase 7 — Tauri native build (later)

- [ ] Manifest: `hasTauri`, `tauriDir`
- [ ] Probe: `cargo tauri build` or `just build-native`
- [ ] Outcomes: `tauri_build_ok`, `tauri_run_ok`, `tauri_failed`, `tauri_skip`

---

## Phase 8 — Self-contained runtime

- [x] `fleet_paths.py` — meta_mcp-first path resolution
- [x] `docs/fleet/FLEET_PROBE_ARCHITECTURE.md`
- [x] Vendored probe scripts under `fleet_probes/scripts/`
- [x] Vendored program docs under `docs/fleet/`
- [x] Reports/manifests → `~/.meta_mcp/fleet/`
- [ ] virt-mcp: bundle `stdio_mcp_smoke.py`; drop external handbook paths
- [ ] `fleet_runtime_service` registry decoupled from external webapp-registry

---

## Decisions log

| Date | Decision |
|------|----------|
| 2026-06-07 | Consumer WSB only for naked install; dev-infra excluded |
| 2026-06-07 | Separate report type from cold-start |
| 2026-06-07 | meta_mcp orchestrates; virtualization-mcp owns sandbox APIs |
| 2026-06-07 | mcpb/Option A separate from Option C outcomes |
| 2026-06-07 | Playwright on host after stack_ok — cold-start only |
| 2026-06-07 | Runtime canonical home = meta_mcp + `~/.meta_mcp/fleet/` |
| 2026-06-07 | mcpb = Claude Desktop only; other IDEs = stdio smoke |

---

## Notes

- `mcpb_no_package` is not a failure.
- `stack_ok` + `ui_failed` is valid (Phase 2c).
- Sandbox **Execute**: script generation works; guest run still pending Phase 2.
- See [FLEET_COLD_INSTALL_PHASES_2B_2C.md](FLEET_COLD_INSTALL_PHASES_2B_2C.md) for full phase detail.
