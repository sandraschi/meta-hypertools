# meta-mcp native build log

Running record for Tauri/NSIS builds (required by the NSIS build gate).
Newest entry first.

## 2026-09-29 - operator port move (11220)

Review note: the operator backend used the dev port 10718, so the
installed app and the dev stack could never run side by side (and the
operator's free_port would kill dev). Claimed `meta-mcp-native`
11219/11220 via claim_ports.py (registered in WEBAPP_PORTS.md); operator
backend now spawns on 11220 with the frontend baked to match, CSP
updated, dev default untouched. Rebuilt + re-uploaded below.

Phase 1 audit (TAURI_PRODUCTION_PITFALLS A-J) before building:

- A ports/naming: backend 10718, `META_MCP_TAURI=1` + `PORT` spawn env,
  bundle id `com.sandraschi.meta-mcp`, binaries `meta-mcp-native.exe` /
  `meta-mcp-backend.exe`, currentUser install. OK.
- B frontend: `VITE_API_BASE_URL` set at build time by `build.ps1`;
  client falls back to relative in dev (Vite proxy). CSP connect-src
  covers 127.0.0.1:10718. `label: main` matches capabilities.
- C backend CORS: tauri origins + unconditional regex already present.
  `/health` public (auth middleware only guards fleet/analysis paths).
- D run_server.py: no chdir, frozen env-to-args translation, eager
  `_datetime`/`_strptime`/`mcp.types`, dual-mode stdio/HTTP.
- E spec: upx=False, noarchive=True, pathex src+mcpb, datas package,
  hiddenimports incl. joserfc + pydantic + cachetools + key_value,
  dist-info keep list with separator-prefixed match, SKIP list.
- F/G backend.rs + main.rs from the fixed 2026-09-17 fleet template:
  resources-first resolution, unconditional materialize copy (no version
  cache), self-PID exclusion in free_port, child kill on exit.
- H build.ps1: tsc gate, Step-0 API port check, vite build, venv
  pyinstaller, frozen smoke (/health + chat/context), 5MB size gate,
  resources embed, stale-exe cleanup, tauri nsis, dist staging.
- I hooks.nsh kills BOTH exes pre-install/pre-uninstall; skip WebView2.
- J stdio/HTTP: frozen env translation in run_server; no stdio hijack in
  backend main; `META_MCP_TAURI` set (reserved for future gating).

Result: GREEN 2026-09-29 ~16:15.

- Frontend: tsc clean, vite build with VITE_API_BASE_URL=http://127.0.0.1:10718.
- PyInstaller: dist/meta-mcp-backend.exe 31.9 MB. New failure modes fixed
  along the way (all in-repo fixes, kept): collect_all 2-tuple TOC
  normalization; mcp/fastmcp/pydantic/email-validator/opentelemetry
  dist-info keep list (underscore variant for opentelemetry_api);
  tomli mypyc hashed runtime; docket + burner_redis for FastMCP tasks;
  OTEL runtime hook; smoke poll loop (boot takes ~60s).
- Frozen smoke: /health 200 + /api/v1/chat/context 200 on ephemeral port,
  no traceback/module errors.
- Tauri NSIS: dist/Meta Hypertools_0.5.1_x64-setup.exe, 34.2 MB,
  currentUser, WebView2 skip, kill-both-exes hooks, CSP connect-src set.
- resources/: meta-mcp-backend.exe + .env.example only (no .env, no flat
  target/release shadow).
- Phase 6 install-verify DEFERRED: this machine's dev backend owns port
  10718 and the operator's free_port would kill it. Needs a clean box
  (or stopped dev stack) for install/launch/uninstall + backend-spawn.log
  + UI route check. Do not call this installer verified until then.
