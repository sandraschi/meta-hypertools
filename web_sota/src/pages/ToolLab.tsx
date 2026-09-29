import { AlertTriangle, CheckCircle, FlaskConical, Loader, Play } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api, isSuccessResponse } from "../api/client";
import { DynamicForm } from "../components/common/DynamicForm";
import { JsonView } from "../components/common/JsonView";
import type { ToolWithServer } from "./Tools";

interface ToolLabPageProps {
  tools: ToolWithServer[];
}

const CATEGORIES: { id: string; label: string }[] = [
  { id: "all", label: "All" },
  { id: "heartbeat", label: "Heartbeat" },
  { id: "fleet", label: "Fleet / probe" },
  { id: "scheduler", label: "Scheduler" },
  { id: "meta", label: "Meta / help" },
  { id: "scaffold", label: "Scaffolding" },
];

function matchesCategory(name: string, cat: string): boolean {
  if (cat === "all") return true;
  if (cat === "heartbeat") return name.startsWith("heartbeat_");
  if (cat === "fleet") {
    return (
      name.startsWith("probe_") ||
      name.includes("fleet") ||
      name === "generate_fleet_starts_launcher" ||
      name === "open_fleet_starts_launcher"
    );
  }
  if (cat === "scheduler") return name.startsWith("scheduler_");
  if (cat === "meta") {
    return name.startsWith("meta_") || ["help", "help_tools", "meta_mcp_help"].includes(name);
  }
  if (cat === "scaffold") return name.startsWith("create_");
  return true;
}

