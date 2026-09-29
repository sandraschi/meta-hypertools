import { useCallback, useEffect, useState } from "react";

const BACKEND_URL =
  (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_BASE_URL ||
  "http://127.0.0.1:10718";

const BACKOFFS = [1000, 2000, 4000, 8000, 16000];

/** Backend connection dot: Tauri event when available, backoff HTTP poll otherwise. */
export function BackendDot() {
  const [ok, setOk] = useState<boolean | null>(null);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch(`${BACKEND_URL}/health`);
      setOk(r.ok);
    } catch {
      setOk(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;
    const poll = async () => {
      if (cancelled) return;
      await refresh();
      attempt += 1;
      timer = setTimeout(poll, BACKOFFS[Math.min(attempt, BACKOFFS.length - 1)]);
    };
    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [refresh]);

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        unlisten = await listen<string>("backend-status", (event) => {
          if (event.payload === "ready") setOk(true);
          else if (typeof event.payload === "string" && event.payload.startsWith("error:")) setOk(false);
        });
      } catch {
        // dev browser - HTTP polling handles it
      }
    })();
    return () => {
      if (unlisten) unlisten();
    };
  }, []);

  return (
    <span
      className="inline-flex items-center gap-1.5 text-[11px] text-slate-300"
      data-testid="backend-dot"
      title={ok === null ? "Connecting to backend..." : ok ? "Backend connected" : "Backend offline"}
    >
      <span
        className={`w-2 h-2 rounded-full ${ok === null ? "bg-slate-500 animate-pulse" : ok ? "bg-green-500" : "bg-red-500"}`}
      />
      {ok === null ? "Connecting" : ok ? "Connected" : "Offline"}
    </span>
  );
}
