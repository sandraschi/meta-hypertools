# Demo capture (`demo_ops`)

Fleet webapp demo pipeline in **meta_mcp**: remote-start a webapp, record a Playwright walkthrough, optionally render a polished MP4 with **Remotion**. No OBS, no CUA, no manual screen recording.

Suite registered as **`demo_capture`**. Primary tool: **`demo_ops`** (portmanteau).

Legacy aliases: `generate_demo_script`, `demo_capture_help`.

---

## Why this exists

| Need | Solution |
|------|----------|
| README / YouTube product demos | Scripted Playwright navigation → `.webm` + PNGs |
| Repeatable CI-friendly capture | Same `config.json` every run |
| Polished MP4 with title card | Remotion post-production |
| NSSM-backed fleet services | Reuse live backend; start Vite only (`-FrontendOnly`) |

Static screenshots show *what* the UI looks like. A 30-second screencast shows *what it does* — especially for wrapper MCPs (KiCad, Inkscape, Blender) where the flow matters.

---

## Architecture

```text
demo_ops(plan)
    └─ scan App.tsx routes + data-testid → config.json

demo_ops(record)
    ├─ ensure stack (reuse or start.ps1 -Headless -NoBrowser)
    ├─ wait backend + frontend health
    ├─ Playwright (demo-screenshots.ts, demo-video.ts)
    └─ artifacts: PNG, .webm, trace.zip

demo_ops(render)  [optional]
    ├─ copy .webm → scripts/screencast/public/source.webm
    ├─ npm install (@remotion/cli, remotion, …)  [first run only]
    └─ npx remotion render → docs/screenshots/{repo}-demo.mp4
```

**Bundled templates** (shipped inside meta_mcp, no mcp-central-docs required at runtime):

| Path | Purpose |
|------|---------|
| `src/meta_mcp/demo_capture_templates/` | Playwright specs, `capture.ps1`, `playwright.demo.config.ts` |
| `src/meta_mcp/demo_capture_templates/remotion/` | Remotion project (composition, title overlay, `render.ps1`) |

Handbook copy (optional): `mcp-central-docs/templates/demo-capture/` — Playwright-only; meta_mcp extends it with Remotion and MCP orchestration.

---

## MCP tool reference

### `demo_ops`

```python
await demo_ops(
    operation="plan" | "record" | "render" | "health" | "help",
    app_id="inkscape-mcp",  # fleet manifest id
    repo_path="D:\\Dev\\repos\\inkscape-mcp",  # alternative to app_id
    description="Show dashboard and tools page",
    screenshots=True,
    video=True,
    start_if_needed=True,
    timeout_sec=90,
    render_mp4=False,  # record: chain Remotion after Playwright
    video_path=None,  # render: explicit .webm path
    title=None,  # render: title card (default: "{repo} — Fleet Demo")
    subtitle="",
)
```

| Operation | Description |
|-----------|-------------|
| `help` | Pipeline overview, prerequisites, output paths |
| `plan` | Build `config.json` from routes, ports, NL description |
| `record` | Start/reuse stack + Playwright capture |
| `render` | Remotion: `.webm` → MP4 (standalone or after record) |
| `health` | Poll manifest backend + frontend until ready |

### Return shape

Standard meta_mcp response:

```json
{
  "success": true,
  "operation": "record",
  "message": "Demo capture completed for inkscape-mcp",
  "data": {
    "repo": "inkscape-mcp",
    "e2e_dir": ".../web_sota/e2e",
    "output_dir": ".../docs/screenshots",
    "artifacts": {
      "screenshots": [".../dashboard.png"],
      "videos": [".../demo-test-results/.../video.webm"],
      "traces": [".../demo-trace.zip"],
      "mp4": [".../docs/screenshots/inkscape-mcp-demo.mp4"]
    },
    "playwright": { "returncode": 0 },
    "remotion": { "..." }
  }
}
```

---

## Per-repo file layout (materialized on first run)

After `record`:

```text
{repo}/
  web_sota/e2e/                    # or webapp/e2e
    config.json                    # ports, pages, video_steps
    demo-screenshots.ts
    demo-video.ts
    playwright.demo.config.ts
    demo-test-results/             # Playwright output (.webm)
  docs/screenshots/
    *.png                          # full-page screenshots
    demo-trace.zip
```

After `render`:

```text
{repo}/
  scripts/screencast/
    package.json
    tsconfig.json
    screencast.config.json
    screencast.props.json          # title/subtitle passed to Remotion
    public/source.webm
    src/
      index.ts
      Root.tsx
      DemoComposition.tsx
    node_modules/                  # created by npm install (first render)
  docs/screenshots/
    {repo}-demo.mp4
```

Nothing is committed automatically — agents or developers commit artifacts when ready.

---

## Prerequisites

### One-time (machine)

```powershell
npx playwright install chromium
```

Node.js 18+ with `npm` / `npx` on PATH.

### Per repo

