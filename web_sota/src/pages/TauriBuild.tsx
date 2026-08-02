import { motion } from "framer-motion";
import {
  ClipboardList,
  Cpu,
  Hammer,
  Loader2,
  Package,
  Play,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { useCallback, useState } from "react";
import { api } from "../api/client";

type RepoInfo = {
  name: string;
  root: string;
  backend_port: number;
  frontend_port: number;
  status: "none" | "scaffolded" | "built" | "error";
  has_nsis: boolean;
};

type LogLine = { kind: "info" | "ok" | "warn" | "err" | "dry"; text: string };

const PRIORITY_REPOS: RepoInfo[] = [
  {
    name: "scraper-mcp",
    root: "D:\\Dev\\repos\\scraper-mcp",
    backend_port: 10998,
    frontend_port: 10999,
    status: "none",
    has_nsis: false,
  },
  {
    name: "email-mcp",
    root: "D:\\Dev\\repos\\email-mcp",
    backend_port: 10813,
    frontend_port: 10812,
    status: "none",
    has_nsis: false,
  },
  {
    name: "aiwatcher-mcp",
    root: "D:\\Dev\\repos\\aiwatcher-mcp",
    backend_port: 10946,
    frontend_port: 10947,
    status: "none",
    has_nsis: false,
  },
  {
    name: "glama-status-mcp",
    root: "D:\\Dev\\repos\\glama-status-mcp",
    backend_port: 11072,
    frontend_port: 11073,
    status: "none",
    has_nsis: false,
  },
  {
    name: "arr-mcp",
    root: "D:\\Dev\\repos\\arr-mcp",
    backend_port: 10938,
    frontend_port: 10939,
    status: "none",
    has_nsis: false,
  },
  {
    name: "browser-mcp",
    root: "D:\\Dev\\repos\\browser-mcp",
    backend_port: 10780,
    frontend_port: 10781,
    status: "none",
    has_nsis: false,
  },
  {
    name: "calibre-mcp",
    root: "D:\\Dev\\repos\\calibre-mcp",
    backend_port: 10720,
    frontend_port: 10721,
    status: "none",
    has_nsis: false,
  },
  {
    name: "jellyfin-mcp",
    root: "D:\\Dev\\repos\\jellyfin-mcp",
    backend_port: 10934,
    frontend_port: 10935,
    status: "none",
    has_nsis: false,
  },
  {
    name: "multi-backup-mcp",
    root: "D:\\Dev\\repos\\multi-backup-mcp",
    backend_port: 10799,
    frontend_port: 10798,
    status: "none",
    has_nsis: false,
  },
  {
    name: "documentation-mcp",
    root: "D:\\Dev\\repos\\documentation-mcp",
    backend_port: 10795,
    frontend_port: 10794,
    status: "none",
    has_nsis: false,
  },
  {
    name: "godot-mcp",
    root: "D:\\Dev\\repos\\godot-mcp",
    backend_port: 10993,
    frontend_port: 10992,
    status: "none",
    has_nsis: false,
  },
  {
    name: "beyondcompare-mcp",
    root: "D:\\Dev\\repos\\beyondcompare-mcp",
    backend_port: 10841,
    frontend_port: 10840,
    status: "none",
    has_nsis: false,
  },
  {
    name: "blender-mcp",
    root: "D:\\Dev\\repos\\blender-mcp",
    backend_port: 10849,
    frontend_port: 10848,
    status: "none",
    has_nsis: false,
  },
  {
    name: "freecad-mcp",
    root: "D:\\Dev\\repos\\freecad-mcp",
    backend_port: 10944,
    frontend_port: 10945,
    status: "none",
    has_nsis: false,
  },
  {
    name: "qcad-mcp",
    root: "D:\\Dev\\repos\\qcad-mcp",
    backend_port: 10966,
    frontend_port: 10967,
    status: "none",
    has_nsis: false,
  },
  {
    name: "filesystem-mcp",
    root: "D:\\Dev\\repos\\filesystem-mcp",
    backend_port: 10742,
    frontend_port: 10743,
    status: "none",
    has_nsis: false,
  },
  {
    name: "docker-mcp",
    root: "D:\\Dev\\repos\\docker-mcp",
    backend_port: 10806,
    frontend_port: 10807,
    status: "none",
    has_nsis: false,
  },
  {
    name: "notion-mcp",
    root: "D:\\Dev\\repos\\notion-mcp",
    backend_port: 10811,
    frontend_port: 10810,
    status: "none",
    has_nsis: false,
  },
  {
    name: "obsidian-mcp",
    root: "D:\\Dev\\repos\\obsidian-mcp",
    backend_port: 10915,
    frontend_port: 10890,
    status: "none",
    has_nsis: false,
  },
  {
    name: "reversing-mcp",
    root: "D:\\Dev\\repos\\reversing-mcp",
    backend_port: 10750,
    frontend_port: 10751,
    status: "none",
    has_nsis: false,
  },
];

function statusColor(s: string) {
  switch (s) {
    case "none":
      return "bg-zinc-800 text-zinc-400";
    case "scaffolded":
      return "bg-blue-900/50 text-blue-300";
    case "built":
      return "bg-green-900/50 text-green-300";
    case "error":
      return "bg-red-900/50 text-red-300";
    default:
      return "bg-zinc-800 text-zinc-400";
  }
}

export default function TauriBuildPage() {
  const [repos, setRepos] = useState<RepoInfo[]>(PRIORITY_REPOS);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"repos" | "logs">("repos");

  const log = useCallback((kind: LogLine["kind"], text: string) => {
    setLogs((prev) => [...prev.slice(-500), { kind, text }]);
  }, []);

  const runAction = useCallback(
    async (repo: RepoInfo, mode: string) => {
      setBusy(`${repo.name}:${mode}`);
      log("info", `[${repo.name}] --mode ${mode} -- starting`);
      try {
        const resp = await api.scaffoldTauriNsis({
          repo_root: repo.root,
          repo_name: repo.name,
          backend_port: repo.backend_port,
          frontend_port: repo.frontend_port,
          mode,
        });
        const data = typeof resp === "string" ? JSON.parse(resp) : resp;
        if (data.report) {
          for (const r of data.report) {
            const kind =
              r.status === "OK"
                ? "ok"
                : r.status === "WARN"
                  ? "warn"
                  : r.status === "ERR"
                    ? "err"
                    : "info";
            log(kind, `[${repo.name}] ${r.category}: ${r.detail}`);
          }
        }
        if (data.success) {
          log("ok", `[${repo.name}] --mode ${mode} -- success`);
          setRepos((prev) =>
            prev.map((r) =>
              r.name === repo.name
                ? {
                    ...r,
                    status:
                      mode === "scaffold" ? "scaffolded" : mode === "build" ? "built" : r.status,
                  }
                : r,
            ),
          );
        } else {
          log("err", `[${repo.name}] --mode ${mode} -- failed (exit ${data.exit_code})`);
          setRepos((prev) =>
            prev.map((r) => (r.name === repo.name ? { ...r, status: "error" } : r)),
          );
        }
      } catch (e) {
        log(
          "err",
          `[${repo.name}] --mode ${mode} -- ${e instanceof Error ? e.message : String(e)}`,
        );
        setRepos((prev) => prev.map((r) => (r.name === repo.name ? { ...r, status: "error" } : r)));
      }
      setBusy(null);
    },
    [log],
  );

  const isBusy = (repo: RepoInfo, mode: string) => busy === `${repo.name}:${mode}`;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Tauri NSIS Build</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Scaffold, build, and test desktop installers for fleet MCP repos
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => runAction(repos[0], "check")}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg text-sm transition-colors"
          >
            <Cpu size={16} /> Pre-flight Check
          </button>
          <button
            onClick={() => setLogs([])}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg text-sm transition-colors"
          >
            <RotateCcw size={16} /> Clear Logs
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-zinc-900 rounded-lg p-1 w-fit">
        {[
          { id: "repos" as const, label: "Repos", icon: Package },
          { id: "logs" as const, label: "Logs", icon: ClipboardList },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-colors ${
              activeTab === tab.id ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <tab.icon size={16} /> {tab.label}{" "}
            {tab.id === "logs" && logs.length > 0 && (
              <span className="text-xs bg-zinc-700 px-1.5 py-0.5 rounded">{logs.length}</span>
            )}
          </button>
        ))}
      </div>

      {activeTab === "repos" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {repos.map((repo) => (
            <motion.div
              key={repo.name}
              layout
              className="bg-zinc-900/80 border border-zinc-800 rounded-xl p-4 space-y-3 hover:border-zinc-700 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-zinc-100 font-medium">{repo.name}</h3>
                  <p className="text-xs text-zinc-500">
                    :{repo.backend_port}
                    {repo.frontend_port > 0 ? ` / :${repo.frontend_port}` : ""}
                  </p>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${statusColor(repo.status)}`}>
                  {repo.status}
                </span>
              </div>
              <p className="text-xs text-zinc-600 truncate">{repo.root}</p>
              <div className="flex flex-wrap gap-1.5 pt-1">
                <button
                  onClick={() => runAction(repo, "scaffold")}
                  disabled={busy !== null}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 rounded-lg text-xs transition-colors disabled:opacity-40"
                >
                  {isBusy(repo, "scaffold") ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Hammer size={14} />
                  )}
                  Scaffold
                </button>
                <button
                  onClick={() => runAction(repo, "dryrun")}
                  disabled={busy !== null}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-xs transition-colors disabled:opacity-40"
                >
                  <ClipboardList size={14} /> Dry
                </button>
                <button
                  onClick={() => runAction(repo, "build")}
                  disabled={busy !== null}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600/20 hover:bg-green-600/30 text-green-300 rounded-lg text-xs transition-colors disabled:opacity-40"
                >
                  {isBusy(repo, "build") ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Play size={14} />
                  )}
                  Build
                </button>
                <button
                  onClick={() => runAction(repo, "undo")}
                  disabled={busy !== null}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600/20 hover:bg-red-600/30 text-red-300 rounded-lg text-xs transition-colors disabled:opacity-40"
                >
                  <Trash2 size={14} /> Undo
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {activeTab === "logs" && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          {logs.length === 0 ? (
            <div className="text-center py-20 text-zinc-600">
              <ClipboardList size={48} className="mx-auto mb-3 opacity-30" />
              <p>No logs yet. Run an action to see output here.</p>
            </div>
          ) : (
            <div className="bg-black/60 rounded-xl p-4 font-mono text-xs leading-relaxed max-h-[70vh] overflow-y-auto space-y-0.5">
              {logs.map((line, i) => (
                <div
                  key={i}
                  className={`${
                    line.kind === "ok"
                      ? "text-green-400"
                      : line.kind === "warn"
                        ? "text-yellow-400"
                        : line.kind === "err"
                          ? "text-red-400"
                          : line.kind === "dry"
                            ? "text-cyan-400"
                            : "text-zinc-400"
                  }`}
                >
                  {line.text}
                </div>
              ))}
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
