import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileCode,
  FileText,
  FolderOpen,
  Play,
  Search,
  Shield,
  Terminal,
  XCircle,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

interface Finding {
  severity: "error" | "warning" | "info";
  message: string;
  line?: number;
  file?: string;
  fixable?: boolean;
}

interface ScanResult {
  success: boolean;
  message: string;
  data?: Record<string, unknown>;
  findings?: Finding[];
}

const SCRUBBERS = [
  {
    id: "unicode",
    label: "Unicode Scanner",
    icon: FileText,
    description:
      "Scan for non-ASCII characters (emojis, em dashes, smart quotes) in logger/print calls",
    color: "from-blue-500",
    shadow: "shadow-blue-500/20",
    run: async (path: string) => {
      const r = await api.runEmojiBuster({ operation: "scan", repo_path: path });
      return parseResult(r);
    },
  },
  {
    id: "pwsh",
    label: "PowerShell Validator",
    icon: Terminal,
    description: "Check for Linux aliases (ls, grep, cat) in .ps1 files",
    color: "from-amber-500",
    shadow: "shadow-amber-500/20",
    run: async (path: string) => {
      const r = await api.runPowerShellTools({ operation: "validate", repo_path: path });
      return parseResult(r);
    },
  },
  {
    id: "justfile",
    label: "Justfile Validator",
    icon: FileCode,
    description: "Verify justfile fleet standards: required recipes, formatting, inline PowerShell",
    color: "from-emerald-500",
    shadow: "shadow-emerald-500/20",
    run: async (path: string) => {
      const r = await api.validateJustfile({ repo_path: path });
      return parseResult(r);
    },
  },
];

function parseResult(raw: {
  success?: boolean;
  message?: string;
  data?: unknown;
  result?: unknown;
}): ScanResult {
  if (raw.success === false) {
    return { success: false, message: String(raw.message || "Unknown error") };
  }
  const data = (raw.data ?? raw.result ?? {}) as Record<string, unknown>;
  const findings: Finding[] = [];
  const rawFindings = data.findings;
  if (Array.isArray(rawFindings)) {
    for (const f of rawFindings) {
      const fObj = f as Record<string, unknown>;
      findings.push({
        severity: (fObj.severity as Finding["severity"]) || "info",
        message: String(fObj.message || ""),
        line: fObj.line as number | undefined,
        file: fObj.file as string | undefined,
        fixable: fObj.fixable as boolean | undefined,
      });
    }
  }
  const rawUnicode = data.unicode_issues;
  if (Array.isArray(rawUnicode)) {
    for (const issue of rawUnicode) {
      const issueObj = issue as Record<string, unknown>;
      const file = String(issueObj.file || "");
      const issues = (issueObj.issues ?? []) as Record<string, unknown>[];
      for (const i of issues) {
        findings.push({
          severity: (i.risk_level as string) === "critical" ? "error" : "warning",
          message: `${String(i.unsafe_match || "")} at line ${String(i.line_number || "?")}`,
          line: i.line_number as number,
          file,
          fixable: true,
        });
      }
    }
  }
  return {
    success: true,
    message: String(data.message || raw.message || "Scan complete"),
    data,
    findings: findings.length > 0 ? findings : undefined,
  };
}

type ScrubberState = "idle" | "running" | "done" | "error";

