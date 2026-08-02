# Fleet probes (canonical runtime)

Vendored probe scripts for cold-start, cold-install, and future Docker/Tauri checks.

**No `mcp-central-docs` required.** meta_mcp services resolve paths via `meta_mcp.fleet_paths`.

## Status

**2026-06-07:** Core cold-install + startup probe scripts vendored from MCD (`scripts/` +
`manifests/`). MCD remains the authoring mirror during transition; runtime resolves here first
via `meta_mcp.fleet_paths` (see `docs/fleet/FLEET_PROBE_ARCHITECTURE.md`).

## Layout

```
fleet_probes/
  scripts/
    fleet-webapp-start-probe.ps1   # cold-start + dirty log
    fleet-cold-install-probe.ps1    # cold-install + mcpb/stdio smoke
    FleetStartMode.ps1              # zombie kill + probe log capture
    stdio_mcp_smoke.py
    Invoke-FleetStdioMcpSmoke.ps1
    Get-FleetMcpClientRegistry.ps1
    sync-fleet-*-manifest.ps1
  manifests/
    fleet-webapp-manifest.json
    fleet-cold-install-manifest.json
```

Live reports default to `~/.meta_mcp/fleet/reports/`; MCD `scripts/out/` remains dev mirror.

## Env overrides

| Variable | Purpose |
|----------|---------|
| `META_MCP_FLEET_PROBES_ROOT` | Script directory |
| `META_MCP_FLEET_DEPOT` | `~/.meta_mcp/fleet` root (reports + manifests) |
| `META_MCP_FLEET_MANIFESTS_DIR` | Manifest JSON directory |
| `META_MCP_FLEET_REPORTS_DIR` | Report output directory |
| `FLEET_REPOS_ROOT` | Fleet repo scan root |
| `FLEET_PROBE_RUN` | Set by cold-start probe; start scripts redirect child logs |
| `FLEET_PROBE_LOG_DIR` | Per-repo capture dir (`probe-logs/<repo>/`) |

Legacy (dev only): `MCP_CENTRAL_DOCS_ROOT/scripts` fallback until vendoring completes.

## Dirty log (cold-start)

Every probe run merges starter stdout/stderr + captured backend/frontend logs. Issues (HTTP 4xx/5xx, STARTUP PROBE warnings, proxy errors) surface as `dirtyLog` in JSON/MD reports even when `stack_ok`. See `docs/operations/FLEET_WEBAPP_PROBE.md` in MCD handbook mirror.
