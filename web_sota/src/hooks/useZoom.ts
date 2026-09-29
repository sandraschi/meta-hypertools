import { useCallback, useEffect, useState } from "react";

const ZOOM_LEVELS = [0.8, 1.0, 1.25, 1.5, 2.0, 3.0];
const ZOOM_KEY = "tauri-zoom";

/** Ctrl+scroll zoom ladder (Tauri setZoom, CSS fallback in dev browser). */
export function useZoom() {
  const [, setZoomIndex] = useState(() => {
    try {
      const saved = localStorage.getItem(ZOOM_KEY);
      const idx = saved ? ZOOM_LEVELS.indexOf(Number.parseFloat(saved)) : 1;
      return idx >= 0 ? idx : 1;
    } catch {
      return 1;
    }
  });

  const applyZoom = useCallback(async (level: number) => {
    try {
      localStorage.setItem(ZOOM_KEY, String(level));
    } catch {
      // ignore localstorage errors
    }
    try {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      const win = getCurrentWindow() as unknown as { setZoom?: (n: number) => Promise<void> };
      if (typeof win.setZoom === "function") {
        await win.setZoom(level);
        return;
      }
    } catch {
      // dev browser - fall through to CSS zoom
    }
    document.documentElement.style.zoom = String(level);
  }, []);

  useEffect(() => {
    const handler = (e: WheelEvent) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      setZoomIndex((prev) => {
        const next =
          e.deltaY < 0
            ? Math.min(prev + 1, ZOOM_LEVELS.length - 1)
            : Math.max(prev - 1, 0);
        if (next !== prev) void applyZoom(ZOOM_LEVELS[next]);
        return next;
      });
    };
    window.addEventListener("wheel", handler, { passive: false });
    try {
      const saved = localStorage.getItem(ZOOM_KEY);
      if (saved) void applyZoom(Number.parseFloat(saved));
    } catch {
      // ignore
    }
    return () => window.removeEventListener("wheel", handler);
  }, [applyZoom]);
}
