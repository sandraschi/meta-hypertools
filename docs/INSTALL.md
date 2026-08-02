# Install & run

Everything assumes the **repository root** as the working directory (where `pyproject.toml` lives).

## Prerequisites

- **Python** 3.10 or newer  
- **[uv](https://docs.astral.sh/uv/)** (recommended for installs and runs)

Optional: **Node.js** if you want to develop or build the web UI (`web_sota`).

## Install Python dependencies

```powershell
cd D:\Dev\repos\meta_mcp
uv sync --group dev
```

This installs the package and **dev** tools (e.g. Ruff). Use `uv sync` without `--group dev` if you only need runtime deps.

## Run the web dashboard (FastAPI)

The **`meta-mcp`** entry starts the API, serves the MCP HTTP app at **`/mcp`**, and (if built) static files from **`web_sota/dist`**.

```powershell
uv run meta-mcp
```

- Default URL is **`http://127.0.0.1:8000`** unless you set **`PORT`** / **`HOST`**.  
- Fleet convention in this workspace: backend **`10718`** — e.g. `$env:PORT='10718'; uv run meta-mcp`  
- Open **Tool Lab** in the sidebar to call tools interactively.

### Frontend dev (Vite)

```powershell
Set-Location web_sota
npm install
npm run dev
```

Vite listens on **10719** and proxies **`/api`** and **`/mcp`** to **10718**. Build the production bundle with `npm run build` (output: `web_sota/dist`).

## Native desktop (Tauri + installer)

Ship a **Windows installer** with embedded Python backend (no runtime deps for end users):

```powershell
uv sync --group dev
just build-native
```

Installer output: `native/target/release/bundle/nsis/MetaMCP_*-setup.exe`

Full pipeline, sidecar lifecycle, and troubleshooting: **[docs/TAURI.md](TAURI.md)**.

## Run the MCP server (stdio) for IDEs

For Cursor, Claude Desktop, Claude Code, etc., use the **stdio** server:

```powershell
uv run meta-mcp-server
```

You should see tool suites registering in the log. Stop with **Ctrl+C**.

### Cursor

In your MCP config, point **`cwd`** at this repo root and run **`meta-mcp-server`** via **`uv`**:

```json
{
  "mcpServers": {
    "meta-mcp": {
      "command": "uv",
      "args": ["run", "meta-mcp-server"],
      "cwd": "/path/to/meta-mcp"
    }
  }
}
```

Adjust **`cwd`** to your clone path. Restart the IDE after changing MCP config.

### Claude Desktop

Use the same idea as Cursor: **`uv`** + **`run`** + **`meta-mcp-server`** with **`cwd`** set to the repo root.

## Useful commands ([justfile](../justfile))

| Command | Meaning |
|---------|---------|
| `just sync` | `uv sync --group dev` |
| `just run` | `uv run meta-mcp` |
| `just web-dev` | Vite dev server in `web_sota` |
| `just web-build` | Production frontend build |
| `just fix` | Ruff fix + format on `src` |
| `just tools` | Print registered MCP tool names |

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| **`meta-mcp-server` not found** | Run from repo root: `uv run meta-mcp-server` |
| **Tools missing in IDE** | Fully restart the IDE; confirm **`cwd`** is the repo root |
| **Web UI empty / 404** | Run `npm run build` in `web_sota` or use `npm run dev` for development |
| **Port in use** | Set **`PORT`** to another value or free the port |

For architecture and API details, see [ARCHITECTURE.md](ARCHITECTURE.md).
