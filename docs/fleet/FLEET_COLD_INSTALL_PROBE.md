# Fleet cold-install probe: naked Windows validation cycle

**Goal:** Prove each fleet repo's published install path works on a **clean Windows consumer baseline** — not on the dev machine. Complements the cold-start probe (which assumes deps already exist).

**Last updated:** 2026-06-07 (Phase 2b host smoke landed; sandbox guest execute pending)

**Program tracker:** [FLEET_COLD_INSTALL_TODO.md](FLEET_COLD_INSTALL_TODO.md)  
**Phases 2b / 2c spec:** [FLEET_COLD_INSTALL_PHASES_2B_2C.md](FLEET_COLD_INSTALL_PHASES_2B_2C.md)

## Relationship to cold-start

| Probe | Host | Question |
|-------|------|----------|
| **Cold-start** (`fleet-webapp-start-probe.ps1`) | Dev machine (`FLEET_REPOS_ROOT`) | Does `start.ps1` parse and does the stack come up? |
| **Cold-install** (`fleet-cold-install-probe.ps1`) | Windows Sandbox **consumer** or VB `clean-base` | Does `INSTALL.md` / Option A–C work from zero tools? |

Run cold-install first for new repos or after INSTALL.md changes; run cold-start after install succeeds on the host.

**Phase 2c (Playwright UI smoke)** extends **cold-start**, not cold-install — see [FLEET_COLD_INSTALL_PHASES_2B_2C.md](FLEET_COLD_INSTALL_PHASES_2B_2C.md).

## Architecture (MCD-free runtime)

```
meta_mcp (orchestrator)
  Fleet Dashboard → Cold install tab
  API: POST /api/v1/fleet/cold-install/run
  Service: FleetColdInstallService
  Scripts: fleet_probes/scripts/
       │
       ▼
virtualization-mcp (execution, optional)
  Windows Sandbox consumer (default for -Execute)
  POST /api/v1/fleet/install-script
  POST /api/v1/fleet/install-mcpb
  POST /api/v1/fleet/stdio-smoke
  POST /api/v1/fleet/install-run  (script persist; guest run pending)
       │
       ▼
~/.meta_mcp/fleet/  (reports + synced manifests)
  reports/fleet-cold-install-report.json
  manifests/fleet-cold-install-manifest.json
```

**Artifact host path:** `FLEET_REPOS_ROOT\_sandbox_runs\<run_id>\` (import logs after sandbox teardown).

Path resolution: `src/meta_mcp/fleet_paths.py`.

## Probe modes

| Mode | CLI | MetaMCP UI | Description |
|------|-----|------------|-------------|
| **Preflight** | `-PreflightOnly` | default | INSTALL.md + release asset check only |
| **Host mcpb/stdio** | `-TestMcpb`, `-HostMcpbSmoke` | toggles | Phase 2b — see below |
| **Pilot batch** | `-BatchSize 10` | **Pilot (N)** | First tranche for script shakeout |
| **Full fleet** | (default) | **Full fleet** | All manifest entries with `INSTALL.md` |
| **Broken only** | `-BrokenOnly` | **Broken\* (N)** | Re-probe repos where last outcome failed |
| **Sandbox execute** | `-Execute` | **Execute** | Generate/persist install scripts (guest run pending) |
| **Single repo** | `-RepoFilter foo-mcp` | **Test one** | One repo; full log capture |

Cannot combine `-RepoFilter` with `-BrokenOnly` (same rule as cold-start).

## Phase 2b — mcpb + multi-IDE stdio (host)

**mcpb (Option A) is Claude Desktop only** — `mcpb install` writes `claude_desktop_config.json` only. Other IDEs are validated via **stdio** outcomes on uv/manual configs.

| mcpb outcome | Meaning |
|--------------|---------|
| `mcpb_ok` | Install succeeded, config valid, stdio smoke passed |
| `mcpb_install_failed` | `mcpb install` failed or no config entry |
| `mcpb_smoke_failed` | Installed but stdio initialize failed |
| `mcpb_no_package` | No `.mcpb` on releases — not a failure |

| stdio outcome | Meaning |
|---------------|---------|
| `stdio_ok` | At least one IDE config entry passed initialize smoke |
| `stdio_failed` | Config found; all smokes failed |
| `stdio_no_config` | Repo not in any scanned IDE config |

**Registry:** `fleet_probes/scripts/Get-FleetMcpClientRegistry.ps1`  
**Smoke:** `fleet_probes/scripts/stdio_mcp_smoke.py` + `Invoke-FleetStdioMcpSmoke.ps1`

## Option C outcomes (INSTALL.md / uv path)

| Outcome | Meaning |
|---------|---------|
| `install_ok` | Primary INSTALL path completed; verify passed |
| `install_failed` | Script/install command failed |
| `doc_gap` | INSTALL.md ambiguous, wrong winget id, or missing step |
| `verify_failed` | Installed but entrypoint/health check failed |
| `preflight_ok` | Doc/asset check only |
| `skip` | No INSTALL.md or `probeSkip` |

## Sandbox profile

Use **consumer** bringup only for naked install tests (`virtualization-mcp` consumer sandbox). Do not use dev-infra WSB modes — they pre-install git/uv/node and invalidate the test.

## Implementation status (2026-06-07)

| Component | Status |
|-----------|--------|
| `fleet-cold-install-probe.ps1` | Preflight + mcpb + multi-IDE host smoke |
| meta_mcp Cold install tab + API + MCP tools | Implemented |
| Vendored manifests under `fleet_probes/manifests/` | Implemented |
| virt-mcp fleet APIs | Implemented — restart backend after route changes |
| Sandbox **guest** execute (`-Execute` full run) | **Pending** Phase 2 |
| Phase 2c Playwright (cold-start) | **Pending** — spec only |

## References (in this repo)

- [FLEET_COLD_INSTALL_TODO.md](FLEET_COLD_INSTALL_TODO.md)
- [FLEET_COLD_INSTALL_PHASES_2B_2C.md](FLEET_COLD_INSTALL_PHASES_2B_2C.md)
- [FLEET_PROBE_ARCHITECTURE.md](FLEET_PROBE_ARCHITECTURE.md)
- [fleet_probes/README.md](../../fleet_probes/README.md)
