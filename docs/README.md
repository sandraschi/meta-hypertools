# Meta MCP — documentation

Start here, then jump to the guide you need.

## Quick reference

| Tool pattern | Description |
|-------------|-------------|
| `scaffold_ops` | Generate projects (MCP servers, fullstack apps, landing pages, games) |
| `fleet_ops` | Fleet lifecycle (status, launch, stop, probes) |
| `analysis_ops` | SOTA compliance, runt detection, depot |
| `diagnostics_ops` | Tool discovery, unicode/pwsh/justfile validation |
| `server_ops` | MCP server start/stop/list/status |
| `heartbeat_ops` | Health pulse, ping, liveness |
| `client_ops` | IDE config read/update/add/remove |
| `meta_dev_ops` | Diff, snippet, orphan detection, env check |
| `token_ops` | File/dir token analysis, context limits |
| `scheduler_ops` | Background task scheduling |
| `toolchain_ops` | Toolchain presets |
| `pack_ops` | Repository packing for LLM |
| `discovery_ops` | Server discovery, IDE audit |
| `inspire_repo` | Study public GitHub repos without cloning |
| `harness_analyze` / `harness_generate` / `harness_refine` | FastMCP server generation from source analysis |
| `fleet_config_audit` | Scan fleet for agent/discovery config files |

## Guides

| Guide | Description |
|-------|-------------|
| [INSTALL.md](INSTALL.md) | Prerequisites, `uv`, web dashboard, Cursor / Claude, ports |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, transports, REST vs MCP, static UI |
| [TOOLS.md](TOOLS.md) | Tool suites at a glance + deep links |
| [tools/repo-inspiration.md](tools/repo-inspiration.md) | Public GitHub study (`inspire_repo`; credit [Repomuse](https://www.npmjs.com/package/repomuse)) |

## Detailed tool suites

Per-domain pages live under **[tools/](tools/README.md)** (scaffolding, fleet, diagnostics, meta_dev, etc.).
Harness generation methodology (CLI-Anything adaptation): [tools/harness-generation.md](tools/harness-generation.md)

## Project references

| File | Purpose |
|------|---------|
| [CHANGELOG.md](../CHANGELOG.md) | Version history |
| [PRD.md](../PRD.md) | Product requirements |
| [justfile](../justfile) | Common commands (`just sync`, `just run`, …) |

## Security & advanced topics

- [PRIVACY.md](PRIVACY.md) — local data, secrets, hostname scrub
- [DYNAMIC_SECURITY_PLAN_TODO.md](DYNAMIC_SECURITY_PLAN_TODO.md)
- [SUPPLY_CHAIN_SCANNER_NOTES_2026-03.md](SUPPLY_CHAIN_SCANNER_NOTES_2026-03.md)
- [schemas/SCANNER_ADAPTER_CONTRACT.md](schemas/SCANNER_ADAPTER_CONTRACT.md)
- [DEV_SANDBOX_HARDENING_PROFILE.md](DEV_SANDBOX_HARDENING_PROFILE.md)
