import { motion } from "framer-motion";
import { CheckCircle2, Copy, FileDown, Loader2, Package, Play, RefreshCw, Zap } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  type FleetColdInstallRow,
  type FleetStdioSmokeResult,
  buildColdInstallCsv,
  buildColdInstallMarkdown,
  coldInstallExportFilename,
  downloadTextFile,
} from "../utils/fleetColdInstallExport";

type ColdInstallReport = {
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
      install_failed_prior?: number;
      install_failed_now?: number;
      install_failed_delta?: number;
      mcpb_ok_prior?: number;
      mcpb_ok_now?: number;
      mcpb_ok_delta?: number;
      probeMode?: string;
      reposProbed?: number;
      priorGeneratedAt?: string;
    } | null;
    preflight_only?: boolean;
    test_mcpb?: boolean;
    results?: FleetColdInstallRow[];
  };
};

const API = "/api/v1/fleet/cold-install";

function outcomeStyle(outcome: string): string {
  if (outcome === "preflight_ok" || outcome === "install_ok") {
    return "text-green-400 border-green-500/30 bg-green-500/10";
  }
  if (outcome === "doc_gap" || outcome === "install_pending") {
    return "text-amber-400 border-amber-500/30 bg-amber-500/10";
  }
  if (outcome === "install_failed" || outcome === "verify_failed") {
    return "text-red-400 border-red-500/30 bg-red-500/10";
  }
  return "text-white/40 border-white/10 bg-white/5";
}

function mcpbStyle(mcpb: string): string {
  if (mcpb === "mcpb_ok") return "text-green-400 border-green-500/30 bg-green-500/10";
  if (mcpb === "mcpb_pending") return "text-amber-400 border-amber-500/30 bg-amber-500/10";
  if (mcpb === "mcpb_no_package") return "text-white/30 border-white/10 bg-white/5";
  if (mcpb) return "text-red-400 border-red-500/30 bg-red-500/10";
  return "text-white/20 border-white/5 bg-transparent";
}

