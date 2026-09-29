import { useState, type ReactNode } from "react";

type Mode = "pretty" | "raw";
const MODE_KEY = "metamcp_jsonview_mode";

/** Split pretty JSON into colored spans (keys / strings / numbers / literals). */
function highlight(json: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const re =
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g;
  let last = 0;
  let i = 0;
  for (const m of json.matchAll(re)) {
    if (m.index > last) parts.push(json.slice(last, m.index));
    const tok = m[0];
    let cls = "text-purple-300"; // number
    if (tok.startsWith('"')) cls = /:\s*$/.test(tok) ? "text-blue-300" : "text-amber-200";
    else if (tok === "true" || tok === "false") cls = "text-orange-300";
    else if (tok === "null") cls = "text-slate-500";
    parts.push(
      <span key={i++} className={cls}>
        {tok}
      </span>,
    );
    last = m.index + tok.length;
  }
  if (last < json.length) parts.push(json.slice(last));
  return parts;
}

export function JsonView({
  value,
  className = "",
}: {
  /** Object to render, or a string (JSON auto-detected; plain text passes through). */
  value: unknown;
  className?: string;
}) {
  const [mode, setMode] = useState<Mode>(() => {
    try {
      return localStorage.getItem(MODE_KEY) === "raw" ? "raw" : "pretty";
    } catch {
      return "pretty";
    }
  });

  const setStoredMode = (m: Mode) => {
    setMode(m);
    try {
      localStorage.setItem(MODE_KEY, m);
    } catch {
      // ignore localstorage errors
    }
  };

  const text = typeof value === "string" ? value : JSON.stringify(value ?? null, null, 2);
  let parsed: unknown = null;
  let isJson = typeof value !== "string";
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value);
      isJson = true;
    } catch {
      isJson = false;
    }
  } else {
    parsed = value ?? null;
  }

  if (!isJson) {
    return <pre className={`whitespace-pre-wrap font-mono ${className}`}>{text}</pre>;
  }

  const pretty = JSON.stringify(parsed, null, 2);
  const raw = JSON.stringify(parsed);

  return (
    <div className="min-w-0">
      <div className="flex items-center justify-end gap-1 mb-1.5">
        <div className="flex rounded-md border border-slate-700 overflow-hidden text-[11px]">
          <button
            type="button"
            onClick={() => setStoredMode("pretty")}
            aria-label="Pretty JSON view"
            className={`px-2 py-0.5 transition-colors ${mode === "pretty" ? "bg-blue-600/30 text-blue-200" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}
          >
            Pretty
          </button>
          <button
            type="button"
            onClick={() => setStoredMode("raw")}
            aria-label="Raw JSON view"
            className={`px-2 py-0.5 transition-colors ${mode === "raw" ? "bg-blue-600/30 text-blue-200" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}
          >
            Raw
          </button>
        </div>
      </div>
      {mode === "pretty" ? (
        <pre className={`whitespace-pre-wrap font-mono overflow-x-auto ${className}`}>
          {highlight(pretty)}
        </pre>
      ) : (
        <pre className={`whitespace-pre-wrap font-mono overflow-x-auto ${className}`}>{raw}</pre>
      )}
    </div>
  );
}
