import { motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCopy,
  Clock,
  Download,
  FileJson,
  FileText,
  Loader2,
  Play,
  RefreshCw,
  Rocket,
  Search,
  Sparkles,
  Square,
  Terminal,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

const API = "/api/v1/fleet/ops";

type OpParam = {
  name: string;
  label: string;
  kind: string;
  default: string | boolean;
  placeholder?: string;
  hint?: string;
  options?: { value: string; label: string }[];
};

type OpScript = {
  id: string;
  name: string;
  category?: string;
  description: string;
  danger?: string;
  params: OpParam[];
};

type OpJob = {
  id: string;
  script_id: string;
  name: string;
  status: string;
  exit_code: number | null;
  started_at: number;
  finished_at: number | null;
  command: string;
  log_tail?: string;
};

type ReportRow = { name: string; kind: string; size: number; mtime: number };

function fmtDuration(started: number, finished: number | null): string {
  const end = finished ? finished : Date.now() / 1000;
  const sec = Math.max(0, Math.floor(end - started));
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  return `${min}m ${sec % 60}s`;
}

function fmtAge(ts: number): string {
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (s < 90) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 90) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
}

function fmtBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    running:
      "bg-blue-500/20 text-blue-300 border border-blue-500/40 shadow-[0_0_10px_rgba(59,130,246,0.3)]",
    done: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40",
    failed: "bg-red-500/20 text-red-300 border border-red-500/40",
    killed: "bg-amber-500/20 text-amber-300 border border-amber-500/40",
  };
  return (
    <span
      className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
        styles[status] ?? "bg-slate-800 text-slate-300 border border-slate-700"
      }`}
    >
      {status}
    </span>
  );
}

export function FleetOps() {
  const [scripts, setScripts] = useState<OpScript[]>([]);
  const [jobs, setJobs] = useState<OpJob[]>([]);
  const [reports, setReports] = useState<ReportRow[]>([]);
  const [formValues, setFormValues] = useState<Record<string, Record<string, string | boolean>>>(
    {},
  );
  const [expandedJob, setExpandedJob] = useState<string | null>(null);
  const [runningIds, setRunningIds] = useState<Set<string>>(new Set());
  const [preview, setPreview] = useState<{ name: string; kind: string; content: string } | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [copyOk, setCopyOk] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [reportSearch, setReportSearch] = useState("");
  const [jsonParsed, setJsonParsed] = useState<unknown | null>(null);

  const fetchCatalog = useCallback(async () => {
    try {
      const r = await fetch(`${API}/catalog`);
      const j = (await r.json()) as { data?: { scripts?: OpScript[] } };
      const list = j.data?.scripts ?? [];
      setScripts(list);
      setFormValues((prev) => {
        const next = { ...prev };
        for (const s of list) {
          if (!next[s.id]) {
            next[s.id] = {};
            for (const p of s.params) next[s.id][p.name] = p.default;
          }
        }
        return next;
      });
    } catch {
      setError("Catalog unavailable - is the meta-mcp backend running?");
    }
  }, []);

  const fetchJobs = useCallback(async () => {
    try {
      const r = await fetch(`${API}/jobs`);
      const j = (await r.json()) as { data?: { jobs?: OpJob[] } };
      const list = j.data?.jobs ?? [];
      setJobs(list);
      setRunningIds(new Set(list.filter((j2) => j2.status === "running").map((j2) => j2.id)));
    } catch {
      /* backend restarting */
    }
  }, []);

  const fetchReports = useCallback(async () => {
    try {
      const r = await fetch(`${API}/reports`);
      const j = (await r.json()) as { data?: { reports?: ReportRow[] } };
      setReports(j.data?.reports ?? []);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetchCatalog();
    fetchJobs();
    fetchReports();
    const t = setInterval(() => {
      fetchJobs();
      if (runningIds.size === 0) fetchReports();
    }, 3000);
    return () => clearInterval(t);
  }, [fetchCatalog, fetchJobs, fetchReports, runningIds.size]);

  const setParam = useCallback((scriptId: string, name: string, value: string | boolean) => {
    setFormValues((prev) => ({
      ...prev,
      [scriptId]: { ...prev[scriptId], [name]: value },
    }));
  }, []);

  const runScript = useCallback(
    async (s: OpScript) => {
      setError(null);
      const params = formValues[s.id] ?? {};
      try {
        const r = await fetch(`${API}/jobs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ script_id: s.id, params }),
        });
        const j = (await r.json()) as {
          success?: boolean;
          message?: string;
          data?: { job?: OpJob };
        };
        if (!j.success) {
          setError(j.message ?? "Failed to start job");
          return;
        }
        if (j.data?.job?.id) setExpandedJob(j.data.job.id);
        await fetchJobs();
      } catch {
        setError("Failed to start job");
      }
    },
    [formValues, fetchJobs],
  );

  const killJob = useCallback(
    async (id: string) => {
      try {
        await fetch(`${API}/jobs/${id}/kill`, { method: "POST" });
        await fetchJobs();
      } catch {
        /* ignore */
      }
    },
    [fetchJobs],
  );

  const copyCommand = useCallback(
    async (s: OpScript) => {
      const params = formValues[s.id] ?? {};
      try {
        const r = await fetch(`${API}/jobs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ script_id: s.id, params }),
        });
        const j = (await r.json()) as { data?: { command?: string } };
        if (j.data?.command) {
          await navigator.clipboard.writeText(j.data.command);
          setCopyOk(s.id);
          setTimeout(() => setCopyOk(null), 2000);
        }
      } catch {
        /* ignore */
      }
    },
    [formValues],
  );

  const openReport = useCallback(async (name: string) => {
    try {
      const r = await fetch(`${API}/reports/${name}`);
      const j = (await r.json()) as { data?: { name: string; kind: string; content: string } };
      if (j.data) {
        setPreview(j.data);
        if (j.data.kind === "json") {
          try {
            setJsonParsed(JSON.parse(j.data.content));
          } catch {
            setJsonParsed(null);
          }
        } else {
          setJsonParsed(null);
        }
      }
    } catch {
      /* ignore */
    }
  }, []);

  const downloadReport = useCallback(() => {
    if (!preview) return;
    const blob = new Blob([preview.content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = preview.name;
    a.click();
    URL.revokeObjectURL(url);
  }, [preview]);

  const categories = useMemo(() => {
    const cats = new Set<string>();
    for (const s of scripts) {
      if (s.category) cats.add(s.category);
    }
    return ["all", ...Array.from(cats)];
  }, [scripts]);

  const filteredScripts = useMemo(() => {
    return scripts.filter((s) => {
      const matchesCat = selectedCategory === "all" || s.category === selectedCategory;
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.id.toLowerCase().includes(q);
      return matchesCat && matchesSearch;
    });
  }, [scripts, selectedCategory, searchQuery]);

  const filteredReports = useMemo(() => {
    if (!reportSearch.trim()) return reports;
    const q = reportSearch.toLowerCase().trim();
    return reports.filter((r) => r.name.toLowerCase().includes(q));
  }, [reports, reportSearch]);

  const activeCount = runningIds.size;

  // JSON Elucidation Stats
  const jsonSummary = useMemo(() => {
    if (!jsonParsed || typeof jsonParsed !== "object") return null;
    const obj = jsonParsed as Record<string, unknown>;
    const keys = Object.keys(obj);
    let totalCount = 0;
    let passedCount = 0;
    let failedCount = 0;

    if (Array.isArray(obj.results) || Array.isArray(obj.webapps) || Array.isArray(obj.servers)) {
      const items = (obj.results || obj.webapps || obj.servers) as Record<string, unknown>[];
      totalCount = items.length;
      passedCount = items.filter(
        (i) =>
          i.status === "ok" || i.status === "passed" || i.passed === true || i.success === true,
      ).length;
      failedCount = totalCount - passedCount;
    }

    return {
      topKeys: keys.slice(0, 8),
      totalCount,
      passedCount,
      failedCount,
    };
  }, [jsonParsed]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 select-none" data-testid="fleet-ops">
      {/* Top Banner & Header */}
      <div className="bg-[#0e0f18] border border-slate-800/90 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-[0_0_20px_rgba(59,130,246,0.5)] shrink-0">
              <Rocket className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-white tracking-tight">
                  Fleet Ops & Script Center
                </h1>
                {activeCount > 0 && (
                  <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/40 text-xs font-bold animate-pulse">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> {activeCount} running
                  </span>
                )}
              </div>
              <p className="text-slate-300 text-sm mt-1">
                Launch, monitor, and troubleshoot fleet-wide automation scripts with live progress
                and elucidated reports.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => {
                fetchCatalog();
                fetchJobs();
                fetchReports();
              }}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-sm transition-all border border-slate-700"
            >
              <RefreshCw className="w-4 h-4" /> Refresh All
            </button>
          </div>
        </div>

        {/* Global Quick Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-5 border-t border-slate-800/80">
          <div className="bg-[#141624] border border-slate-800 rounded-xl p-3.5">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Available Scripts
            </span>
            <p className="text-xl font-bold text-slate-100 mt-0.5">{scripts.length}</p>
          </div>
          <div className="bg-[#141624] border border-slate-800 rounded-xl p-3.5">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Active Jobs
            </span>
            <p className="text-xl font-bold text-blue-300 mt-0.5">{activeCount}</p>
          </div>
          <div className="bg-[#141624] border border-slate-800 rounded-xl p-3.5">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Completed Jobs
            </span>
            <p className="text-xl font-bold text-emerald-300 mt-0.5">
              {jobs.filter((j) => j.status === "done").length}
            </p>
          </div>
          <div className="bg-[#141624] border border-slate-800 rounded-xl p-3.5">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Generated Reports
            </span>
            <p className="text-xl font-bold text-purple-300 mt-0.5">{reports.length}</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="px-4 py-3 rounded-xl bg-red-500/15 border border-red-500/40 text-red-200 text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1">
          {categories.map((cat) => (
            <button
              type="button"
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`
                px-3.5 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider whitespace-nowrap transition-all
                ${
                  selectedCategory === cat
                    ? "bg-blue-600 text-white shadow-[0_0_12px_rgba(59,130,246,0.5)] font-black"
                    : "bg-slate-900/80 text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-800"
                }
              `}
            >
              {cat === "all" ? "All Scripts" : cat}
            </button>
          ))}
        </div>

        {/* Script Search */}
        <div className="relative min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search scripts & tools..."
            className="w-full pl-9 pr-3 py-1.5 bg-[#12131f] border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Script Catalog Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="ops-catalog">
        {filteredScripts.map((s) => (
          <motion.div
            key={s.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl border border-slate-800 bg-[#0f101a] p-5 flex flex-col justify-between hover:border-slate-700 transition-colors shadow-lg"
          >
            <div>
              <div className="flex items-start justify-between gap-3 mb-2">
                <div>
                  <h3 className="font-bold text-base text-slate-100">{s.name}</h3>
                  <span className="inline-block mt-0.5 px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-blue-300 border border-slate-700">
                    {s.category || "Fleet Operations"}
                  </span>
                </div>
                {s.danger && (
                  <span
                    className="flex items-center gap-1 text-amber-300 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded text-xs font-semibold shrink-0"
                    title={s.danger}
                  >
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Caution
                  </span>
                )}
              </div>

              <p className="text-slate-300 text-sm mb-4 leading-relaxed">{s.description}</p>

              {/* Form Parameters */}
              {s.params.length > 0 && (
                <div className="space-y-3 bg-[#151624] rounded-xl p-3.5 border border-slate-800/80 mb-4">
                  {s.params.map((p) => (
                    <div key={p.name}>
                      <label className="block text-xs font-bold text-slate-200 mb-1">
                        {p.label}
                        {p.hint && (
                          <span className="text-slate-400 font-normal ml-1.5 font-sans">
                            ({p.hint})
                          </span>
                        )}
                      </label>
                      {p.kind === "select" && (
                        <select
                          data-testid={`param-${s.id}-${p.name}`}
                          value={String(formValues[s.id]?.[p.name] ?? p.default)}
                          onChange={(e) => setParam(s.id, p.name, e.target.value)}
                          className="w-full px-3 py-2 rounded-lg bg-zinc-900 text-zinc-100 border border-zinc-700 text-sm focus:outline-none focus:border-blue-500"
                        >
                          {p.options?.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </select>
                      )}
                      {p.kind === "bool" && (
                        <label className="flex items-center gap-2.5 cursor-pointer py-1">
                          <input
                            type="checkbox"
                            data-testid={`param-${s.id}-${p.name}`}
                            checked={Boolean(formValues[s.id]?.[p.name] ?? p.default)}
                            onChange={(e) => setParam(s.id, p.name, e.target.checked)}
                            className="accent-blue-500 w-4 h-4 rounded"
                          />
                          <span className="text-sm font-medium text-slate-200">
                            {(formValues[s.id]?.[p.name] ?? p.default) ? "Enabled" : "Disabled"}
                          </span>
                        </label>
                      )}
                      {p.kind !== "select" && p.kind !== "bool" && (
                        <input
                          type={p.kind === "number" ? "number" : "text"}
                          data-testid={`param-${s.id}-${p.name}`}
                          value={String(formValues[s.id]?.[p.name] ?? p.default ?? "")}
                          placeholder={p.placeholder}
                          onChange={(e) => setParam(s.id, p.name, e.target.value)}
                          className="w-full px-3 py-2 rounded-lg bg-zinc-900 text-zinc-100 border border-zinc-700 text-sm placeholder-zinc-500 focus:outline-none focus:border-blue-500"
                        />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Run Actions */}
            <div className="flex items-center gap-2 pt-3 border-t border-slate-800/80">
              <button
                type="button"
                data-testid={`run-${s.id}`}
                onClick={() => runScript(s)}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold shadow-[0_0_15px_rgba(59,130,246,0.3)] transition-all"
              >
                <Play className="w-4 h-4 fill-current" /> Run Script
              </button>
              <button
                type="button"
                data-testid={`copy-${s.id}`}
                onClick={() => copyCommand(s)}
                className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-200 text-sm font-medium transition-colors"
                title="Copy full CLI invocation to clipboard"
              >
                {copyOk === s.id ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <ClipboardCopy className="w-4 h-4 text-slate-300" />
                )}
                <span>{copyOk === s.id ? "Copied" : "Copy CLI"}</span>
              </button>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Jobs & Reports Double Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" data-testid="ops-jobs">
        {/* Active & Historic Jobs */}
        <div className="rounded-2xl border border-slate-800 bg-[#0f101a] p-5 flex flex-col shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Terminal className="w-5 h-5 text-blue-400" />
              <h3 className="font-bold text-base text-slate-100">Live Process & Job Monitor</h3>
            </div>
            <span className="text-xs font-semibold text-slate-400">{jobs.length} jobs tracked</span>
          </div>

          {jobs.length === 0 && (
            <div className="py-12 text-center text-slate-400 text-sm">
              No active or past jobs in this session. Run a script above to see live progress.
            </div>
          )}

          <div className="space-y-3 max-h-[460px] overflow-y-auto no-scrollbar">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="rounded-xl bg-[#141624] border border-slate-800 p-4 space-y-2"
              >
                <div className="flex items-center gap-2.5 flex-wrap">
                  <StatusBadge status={job.status} />
                  <span className="text-sm font-bold text-slate-100">{job.name}</span>
                  <span className="text-xs font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                    {job.id}
                  </span>
                  <div className="flex items-center gap-1 text-xs text-slate-400 ml-auto">
                    <Clock className="w-3 h-3 text-slate-400" />
                    <span>{fmtDuration(job.started_at, job.finished_at)}</span>
                  </div>
                  {job.status === "running" && (
                    <button
                      type="button"
                      data-testid={`kill-${job.id}`}
                      onClick={() => killJob(job.id)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-red-500/20 text-red-300 border border-red-500/40 hover:bg-red-500/30 text-xs font-bold transition-colors"
                    >
                      <Square className="w-3 h-3 fill-current" /> Terminate
                    </button>
                  )}
                  <button
                    type="button"
                    data-testid={`log-${job.id}`}
                    onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                    className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                    title="Toggle Console Log Output"
                  >
                    {expandedJob === job.id ? (
                      <ChevronUp className="w-4 h-4" />
                    ) : (
                      <ChevronDown className="w-4 h-4" />
                    )}
                  </button>
                </div>

                {job.command && (
                  <p className="text-xs text-slate-400 font-mono bg-black/40 px-2 py-1 rounded truncate">
                    {job.command}
                  </p>
                )}

                {expandedJob === job.id && (
                  <div className="mt-2 space-y-1">
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>Log Tail ({job.status})</span>
                      <button
                        type="button"
                        onClick={() => navigator.clipboard.writeText(job.log_tail || "")}
                        className="text-blue-400 hover:underline flex items-center gap-1"
                      >
                        <ClipboardCopy className="w-3 h-3" /> Copy Log
                      </button>
                    </div>
                    <pre className="text-xs font-mono text-emerald-300 bg-black/80 border border-slate-800 rounded-lg p-3 overflow-x-auto max-h-60 overflow-y-auto whitespace-pre-wrap leading-relaxed shadow-inner">
                      {job.log_tail || "(waiting for initial stdout/stderr output...)"}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Reports Browser & Elucidation */}
        <div
          className="rounded-2xl border border-slate-800 bg-[#0f101a] p-5 flex flex-col shadow-xl"
          data-testid="ops-reports"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-400" />
              <h3 className="font-bold text-base text-slate-100">Reports & Artifact Elucidator</h3>
            </div>
            <button
              type="button"
              onClick={fetchReports}
              className="text-xs font-bold text-slate-200 hover:text-white border border-slate-700 bg-slate-800 rounded-lg px-2.5 py-1 transition-colors"
            >
              Refresh Reports
            </button>
          </div>

          <div className="relative mb-3">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={reportSearch}
              onChange={(e) => setReportSearch(e.target.value)}
              placeholder="Search reports by filename..."
              className="w-full pl-9 pr-3 py-1.5 bg-[#141624] border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:border-purple-500"
            />
          </div>

          {filteredReports.length === 0 && (
            <div className="py-12 text-center text-slate-400 text-sm">
              No reports generated yet. Run a fleet probe or audit script to produce report
              artifacts.
            </div>
          )}

          <div className="space-y-1.5 max-h-[460px] overflow-y-auto no-scrollbar">
            {filteredReports.map((rep) => (
              <button
                type="button"
                key={rep.name}
                data-testid={`report-${rep.name}`}
                onClick={() => openReport(rep.name)}
                className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-[#141624] hover:bg-slate-800/80 border border-slate-800/80 text-left transition-all group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {rep.kind === "json" ? (
                    <div className="p-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 shrink-0">
                      <FileJson className="w-4 h-4" />
                    </div>
                  ) : (
                    <div className="p-1.5 rounded-lg bg-blue-500/15 border border-blue-500/30 text-blue-400 shrink-0">
                      <FileText className="w-4 h-4" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <span className="text-sm font-semibold text-slate-100 group-hover:text-white truncate block">
                      {rep.name}
                    </span>
                    <span className="text-xs text-slate-400">{fmtBytes(rep.size)}</span>
                  </div>
                </div>
                <span className="text-xs text-slate-400 shrink-0 ml-3 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                  {fmtAge(rep.mtime)}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Report Elucidation Modal */}
      {preview && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6"
          onClick={() => setPreview(null)}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-[#0f101a] border border-slate-700/80 rounded-2xl w-full max-w-5xl max-h-[88vh] flex flex-col shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#141624]">
              <div className="flex items-center gap-3 min-w-0">
                {preview.kind === "json" ? (
                  <FileJson className="w-5 h-5 text-emerald-400 shrink-0" />
                ) : (
                  <FileText className="w-5 h-5 text-blue-400 shrink-0" />
                )}
                <div>
                  <h3 className="text-base font-bold text-white truncate">{preview.name}</h3>
                  <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">
                    Elucidated {preview.kind.toUpperCase()} Artifact
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => navigator.clipboard.writeText(preview.content)}
                  className="flex items-center gap-1.5 text-xs font-semibold text-slate-200 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 hover:bg-slate-700 transition-colors"
                >
                  <ClipboardCopy className="w-3.5 h-3.5" /> Copy Raw
                </button>
                <button
                  type="button"
                  onClick={downloadReport}
                  className="flex items-center gap-1.5 text-xs font-semibold text-blue-200 bg-blue-600/30 border border-blue-500/40 rounded-lg px-3 py-1.5 hover:bg-blue-600/50 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" /> Download
                </button>
                <button
                  type="button"
                  onClick={() => setPreview(null)}
                  className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors ml-2"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* High-Level Elucidation Summary for JSON */}
            {preview.kind === "json" && jsonSummary && jsonSummary.totalCount > 0 && (
              <div className="px-6 py-3 bg-[#181a2e] border-b border-slate-800 flex items-center gap-4 flex-wrap">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Summary Analysis:
                </span>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-200 font-semibold border border-slate-700">
                  Total Items: {jsonSummary.totalCount}
                </span>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/40">
                  Passed / Healthy: {jsonSummary.passedCount}
                </span>
                {jsonSummary.failedCount > 0 && (
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-red-500/20 text-red-300 font-semibold border border-red-500/40">
                    Failed / Issues: {jsonSummary.failedCount}
                  </span>
                )}
              </div>
            )}

            {/* Modal Body */}
            <div className="overflow-auto p-6 flex-1 bg-[#0b0c14]">
              {preview.kind === "md" ? (
                <div className="prose prose-invert max-w-none text-slate-200 text-sm leading-relaxed space-y-4">
                  <ReactMarkdown>{preview.content}</ReactMarkdown>
                </div>
              ) : (
                <pre className="text-xs font-mono text-emerald-300 bg-black/90 rounded-xl p-4 overflow-x-auto whitespace-pre-wrap leading-relaxed border border-slate-800 shadow-inner">
                  {(() => {
                    try {
                      return JSON.stringify(JSON.parse(preview.content), null, 2);
                    } catch {
                      return preview.content;
                    }
                  })()}
                </pre>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}

export default FleetOps;
