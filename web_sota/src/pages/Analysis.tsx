import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Code2,
  FileSearch,
  Flag,
  FolderOpen,
  Loader2,
  Play,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  Terminal,
  XCircle,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { type ApiResponse, api } from "../api/client";
import { llmService } from "../services/llm";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Finding {
  severity: "error" | "warning" | "info";
  message: string;
  recommendation?: string;
  rule_id?: string;
  category?: string;
  file?: string;
  line?: number;
  score_deduction?: number;
}

interface AnalysisResult {
  success: boolean;
  message: string;
  is_runt?: boolean;
  sota_score?: number;
  violations?: Finding[];
  critical_violations?: Finding[];
  runt_reasons?: string[];
  recommendations?: string[];
  summary?: Record<string, unknown>;
  error?: string;
  data?: Record<string, unknown>;
}

type RunState = "idle" | "running" | "done" | "error";

// ---------------------------------------------------------------------------
// Analysis Tool Definitions
// ---------------------------------------------------------------------------

interface AnalysisTool {
  id: string;
  label: string;
  icon: React.ElementType;
  description: string;
  color: string;
  requiresPath: boolean;
  hasDryRun: boolean;
  hasBak: boolean;
  run: (path: string, dryRun: boolean, createBak: boolean) => Promise<AnalysisResult>;
}

function parseFindings(raw: Record<string, unknown>): Finding[] {
  const findings: Finding[] = [];
  const violations = raw.violations;
  if (Array.isArray(violations)) {
    for (const v of violations) {
      const vo = v as Record<string, unknown>;
      findings.push({
        severity:
          (vo.severity as string) === "critical"
            ? "error"
            : vo.severity === "warning"
              ? "warning"
              : "info",
        message: String(vo.message || ""),
        recommendation: String(vo.recommendation || ""),
        rule_id: String(vo.rule_id || ""),
        category: String(vo.category || ""),
        score_deduction: vo.score_deduction as number,
      });
    }
  }
  return findings;
}

function parseResult(raw: Record<string, unknown>): AnalysisResult {
  const success = raw.success === true;
  if (!success) {
    return { success: false, message: String(raw.message || raw.error || "Unknown error") };
  }
  const data = (raw.data ?? raw.result ?? raw) as Record<string, unknown>;
  const violations = parseFindings(data);
  const critical = parseFindings({ violations: data.critical_violations });
  return {
    success: true,
    message: String(data.message || raw.message || "Analysis complete"),
    is_runt: data.is_runt as boolean,
    sota_score: data.sota_score as number,
    violations,
    critical_violations: critical,
    runt_reasons: data.runt_reasons as string[],
    recommendations: data.recommendations as string[],
    summary: {
      total_mcp_repos: data.total_mcp_repos,
      runts: data.runts,
      sota: data.sota,
      score_deduction: data.score_deduction,
      violation_count: data.violation_count,
      critical_count: data.critical_count,
    } as Record<string, unknown>,
    data,
  };
}

