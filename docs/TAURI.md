# Tauri 2.0 native desktop app

MetaMCP ships a **Tauri 2.0** wrapper that bundles:

- **Rust shell** — WebView2 window, process lifecycle
- **React dashboard** — `web_sota/dist` (Vite production build)
- **Python backend** — PyInstaller one-file sidecar (`meta_mcp-backend.exe`)

End users install a single **NSIS `.exe`** (or MSI) — no Python, Node.js, or `uv` required on the target machine.

## Prerequisites (build machine only)

| Tool | Purpose |
|------|---------|
| [Rust](https://rustup.rs/) | Tauri compile (`cargo`) |
| [Node.js](https://nodejs.org/) | Vite frontend + `@tauri-apps/cli` |
| [uv](https://docs.astral.sh/uv/) | Python deps + PyInstaller |
| WebView2 | Runtime on Windows (usually preinstalled on Win11) |

```powershell
winget install Rustlang.Rustup
winget install OpenJS.NodeJS.LTS
# uv: see https://docs.astral.sh/uv/
```

## One-command release build

```powershell
cd D:\Dev\repos\meta_mcp
uv sync --group dev
just build-native
```

Pipeline (`native/build.ps1`):

1. **Frontend** — `web_sota` via `npm run build` (`tsc` + Vite) with `VITE_API_BASE_URL=http://127.0.0.1:10718`
2. **Icons** — `scripts/generate-tauri-icon.ps1` → `npx tauri icon`
3. **Sidecar** — `native/build-sidecar.ps1` → PyInstaller via `meta_mcp-backend.spec`
4. **Tauri** — `npx tauri build` → NSIS + MSI + portable exe

### Output paths

| Artifact | Typical path |
|----------|----------------|
| **NSIS installer** | `native/target/release/bundle/nsis/MetaMCP_0.3.0_x64-setup.exe` |
| **MSI** | `native/target/release/bundle/msi/MetaMCP_0.3.0_x64_en-US.msi` |
| **Portable exe** | `native/target/release/meta-mcp-native.exe` |
| **Sidecar (intermediate)** | `native/binaries/meta_mcp-backend-x86_64-pc-windows-msvc.exe` |

Version strings follow `native/tauri.conf.json` and `native/Cargo.toml` (numeric only — WiX/MSI rejects `-beta` suffixes; Python package may still be `0.3.0-beta`).

## Architecture

```
Tauri window (WebView2)
  ↓ loads bundled React (custom protocol / frontendDist)
  ↓ fetch http://127.0.0.1:10718/api/*
PyInstaller sidecar (meta_mcp-backend.exe)
  ↓ FastAPI + MCP HTTP bridge
MetaMCP Python stack (meta_mcp package)
```

### Sidecar lifecycle

- On app start, Rust spawns `meta_mcp-backend --http --port 10718` via Tauri **externalBin**
- Stdout is watched for `Uvicorn running` / `Application startup complete`
- Frontend receives `backend-status: ready` when the API is up
- On app exit, the sidecar child process is killed

Configured in:

- `native/tauri.conf.json` → `bundle.externalBin`
- `native/src/main.rs` → `sidecar("meta_mcp-backend")`

## Partial builds

```powershell
# Sidecar only (PyInstaller)
just tauri-sidecar

# Tauri dev — Vite :10719, stub sidecar if not built yet
just tauri-dev

# Debug bundle (faster, larger)
just build-native-debug
```

## PyInstaller spec

`meta_mcp-backend.spec` at repo root:

- Entry: `run_server.py` (requires `--http`)
- Packages: `collect_submodules("meta_mcp")`
- Output: `dist/meta_mcp-backend.exe` (one-file)

Sidecar copy step renames to `native/binaries/meta_mcp-backend-x86_64-pc-windows-msvc.exe` (Tauri target-triple convention).

## Dev vs production API URL

| Mode | Frontend | API |
|------|----------|-----|
| **Vite dev** (`npm run dev`) | `:10719` | Proxied to `:10718` |
| **Tauri dev** (`just tauri-dev`) | `:10719` via `devUrl` | Sidecar or host `uv run meta-mcp` |
| **Tauri release** | Bundled static | `VITE_API_BASE_URL` baked as `http://127.0.0.1:10718` |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `sidecar error` / missing binary | Run `just tauri-sidecar` or full `just build-native` |
| `icons/icon.ico` missing | `pwsh scripts/generate-tauri-icon.ps1` then `npx tauri icon native/icons/icon.png` |
| PyInstaller import errors | Add module to `hiddenimports` in `meta_mcp-backend.spec` |
| Blank UI, API errors | Confirm sidecar log shows Uvicorn on 10718; check WebView2 |
| Rust not found | `$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"` |

## CI / releases (manual today)

1. `just build-native` on a Windows builder
2. Upload `native/target/release/bundle/nsis/*-setup.exe` to GitHub Releases
3. Optional: attach MSI alongside the MCPB package

Future: `.github/workflows/native.yml` with `tauri-apps/tauri-action` + `uv` + PyInstaller.

## Related docs

- [INSTALL.md](INSTALL.md) — Python/uv install path
- [ARCHITECTURE.md](ARCHITECTURE.md) — FastAPI + MCP server layout
- [fleet FLEET_PROBE_ARCHITECTURE.md](fleet/FLEET_PROBE_ARCHITECTURE.md) — Phase 7 Tauri probe (planned)