export const FleetColdInstall: React.FC = () => {
  const [report, setReport] = useState<ColdInstallReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [repoFilter, setRepoFilter] = useState("");
  const [testMcpb, setTestMcpb] = useState(false);
  const [hostMcpbSmoke, setHostMcpbSmoke] = useState(false);
  const [mcpClients, setMcpClients] = useState("");
  const [batchSize, setBatchSize] = useState(10);
  const [filterOutcome, setFilterOutcome] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [copyOk, setCopyOk] = useState(false);

  const fetchReport = useCallback(async () => {
    try {
      const res = await fetch(`${API}/report`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = (await res.json()) as ColdInstallReport;
      setReport(json);
      setRunning(json.data?.status === "running");
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

  const runProbe = async (mode: "single" | "full" | "broken" | "pilot") => {
    if (mode === "broken") {
      const brokenN = (report?.data?.results ?? []).filter(
        (r) =>
          (r.outcome && !["preflight_ok", "install_ok", "skip"].includes(r.outcome)) ||
          (r.mcpbOutcome && !["mcpb_ok", "mcpb_no_package", ""].includes(r.mcpbOutcome)),
      ).length;
      if (brokenN === 0) {
        setError("No broken repos in the last report — run a full probe first.");
        return;
      }
    }
    setRunning(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        repo_filter: mode === "single" ? repoFilter.trim() : "",
        broken_only: mode === "broken",
        background: true,
        preflight_only: true,
        execute: false,
        test_mcpb: testMcpb,
        host_mcpb_smoke: hostMcpbSmoke,
        mcp_clients: mcpClients.trim(),
        batch_size: mode === "pilot" ? batchSize : 0,
      };
      const res = await fetch(`${API}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const json = await res.json();
      if (!json.success) {
        setError(json.message || "Probe failed to start");
        setRunning(false);
        return;
      }
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
  const completed = data?.completed ?? rows.length;
  const totalExpected = data?.total_expected ?? rows.length;
  const currentRepo = data?.current_repo ?? "";
  const pct = totalExpected > 0 ? Math.round((completed / totalExpected) * 100) : 0;

  const brokenRepoCount = useMemo(
    () =>
      rows.filter(
        (r) =>
          (r.outcome && !["preflight_ok", "install_ok", "skip"].includes(r.outcome)) ||
          (r.mcpbOutcome && !["mcpb_ok", "mcpb_no_package", ""].includes(r.mcpbOutcome ?? "")),
      ).length,
    [rows],
  );

  const filteredRows = rows.filter((r) => {
    if (filterOutcome === "all") return true;
    if (filterOutcome.startsWith("mcpb_")) return r.mcpbOutcome === filterOutcome;
    return r.outcome === filterOutcome;
  });

  const exportMeta = useMemo(
    () => ({
      status,
      generatedAt: data?.generated_at,
      completed,
      totalExpected,
      summary,
      comparison,
      filterLabel: filterOutcome === "all" ? undefined : filterOutcome,
    }),
    [status, data?.generated_at, completed, totalExpected, summary, comparison, filterOutcome],
  );

  const markdownReport = useMemo(
    () => buildColdInstallMarkdown(filteredRows, exportMeta),
    [filteredRows, exportMeta],
  );

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

  const filters = [
    "all",
    "preflight_ok",
    "doc_gap",
    "install_ok",
    "install_failed",
    "skip",
    "mcpb_ok",
    "mcpb_smoke_failed",
    "mcpb_no_package",
    "stdio_ok",
    "stdio_failed",
    "stdio_no_config",
  ];

  return (
    <div className="space-y-8">
      <header className="flex flex-col lg:flex-row justify-between gap-6">
        <div>
          <h3 className="text-2xl font-black text-white flex items-center gap-2">
            <Package className="text-cyan-400" size={28} />
            Cold-Install Probe
          </h3>
          <p className="text-white/50 text-sm mt-1 max-w-2xl">
            INSTALL.md preflight. <strong className="text-cyan-400/90">mcpb</strong> = Claude
            Desktop only (Option A). Multi-IDE <strong className="text-violet-400/90">stdio</strong>{" "}
            smoke covers uv/manual configs (Cursor, Windsurf, Antigravity, Zed, OpenCode).
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            type="text"
            placeholder="repo e.g. docker-mcp"
            value={repoFilter}
            onChange={(e) => setRepoFilter(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-sm text-white min-w-[180px]"
          />
          <label className="flex items-center gap-2 text-xs text-white/50 px-2">
            <input
              type="checkbox"
              checked={testMcpb}
              onChange={(e) => setTestMcpb(e.target.checked)}
            />
            mcpb
          </label>
          <label className="flex items-center gap-2 text-xs text-white/50 px-2">
            <input
              type="checkbox"
              checked={hostMcpbSmoke}
              disabled={!testMcpb}
              onChange={(e) => setHostMcpbSmoke(e.target.checked)}
            />
            IDE smoke
          </label>
          <input
            type="text"
            placeholder="clients: cursor,claude,..."
            value={mcpClients}
            onChange={(e) => setMcpClients(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white min-w-[160px]"
            title="Empty = all IDEs (Claude, Cursor, Windsurf, Antigravity, Zed, OpenCode)"
          />
          <input
            type="number"
            min={1}
            max={50}
            value={batchSize}
            onChange={(e) => setBatchSize(Number(e.target.value) || 10)}
            className="w-16 bg-white/5 border border-white/10 rounded-xl px-2 py-2 text-sm text-white"
            title="Pilot batch size"
          />
          <button
            type="button"
            disabled={running || !repoFilter.trim()}
            onClick={() => runProbe("single")}
            className="px-4 py-2 rounded-xl bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 text-xs font-black uppercase tracking-widest disabled:opacity-40"
          >
            Test one
          </button>
          <button
            type="button"
            disabled={running}
            onClick={() => runProbe("pilot")}
            className="px-4 py-2 rounded-xl bg-violet-500/20 border border-violet-500/30 text-violet-300 text-xs font-black uppercase tracking-widest disabled:opacity-40"
          >
            Pilot ({batchSize})
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
            onClick={() => runProbe("broken")}
            className="px-4 py-2 rounded-xl bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-black uppercase tracking-widest flex items-center gap-2 disabled:opacity-40"
          >
            <Zap size={14} />
            Broken* ({brokenRepoCount})
          </button>
          <button
            type="button"
            onClick={fetchReport}
            className="p-2 rounded-xl border border-white/10 bg-white/5"
          >
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          </button>
          <button
            type="button"
            disabled={filteredRows.length === 0}
            onClick={() =>
              downloadTextFile(
                coldInstallExportFilename("csv"),
                buildColdInstallCsv(filteredRows),
                "text/csv;charset=utf-8",
              )
            }
            className="px-3 py-2 rounded-xl border border-white/10 bg-white/5 text-xs font-black uppercase disabled:opacity-40"
          >
            <FileDown size={14} className="inline mr-1" />
            CSV
          </button>
          <button
            type="button"
            disabled={filteredRows.length === 0}
            onClick={() => void copyMarkdown()}
            className="px-3 py-2 rounded-xl border border-white/10 bg-white/5 text-xs font-black uppercase disabled:opacity-40"
          >
            <Copy size={14} className="inline mr-1" />
            {copyOk ? "Copied" : "Copy MD"}
          </button>
        </div>
      </header>

      {error && (
        <div className="text-red-400 text-sm border border-red-500/30 bg-red-500/10 rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      {(running || status === "running") && (
        <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
          <div className="flex justify-between text-sm text-white/70 mb-2">
            <span>
              {currentRepo ? `Probing ${currentRepo}` : "Starting..."} — {completed}/{totalExpected}
            </span>
            <span>{pct}%</span>
          </div>
          <div className="h-2 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-cyan-400"
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {comparison && (
        <p className="text-xs text-white/40">
          Install/doc failures: {comparison.install_failed_now} (delta{" "}
          {comparison.install_failed_delta})
          {comparison.mcpb_ok_now != null ? ` · mcpb ok: ${comparison.mcpb_ok_now}` : ""}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {filters.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilterOutcome(f)}
            className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest border ${
              filterOutcome === f
                ? "bg-white/10 text-white border-white/20"
                : "text-white/40 border-white/5"
            }`}
          >
            {f.replace(/_/g, " ")}
            {f !== "all" && summary[f] != null ? ` (${summary[f]})` : ""}
          </button>
        ))}
      </div>

      <div className="rounded-2xl border border-white/10 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-white/40 text-[10px] uppercase tracking-widest">
            <tr>
              <th className="text-left p-3">Repo</th>
              <th className="text-left p-3">Outcome</th>
              <th className="text-left p-3">mcpb</th>
              <th className="text-left p-3">stdio</th>
              <th className="text-left p-3">Option</th>
              <th className="text-left p-3">Error</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row) => (
              // biome-ignore lint/a11y/useKeyWithClickEvents: expandable probe result row
              <tr
                key={row.repo}
                className="border-t border-white/5 hover:bg-white/[0.02] cursor-pointer"
                onClick={() => setExpanded(expanded === row.repo ? null : row.repo)}
              >
                <td className="p-3 font-mono text-white/80">{row.repo}</td>
                <td className="p-3">
                  <span
                    className={`px-2 py-0.5 rounded-lg border text-xs ${outcomeStyle(row.outcome)}`}
                  >
                    {row.outcome}
                  </span>
                </td>
                <td className="p-3">
                  <span
                    className={`px-2 py-0.5 rounded-lg border text-xs ${mcpbStyle(row.mcpbOutcome ?? "")}`}
                  >
                    {row.mcpbOutcome || "-"}
                  </span>
                </td>
                <td className="p-3">
                  <span
                    className={`px-2 py-0.5 rounded-lg border text-xs ${mcpbStyle(row.stdioOutcome ?? "")}`}
                  >
                    {row.stdioOutcome || "-"}
                  </span>
                </td>
                <td className="p-3 text-white/40">{row.primaryOption ?? "-"}</td>
                <td className="p-3 text-white/30 text-xs truncate max-w-[240px]">
                  {row.errorMessage || "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredRows.length === 0 && !loading && (
          <p className="p-8 text-center text-white/30 text-sm">No results — run a probe</p>
        )}
      </div>

      {expanded && (
        <div className="rounded-2xl border border-white/10 bg-black/40 p-4 font-mono text-xs text-white/60 whitespace-pre-wrap">
          {(() => {
            const row = filteredRows.find((r) => r.repo === expanded);
            if (!row) return "No log excerpt";
            const clientLines = (row.stdioSmokeResults as FleetStdioSmokeResult[] | undefined)
              ?.map((s) => `${s.client} (${s.serverName}): ${s.ok ? "ok" : s.error}`)
              .join("\n");
            return clientLines || row.logExcerpt || row.errorMessage || "No log excerpt";
          })()}
        </div>
      )}

      {status === "complete" && (
        <p className="text-[10px] text-white/30 flex items-center gap-1">
          <CheckCircle2 size={12} className="text-green-400" />
          Report complete — {summary.total ?? rows.length} repos
        </p>
      )}
    </div>
  );
};