const ANALYSIS_TOOLS: AnalysisTool[] = [
  {
    id: "runts",
    label: "Runt Scanner",
    icon: ShieldAlert,
    description:
      "Scan a directory of repos for SOTA compliance gaps using 40+ 2026 fleet standards. Checks FastMCP version, web stack, Tauri, docs, testing, and safety patterns.",
    color: "from-rose-500",
    requiresPath: true,
    hasDryRun: true,
    hasBak: false,
    run: async (path: string, dryRun: boolean) => {
      const r = await api.runRuntAnalyzer({
        operation: "runts",
        repo_path: path,
        scan_mode: dryRun ? "dry-run" : "full",
      });
      return parseResult(
        (r as { data?: Record<string, unknown>; result?: Record<string, unknown> }).data ??
          (r as unknown as Record<string, unknown>),
      );
    },
  },
  {
    id: "status",
    label: "Repo Status",
    icon: BarChart3,
    description:
      "Get detailed SOTA compliance report for a single repo. Shows score, violations, recommendations, and 2026 fleet standard coverage.",
    color: "from-blue-500",
    requiresPath: true,
    hasDryRun: true,
    hasBak: false,
    run: async (path: string, _dryRun: boolean) => {
      const r = await api.getRepoStatus({ operation: "status", repo_path: path });
      return parseResult(
        (r as { data?: Record<string, unknown> }).data ?? (r as unknown as Record<string, unknown>),
      );
    },
  },
  {
    id: "codebase",
    label: "Deep Codebase Scan",
    icon: Code2,
    description:
      "Deep codebase analysis via repomix — scans repo structure, dependencies, entry points, and surface area for full picture analysis.",
    color: "from-violet-500",
    requiresPath: true,
    hasDryRun: true,
    hasBak: false,
    run: async (path: string, dryRun: boolean) => {
      const r = await api.scanRepository({ repo_path: path, deep_analysis: !dryRun });
      return parseResult(r as unknown as Record<string, unknown>);
    },
  },
  {
    id: "unicode",
    label: "Unicode Scanner",
    icon: Terminal,
    description:
      "Scan for non-ASCII characters (emojis, em dashes, smart quotes) in logger/print calls that cause Windows logging crashes.",
    color: "from-amber-500",
    requiresPath: true,
    hasDryRun: true,
    hasBak: true,
    run: async (path: string, _dr: boolean, createBak: boolean) => {
      const r = await api.runEmojiBuster({
        operation: "scan",
        repo_path: path,
        scan_mode: "comprehensive",
        backup: createBak,
      });
      return parseResult(r as unknown as Record<string, unknown>);
    },
  },
  {
    id: "config-audit",
    label: "Config Audit",
    icon: Shield,
    description:
      "Audit fleet-wide config compliance: CLAUDE.md, AGENTS.md, .cursorrules, llms.txt, glama.json, .env.example, and more.",
    color: "from-emerald-500",
    requiresPath: false,
    hasDryRun: false,
    hasBak: false,
    run: async () => {
      const r = await fetch("").then(
        () =>
          ({
            success: false,
            message:
              "Config Audit page has its own dedicated view. Navigate to Config Audit in the sidebar.",
          }) as ApiResponse,
      );
      return parseResult(r as unknown as Record<string, unknown>);
    },
  },
  {
    id: "llm-deep",
    label: "LLM Deep Analysis",
    icon: Search,
    description:
      "Send scan results to the local LLM (Ollama) for a natural-language summary and recommendations. Requires Ollama running on port 11434.",
    color: "from-purple-500",
    requiresPath: false,
    hasDryRun: false,
    hasBak: false,
    run: async () => {
      return {
        success: false,
        message: "Select a tool above, run a scan, then use 'Send to LLM' on its results.",
      };
    },
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AnalysisPage() {
  const [repoPath, setRepoPath] = useState("");
  const [recentPaths, setRecentPaths] = useState<string[]>([]);
  const [states, setStates] = useState<Record<string, RunState>>({});
  const [results, setResults] = useState<Record<string, AnalysisResult | null>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [dryRun, setDryRun] = useState(false);
  const [createBak, setCreateBak] = useState(false);
  const [llmAnalysis, setLlmAnalysis] = useState<string>("");
  const [llmLoading, setLlmLoading] = useState(false);
  const resultsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem("analysis_recent_paths");
    if (stored) {
      try {
        setRecentPaths(JSON.parse(stored));
      } catch {
        /* ignore */
      }
    }
  }, []);

  const savePath = useCallback(
    (path: string) => {
      const updated = [path, ...recentPaths.filter((p) => p !== path)].slice(0, 10);
      setRecentPaths(updated);
      localStorage.setItem("analysis_recent_paths", JSON.stringify(updated));
    },
    [recentPaths],
  );

  const runTool = useCallback(
    async (tool: AnalysisTool) => {
      if (tool.requiresPath && !repoPath.trim()) return;
      const id = tool.id;
      setStates((s) => ({ ...s, [id]: "running" }));
      setResults((r) => ({ ...r, [id]: null }));
      try {
        const result = await tool.run(repoPath.trim(), dryRun, createBak);
        setResults((r) => ({ ...r, [id]: result }));
        setStates((s) => ({ ...s, [id]: result.success ? "done" : "error" }));
        setExpanded((e) => ({ ...e, [id]: true }));
        if (tool.requiresPath) savePath(repoPath.trim());
      } catch (err) {
        setResults((r) => ({
          ...r,
          [id]: { success: false, message: String(err) },
        }));
        setStates((s) => ({ ...s, [id]: "error" }));
      }
    },
    [repoPath, dryRun, createBak, savePath],
  );

  const runAll = useCallback(async () => {
    for (const tool of ANALYSIS_TOOLS.filter((t) => t.id !== "llm-deep")) {
      if (tool.requiresPath && !repoPath.trim()) continue;
      await runTool(tool);
    }
  }, [runTool, repoPath]);

  const sendToLlm = useCallback(
    async (toolId: string) => {
      const result = results[toolId];
      if (!result?.success) return;
      setLlmLoading(true);
      setLlmAnalysis("");
      try {
        const prompt = `You are a fleet code quality analyst. Review the following analysis results and provide a concise summary of the key issues, their severity, and recommended actions.\n\nTool: ${toolId}\n\nResults:\n\`\`\`json\n${JSON.stringify(result, null, 2)}\n\`\`\``;
        const response = await llmService.completion(prompt);
        setLlmAnalysis(response);
      } catch (err) {
        setLlmAnalysis(
          `**LLM analysis failed** — ${err instanceof Error ? err.message : "Is Ollama running on port 11434?"}`,
        );
      } finally {
        setLlmLoading(false);
      }
    },
    [results],
  );

  const severityIcon = (sev: string) => {
    switch (sev) {
      case "error":
        return <XCircle size={14} className="text-red-400 shrink-0" />;
      case "warning":
        return <AlertTriangle size={14} className="text-amber-400 shrink-0" />;
      default:
        return <CheckCircle2 size={14} className="text-slate-500 shrink-0" />;
    }
  };

  const severityClass = (sev: string) => {
    switch (sev) {
      case "error":
        return "bg-red-500/10 text-red-300 border-red-500/20";
      case "warning":
        return "bg-amber-500/10 text-amber-300 border-amber-500/20";
      default:
        return "bg-slate-500/10 text-slate-300 border-slate-500/20";
    }
  };

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-2xl p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="p-3 bg-blue-500/20 rounded-xl border border-blue-500/30">
            <FileSearch className="text-white" size={28} />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-100">
              Code Analysis &amp; SOTA Compliance
            </h2>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Run fleet analysis tools against repositories. Check SOTA compliance (40+ 2026
              standards), detect runts, scan for Unicode crashes, and audit config coverage. Results
              are structured with severity indicators and actionable recommendations.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-4 text-xs text-slate-500 border-t border-slate-700 pt-4 mt-2">
          <span>
            <span className="text-red-400 font-semibold">Red</span> = Critical (runt-defining)
          </span>
          <span>
            <span className="text-amber-400 font-semibold">Amber</span> = Warning
          </span>
          <span>
            <span className="text-slate-400 font-semibold">Gray</span> = Info
          </span>
          <span className="text-blue-400 font-semibold">SOTA score</span>
          <span className="text-rose-400">Runt detection</span>
        </div>
      </div>

      {/* Repo Path + Controls */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-5">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[300px]">
            <label className="text-xs font-semibold text-slate-400 mb-2 block">
              Repository Path
            </label>
            <div className="relative">
              <FolderOpen
                size={16}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"
              />
              <input
                type="text"
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") runAll();
                }}
                placeholder="D:\Dev\repos\arxiv-mcp"
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-sm rounded-xl pl-12 pr-4 py-3 focus:outline-none focus:border-blue-500/50"
              />
            </div>
          </div>
          {recentPaths.length > 0 && (
            <div>
              <label className="text-xs font-semibold text-slate-400 mb-2 block opacity-0">_</label>
              <select
                onChange={(e) => {
                  if (e.target.value) setRepoPath(e.target.value);
                }}
                value=""
                className="bg-slate-950 border border-slate-700 text-slate-400 text-sm rounded-xl px-3 py-3 focus:outline-none cursor-pointer"
              >
                <option value="" disabled>
                  Recent
                </option>
                {recentPaths.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="text-xs font-semibold text-slate-400 mb-2 block">Safety</label>
            <div className="flex gap-2">
              <label className="flex items-center gap-1.5 px-3 py-2.5 bg-slate-950 border border-slate-700 rounded-xl cursor-pointer text-xs text-slate-400 hover:text-slate-200 transition-colors">
                <input
                  type="checkbox"
                  checked={dryRun}
                  onChange={(e) => setDryRun(e.target.checked)}
                  className="rounded"
                />
                --dry-run
              </label>
              <label className="flex items-center gap-1.5 px-3 py-2.5 bg-slate-950 border border-slate-700 rounded-xl cursor-pointer text-xs text-slate-400 hover:text-slate-200 transition-colors">
                <input
                  type="checkbox"
                  checked={createBak}
                  onChange={(e) => setCreateBak(e.target.checked)}
                  className="rounded"
                />
                --bak
              </label>
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-400 mb-2 block opacity-0">_</label>
            <button
              type="button"
              onClick={runAll}
              disabled={!repoPath.trim()}
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-xl transition-all text-sm font-semibold"
            >
              <Play size={16} />
              Run All
            </button>
          </div>
        </div>
      </div>

      {/* Tool Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
        {ANALYSIS_TOOLS.map((tool) => {
          const state = states[tool.id] || "idle";
          const result = results[tool.id];
          const isExpanded = expanded[tool.id] ?? true;
          const Icon = tool.icon;
          const errorCount = result?.violations?.filter((f) => f.severity === "error").length ?? 0;
          const warnCount = result?.violations?.filter((f) => f.severity === "warning").length ?? 0;
          const sotaScore = result?.sota_score;
          const isRunt = result?.is_runt;
          const needsPath = tool.requiresPath && !repoPath.trim();
          const isLlmTool = tool.id === "llm-deep";

          return (
            <div
              key={tool.id}
              className={`bg-slate-900/50 border ${state === "done" && result?.success ? (isRunt ? "border-rose-500/30" : "border-emerald-500/20") : "border-slate-700"} rounded-xl overflow-hidden transition-colors`}
            >
              {/* Card Header */}
              <div className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`p-2.5 rounded-xl bg-slate-800 border border-slate-700 shrink-0`}
                    >
                      <Icon size={20} className="text-slate-300" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-base font-bold text-slate-200 truncate">
                        {tool.label}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5 leading-tight line-clamp-2">
                        {tool.description}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-wrap gap-2">
                  {!isLlmTool && (
                    <button
                      type="button"
                      disabled={state === "running" || needsPath}
                      onClick={() => runTool(tool)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all text-xs font-bold ${
                        state === "running"
                          ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                          : state === "done"
                            ? "bg-green-500/20 text-green-300 border border-green-500/30 hover:bg-green-500/30"
                            : state === "error"
                              ? "bg-red-500/20 text-red-300 border border-red-500/30 hover:bg-red-500/30"
                              : "bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700"
                      }`}
                    >
                      {state === "running" ? (
                        <>
                          <Loader2 size={12} className="animate-spin" /> Running...
                        </>
                      ) : (
                        <>
                          <Search size={12} />{" "}
                          {state === "done" ? "Re-scan" : state === "error" ? "Retry" : "Run"}
                        </>
                      )}
                    </button>
                  )}
                  {state === "done" && result?.success && !isLlmTool && (
                    <button
                      type="button"
                      onClick={() => sendToLlm(tool.id)}
                      disabled={llmLoading}
                      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-500/20 border border-purple-500/30 text-purple-300 hover:bg-purple-500/30 transition-all text-xs font-bold"
                    >
                      <Terminal size={12} />
                      Analyze with LLM
                    </button>
                  )}
                  {isLlmTool && llmAnalysis && (
                    <button
                      type="button"
                      onClick={() => setLlmAnalysis("")}
                      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700 transition-all text-xs font-bold"
                    >
                      <RefreshCw size={12} />
                      Clear
                    </button>
                  )}
                </div>

                {/* Status badges */}
                {state === "done" && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {isRunt !== undefined && (
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest border ${
                          isRunt
                            ? "bg-rose-500/20 text-rose-300 border-rose-500/30"
                            : "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                        }`}
                      >
                        {isRunt ? "RUNT" : "SOTA OK"}
                      </span>
                    )}
                    {sotaScore !== undefined && (
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest border ${
                          sotaScore >= 80
                            ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                            : sotaScore >= 50
                              ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
                              : "bg-red-500/20 text-red-300 border-red-500/30"
                        }`}
                      >
                        Score: {sotaScore}/100
                      </span>
                    )}
                    {errorCount > 0 && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest bg-red-500/20 text-red-300 border border-red-500/30">
                        {errorCount} critical
                      </span>
                    )}
                    {warnCount > 0 && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        {warnCount} warnings
                      </span>
                    )}
                    {errorCount === 0 && warnCount === 0 && !isRunt && sotaScore === undefined && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest bg-green-500/20 text-green-300 border border-green-500/30">
                        Clean
                      </span>
                    )}
                  </div>
                )}

                {/* Error */}
                {state === "error" && result && (
                  <div className="mt-3 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm">
                    {result.message || result.error}
                  </div>
                )}

                {/* LLM analysis output */}
                {tool.id === "llm-deep" && llmLoading && (
                  <div className="mt-3 p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-300 text-sm flex items-center gap-2">
                    <Loader2 size={14} className="animate-spin" />
                    Analyzing with LLM...
                  </div>
                )}
                {tool.id === "llm-deep" && llmAnalysis && !llmLoading && (
                  <div className="mt-3 p-3 rounded-xl bg-slate-800 border border-slate-700 text-sm">
                    <div className="prose prose-invert prose-p:text-slate-300 prose-headings:text-slate-100 max-w-none text-sm">
                      <ReactMarkdown>{llmAnalysis}</ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>

              {/* Expandable Findings */}
              <AnimatePresence>
                {result?.success && (result.violations || result.recommendations) && (
                  <motion.div initial={false} className="border-t border-slate-700">
                    <button
                      type="button"
                      onClick={() => setExpanded((e) => ({ ...e, [tool.id]: !isExpanded }))}
                      className="flex items-center gap-2 px-5 py-3 w-full text-left text-xs font-semibold text-slate-500 hover:text-slate-300 transition-colors"
                    >
                      {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      {result.violations?.length || 0} finding
                      {(result.violations?.length || 0) !== 1 ? "s" : ""}
                      {result.recommendations?.length
                        ? ` · ${result.recommendations.length} recommendations`
                        : ""}
                    </button>
                    {isExpanded && (
                      <div className="px-3 pb-3 space-y-1.5 max-h-[400px] overflow-y-auto custom-scrollbar">
                        {/* Runt reasons */}
                        {result.runt_reasons && result.runt_reasons.length > 0 && (
                          <div className="mb-3 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20">
                            <p className="text-[10px] font-black uppercase tracking-widest text-rose-400 mb-2">
                              Runt Reasons
                            </p>
                            {result.runt_reasons.map((r, i) => (
                              <p
                                key={i}
                                className="text-xs text-rose-300 flex items-start gap-2 mb-1"
                              >
                                <Flag size={12} className="shrink-0 mt-0.5" />
                                {r}
                              </p>
                            ))}
                          </div>
                        )}
                        {/* Findings */}
                        {result.violations?.map((f, i) => (
                          <div
                            key={i}
                            className={`flex items-start gap-2 px-3 py-2 rounded-lg border text-xs ${severityClass(f.severity)}`}
                          >
                            {severityIcon(f.severity)}
                            <div className="flex-1 min-w-0">
                              <span className="block">{f.message}</span>
                              {f.recommendation && (
                                <span className="text-[10px] text-slate-500 mt-0.5 block">
                                  Fix: {f.recommendation}
                                </span>
                              )}
                              {f.rule_id && (
                                <span className="text-[10px] text-slate-600 mt-0.5 block font-mono">
                                  {f.rule_id}
                                  {f.score_deduction ? ` (-${f.score_deduction} pts)` : ""}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                        {/* Recommendations */}
                        {result.recommendations && result.recommendations.length > 0 && (
                          <div className="mt-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                            <p className="text-[10px] font-black uppercase tracking-widest text-blue-400 mb-2">
                              Recommendations
                            </p>
                            {result.recommendations.map((r, i) => (
                              <p key={i} className="text-xs text-blue-300 mb-1">
                                • {r}
                              </p>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Summary KPIs for fleet-wide scans */}
              {result?.success && result.summary && Object.keys(result.summary).length > 0 && (
                <div className="px-5 pb-4">
                  <div className="flex flex-wrap gap-2 mt-1">
                    {Object.entries(result.summary).map(
                      ([k, v]) =>
                        v !== undefined &&
                        v !== null &&
                        typeof v !== "object" && (
                          <div
                            key={k}
                            className="text-[10px] text-slate-500 bg-slate-800 px-2 py-1 rounded"
                          >
                            <span className="text-slate-400 font-semibold">
                              {k.replace(/_/g, " ")}
                            </span>
                            : {String(v)}
                          </div>
                        ),
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div ref={resultsEndRef} />
    </div>
  );
}
