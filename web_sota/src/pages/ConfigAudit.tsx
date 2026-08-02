import { AlertTriangle, CheckCircle, Globe, Info, Layers, Search, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, isSuccessResponse } from "../api/client";

interface ConfigFileEntry {
  exists: boolean;
  last_modified: string;
  size_bytes: number;
  category: string;
  description: string;
}

interface RepoFiles {
  [relPath: string]: ConfigFileEntry;
}

interface RepoEntry {
  name: string;
  files: RepoFiles;
}

interface GlobalFiles {
  [key: string]: { exists: boolean; last_modified: string; size_bytes: number };
}

interface AuditReport {
  total_repos: number;
  repos: RepoEntry[];
  global_files: GlobalFiles;
  file_type_counts: { [relPath: string]: number };
  config_priority_chain: [string, string, string][];
}

const CONFIG_LABELS: Record<string, string> = {
  "CLAUDE.md": "CLAUDE.md",
  "AGENTS.md": "AGENTS.md",
  ".cursorrules": ".cursorrules",
  ".cursor/rules/": ".cursor/rules/",
  ".windsurfrules": ".windsurfrules",
  "llms.txt": "llms.txt",
  "llms-full.txt": "llms-full.txt",
  "glama.json": "glama.json",
  ".env.example": ".env.example",
  "CHANGELOG.md": "CHANGELOG.md",
};

const CONFIG_CATEGORIES = [
  { key: "agent", label: "Agent behavior", color: "text-blue-400" },
  { key: "discovery", label: "Discovery", color: "text-emerald-400" },
  { key: "metadata", label: "Metadata", color: "text-amber-400" },
];

const IMPORTANT_CONFIGS = [
  "CLAUDE.md",
  "AGENTS.md",
  ".cursorrules",
  "llms.txt",
  "llms-full.txt",
  "glama.json",
];

