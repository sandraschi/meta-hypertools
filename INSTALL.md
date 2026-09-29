# Installation

## 🚀 Quick Start (recommended)

```powershell
# Install just if you don't have it
winget install Casey.Just    # Windows
# scoop install just          # Windows (alternative)
# brew install just           # macOS
# sudo apt install just       # Debian/Ubuntu
# cargo install just          # Linux (Rust)

git clone https://github.com/sandraschi/meta_mcp
cd meta_mcp
just
```

The interactive recipe dashboard opens in your browser. From there:

```powershell
just bootstrap   # install all dependencies
just serve       # start the server
just web         # start the frontend (if applicable)
```

> **Why not `pip install`?** MCP servers bundle webapps, configs, project scaffolding, and tooling that a flat Python package can't deliver. PyPI offers no safety advantage — it doesn't audit packages either. `just` gives you the complete, ready-to-run stack.

---

## 🐌 Traditional Setup

If you prefer not to use `just`:

1. Install [Python 3.13+](https://python.org) and [uv](https://docs.astral.sh/uv/)
2. Clone and enter the repo:
   ```powershell
   git clone https://github.com/sandraschi/meta_mcp
   cd meta_mcp
   ```
3. Install dependencies:
   ```powershell
   uv sync --all-extras
   ```
4. Start the server:
   ```powershell
   # stdio mode (for MCP clients like Claude Desktop)
   uv run meta-mcp-server

   # HTTP mode (for web dashboard)
   uv run uvicorn meta_mcp.server:app --port 10718
   ```
5. Open `http://localhost:10718` or the frontend URL.

---

## Desktop app (no dev stack needed)

Download `Meta Hypertools_0.5.1_x64-setup.exe` from
[Releases](https://github.com/sandraschi/meta-hypertools/releases) and run
it. The installer bundles the dashboard plus its own backend on port
11220, so it runs side by side with a dev stack on 10718/10719. First
launch seeds `.env` from the bundled example. Build it yourself with
`just build-native`; details in [docs/TAURI.md](docs/TAURI.md).

---

## ❓ Troubleshooting

| Issue | Fix |
|---|---|
| `just` not found | Install via `winget install Casey.Just`, `scoop install just`, or `brew install just` |
| Port conflict | Run `just kill-all` to clear fleet ports (10700–11000) |
| Dependencies out of sync | `uv sync --all-extras` |
| Something else | [Open a GitHub issue](https://github.com/sandraschi/meta_mcp/issues) |

---

*See the main [README](README.md) for feature overview and documentation.

---

## Legacy Documentation

_This INSTALL.md was updated with the standard fleet Quick Start template. The original instructions are preserved below._

# Installation

The installation guide lives here:

**[docs/INSTALL.md](docs/INSTALL.md)**

That page covers `uv`, the web dashboard, stdio MCP for Cursor/Claude, ports, and troubleshooting.
