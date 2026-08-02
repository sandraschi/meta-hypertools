# Analysis suite

**SOTA compliance, fleet runt scans, and a persistent analysis depot with MCD export.**

## Tools

### `analyze_mcp_runts`

Scans a directory for MCP repos and classifies runts vs SOTA.

| Parameter | Description |
|-----------|-------------|
| `scan_path` | Root folder (default `REPOS_DIR`) |
| `format` | `json` or `markdown` |
| `use_cache` | Reuse depot cache (default true, 24h TTL) |
| `export_mcd` | After scan, publish to `mcp-central-docs/projects/analysis/` |

Every successful scan is **archived** under `%USERPROFILE%\.meta_mcp\analysis\runs/<run_id>/`.

### `show_mcp_status`

Single-repo SOTA report; also archived as `repo_status` runs.

| Parameter | Description |
|-----------|-------------|
| `repo_path` | Repository path |
| `export_mcd` | Publish snapshots to MCD when true |

### `publish_analysis_to_mcd`

Export a depot run (latest if `run_id` omitted) to the **MCD analysis section**:

- `projects/analysis/FLEET_RUNTS_LATEST.md` or `FLEET_MULTIDIM_LATEST.md`
- `projects/analysis/runs/<run_id>/`
- `projects/analysis/repos/<slug>.md`
- `projects/<repo>/ANALYSIS_SNAPSHOT.md` when that project folder already exists

### `list_analysis_depot` / `get_analysis_depot_run`

Inspect local history (`json` or `markdown` per run).

### `analyze_mcp_codebase`

Repomix-style deep pack analysis (not stored in depot by default).

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `REPOS_DIR` | `~/repos` (if unset) | Default scan root |
| `MCP_CENTRAL_DOCS_ROOT` | `{REPOS_DIR}/mcp-central-docs` | MCD export target |
| `META_MCP_ANALYSIS_DEPOT` | `%USERPROFILE%\.meta_mcp\analysis` | Local depot root |
| `META_MCP_ANALYSIS_CACHE_TTL` | `86400` | Fast cache TTL (seconds) |

## HTTP API

- `POST /api/v1/repos/scan` — deep scan (repository_analysis suite)
- `GET /api/v1/analysis/fleet` — multi-dimensional fleet analysis (also depot-archived)

## Related

- MCD hub: [mcp-central-docs/projects/analysis/](https://github.com/sandraschi/mcp-central-docs/tree/main/projects/analysis)
- Diagnostics: [diagnostics.md](diagnostics.md)
