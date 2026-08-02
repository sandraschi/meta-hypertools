import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Download,
  Loader2,
  RefreshCw,
  Search,
  Terminal,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

const API = "/api/logs";

interface LogEntry {
  id: string;
  timestamp: string;
  level: string;
  kind: string;
  detail: string;
  meta?: Record<string, unknown>;
}

interface LogsQueryResult {
  entries: LogEntry[];
  total: number;
  limit: number;
  offset: number;
  max_entries: number;
  sort: string;
}

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: "text-purple-400",
  INFO: "text-blue-400",
  WARNING: "text-yellow-400",
  ERROR: "text-red-400",
};

export function LogsPage() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [level, setLevel] = useState("");
  const [kind, setKind] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"desc" | "asc">("desc");
  const [liveTail, setLiveTail] = useState(false);
  const [kinds, setKinds] = useState<string[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const [userScrolled, setUserScrolled] = useState(false);
  const [clearing, setClearing] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  const fetchLogs = useCallback(
    async (opts?: { append?: boolean }) => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        params.set("limit", String(limit));
        params.set("offset", String(opts?.append ? 0 : offset));
        params.set("sort", sort);
        if (level) params.set("level", level);
        if (kind) params.set("kind", kind);
        if (search) params.set("search", search);

        const res = await fetch(`${API}?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: LogsQueryResult = await res.json();
        setEntries(data.entries);
        setTotal(data.total);
        if (opts?.append && data.entries.length > 0) {
          setUserScrolled(false);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load logs");
      } finally {
        setLoading(false);
      }
    },
    [limit, offset, level, kind, search, sort],
  );

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API}/stats`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.kinds) {
        setKinds(Object.keys(data.kinds).sort());
      }
    } catch {
      // non-critical
    }
  }, []);

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, [fetchLogs, fetchStats]);

  useEffect(() => {
    if (!liveTail) return;
    const interval = setInterval(async () => {
      try {
        const lastId = entries.length > 0 ? entries[0].id : "";
        if (!lastId) {
          fetchLogs();
          return;
        }
        const params = new URLSearchParams();
        params.set("limit", String(limit));
        params.set("after_id", lastId);
        params.set("sort", "desc");
        if (level) params.set("level", level);
        if (kind) params.set("kind", kind);
        if (search) params.set("search", search);
        const res = await fetch(`${API}?${params}`);
        if (!res.ok) return;
        const data: LogsQueryResult = await res.json();
        if (data.entries.length > 0) {
          setEntries((prev) => {
            const merged = [...data.entries, ...prev].slice(0, 500);
            return merged;
          });
          setTotal((prev) => prev + data.entries.length);
          if (!userScrolled) {
            scrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
          }
        }
      } catch {
        // silent
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [liveTail, limit, level, kind, search, sort, entries, userScrolled, fetchLogs]);

  const handleSearch = (val: string) => {
    setSearch(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {}, 300);
  };

  const handleClear = async () => {
    if (!confirm("Clear all log entries? This cannot be undone.")) return;
    setClearing(true);
    try {
      const res = await fetch(API, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setEntries([]);
      setTotal(0);
      setOffset(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to clear logs");
    } finally {
      setClearing(false);
    }
  };

  const handleExport = async (format: "json" | "csv") => {
    const params = new URLSearchParams();
    params.set("format", format);
    if (level) params.set("level", level);
    if (kind) params.set("kind", kind);
    if (search) params.set("search", search);
    try {
      const res = await fetch(`${API}/export?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `metamcp-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / limit));
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="space-y-6 pb-12">
      <header className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h2 className="text-3xl font-black text-white flex items-center gap-3">
            <Terminal className="text-blue-400" size={28} />
            Logs
          </h2>
          <p className="text-white/60 text-sm mt-1">
            Tool calls, exports, server events — {total} entries (max {2000})
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <button
            type="button"
            onClick={() => setLiveTail(!liveTail)}
            className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all border flex items-center gap-2 ${
              liveTail
                ? "bg-green-500/20 border-green-500/30 text-green-400"
                : "bg-white/5 border-white/10 text-white/60 hover:text-white"
            }`}
          >
            {liveTail && <Loader2 size={12} className="animate-spin" />}
            {liveTail ? "LIVE" : "Tail"}
          </button>
          <button
            type="button"
            onClick={() => handleExport("json")}
            className="px-3 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-white/60 text-xs font-black uppercase tracking-widest flex items-center gap-1.5"
          >
            <Download size={14} /> JSON
          </button>
          <button
            type="button"
            onClick={() => handleExport("csv")}
            className="px-3 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-white/60 text-xs font-black uppercase tracking-widest flex items-center gap-1.5"
          >
            <Download size={14} /> CSV
          </button>
          <button
            type="button"
            onClick={handleClear}
            disabled={clearing || total === 0}
            className="px-3 py-2 rounded-xl border border-red-500/20 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs font-black uppercase tracking-widest flex items-center gap-1.5 disabled:opacity-40"
          >
            <Trash2 size={14} /> {clearing ? "Clearing..." : "Clear"}
          </button>
          <button
            type="button"
            onClick={() => fetchLogs()}
            className="p-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </header>

      {error && (
        <div className="glass-panel p-4 border-red-500/30 text-red-300 text-sm flex gap-2">
          <AlertTriangle size={18} /> {error}
        </div>
      )}

      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={16} />
          <input
            type="text"
            placeholder="Search log detail..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-xl py-2 pl-10 pr-4 text-sm text-white focus:outline-none focus:border-blue-500/50 transition-all"
          />
        </div>
        <select
          value={level}
          onChange={(e) => {
            setLevel(e.target.value);
            setOffset(0);
          }}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50"
        >
          <option value="">All levels</option>
          <option value="DEBUG">DEBUG</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
        </select>
        <select
          value={kind}
          onChange={(e) => {
            setKind(e.target.value);
            setOffset(0);
          }}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50 min-w-[120px]"
        >
          <option value="">All kinds</option>
          {kinds.map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => setSort(sort === "desc" ? "asc" : "asc")}
          className="px-3 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-white/60 text-xs font-black uppercase tracking-widest flex items-center gap-1.5"
        >
          {sort === "desc" ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          {sort === "desc" ? "Newest" : "Oldest"}
        </button>
        <select
          value={limit}
          onChange={(e) => {
            setLimit(Number(e.target.value));
            setOffset(0);
          }}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none"
        >
          <option value={25}>25/page</option>
          <option value={50}>50/page</option>
          <option value={100}>100/page</option>
          <option value={200}>200/page</option>
        </select>
      </div>

      <div
        ref={scrollRef}
        onScroll={() => {
          if (scrollRef.current && scrollRef.current.scrollTop < -30) setUserScrolled(true);
        }}
        className="glass-panel p-0 overflow-auto max-h-[600px] font-mono text-xs"
      >
        {loading && entries.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-white/40">
            <Loader2 className="animate-spin mr-2" size={18} /> Loading...
          </div>
        ) : entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-white/40">
            <Terminal size={32} className="mb-2 opacity-40" />
            <p>No log entries match current filters</p>
          </div>
        ) : (
          entries.map((entry) => (
            <div
              key={entry.id}
              className="flex gap-3 px-4 py-1.5 border-b border-white/5 hover:bg-white/[0.02] transition-colors items-start"
            >
              <span
                className={`shrink-0 w-16 text-[10px] font-bold ${LEVEL_COLORS[entry.level] || "text-white/40"}`}
              >
                {entry.level}
              </span>
              <span className="shrink-0 text-[10px] text-white/30 w-36">
                {entry.timestamp ? entry.timestamp.slice(11, 23) : ""}
              </span>
              <span className="shrink-0 text-[10px] text-white/25 w-20 truncate" title={entry.kind}>
                {entry.kind}
              </span>
              <span className="break-all text-white/80 min-w-0 flex-1">{entry.detail}</span>
            </div>
          ))
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-white/40">
        <span>
          {total} entries (page {currentPage} of {totalPages})
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={offset <= 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
            className="px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 disabled:opacity-30 text-white/60"
          >
            Previous
          </button>
          <button
            type="button"
            disabled={offset + limit >= total}
            onClick={() => setOffset(offset + limit)}
            className="px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 disabled:opacity-30 text-white/60"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
