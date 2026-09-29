import { motion } from "framer-motion";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  ExternalLink,
  FileText,
  RefreshCw,
  Search,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, isSuccessResponse } from "../api/client";

interface ReportEntry {
  repo: string;
  timestamp: { timestamp?: string; commit?: string; score?: number } | null;
  latest_report: {
    report_date?: string;
    score?: number;
    preview?: string;
    report_path?: string;
  } | null;
}

interface StatsData {
  total_assessed: number;
  total_with_reports: number;
  average_score: number | null;
  min_score: number | null;
  max_score: number | null;
}

type FilterMode = "all" | "reports" | "needs-work" | "no-report";
type SortMode = "name-asc" | "name-desc" | "score-desc" | "score-asc" | "date-desc" | "date-asc";

const PAGE_SIZE = 20;

function entryScore(e: ReportEntry): number | null {
  return e.latest_report?.score ?? e.timestamp?.score ?? null;
}

function entryDate(e: ReportEntry): string {
  return e.latest_report?.report_date ?? e.timestamp?.timestamp?.slice(0, 10) ?? "";
}

function scoreBadge(score: number): string {
  if (score >= 80) return "bg-green-500/15 text-green-400";
  if (score >= 60) return "bg-amber-500/15 text-amber-400";
  return "bg-red-500/15 text-red-400";
}

