# MetaMCP Repository

Fleet MCP orchestrator: scaffolding, analysis, runtime, diagnostics, repo inspiration, cold-start and cold-install probes, routing, harness generation.

## Commands

```powershell
uv sync --group dev
uv run ruff check src/
uv run ruff check src/ --fix
uv run ruff format src/
uv run pytest tests/ -v
just serve        # uvicorn on :10718
just mcp-stdio    # stdio MCP mode
```

## Ports

- Backend: 10718
- Frontend dev: 10719
