# 📊 Repository Intelligence Suite

**Deep codebase analysis and health assessment.**

Surpassing simple linting, this suite provides a holistic health check for repositories, analyzing structure, standards compliance, and overall "fitness" for the MCP ecosystem.

## Tools

### `scan_repository_deep`
Perform a comprehensive scan of a target repository.
- **Analysis**: Folder structure, file types, size distribution, and key files.
- **Args**: `repo_path` (str), `deep_analysis` (bool)

### `get_repo_status`
Retrieve a high-level status summary.
- **Metrics**: Git status, recent activity, primary languages.
- **Args**: `repo_path` (str)

### `analyze_runts` (Runt Analyzer)
Specialized analysis for identifying "runt" repositories—legacy or incomplete projects needing upgrades.
- **Features**: Detects missing SOTA standards, old patterns, and "zombie" files.
- **Args**: `scan_path` (str)

## Metrics & Scoring
The suite calculates a **Health Score (0-100)** based on:
1. **Structure**: Presence of standardized docs (README, PRD, CHANGELOG).
2. **Compliance**: FastMCP usage, correct dependencies (`pyproject.toml`).
3. **Quality**: Code complexity, documentation coverage, test existence.
4. **Safety**: Unicode safety (hex escapes) and correct logging patterns.

## Use Cases
- **Auditing**: Quickly assess the state of a new project.
- **CI/CD**: Gate deployments based on minimum health scores.
- **Upgrading**: Identify exactly what's missing to bring a legacy repo to 2026 standards.

## Remote GitHub inspiration

For **public repos you do not have locally** (OSS reference architectures), use the **[Repository Inspiration](repo-inspiration.md)** suite (`inspire_repo_*`) — ported from [Repomuse](https://www.npmjs.com/package/repomuse). This suite is for **local path** intelligence only.
