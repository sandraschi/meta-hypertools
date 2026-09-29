import { motion } from "framer-motion";
import {
  CheckCircle2,
  ClipboardList,
  Copy,
  ExternalLink,
  Loader2,
  Play,
  RefreshCw,
  Search,
  Terminal,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { JsonView } from "../components/common/JsonView";

interface RepoEntry {
  name: string;
  path: string;
  hasTimestamp: boolean;
}

const CATEGORIES = [
  {
    id: "1A",
    title: "Required Files",
    checks: [
      "pyproject.toml",
      "justfile",
      "llms.txt",
      "llms-full.txt",
      "glama.json",
      "start.ps1",
      "start.bat",
      "uv.lock",
      ".gitignore",
      ".env.example",
      ".cursorrules",
      "AGENTS.md",
      "CLAUDE.md",
      "bun.lock",
      ".claude-plugin/plugin.json",
      ".pre-commit-config.yaml",
    ],
  },
  {
    id: "1B",
    title: "Tool Surface",
    checks: [
      "help/status tool",
      "Portmanteau if >15 tools",
      "## Return Format in docstrings",
      "## Examples in docstrings",
      "No Args: blocks",
      "Prefab cards on list/status tools",
      "Tool annotations",
      "Dialogic returns {success,message,data}",
      "GET /api/v1/diagnostics",
      "Error helper with auto-logging",
    ],
  },
  {
    id: "1C",
    title: "Testing",
    checks: [
      "Has tests",
      "Tests pass",
      "Coverage config",
      "Playwright E2E config",
      "Playwright E2E tests",
    ],
  },
  {
    id: "1D",
    title: "Webapp SOTA",
    checks: [
      "React+Vite+Tailwind+Zustand",
      "Dark theme, color-scheme:dark",
      "All mandatory pages",
      "Skill-first Chat",
      "Local LLM glom-on",
      "data-testid coverage",
      "Logger modal",
      "Help modal",
      "Multiple .env antipattern check",
      "Zustand LLM state",
      "Tauri listen() pattern",
      "Apps Hub dynamic discovery",
      "Keyboard shortcuts",
    ],
  },
  {
    id: "1E",
    title: "REST API Endpoints",
    checks: [
      "GET /health",
      "GET /api/status",
      "POST /api/chat",
      "GET /api/skills",
      "GET /api/llm/discover",
      "GET /docs (Swagger)",
      "GET /api/v1/diagnostics",
      "Self-termination endpoint",
    ],
  },
  {
    id: "1F",
    title: "CORS",
    checks: [
      'No allow_origins=["*"]',
      "Unconditional allow_origin_regex",
      "tauri://localhost origins",
      "No run_http_async()",
    ],
  },
  {
    id: "1G",
    title: "Security",
    checks: [
      "build.ps1 bundles .env.example, not .env",
      ".env.example at repo root",
      "No hardcoded secrets",
      ".gitignore covers *.mcpb, native/target/",
    ],
  },
  {
    id: "1H",
    title: "Tauri / Native",
    checks: [
      "free_port() multi-layer kill",
      "Stream watching + health poll",
      "hooks.nsh process names correct",
      "tauri.conf.json targets nsis",
      "Frontend useZoom() hook",
      "Backend-status listener",
      "CUA smoke test",
    ],
  },
  {
    id: "1I",
    title: "FastMCP Features",
    checks: [
      "FastMCP >=3.4.2",
      "ctx.sample()",
      "Agentic workflow tools",
      "SkillsDirectoryProvider",
      "@mcp.prompt() templates",
      "@mcp.resource() resources",
      "Prefab UI in core deps",
      "Tool annotations",
      "Pydantic v2 patterns",
    ],
  },
  {
    id: "1K",
    title: "Error Handling",
    checks: [
      "No bare except:pass",
      "Module-import functions raise",
      "_error_response() with logger.exception()",
      "Configured logger",
    ],
  },
  {
    id: "1P",
    title: "Dashboard & LLM",
    checks: [
      "No hardcoded ports/versions",
      "Hero section on dashboard",
      "LLM auto-detect (Ollama/LM Studio)",
      "Zero-config binding",
      "Graceful fallback",
      "GPU detection",
      "GPU opportunity prompt",
      "Settings with Local+Cloud config",
    ],
  },
  {
    id: "1S",
    title: "Session Context",
    checks: [
      ".claude-plugin/plugin.json + hooks",
      ".cursorrules with ## Session Context",
      ".windsurfrules (copy)",
      ".github/copilot-instructions.md",
      ".opencode/skills/ SKILL.md",
    ],
  },
];

const SOP_INTRO =
  "The Assess & Fix SOP audits a repo against every fleet standard, fixes in severity order, lints, syncs docs, builds packages, and pushes. The full flow (Phases 1-6) runs via the `assess and fix` LLM macro in opencode/Claude. The read-only assessment (Phase 1) can be triggered from here.";

const SOP_SECTIONS = [
  {
    title: "Phase 1 — Assess",
    desc: "Read-only audit across 19 categories. Score out of 100 (>=80 = SOTA, 60-79 = needs work, <60 = runt). Report saved to docs/assess-reports/. Runnable from this page.",
  },
  {
    title: "Phase 2 — Fix",
    desc: "Fix in severity order: CRITICAL -> HIGH -> MEDIUM -> LOW. Requires LLM reasoning — run `assess and fix <repo>` in opencode/Claude.",
  },
  {
    title: "Phase 3 — Lint & Typecheck",
    desc: "ruff check --fix, ruff format, npx tsc --noEmit, npx biome check. Iterate until clean.",
  },
  {
    title: "Phase 4 — Docs Sync",
    desc: "README, CHANGELOG, llms-full.txt, mcp-central-docs project page synced with current state.",
  },
  {
    title: "Phase 5 — Build MCPB",
    desc: "Verify manifest.json, assets/icon.png, src/ is self-contained. Run mcpb pack. Skip if .nopublish.",
  },
  {
    title: "Phase 6 — Verify & Push",
    desc: "Run all gates. Write .assess-fix-timestamp. git add, commit, push. Report what was done.",
  },
];

export function AssfixSOPPage() {
  const [repos, setRepos] = useState<RepoEntry[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [assessing, setAssessing] = useState(false);
  const [assessmentResult, setAssessmentResult] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedCat, setExpandedCat] = useState<string | null>(null);

  const fetchRepos = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch("/api/v1/repos/scan?root=D:\\Dev\\repos&depth=1");
      if (resp.ok) {
        const data = await resp.json();
        const list: RepoEntry[] = (data?.repos ?? data?.data ?? []).map(
          (r: { name?: string; path?: string }) => ({
            name: r.name ?? r.path?.split("\\").pop() ?? "unknown",
            path: r.path ?? "",
            hasTimestamp: false,
          }),
        );
        setRepos(list.sort((a: RepoEntry, b: RepoEntry) => a.name.localeCompare(b.name)));
      }
    } catch {
      const fs = await fetch("/api/v1/tools/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ server_id: "metaops", tool: "list_mcp_servers", params: {} }),
      });
      if (fs.ok) {
        const data = await fs.json();
        const servers = (data?.result ?? data?.data ?? []).map(
          (s: { server_id?: string; name?: string }) => s.server_id ?? s.name ?? "",
        );
        const fallback = [
          "arxiv-mcp",
          "calibre-mcp",
          "email-mcp",
          "git-github-mcp",
          "kicad-mcp",
          "libreoffice-mcp",
          "plex-mcp",
          "pywinauto-mcp",
        ];
        const names = servers.length > 0 ? servers : fallback;
        setRepos(
          names.map((n: string) => ({
            name: n,
            path: `D:\\Dev\\repos\\${n}`,
            hasTimestamp: false,
          })),
        );
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRepos();
  }, [fetchRepos]);

  const copyAssfixCmd = () => {
    if (!selectedRepo) return;
    navigator.clipboard.writeText(`assess and fix ${selectedRepo}`).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const runAssessment = async () => {
    if (!selectedRepo) return;
    setAssessing(true);
    setAssessmentResult(null);
    try {
      const resp = await fetch("/api/v1/analysis/repo-status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo: selectedRepo, path: `D:\\Dev\\repos\\${selectedRepo}` }),
      });
      if (resp.ok) {
        const data = await resp.json();
        const text = typeof data === "string" ? data : JSON.stringify(data, null, 2);
        setAssessmentResult(text.slice(0, 5000));
      } else {
        const text = await resp.text();
        setAssessmentResult(`API error ${resp.status}: ${text.slice(0, 500)}`);
      }
    } catch (err) {
      setAssessmentResult(`Failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setAssessing(false);
    }
  };

  const filtered = CATEGORIES.filter(
    (c) =>
      !searchQuery ||
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.checks.some((ch) => ch.toLowerCase().includes(searchQuery.toLowerCase())),
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 max-w-6xl"
    >
      {/* Header + Repo selector */}
      <div className="mb-6 flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
            <ClipboardList size={20} className="text-blue-400" />
            Assess & Fix SOP
          </h1>
          <p className="text-sm text-slate-400 mt-0.5 max-w-2xl">{SOP_INTRO}</p>
        </div>
        <button
          onClick={fetchRepos}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm rounded-md transition-colors"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Repo selector + action buttons */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 mb-6">
        <div className="flex items-end gap-4 flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs text-slate-500 mb-1 font-medium">
              Select Repository
            </label>
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="">-- Choose a repo --</option>
              {repos.map((r) => (
                <option key={r.name} value={r.name}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={runAssessment}
            disabled={!selectedRepo || assessing}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {assessing ? <Loader2 size={14} className="animate-spin" /> : <Terminal size={14} />}
            {assessing ? "Scanning..." : "Run Read-Only Assessment"}
          </button>
          <button
            type="button"
            onClick={copyAssfixCmd}
            disabled={!selectedRepo}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {copied ? <CheckCircle2 size={14} className="text-green-300" /> : <Copy size={14} />}
            {copied ? "Copied!" : "Copy Assfix Command"}
          </button>
        </div>
        <div className="mt-2 flex items-center gap-3 text-xs text-slate-600">
          <span className="flex items-center gap-1">
            <Terminal size={10} /> Phase 1 runs here
          </span>
          <span className="text-slate-700">|</span>
          <span className="flex items-center gap-1">
            <Play size={10} /> Phases 2-6 need LLM — paste in opencode/Claude
          </span>
        </div>
      </div>

      {/* Assessment result */}
      {assessmentResult && (
        <div className="bg-slate-950 border border-slate-700 rounded-lg p-4 mb-6 max-h-96 overflow-auto">
          <div className="text-xs font-medium text-slate-400 mb-2">Assessment Result</div>
          <JsonView value={assessmentResult} className="text-xs text-slate-300" />
        </div>
      )}

      {/* SOP Phases */}
      <div className="mb-6">
        <h2 className="text-sm font-semibold text-slate-300 mb-3">Pipeline Phases</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {SOP_SECTIONS.map((s) => (
            <div key={s.title} className="bg-slate-900 border border-slate-800 rounded-lg p-3">
              <div className="text-xs font-medium text-blue-400 mb-1">{s.title}</div>
              <div className="text-xs text-slate-400 leading-relaxed">{s.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search categories or checks..."
          className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* Category checklist */}
      <div className="space-y-2">
        {filtered.map((cat) => (
          <div
            key={cat.id}
            className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden"
          >
            <button
              type="button"
              onClick={() => setExpandedCat(expandedCat === cat.id ? null : cat.id)}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-slate-800/50 transition-colors"
            >
              <span className="text-xs font-mono text-blue-500 w-8">{cat.id}</span>
              <span className="text-sm font-medium text-slate-200">{cat.title}</span>
              <span className="text-xs text-slate-500 ml-auto">{cat.checks.length} checks</span>
            </button>
            {expandedCat === cat.id && (
              <div className="px-4 pb-3 grid grid-cols-1 sm:grid-cols-2 gap-1">
                {cat.checks.map((ch) => (
                  <div key={ch} className="flex items-center gap-2 text-xs text-slate-400 py-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-600 shrink-0" />
                    {ch}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer link */}
      <div className="mt-6 text-xs text-slate-600 flex items-center gap-2">
        <ExternalLink size={12} />
        <span>Canonical SOP:</span>
        <code className="font-mono text-slate-500">
          mcp-central-docs/patterns/repo-assess-and-fix.md
        </code>
      </div>
    </motion.div>
  );
}
