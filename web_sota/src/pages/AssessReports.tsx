import { motion } from "framer-motion";
import {
  ChevronDown,
  ChevronRight,
  ClipboardList,
  ExternalLink,
  FileText,
  RefreshCw,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
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

export function AssessReportsPage() {
  const [entries, setEntries] = useState<ReportEntry[]>([]);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const listResp = await api.executeTool("metaops", "assess_reports_ops", {
        operation: "list",
      });
      if (isSuccessResponse(listResp)) {
        const data = (listResp.result ?? listResp.data) as {
          reports?: ReportEntry[];
        };
        setEntries(data?.reports ?? []);
      }

      const statsResp = await api.executeTool("metaops", "assess_reports_ops", {
        operation: "stats",
      });
      if (isSuccessResponse(statsResp)) {
        const data = (statsResp.result ?? statsResp.data) as StatsData;
        setStats(data);
      }
    } catch (err) {
      console.error("Failed to fetch assess reports", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

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

      {/* Report list */}
      {loading && (
        <div className="flex items-center justify-center py-12 text-slate-400">
          <div className="animate-spin mr-2 h-5 w-5 border-b-2 border-current rounded-full" />
          Scanning fleet repos...
        </div>
      )}

      {!loading && entries.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-8 text-center">
          <ClipboardList size={36} className="mx-auto mb-3 text-slate-700" />
          <p className="text-sm text-slate-400">
            No assess reports found. Run <code className="font-mono text-blue-400">assfix</code> on
            repos first.
          </p>
        </div>
      )}

      <div className="space-y-2">
        {entries.map((entry) => (
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
              {entry.latest_report?.score != null && (
                <span
                  className={`text-xs px-2 py-0.5 rounded font-medium ${
                    entry.latest_report.score >= 80
                      ? "bg-green-500/15 text-green-400"
                      : entry.latest_report.score >= 60
                        ? "bg-amber-500/15 text-amber-400"
                        : "bg-red-500/15 text-red-400"
                  }`}
                >
                  {entry.latest_report.score}/100
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
                      href={`file:///${entry.repo}/${entry.latest_report.report_path}`}
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
        ))}
      </div>
    </motion.div>
  );
}