- Webapp under `web_sota/`, `webapp/`, or `webapp/frontend/` with `package.json`
- `start.ps1` with `$BackendPort` / `$FrontendPort` (or fleet manifest entry)
- Recommended: `data-testid` on dashboard and KPI elements for stable selectors

### First Remotion render per repo

`demo_ops(render)` runs `npm install` in `scripts/screencast/` (~30s). Subsequent renders reuse `node_modules/`.

---

## Usage examples

### Plan only (inspect config before recording)

```python
await demo_ops(operation="plan", app_id="inkscape-mcp", description="Dashboard, then animation studio presets")
```

### Record walkthrough (Playwright only)

```python
await demo_ops(
    operation="record", app_id="inkscape-mcp", description="Show dashboard and tools page", screenshots=True, video=True
)
```

### Full pipeline (Playwright + Remotion MP4)

```python
await demo_ops(
    operation="record",
    app_id="inkscape-mcp",
    render_mp4=True,
    title="Inkscape MCP",
    subtitle="SVG validate and optimize from the dashboard",
)
```

### Render existing capture

```python
await demo_ops(
    operation="render",
    app_id="inkscape-mcp",
    video_path=r"D:\Dev\repos\inkscape-mcp\web_sota\e2e\demo-test-results\...\video.webm",
    title="Inkscape MCP Tour",
)
```

### Manual PowerShell (without MCP)

Playwright only:

```powershell
Set-Location D:\Dev\repos\inkscape-mcp\web_sota\e2e
pwsh .\capture.ps1 -Screenshots -Video
```

Remotion only (after `source.webm` is in place):

```powershell
Set-Location D:\Dev\repos\inkscape-mcp\scripts\screencast
pwsh .\render.ps1 -Title "Inkscape MCP" -Subtitle "Dashboard tour"
```

---

## Stack startup behavior

| Scenario | Behavior |
|----------|----------|
| Backend + frontend already healthy | Reuse (no restart) |
| Cold start | `start.ps1 -Headless -NoBrowser` |
| Manifest has `nssmService` | `-FrontendOnly` (keep NSSM backend, start Vite only) |
| Health timeout | `timeout_sec` (default 90s) on backend HTTP + frontend TCP |

Implementation: `DemoCaptureService.ensure_stack()` + `FleetRuntimeService.start_app()`.

---

## Config format (`config.json`)

Generated by `plan` / materialized into `{frontend}/e2e/config.json`:

```json
{
  "backend_port": 11028,
  "frontend_port": 11029,
  "health_path": "/api/health",
  "output_dir": "../../docs/screenshots",
  "pages": [
    { "route": "/", "selector": "[data-testid='dashboard']", "name": "Dashboard" }
  ],
  "video_steps": [
    { "action": "goto", "url": "/" },
    { "action": "wait", "ms": 2000 },
    { "action": "goto", "url": "/tools" },
    { "action": "wait_selector", "selector": "[data-testid='tools-panel']" }
  ]
}
```

Supported `video_steps` actions: `goto`, `wait`, `wait_selector`, `click`, `fill`.

NL `description` keywords map to routes: `animat`, `layer`, `tool`, `setting`, `status`, `log`, `help`, `chat`.

---

## Remotion composition

Default composition id: **`DemoComposition`**.

- Full-frame `<Video>` from `public/source.webm`
- Title card overlay (fade in/out, first ~2.5s)
- Duration auto-detected via `@remotion/media-utils` `getVideoMetadata()`
- Output: H.264 MP4, 1280×720 (from source video dimensions when available)

Customize by editing `{repo}/scripts/screencast/src/DemoComposition.tsx` after first materialization.

**License:** [Remotion](https://remotion.dev) is FOSS; commercial use may require a company license — check remotion.dev/license for your setup.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `npx not found` | Install Node.js, ensure on PATH |
| Frontend timeout on record | Increase `timeout_sec`; check Vite port in manifest |
| `No Playwright .webm found` on render | Run `record` with `video=True` first, or pass `video_path` |
| Remotion `npm install` fails | Run manually in `scripts/screencast/`; check network |
| Empty dashboard in video | Stack not ready — use `health` op first or increase timeout |
| NSSM backend killed by smoke/probe | Unrelated — probe should skip service PIDs; use `reuse_existing` |

---

## Code map

| File | Role |
|------|------|
| `tools/registries/demo_capture.py` | MCP tool registration (`demo_ops`) |
| `services/demo_capture_service.py` | Orchestration (start, Playwright, Remotion) |
| `utils/demo_capture_config.py` | Route scan, config builder |
| `services/fleet_runtime_service.py` | `start_app()` with headless / frontend-only / health wait |
| `demo_capture_templates/` | Playwright + Remotion templates |
| `tests/test_demo_capture.py` | Unit tests |

---

## Related docs

- Playwright-only handbook template: `mcp-central-docs/templates/demo-capture/README.md`
- Fleet manifest ports: `mcp-central-docs/operations/WEBAPP_PORTS.md`
- Future ideas (not scheduled): [demo-capture-future-ideas.md](demo-capture-future-ideas.md)
