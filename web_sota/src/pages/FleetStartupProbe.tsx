import { motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Copy,
  FileDown,
  FileText,
  Loader2,
  Play,
  RefreshCw,
  ServerCrash,
  Zap,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { FleetBadgeFilterChips, FleetStatusBadgeRow } from "../components/FleetStatusBadge";
import {
  type FleetProbeRow,
  buildProbeCsv,
  buildProbeMarkdown,
  downloadTextFile,
  probeExportFilename,
} from "../utils/fleetProbeExport";
import {
  countProbeBadgeKinds,
  deriveProbeBadges,
  probeMatchesBadgeFilter,
} from "../utils/fleetStatusBadges";

type ProbeReport = {
  success: boolean;
  message: string;
  data?: {
    status: string;
    generated_at?: string;
    completed?: number;
    total_expected?: number;
    current_repo?: string | null;
    summary?: Record<string, number>;
    comparison?: {
      parse_failed_prior?: number;
      parse_failed_now?: number;
      parse_failed_delta?: number;
      root_order_failed_prior?: number;
      root_order_failed_now?: number;
      root_order_failed_delta?: number;
      probeMode?: string;
      reposProbed?: number;
      priorGeneratedAt?: string;
    } | null;
    results?: FleetProbeRow[];
  };
};

const API = "/api/v1/fleet/startup-probe";
const PROBE_HOST_REPOS = new Set(["meta_mcp"]);

export const FleetStartupProbe: React.FC = () => {
  const [report, setReport] = useState<ProbeReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [repoFilter, setRepoFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filterOutcome, setFilterOutcome] = useState("all");
  const [showMdPreview, setShowMdPreview] = useState(false);
  const [copyOk, setCopyOk] = useState(false);

  const fetchReport = useCallback(async () => {
    try {
      const res = await fetch(`${API}/report`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = (await res.json()) as ProbeReport;
      setReport(json);
      const st = json.data?.status ?? "idle";
      setRunning(st === "running");
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, []);

  const pollActive = running || report?.data?.status === "running";

  useEffect(() => {
    fetchReport();
    const ms = pollActive ? 2000 : 30000;
    const t = setInterval(fetchReport, ms);
    return () => clearInterval(t);
  }, [fetchReport, pollActive]);

  const repoFilterNorm = repoFilter.trim().toLowerCase();
  const probeHostFiltered = PROBE_HOST_REPOS.has(repoFilterNorm);

  const runProbe = async (mode: "single" | "full" | "broken" = "full") => {
    if (mode === "single" && probeHostFiltered) {
      setError("meta_mcp is the probe host and cannot cold-start itself from this UI.");
      return;
    }
    if (mode === "broken") {
      const brokenN = (report?.data?.results ?? []).filter(
        (r) => r.outcome && r.outcome !== "stack_ok" && r.outcome !== "skip",
      ).length;
      if (brokenN === 0) {
        setError("No broken repos in the last report — run a full fleet probe first.");
        return;
      }
    }
    setRunning(true);
    setError(null);
    try {
      const res = await fetch(`${API}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo_filter: mode === "single" ? repoFilter.trim() : "",
          broken_only: mode === "broken",
          background: true,
        }),
      });
      const json = await res.json();
      if (!json.success) {
        setError(json.message || "Probe failed to start");
        setRunning(false);
        return;
      }
      setReport((prev) => ({
        success: true,
        message: json.message || "Probe started",
        data: {
          ...(prev?.data ?? {}),
          status: "running",
          total_expected: json.data?.total_expected ?? prev?.data?.total_expected ?? 1,
          completed: 0,
          results: [],
        },
      }));
      await fetchReport();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run failed");
      setRunning(false);
    }
  };

  const data = report?.data;
  const rows = data?.results ?? [];
  const summary = data?.summary ?? {};
  const comparison = data?.comparison ?? null;
  const status = data?.status ?? "idle";
  const brokenRepoCount = useMemo(
    () => rows.filter((r) => r.outcome && r.outcome !== "stack_ok" && r.outcome !== "skip").length,
    [rows],
  );
  const completed = data?.completed ?? rows.length;
  const totalExpected = data?.total_expected ?? rows.length;
  const currentRepo = data?.current_repo ?? "";
  const pct = totalExpected > 0 ? Math.round((completed / totalExpected) * 100) : 0;
  const scanActive = running || status === "running" || status === "interrupted";

  const probeFilters = useMemo(
    () => [
      { id: "all", label: "all" },
      { id: "stack_ok", label: "stack ok" },
      { id: "pages_404", label: "404" },
      { id: "500", label: "500" },
      { id: "offline", label: "offline" },
      { id: "unavailable", label: "unavailable" },
      { id: "parse_failed", label: "parse" },
      { id: "root_order_failed", label: "root order" },
      { id: "start_failed", label: "start fail" },
      { id: "backend_ok", label: "backend ok" },
      { id: "skip", label: "skip" },
    ],
    [],
  );

  const filteredRows = rows.filter((r) => probeMatchesBadgeFilter(r, filterOutcome));
  const badgeCounts = useMemo(() => countProbeBadgeKinds(rows), [rows]);

  const exportMeta = useMemo(
    () => ({
      status,
      generatedAt: data?.generated_at,
      completed,
      totalExpected,
      summary,
      comparison,
      filterLabel: filterOutcome === "all" ? undefined : `outcome=${filterOutcome}`,
    }),
    [status, data?.generated_at, completed, totalExpected, summary, comparison, filterOutcome],
  );

  const markdownReport = useMemo(
    () => buildProbeMarkdown(filteredRows, exportMeta),
    [filteredRows, exportMeta],
  );

  const exportCsv = () => {
    if (filteredRows.length === 0) return;
    downloadTextFile(
      buildProbeCsv(filteredRows),
      probeExportFilename("csv", data?.generated_at),
      "text/csv;charset=utf-8",
    );
  };

  const exportMd = () => {
    if (filteredRows.length === 0) return;
    downloadTextFile(
      markdownReport,
      probeExportFilename("md", data?.generated_at),
      "text/markdown;charset=utf-8",
    );
  };

  const copyMarkdown = async () => {
    if (filteredRows.length === 0) return;
    try {
      await navigator.clipboard.writeText(markdownReport);
      setCopyOk(true);
      setTimeout(() => setCopyOk(false), 2000);
    } catch {
      setError("Clipboard copy failed");
    }
  };

  const outcomeStyle = (outcome: string) => {
    if (outcome === "stack_ok") return "text-green-400 border-green-500/30 bg-green-500/10";
    if (outcome === "backend_ok") return "text-amber-400 border-amber-500/30 bg-amber-500/10";
    if (outcome === "pages_404") return "text-orange-400 border-orange-500/30 bg-orange-500/10";
    if (outcome === "parse_failed") return "text-red-400 border-red-500/30 bg-red-500/10";
    if (outcome === "root_order_failed") return "text-rose-400 border-rose-500/30 bg-rose-500/10";
    if (outcome === "start_failed") return "text-red-400 border-red-500/30 bg-red-500/10";
    return "text-white/40 border-white/10 bg-white/5";
  };

  return (
    <div className="space-y-8">
      <header className="flex flex-col lg:flex-row justify-between gap-6">
        <div>
          <h3 className="text-2xl font-black text-white flex items-center gap-2">
            <ServerCrash className="text-amber-400" size={28} />
            Cold-Start Probe
          </h3>
          <p className="text-white/50 text-sm mt-1 max-w-2xl">
            Sequential test: parse-check, start, probe stack, then{" "}
            <strong className="text-white/70">teardown</strong> (kill backend + frontend ports)
            before the next repo. Safe for goliath.{" "}
            <strong className="text-amber-400/90">Test one</strong> also hits SPA routes (manifest{" "}
            <code className="text-white/40">frontendRoutes</code> or repo{" "}
            <code className="text-white/40">probe-routes.json</code>) and flags{" "}
            <strong className="text-orange-400/90">pages_404</strong>.{" "}
            <strong className="text-amber-400/90">meta_mcp</strong> is skipped (this dashboard runs
            the probe).
          </p>
          {report?.message && (
            <p className="text-[10px] text-white/30 mt-2 uppercase tracking-widest">
              {report.message}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            type="text"
            placeholder="repo filter e.g. toolbench-mcp"
            value={repoFilter}
            onChange={(e) => setRepoFilter(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-sm text-white min-w-[200px]"
          />
          <button
            type="button"
            disabled={running || !repoFilter.trim() || probeHostFiltered}
            title={probeHostFiltered ? "meta_mcp is the probe host" : undefined}
            onClick={() => runProbe("single")}
            className="px-4 py-2 rounded-xl bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-black uppercase tracking-widest disabled:opacity-40"
          >
            Test one
          </button>
          <button
            type="button"
            disabled={running}
            onClick={() => runProbe("full")}
            className="px-4 py-2 rounded-xl bg-blue-500/20 border border-blue-500/30 text-blue-300 text-xs font-black uppercase tracking-widest flex items-center gap-2 disabled:opacity-40"
          >
            {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            Full fleet
          </button>
          <button
            type="button"
            disabled={running || brokenRepoCount === 0 || status !== "complete"}
            title={
              brokenRepoCount === 0
                ? "Run a full fleet probe first"
                : `Re-test ${brokenRepoCount} repos that were not stack_ok in the last report`
            }
            onClick={() => runProbe("broken")}
            className="px-4 py-2 rounded-xl bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-black uppercase tracking-widest flex items-center gap-2 disabled:opacity-40"
          >
            {running ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            Broken* ({brokenRepoCount})
          </button>
          <button
            type="button"
            onClick={fetchReport}
            className="p-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10"
          >
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          </button>
          <div className="h-8 w-px bg-white/10" />
          <button
            type="button"
            disabled={filteredRows.length === 0}
            onClick={exportCsv}
            className="px-3 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-white/70 text-xs font-black uppercase tracking-widest flex items-center gap-1.5 disabled:opacity-40"
          >
            <FileDown size={14} />
            CSV
          </button>
          <button
            type="button"
            disabled={filteredRows.length === 0}
            onClick={exportMd}
            className="px-3 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-white/70 text-xs font-black uppercase tracking-widest flex items-center gap-1.5 disabled:opacity-40"
          >
            <FileDown size={14} />
            MD
          </button>
          <button
            type="button"
            disabled={filteredRows.length === 0}
            onClick={() => void copyMarkdown()}
            className="px-3 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-white/70 text-xs font-black uppercase tracking-widest flex items-center gap-1.5 disabled:opacity-40"
          >
            <Copy size={14} />
            {copyOk ? "Copied" : "Copy MD"}
          </button>
          <button
            type="button"
            disabled={filteredRows.length === 0}
            onClick={() => setShowMdPreview((v) => !v)}
            className={`px-3 py-2 rounded-xl border text-xs font-black uppercase tracking-widest flex items-center gap-1.5 disabled:opacity-40 ${
              showMdPreview
                ? "border-violet-500/40 bg-violet-500/20 text-violet-200"
                : "border-white/10 bg-white/5 hover:bg-white/10 text-white/70"
            }`}
          >
            <FileText size={14} />
            {showMdPreview ? "Hide report" : "Preview MD"}
          </button>
        </div>
      </header>

      {error && (
        <div className="glass-panel p-4 border-red-500/30 text-red-300 text-sm flex gap-2">
          <AlertTriangle size={18} />
          {error}
        </div>
      )}

      {scanActive && (
        <div className="glass-panel p-4 border-amber-500/20">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 text-xs font-black uppercase tracking-widest text-amber-300 mb-2">
            <span>
              Progress {completed} / {totalExpected}
              {currentRepo ? (
                <span className="block sm:inline sm:ml-3 text-[10px] text-amber-200/80 normal-case tracking-normal font-bold">
                  Current: {currentRepo}
                </span>
              ) : null}
            </span>
            <span className="flex items-center gap-2">
              {scanActive ? <Loader2 size={12} className="animate-spin" /> : null}
              {pct}%
            </span>
          </div>
          <div className="h-2 bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-500 transition-all duration-500"
              style={{ width: `${pct}%` }}
            />
          </div>
          {totalExpected > 1 && completed < totalExpected && (
            <p className="text-[10px] text-white/35 mt-2 normal-case tracking-normal">
              Full fleet cold-start takes several minutes (~90s per repo + 5s cooldown). Results
              appear below as each repo finishes.
            </p>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-10 gap-3">
        {[
          {
            label: "Status",
            val: status.toUpperCase(),
            color: scanActive
              ? "text-amber-400"
              : status === "interrupted"
                ? "text-orange-400"
                : "text-green-400",
          },
          { label: "Stack OK", val: summary.stack_ok ?? 0, color: "text-green-400" },
          { label: "Parse fail", val: summary.parse_failed ?? 0, color: "text-red-400" },
          {
            label: "Root order",
            val: summary.root_order_failed ?? 0,
            color: "text-rose-400",
          },
          { label: "Start fail", val: summary.start_failed ?? 0, color: "text-red-400" },
          {
            label: "404",
            val: badgeCounts["404"] || summary.pages_404 || 0,
            color: "text-orange-400",
          },
          { label: "500", val: badgeCounts["500"] || 0, color: "text-red-400" },
          { label: "Offline", val: badgeCounts.offline || 0, color: "text-white/60" },
          {
            label: "Unavailable",
            val: badgeCounts.unavailable || 0,
            color: "text-red-300",
          },
          { label: "Teardown fail", val: summary.teardown_fail ?? 0, color: "text-orange-400" },
          { label: "Total", val: summary.total ?? rows.length, color: "text-white" },
        ].map((s) => (
          <div key={s.label} className="glass-panel p-4 border-white/5">
            <p className="text-[9px] uppercase tracking-widest opacity-40 font-black">{s.label}</p>
            <p className={`text-2xl font-black ${s.color}`}>{s.val}</p>
          </div>
        ))}
      </div>

      {data?.generated_at && (
        <p className="text-[10px] text-white/30 uppercase tracking-widest">
          Last run: {data.generated_at}
        </p>
      )}

      {comparison && (
        <p className="text-sm text-white/60">
          Parse failures:{" "}
          <span className="font-bold text-white">{comparison.parse_failed_now ?? 0}</span> (was{" "}
          {comparison.parse_failed_prior ?? 0}
          {comparison.parse_failed_delta != null && (
            <span
              className={
                comparison.parse_failed_delta < 0
                  ? " text-green-400"
                  : comparison.parse_failed_delta > 0
                    ? " text-red-400"
                    : ""
              }
            >
              {" "}
              {comparison.parse_failed_delta > 0 ? "+" : ""}
              {comparison.parse_failed_delta}
            </span>
          )}
          )
        </p>
      )}

      <FleetBadgeFilterChips
        filters={probeFilters}
        active={filterOutcome}
        onChange={setFilterOutcome}
      />

      {showMdPreview && filteredRows.length > 0 && (
        <div className="glass-panel border-violet-500/20 p-6 max-h-[480px] overflow-y-auto custom-scrollbar prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{markdownReport}</ReactMarkdown>
        </div>
      )}

      {loading && !report ? (
        <div className="flex justify-center py-16 text-white/40">
          <Loader2 className="animate-spin mr-2" />
          Loading probe report...
        </div>
      ) : filteredRows.length === 0 && scanActive ? (
        <div className="glass-panel p-12 text-center text-white/40 border-dashed">
          <Loader2 className="mx-auto mb-4 animate-spin opacity-40" size={48} />
          <p>
            {currentRepo
              ? `Probing ${currentRepo}…`
              : `Fleet scan started — waiting for first result (${completed}/${totalExpected}).`}
          </p>
        </div>
      ) : filteredRows.length === 0 ? (
        <div className="glass-panel p-12 text-center text-white/40 border-dashed">
          <Zap className="mx-auto mb-4 opacity-20" size={48} />
          <p>No probe results yet. Run Full fleet or Test one repo.</p>
        </div>
      ) : (
        <motion.div layout className="space-y-2 max-h-[600px] overflow-y-auto custom-scrollbar">
          {filteredRows.map((row) => (
            <div key={row.repo} className={`glass-panel border ${outcomeStyle(row.outcome)}`}>
              {/* biome-ignore lint/a11y/useKeyWithClickEvents: expandable probe result card */}
              <div
                className="p-4 flex flex-col md:flex-row md:items-center gap-3 cursor-pointer"
                onClick={() => setExpanded(expanded === row.repo ? null : row.repo)}
              >
                <div className="flex-1 min-w-0">
                  <p className="font-black text-white">{row.repo}</p>
                  {row.errorMessage && (
                    <p className="text-[10px] opacity-80 mt-1">{row.errorMessage}</p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2 text-[9px] font-black uppercase tracking-widest items-center">
                  <FleetStatusBadgeRow badges={deriveProbeBadges(row)} />
                  <span className="px-2 py-1 rounded border border-current flex items-center gap-1">
                    {row.outcome === "stack_ok" ? <CheckCircle2 size={10} /> : null}
                    {row.outcome}
                  </span>
                  {row.logExcerpt ? (
                    expanded === row.repo ? (
                      <ChevronUp size={14} />
                    ) : (
                      <ChevronDown size={14} />
                    )
                  ) : null}
                </div>
              </div>
              {expanded === row.repo && row.logExcerpt && (
                <pre className="px-4 pb-4 text-[10px] text-white/50 overflow-x-auto whitespace-pre-wrap border-t border-white/5 pt-3">
                  {row.logExcerpt}
                </pre>
              )}
              {row.pageChecks && row.pageChecks.length > 0 && expanded === row.repo && (
                <p className="px-4 pb-2 text-[9px] text-white/40 border-t border-white/5 pt-3">
                  SPA routes:{" "}
                  {row.pageChecks
                    .map((pc) => `${pc.path} (${pc.ok ? "OK" : `HTTP ${pc.status ?? "?"}`})`)
                    .join(" · ")}
                </p>
              )}
              {row.teardownDetail && expanded === row.repo && (
                <p className="px-4 pb-3 text-[9px] text-white/30">{row.teardownDetail}</p>
              )}
            </div>
          ))}
        </motion.div>
      )}
    </div>
  );
};