export const ScrubbersPage: React.FC = () => {
  const [repoPath, setRepoPath] = useState("");
  const [recentPaths, setRecentPaths] = useState<string[]>([]);
  const [states, setStates] = useState<Record<string, ScrubberState>>({});
  const [results, setResults] = useState<Record<string, ScanResult | null>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const stored = localStorage.getItem("scrubber_recent_paths");
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
      localStorage.setItem("scrubber_recent_paths", JSON.stringify(updated));
    },
    [recentPaths],
  );

  const runScrubber = useCallback(
    async (id: string) => {
      if (!repoPath.trim()) return;
      setStates((s) => ({ ...s, [id]: "running" }));
      setResults((r) => ({ ...r, [id]: null }));
      try {
        const scrubber = SCRUBBERS.find((s) => s.id === id);
        if (!scrubber) return;
        const result = await scrubber.run(repoPath.trim());
        setResults((r) => ({ ...r, [id]: result }));
        setStates((s) => ({ ...s, [id]: result.success ? "done" : "error" }));
        setExpanded((e) => ({ ...e, [id]: true }));
        savePath(repoPath.trim());
      } catch (err) {
        setResults((r) => ({
          ...r,
          [id]: { success: false, message: String(err) },
        }));
        setStates((s) => ({ ...s, [id]: "error" }));
      }
    },
    [repoPath, savePath],
  );

  const runAll = useCallback(async () => {
    for (const s of SCRUBBERS) {
      await runScrubber(s.id);
    }
  }, [runScrubber]);

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
      <div className="glass-panel p-8 bg-white/[0.01] border-white/5">
        <div className="flex items-center gap-4 mb-4">
          <div className="p-3 bg-rose-500/20 rounded-xl border border-rose-500/30">
            <Shield className="text-white" size={28} />
          </div>
          <div>
            <h2 className="text-3xl font-black tracking-tight text-white">Scrubbers</h2>
            <p className="text-[#94a3b8] mt-1">
              Unicode safety, PowerShell compliance, and justfile standards — all in one place.
            </p>
          </div>
        </div>
      </div>

      {/* Repo Path */}
      <div className="glass-panel p-6 border-white/5">
        <label className="text-xs font-black uppercase tracking-widest text-[#94a3b8] mb-3 block">
          Repository Path
        </label>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <FolderOpen
              size={16}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-[#94a3b8]"
            />
            <input
              type="text"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") runAll();
              }}
              placeholder="D:\Dev\repos\database-operations-mcp"
              className="w-full bg-black/60 border border-white/10 text-white text-sm rounded-xl pl-12 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-[#00f3ff]/50 focus:border-blue-500/50"
            />
          </div>
          {recentPaths.length > 0 && (
            <select
              onChange={(e) => {
                if (e.target.value) setRepoPath(e.target.value);
              }}
              value=""
              className="bg-black/60 border border-white/10 text-white/60 text-sm rounded-xl px-3 py-3 focus:outline-none focus:ring-2 focus:ring-[#00f3ff]/50 cursor-pointer min-w-[40px]"
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
          )}
          <button
            type="button"
            onClick={runAll}
            disabled={!repoPath.trim()}
            className="flex items-center gap-2 px-6 py-3 bg-blue-500/20 border border-blue-500/30 rounded-xl hover:bg-blue-500/30 transition-all text-sm font-bold text-white disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Play size={16} />
            Run All
          </button>
        </div>
      </div>

      {/* Scrubber Cards */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {SCRUBBERS.map((scrubber) => {
          const state = states[scrubber.id] || "idle";
          const result = results[scrubber.id];
          const isExpanded = expanded[scrubber.id] ?? true;
          const Icon = scrubber.icon;
          const errorCount = result?.findings?.filter((f) => f.severity === "error").length ?? 0;
          const warnCount = result?.findings?.filter((f) => f.severity === "warning").length ?? 0;

          return (
            <div
              key={scrubber.id}
              className={`glass-panel border-white/5 bg-gradient-to-b ${scrubber.color}/5 to-transparent overflow-hidden`}
            >
              {/* Card Header */}
              <div className="p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2.5 rounded-xl bg-black/40 border border-white/5 ${scrubber.shadow}`}
                    >
                      <Icon size={20} className="text-white" />
                    </div>
                    <div>
                      <div className="text-base font-bold text-white">{scrubber.label}</div>
                      <div className="text-xs text-[#94a3b8] mt-0.5 max-w-[200px] leading-tight">
                        {scrubber.description}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={state === "running" || !repoPath.trim()}
                    onClick={() => runScrubber(scrubber.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all text-xs font-bold ${
                      state === "running"
                        ? "bg-white/5 text-[#94a3b8] cursor-not-allowed"
                        : state === "done"
                          ? "bg-green-500/20 text-green-300 border border-green-500/30 hover:bg-green-500/30"
                          : state === "error"
                            ? "bg-red-500/20 text-red-300 border border-red-500/30 hover:bg-red-500/30"
                            : "bg-white/10 text-white hover:bg-white/20 border border-white/10"
                    }`}
                  >
                    {state === "running" ? (
                      <>
                        <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Scanning...
                      </>
                    ) : (
                      <>
                        <Search size={12} />
                        {state === "done" ? "Re-scan" : state === "error" ? "Retry" : "Scan"}
                      </>
                    )}
                  </button>
                </div>

                {/* Status Tags */}
                {state === "done" && (
                  <div className="flex gap-2 mb-3">
                    {errorCount > 0 && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest bg-red-500/20 text-red-300 border border-red-500/30">
                        {errorCount} error{errorCount !== 1 ? "s" : ""}
                      </span>
                    )}
                    {warnCount > 0 && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        {warnCount} warning{warnCount !== 1 ? "s" : ""}
                      </span>
                    )}
                    {errorCount === 0 && warnCount === 0 && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest bg-green-500/20 text-green-300 border border-green-500/30">
                        Clean
                      </span>
                    )}
                  </div>
                )}

                {state === "error" && result && (
                  <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm">
                    {result.message}
                  </div>
                )}
              </div>

              {/* Results */}
              <AnimatePresence>
                {result?.findings && result.findings.length > 0 && (
                  <motion.div initial={false} className="border-t border-white/5">
                    <button
                      type="button"
                      onClick={() => setExpanded((e) => ({ ...e, [scrubber.id]: !isExpanded }))}
                      className="flex items-center gap-2 px-5 py-3 w-full text-left text-xs font-bold text-[#94a3b8] hover:text-white transition-colors"
                    >
                      {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      {result.findings.length} finding{result.findings.length !== 1 ? "s" : ""}
                    </button>
                    {isExpanded && (
                      <div className="px-3 pb-3 space-y-1">
                        {result.findings.map((f, i) => (
                          <div
                            key={i}
                            className={`flex items-start gap-2 px-3 py-2 rounded-lg border text-xs ${severityClass(f.severity)}`}
                          >
                            {severityIcon(f.severity)}
                            <div className="flex-1 min-w-0">
                              <span className="block truncate">{f.message}</span>
                              {(f.file || f.line) && (
                                <span className="text-[10px] opacity-60 mt-0.5 block">
                                  {f.file}
                                  {f.line ? `:${f.line}` : ""}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </div>
  );
};
