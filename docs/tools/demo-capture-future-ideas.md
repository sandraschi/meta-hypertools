# Demo capture — future ideas

**Status:** Not scheduled. Core pipeline is shipped — see [demo-capture.md](demo-capture.md).

---

## Remotion polish

- Animated cursor overlay (not just raw Playwright video under title card)
- Scene transitions between routes (fade/slide)
- Subtitle track from `video_steps` labels
- Optional voiceover via Remotion `<Audio>` (record separately, sync in composition)

## CI / fleet

- `npx remotion render` on tag push (public repos only — no private GitHub Actions per fleet policy)
- Gallery page linking per-repo screencasts (host TBD — not MCD root TODO)

## Screencast types (when recording fleet-wide)

| Type | Length | Content |
|------|--------|---------|
| Dashboard tour | 15s | Sidebar → KPIs → one tool call |
| Tool walkthrough | 30s | Params → run → output |
| Wrapped-app showcase | 45s | CAD/host app visible result |
| Full workflow | 60s | Multi-step export flow |

**Test drive candidate:** kicad-mcp or freecad-mcp (high visual payoff).

## License note

Remotion commercial use may require company license — [remotion.dev/license](https://www.remotion.dev/docs/license).
