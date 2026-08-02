# Scaffolding Suite

**Professional project generation.**

Rapidly bootstrap new MCP servers, applications, and tools using battle-tested templates that enforce professional standards from day one.

## Tools

### `scaffold_ops(operation='spec_kit')` — Spec Kit (SDD)
Integrate GitHub's Spec-Driven Development toolkit. Scaffolds a project with `/speckit.*`
slash commands for structured planning. See [spec-kit-integration.md](../spec-kit-integration.md).
- **Args**: `project_name` (str), `output_path` (str), `features.ai_integration` (str: opencode/claude/copilot/cursor/gemini)
- **Default AI**: opencode

### `create_mcp_server`
Generate a new MCP server project.
- **Features**: FastMCP setup, `pyproject.toml`, Docker config, CI/CD workflows, and professional structure (`src/`, `tests/`).
- **Args**: `name` (str), `description` (str), `author` (str)

### `create_fullstack_app`
Scaffold a modern web application with MCP integration.
- **Stack**: FastAPI (backend) + React/Vite (frontend).
- **Args**: `config` (dict)

### `create_landing_page`
Generate a high-conversion landing page.
- **Features**: Tailwind CSS, responsive design, AI-optimized copy placeholders.
- **Args**: `config` (dict)

### `create_webshop`
Scaffold an e-commerce platform foundation.
- **Args**: `config` (dict)

### `create_game`
Bootstrap a web-based game project.
- **Args**: `config` (dict)

## Philosophy
- **"Batteries Included"**: Templates come with linting (Ruff), formatting, and testing already set up.
- **SOTA by Default**: Updates to templates immediately propagate SOTA standards (e.g., Unicode safety) to new projects.