export function AssessReportsPage() {
  const [entries, setEntries] = useState<ReportEntry[]>([]);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterMode>("all");
  const [sort, setSort] = useState<SortMode>("name-asc");
  const [page, setPage] = useState(1);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const listResp = await api.executeTool("metaops", "assess_reports_ops", {
        operation: "list",
      });
      if (isSuccessResponse(listResp)) {
        const data = (listResp.result ?? listResp.data) as {
          reports?: ReportEntry[];
        };
        setEntries(data?.reports ?? []);
      } else {
        setError("Failed to load assess reports list");
      }

      const statsResp = await api.executeTool("metaops", "assess_reports_ops", {
        operation: "stats",
      });
      if (isSuccessResponse(statsResp)) {
        const data = (statsResp.result ?? statsResp.data) as StatsData;
        setStats(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load assess reports");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const rows = entries.filter((e) => {
      if (needle && !e.repo.toLowerCase().includes(needle)) return false;
      const score = entryScore(e);
      if (filter === "reports" && !e.latest_report) return false;
      if (filter === "no-report" && e.latest_report) return false;
      if (filter === "needs-work" && (score == null || score >= 60)) return false;
      return true;
    });
    const byScoreNullsLast = (a: ReportEntry, b: ReportEntry) => {
      const sa = entryScore(a);
      const sb = entryScore(b);
      if (sa == null && sb == null) return a.repo.localeCompare(b.repo);
      if (sa == null) return 1;
      if (sb == null) return -1;
      return sb - sa;
    };
    const byDate = (desc: boolean) => (a: ReportEntry, b: ReportEntry) => {
      const da = entryDate(a);
      const db = entryDate(b);
      if (!da && !db) return a.repo.localeCompare(b.repo);
      if (!da) return 1;
      if (!db) return -1;
      return desc ? db.localeCompare(da) : da.localeCompare(db);
    };
    switch (sort) {
      case "name-desc":
        rows.sort((a, b) => b.repo.localeCompare(a.repo));
        break;
      case "score-desc":
        rows.sort(byScoreNullsLast);
        break;
      case "score-asc":
        rows.sort((a, b) => -byScoreNullsLast(a, b));
        break;
      case "date-desc":
        rows.sort(byDate(true));
        break;
      case "date-asc":
        rows.sort(byDate(false));
        break;
      default: // name-asc
        rows.sort((a, b) => a.repo.localeCompare(b.repo));
        break;
    }
    return rows;
  }, [entries, query, filter, sort]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const pageRows = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const resetPage = () => setPage(1);

  const toggleExpand = (repo: string) => {
    setExpanded(expanded === repo ? null : repo);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 max-w-5xl"
    >
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Assess Reports</h1>
          <p className="text-sm text-slate-400 mt-0.5">Fleet-wide assess-fix report registry</p>
        </div>
        <button
          onClick={fetch}
          className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-md transition-colors"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300 mb-4">
          {error}
        </div>
      )}

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-500 mb-1">Repos Assessed</div>
            <div className="text-2xl font-bold text-slate-100">{stats.total_assessed}</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-500 mb-1">With Reports</div>
            <div className="text-2xl font-bold text-slate-100">{stats.total_with_reports}</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-500 mb-1">Avg Score</div>
            <div className="text-2xl font-bold text-slate-100 flex items-center gap-1">
              {stats.average_score != null ? (
                <>
                  {stats.average_score}
                  {stats.average_score >= 60 ? (
                    <TrendingUp size={18} className="text-green-400" />
                  ) : (
                    <TrendingDown size={18} className="text-red-400" />
                  )}
                </>
              ) : (
                "--"
              )}
            </div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-500 mb-1">Range</div>
            <div className="text-2xl font-bold text-slate-100">
              {stats.min_score != null ? `${stats.min_score} - ${stats.max_score}` : "--"}
            </div>
          </div>
        </div>
      )}

      {/* Search / filter / sort */}
      {!loading && entries.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap mb-4">
          <div className="relative flex-1 min-w-[180px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                resetPage();
              }}
              placeholder="Search repos..."
              className="w-full rounded-lg border border-slate-700 bg-slate-900/60 pl-9 pr-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>
          <select
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value as FilterMode);
              resetPage();
            }}
            className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
          >
            <option value="all">All repos</option>
            <option value="reports">With report</option>
            <option value="needs-work">Needs work (&lt;60)</option>
            <option value="no-report">No report</option>
          </select>
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value as SortMode);
              resetPage();
            }}
            className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
          >
            <option value="name-asc">Name A–Z</option>
            <option value="name-desc">Name Z–A</option>
            <option value="score-desc">Score high–low</option>
            <option value="score-asc">Score low–high</option>
            <option value="date-desc">Newest first</option>
            <option value="date-asc">Oldest first</option>
          </select>
          <span className="text-xs text-slate-500">
            {filtered.length} of {entries.length}
          </span>
        </div>
      )}

      {/* Report list */}
      {loading && (
        <div className="flex items-center justify-center py-12 text-slate-400">
          <div className="animate-spin mr-2 h-5 w-5 border-b-2 border-current rounded-full" />
          Scanning fleet repos...
        </div>
      )}

      {!loading && entries.length === 0 && !error && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-8 text-center">
          <ClipboardList size={36} className="mx-auto mb-3 text-slate-700" />
          <p className="text-sm text-slate-400">
            No assess reports found. Run <code className="font-mono text-blue-400">assfix</code> on
            repos first.
          </p>
        </div>
      )}

      {!loading && entries.length > 0 && filtered.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-8 text-center text-sm text-slate-500">
          No repos match this filter.
        </div>
      )}

      <div className="space-y-2">
        {pageRows.map((entry) => {
          const score = entryScore(entry);
          return (
            <div
              key={entry.repo}
              className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden"
            >
              <button
                onClick={() => toggleExpand(entry.repo)}
                className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-800/50 transition-colors"
              >
                {expanded === entry.repo ? (
                  <ChevronDown size={14} className="text-slate-500 shrink-0" />
                ) : (
                  <ChevronRight size={14} className="text-slate-500 shrink-0" />
                )}
                <span className="text-sm font-medium text-slate-200">{entry.repo}</span>
                {score != null && (
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-medium ${scoreBadge(score)}`}
                  >
                    {score}/100
                  </span>
                )}
                <span className="text-xs text-slate-500 ml-auto">
                  {entry.latest_report?.report_date ?? "no report"}
                </span>
                {entry.timestamp?.commit && (
                  <span className="text-xs font-mono text-slate-600 hidden md:inline">
                    {entry.timestamp.commit.slice(0, 8)}
                  </span>
                )}
              </button>

              {expanded === entry.repo && (
                <div className="px-4 pb-4 space-y-2">
                  {entry.timestamp && (
                    <div className="bg-slate-950 border border-slate-800 rounded p-2.5 text-xs font-mono text-slate-400 space-y-1">
                      <div>Assessed: {entry.timestamp.timestamp?.slice(0, 19) ?? "unknown"}</div>
                      {entry.timestamp.commit && <div>Commit: {entry.timestamp.commit}</div>}
                    </div>
                  )}

                  {entry.latest_report?.preview && (
                    <div className="bg-slate-950 border border-slate-800 rounded p-2.5 text-xs text-slate-400 whitespace-pre-wrap max-h-48 overflow-y-auto font-mono">
                      {entry.latest_report.preview}
                    </div>
                  )}

                  {entry.latest_report?.report_path && (
                    <div className="flex gap-2">
                      <a
                        href={`https://github.com/sandraschi/${entry.repo}/blob/master/${entry.latest_report.report_path.split(`${entry.repo}/`).pop()}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300"
                      >
                        <FileText size={12} />
                        Open full report
                      </a>
                      <a
                        href={`https://github.com/sandraschi/${entry.repo}/tree/master/docs/assess-reports`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300"
                      >
                        <ExternalLink size={12} />
                        GitHub
                      </a>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Pagination */}
      {!loading && pageCount > 1 && (
        <div className="flex items-center justify-center gap-1.5 mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={safePage <= 1}
            aria-label="Previous page"
            className="p-2 rounded-lg border border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-40 disabled:pointer-events-none"
          >
            <ChevronLeft size={14} />
          </button>
          {Array.from({ length: pageCount }, (_, i) => i + 1).map((n) => (
            <button
              key={n}
              onClick={() => setPage(n)}
              className={`min-w-8 px-2 py-1.5 rounded-lg text-sm transition-colors ${
                n === safePage
                  ? "bg-blue-600/30 text-blue-200 border border-blue-500/40"
                  : "text-slate-400 border border-transparent hover:text-white hover:bg-slate-800"
              }`}
            >
              {n}
            </button>
          ))}
          <button
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
            disabled={safePage >= pageCount}
            aria-label="Next page"
            className="p-2 rounded-lg border border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-40 disabled:pointer-events-none"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      )}
    </motion.div>
  );
}