export function ToolLabPage({ tools }: ToolLabPageProps) {
  const [search, setSearch] = useState("");
  const [cat, setCat] = useState("all");
  const [selected, setSelected] = useState<ToolWithServer | null>(null);
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [jsonParams, setJsonParams] = useState("{}");
  const [mode, setMode] = useState<"form" | "json">("form");
  const [running, setRunning] = useState(false);
  const [out, setOut] = useState<unknown>(null);
  const [err, setErr] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    return tools.filter((t) => {
      if (!matchesCategory(t.name, cat)) return false;
      if (!q) return true;
      return t.name.toLowerCase().includes(q) || (t.description || "").toLowerCase().includes(q);
    });
  }, [tools, cat, search]);

  useEffect(() => {
    if (selected) {
      setParams({});
      setJsonParams("{}");
      setOut(null);
      setErr(null);
      setMode("form");
    }
  }, [selected]);

  const run = async () => {
    if (!selected) return;
    setRunning(true);
    setErr(null);
    setOut(null);
    try {
      let finalParams: Record<string, unknown> = params;
      if (mode === "json") {
        finalParams = JSON.parse(jsonParams) as Record<string, unknown>;
      }
      const resp = await api.executeTool(selected.server, selected.name, finalParams);
      if (isSuccessResponse(resp)) {
        setOut(resp.result ?? resp.data);
      } else {
        setErr(resp.message || "Execution failed");
      }
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const schema = selected?.parameters ?? {};

  return (
    <div className="space-y-6 h-full flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="glass-panel p-8 relative overflow-hidden bg-white/[0.01] border-white/5 flex items-start gap-6">
        <div className="p-4 rounded-2xl bg-purple-600/10 border border-purple-600/20 text-purple-400">
          <FlaskConical size={36} />
        </div>
        <div>
          <h1 className="text-3xl font-black mb-2 bg-gradient-to-r from-white via-white to-white/40 bg-clip-text text-transparent">
            Tool Lab
          </h1>
          <p className="text-[#94a3b8] max-w-2xl">
            Pick a registered Meta MCP tool, fill parameters from JSON Schema, and run against the
            in-process server (same as{" "}
            <code className="text-blue-400/80">POST /api/v1/tools/execute</code>).
          </p>
        </div>
      </div>

      <div className="flex flex-col xl:flex-row gap-6 flex-1 min-h-0">
        <div className="xl:w-[380px] flex flex-col gap-4 glass-panel p-5 bg-white/[0.02] border-white/5 shrink-0">
          <input
            type="text"
            placeholder="Search tools…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-slate-500 outline-none focus:ring-1 focus:ring-[#bd00ff]/50"
          />
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setCat(c.id)}
                className={`text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 rounded-lg border transition-colors ${
                  cat === c.id
                    ? "bg-purple-600/20 border-purple-600/40 text-white"
                    : "bg-black/20 border-white/10 text-[#888] hover:text-white"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-y-auto min-h-[200px] max-h-[55vh] space-y-1 pr-1">
            {filtered.map((t) => (
              <button
                key={t.name}
                type="button"
                onClick={() => setSelected(t)}
                className={`w-full text-left px-3 py-2.5 rounded-xl text-sm border transition-colors ${
                  selected?.name === t.name
                    ? "bg-white/[0.08] border-blue-500/30 text-white"
                    : "bg-black/10 border-transparent text-slate-400 hover:border-white/10 hover:text-white"
                }`}
              >
                <div className="font-mono text-xs text-blue-400/90">{t.name}</div>
                <div className="text-[11px] text-slate-500 line-clamp-2 mt-0.5">
                  {t.description}
                </div>
              </button>
            ))}
            {filtered.length === 0 && (
              <p className="text-sm text-slate-500 text-center py-8">No tools match this filter.</p>
            )}
          </div>
        </div>

        <div className="flex-1 flex flex-col gap-4 glass-panel p-6 bg-white/[0.02] border-white/5 min-h-0">
          {!selected && (
            <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">
              Select a tool from the list to build a request.
            </div>
          )}
          {selected && (
            <>
              <div className="border-b border-white/5 pb-4">
                <h2 className="text-xl font-bold text-white font-mono">{selected.name}</h2>
                <p className="text-sm text-[#888] mt-2">{selected.description}</p>
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setMode("form")}
                  className={`text-xs font-bold uppercase px-3 py-1.5 rounded-lg border ${
                    mode === "form"
                      ? "bg-white/10 border-white/20 text-white"
                      : "border-transparent text-slate-500"
                  }`}
                >
                  Form
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMode("json");
                    setJsonParams(JSON.stringify(params, null, 2));
                  }}
                  className={`text-xs font-bold uppercase px-3 py-1.5 rounded-lg border ${
                    mode === "json"
                      ? "bg-white/10 border-white/20 text-white"
                      : "border-transparent text-slate-500"
                  }`}
                >
                  JSON
                </button>
              </div>

              <div className="flex-1 min-h-0 overflow-y-auto">
                {mode === "form" ? (
                  <DynamicForm schema={schema} value={params} onChange={setParams} />
                ) : (
                  <div className="flex-1 flex flex-col">
                    <label htmlFor="json-params-input" className="sr-only">
                      JSON Parameters
                    </label>
                    <textarea
                      id="json-params-input"
                      value={jsonParams}
                      onChange={(e) => setJsonParams(e.target.value)}
                      className="w-full h-full bg-black/40 border border-white/10 rounded-xl p-4 font-mono text-xs text-[#ccc]"
                    />
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-2 border-t border-white/5">
                <button
                  type="button"
                  onClick={run}
                  disabled={running}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-[#0066ff] text-white text-sm font-bold disabled:opacity-50"
                >
                  {running ? <Loader className="animate-spin" size={18} /> : <Play size={18} />}
                  Run tool
                </button>
              </div>

              {(out !== null || err) && (
                <div
                  className={`rounded-xl border p-4 ${
                    err
                      ? "bg-red-950/20 border-red-900/40"
                      : "bg-emerald-950/20 border-emerald-900/40"
                  }`}
                >
                  <div className="flex items-center gap-2 text-sm font-medium mb-2">
                    {err ? (
                      <span className="text-red-400 flex items-center gap-2">
                        <AlertTriangle size={16} /> Error
                      </span>
                    ) : (
                      <span className="text-emerald-400 flex items-center gap-2">
                        <CheckCircle size={16} /> Result
                      </span>
                    )}
                  </div>
                  {err ? (
                    <pre className="text-xs font-mono whitespace-pre-wrap overflow-x-auto text-[#ccc]">
                      {err}
                    </pre>
                  ) : (
                    <JsonView value={out} className="text-xs text-[#ccc]" />
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