export function ConfigAuditPage() {
  const [report, setReport] = useState<AuditReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");
  const [showGlobal, setShowGlobal] = useState(false);
  const [showPriority, setShowPriority] = useState(false);

  const loadAudit = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await api.executeTool("meta_mcp", "fleet_config_audit", {});
      if (isSuccessResponse(resp)) {
        setReport(resp.data as unknown as AuditReport);
      } else {
        setError(resp.message || "Audit failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAudit();
  }, [loadAudit]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        <div className="animate-spin mr-2 h-5 w-5 border-b-2 border-current rounded-full" />
        Scanning fleet...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-red-400">
        <AlertTriangle size={20} className="mr-2" /> {error}
      </div>
    );
  }

  if (!report) return null;

  const configKeys = Object.keys(CONFIG_LABELS);
  const filteredRepos = filter
    ? report.repos.filter((r) => r.name.toLowerCase().includes(filter.toLowerCase()))
    : report.repos;

  return (
    <div className="space-y-6">
      <div className="bg-slate-900/50 border border-slate-700 rounded-2xl p-6">
        <div className="flex items-center gap-2 text-xs font-semibold text-blue-400 mb-3">
          <Layers size={14} /> Fleet Config Audit
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100 mb-1">Config Audit</h1>
            <p className="text-sm text-slate-400">
              {report.total_repos} repos scanned — agent behavioral files, discovery docs, and
              metadata
            </p>
          </div>
          <button
            type="button"
            onClick={loadAudit}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl text-sm transition-colors flex items-center gap-2"
          >
            <Search size={14} /> Rescan
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {configKeys
          .filter((k) => IMPORTANT_CONFIGS.includes(k))
          .map((key) => {
            const count = report.file_type_counts[key] || 0;
            const pct = Math.round((count / report.total_repos) * 100);
            const isRequired = key === "llms.txt" || key === "llms-full.txt";
            return (
              <div key={key} className="bg-slate-800/80 border border-slate-700 rounded-xl p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-mono font-medium text-slate-300">{key}</span>
                  {pct >= 90 ? (
                    <CheckCircle size={14} className="text-emerald-400" />
                  ) : isRequired && pct < 80 ? (
                    <XCircle size={14} className="text-red-400" />
                  ) : (
                    <AlertTriangle size={14} className="text-amber-400" />
                  )}
                </div>
                <div className="text-lg font-bold text-slate-100">
                  {count}
                  <span className="text-sm font-normal text-slate-500 ml-1">
                    /{report.total_repos}
                  </span>
                </div>
                <div className="text-xs text-slate-500">{pct}% adoption</div>
              </div>
            );
          })}
      </div>

      {/* Priority chain */}
      <div>
        <button
          type="button"
          onClick={() => setShowPriority(!showPriority)}
          className="flex items-center gap-2 text-sm font-medium text-slate-400 hover:text-slate-200 transition-colors"
        >
          <Info size={14} />
          Override priority chain for behavioral files {showPriority ? "▲" : "▼"}
        </button>
        {showPriority && (
          <div className="mt-2 bg-slate-800/60 border border-slate-700 rounded-xl p-4 space-y-2">
            {report.config_priority_chain.map(([name, scope, desc]) => (
              <div key={name} className="flex items-center gap-3 text-sm">
                <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-xs text-slate-400 shrink-0">
                  {report.config_priority_chain.indexOf([name, scope, desc]) + 1}
                </div>
                <div>
                  <span className="font-mono text-slate-300">{name}</span>
                  <span className="text-slate-500 mx-2">({scope})</span>
                  <span className="text-slate-500">{desc}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Global files */}
      <div>
        <button
          type="button"
          onClick={() => setShowGlobal(!showGlobal)}
          className="flex items-center gap-2 text-sm font-medium text-slate-400 hover:text-slate-200 transition-colors"
        >
          <Globe size={14} />
          Global files {showGlobal ? "▲" : "▼"}
        </button>
        {showGlobal && (
          <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {Object.entries(report.global_files).map(([key, entry]) => (
              <div key={key} className="bg-slate-800/60 border border-slate-700 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-mono font-medium text-slate-300">
                    {key.replace("global_", "")}
                  </span>
                  {entry.exists ? (
                    <CheckCircle size={14} className="text-emerald-400" />
                  ) : (
                    <XCircle size={14} className="text-slate-600" />
                  )}
                </div>
                <div className="text-sm text-slate-500">
                  {entry.exists
                    ? `${entry.last_modified}, ${(entry.size_bytes / 1024).toFixed(1)} KB`
                    : "Not found"}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Repo filter */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter repos..."
          className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-blue-500 placeholder:text-slate-600"
        />
      </div>

      {/* Config categories legend */}
      <div className="flex items-center gap-4 text-xs text-slate-500">
        {CONFIG_CATEGORIES.map((cat) => (
          <div key={cat.key} className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${cat.color} opacity-60`} />
            <span>{cat.label}</span>
          </div>
        ))}
      </div>

      {/* Config table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800">
              <th className="text-left py-2 pr-4 text-slate-500 font-medium sticky left-0 bg-[#0a0a0f] z-10">
                Repo
              </th>
              {configKeys.map((key) => (
                <th
                  key={key}
                  className="text-center py-2 px-2 text-slate-500 font-medium font-mono text-xs min-w-[60px]"
                >
                  {key}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredRepos.map((repo) => (
              <tr
                key={repo.name}
                className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
              >
                <td className="py-2 pr-4 text-slate-300 font-medium sticky left-0 bg-[#0a0a0f] z-10">
                  {repo.name}
                </td>
                {configKeys.map((key) => {
                  const file = repo.files[key];
                  const exists = file?.exists;
                  const cat = file?.category;
                  const isRequired = key === "llms.txt" || key === "llms-full.txt";
                  return (
                    <td key={key} className="text-center py-2 px-2">
                      {exists !== undefined && (
                        <div className="flex justify-center" title={file.description}>
                          {exists ? (
                            <CheckCircle
                              size={14}
                              className={
                                cat === "agent"
                                  ? "text-blue-500"
                                  : cat === "discovery"
                                    ? "text-emerald-500"
                                    : "text-amber-500"
                              }
                            />
                          ) : isRequired ? (
                            <XCircle size={14} className="text-red-500/50" />
                          ) : (
                            <span className="text-slate-700">-</span>
                          )}
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-slate-600">
        {filteredRepos.length} of {report.total_repos} repos shown
      </div>
    </div>
  );
}
