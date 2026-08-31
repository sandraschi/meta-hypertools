# Tauri NSIS Wrapper - `scaffold_ops(operation="tauri_nsis")`

Adds a native Windows desktop wrapper to an existing MCP repo. Tauri 2.0,
single NSIS installer, embedded backend - no Electron.

## Usage

```python
scaffold_ops(operation="tauri_nsis", repo_root="D:/Dev/repos/my-mcp", repo_name="my-mcp")

# Legacy alias
create_tauri_nsis(repo_root="D:/Dev/repos/my-mcp")
```

## What you get

- `native/` (or `web_sota/src-tauri/`) with:
  - `Cargo.toml` - Tauri 2.0, shell/fs/process plugins
  - `tauri.conf.json` - embedded backend via `bundle.resources`
    (NOT `externalBin`), NSIS target, `.env.example` bundled, not `.env`
  - `build.rs`, `src/main.rs`, `capabilities/default.json`
  - `build-sidecar.ps1` - PyInstaller pipeline (spec at repo root)
- The backend exe is materialized into `%LOCALAPPDATA%` cache and spawned
  as a child process at launch

## The full native pipeline

```
just build-native     # frontend build -> PyInstaller -> Rust -> NSIS
just cua-nsis-test    # install -> launch -> nav walk -> uninstall (cert)
```

See [../TAURI.md](../TAURI.md) for the complete NSIS build rules and
pitfalls (CORS origins, size gates, kill hooks, `noarchive=True`).

## Limits

- **`repo_root` required** - the wrapper is added to an existing repo,
  not generated standalone.
- **Build toolchain needed**: Rust + MSVC + Tauri CLI on the build
  machine. The wrapper is generated; the build is on you.
- **MCP reachable only while the app runs** - the embedded backend serves
  `/mcp` only when the operator is up (documented in installer copy).
- **WebView2 assumed present** (`webviewInstallMode: skip`); adjust for
  offline Win10 targets.
