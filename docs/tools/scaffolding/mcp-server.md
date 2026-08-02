# MCP Server Builder - `scaffold_ops(operation="mcp_server")`

The flagship maker. Generates a complete FastMCP 3.4+ server repository
that passes the New Repo Gate on day one - no runt iterations.

## What you get

A self-contained repo with:

- `pyproject.toml` with FastMCP 3.4+ floor + committed `uv.lock`
- `justfile` with discoverable recipes (`serve`, `lint`, `test`, `mcpb-pack`)
- `llms.txt` + `llms-full.txt` (LLM discovery corpus)
- `glama.json` (registry manifest)
- MCPB packaging layout: `manifest.json`, `assets/icon.png`,
  `assets/prompts/` at the **3-4-100 gate** (system 3000+ words,
  user 4000+ words, examples 100+)
- `.github/workflows/ci.yml` (uv + ruff + pytest)
- README with Quick Start + INSTALL
- Example tools: portmanteau pattern, `Annotated[Field]` parameters,
  `## Return Format` + `## Examples` docstrings
- Prefab UI surface for list/status tools (`prefab-ui>=0.14.0`)
- pytest scaffold that boots the app and checks health

## Usage

```python
# MCP - the minimum
scaffold_ops(operation="mcp_server", name="weather-mcp",
             description="Weather forecast server")

# MCP - with a webapp and packaging
scaffold_ops(operation="mcp_server", name="weather-mcp",
             description="Weather forecast server",
             include_frontend=True, backend_port=11210, frontend_port=11211)

# Dashboard
Builders page -> MCP Server card -> fill Project Name + Output Path -> Create Project
```

## Generated structure

```
weather-mcp/
├── pyproject.toml          # FastMCP 3.4.4+, uv
├── uv.lock
├── justfile
├── llms.txt / llms-full.txt
├── glama.json
├── README.md / INSTALL.md
├── .github/workflows/ci.yml
├── src/weather_mcp/
│   ├── server.py           # FastMCP app + example tools
│   └── skills/weather_mcp/SKILL.md
├── tests/test_server.py    # health + tools smoke
├── assets/                 # icon.png + prompts (3-4-100)
└── manifest.json           # MCPB layout
```

## After scaffolding

```powershell
cd weather-mcp
just bootstrap && just lint && just test
just mcpb-pack              # Claude Desktop bundle
```

Then register ports in `WEBAPP_PORTS.md` and wire the server into your
IDE with `server_ops(operation="register")`.

## Limits

- **`name` is required** - missing it returns
  `{"success": false, "error": "name required for mcp_server"}`.
- **No host-app integration is generated** - wrapping Blender/GIMP/etc.
  still needs the host lifecycle design (see the wrapper standard).
- **The example tools are placeholders** - replace them with your domain
  tools; the structure around them is the deliverable.
- **Prefab coverage is scaffolded as guidance** - the generated repo
  includes the dependency and pattern, but you must add the actual
  `ToolResult`/`PrefabApp` surfaces per tool.
- **`uv sync` needs network** on first run (package resolution).
