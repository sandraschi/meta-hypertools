# Privacy and sensitive data

MetaMCP is a **local operator tool**. It does not run a multi-user cloud service or store end-user accounts. Still, several features read or write data that can identify you or expose secrets.

## What stays on your machine

| Location | Contents |
|----------|----------|
| `~/.meta_mcp/fleet/` | Probe manifests, JSON reports, progress files |
| `~/.meta_mcp/analysis/` | Analysis depot runs and cache |
| `~/.meta_mcp_toolchains.json` | Toolchain profiles |
| `data/tasks.json` | Scheduler state (gitignored; copy from `data/tasks.example.json`) |
| IDE config paths | Discovered under `%AppData%`, `~/.config`, etc. |

Fleet probe logs may include **absolute paths** and **console output** from child processes. Treat reports as sensitive if your apps log tokens or personal paths.

## Tools that can expose secrets

These read files on disk; output may include API keys, tokens, or paths unless you redact first:

- Client discovery and `export_cursor_mcp_snippet`
- `tail_log_file` (IDE log directories)
- `diff_mcp_configs` / toolchain apply (MCP JSON configs)
- Fleet cold-start probe dirty-log capture
- `pack_repository_for_ai` / repo scans of your working tree

Use **`redact_secrets_audit`** to scan a file for suspicious key/token lines (redacted previews only).

## Heartbeat and host identity

`heartbeat_pulse` includes a **node** field (hostname by default). Set `META_MCP_NODE_LABEL=local` (or any label) in `.env` to avoid emitting your machine name in pulse JSON or scheduler history.

## Environment variables

| Variable | Privacy note |
|----------|----------------|
| `WURST_AUTH_TOKEN` | Required for protected API routes when enforcement is on; never commit |
| `GITHUB_TOKEN` | Used for repo inspiration; keep in `.env` only |
| `REPOS_DIR` | Reveals your dev layout in tool output if echoed |
| `META_MCP_NODE_LABEL` | Optional hostname substitute in pulse data |

## Before sharing artifacts

- Do not commit `.env`, `data/tasks.json`, or `~/.meta_mcp/**` exports
- Scrub probe reports and analysis depot dumps before attaching to issues or PRs
- Rotate tokens if a log or report may have captured them

## Author metadata in the repo

`LICENSE` and package metadata may list a maintainer name. That is standard for open source and is not user PII collected by the application.
