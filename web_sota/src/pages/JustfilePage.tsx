import { motion } from "framer-motion";
import { CheckCircle2, Copy, ExternalLink, Search, Terminal } from "lucide-react";
import { useState } from "react";

interface Recipe {
  name: string;
  doc: string;
  args: string[];
  category: string;
}

const CATEGORIES: Record<string, string> = {
  mcd: "MCD Local",
  fleet: "Fleet Discovery",
  lint: "Linters",
  rag: "RAG",
  webapp: "Webapp",
  security: "Security",
  util: "Utilities",
  maintenance: "Maintenance",
};

const RECIPES: Recipe[] = [
  {
    name: "default",
    doc: "Fleet Command dashboard (recipe browser on :11031)",
    args: [],
    category: "mcd",
  },
  {
    name: "dashboard",
    doc: "Open interactive Fleet Command Dashboard in browser",
    args: [],
    category: "mcd",
  },
  { name: "help", doc: "Print available recipes", args: [], category: "mcd" },
  { name: "search", doc: "Semantic search across docs", args: ["query"], category: "mcd" },
  { name: "semantic", doc: "RAG answer via local Ollama", args: ["query"], category: "mcd" },
  { name: "report", doc: "Multi-pass research report", args: ["topic"], category: "mcd" },
  { name: "stats", doc: "Quantitative snapshot of docs and tools", args: [], category: "mcd" },
  { name: "list-all", doc: "List all fleet repos with metadata", args: [], category: "fleet" },
  {
    name: "do",
    doc: "Run a just recipe on a specific repo",
    args: ["repo", "recipe"],
    category: "fleet",
  },
  {
    name: "start",
    doc: "Start a repo's webapp (backend + frontend)",
    args: ["repo"],
    category: "fleet",
  },
  {
    name: "ps-lint",
    doc: "Lint PowerShell scripts (PSScriptAnalyzer)",
    args: [],
    category: "lint",
  },
  { name: "md-lint", doc: "Lint markdown files", args: [], category: "lint" },
  { name: "yml-lint", doc: "Lint YAML files", args: [], category: "lint" },
  { name: "toml-lint", doc: "Lint TOML files", args: [], category: "lint" },
  { name: "docker-lint", doc: "Lint Dockerfiles", args: [], category: "lint" },
  { name: "sh-lint", doc: "Lint shell scripts", args: [], category: "lint" },
  { name: "gha-lint", doc: "Lint GitHub Actions", args: [], category: "lint" },
  { name: "lint-all", doc: "Run all linters (pass/fail summary)", args: [], category: "lint" },
  { name: "start-webapp", doc: "Start MCD webapp on :10794", args: [], category: "mcd" },
  { name: "view", doc: "Open MCD webapp in browser", args: [], category: "mcd" },
  { name: "rag", doc: "RAG sync all docs", args: [], category: "rag" },
  { name: "rag-gpu", doc: "RAG sync using GPU embeddings", args: [], category: "rag" },
  { name: "rag-gpu-install", doc: "Install GPU RAG dependencies", args: [], category: "rag" },
  { name: "rag-cpu-install", doc: "Install CPU RAG dependencies", args: [], category: "rag" },
  { name: "rag-path", doc: "RAG sync a specific path", args: ["path"], category: "rag" },
  { name: "rag-recent", doc: "RAG sync recent changes", args: ["hours"], category: "rag" },
  { name: "rag-repo", doc: "RAG sync a specific repo", args: ["repo"], category: "rag" },
  { name: "rag-repo-force", doc: "Force re-index a repo", args: ["repo"], category: "rag" },
  { name: "rag-stats", doc: "RAG index statistics", args: [], category: "rag" },
  {
    name: "webapp-fix",
    doc: "Improve a repo's webapp via headless Playwright",
    args: ["repo"],
    category: "webapp",
  },
  { name: "fleet-security-scan", doc: "Full fleet security scan", args: [], category: "security" },
  {
    name: "fleet-security-scan-mcp",
    doc: "Security scan (MCP servers only)",
    args: [],
    category: "security",
  },
  {
    name: "fleet-security-scan-one",
    doc: "Security scan a single repo",
    args: ["repo"],
    category: "security",
  },
  { name: "fleet-trinity-audit", doc: "Fleet-wide trinity audit", args: [], category: "security" },
  { name: "heartbeat", doc: "Ping all fleet MCP servers", args: [], category: "util" },
  { name: "sync-all", doc: "Git pull all fleet repos", args: [], category: "util" },
  { name: "kill-all", doc: "Kill all MCP server processes", args: [], category: "util" },
  {
    name: "clean-all",
    doc: "Clean all build artifacts across fleet",
    args: [],
    category: "maintenance",
  },
];

const NOTABLE_RECIPES = [
  {
    name: "assess and fix <repo>",
    doc: "Full repo audit, fix, docs, build, push (opencode macro)",
    icon: "Play",
  },
  {
    name: "just do <repo> <recipe>",
    doc: "Run any just recipe on any fleet repo remotely",
    icon: "Terminal",
  },
  {
    name: "just start <repo>",
    doc: "Start a repo's full webapp stack (backend + frontend)",
    icon: "Terminal",
  },
  {
    name: "just webapp-fix <repo>",
    doc: "Headless Playwright audit + fix loop for a webapp",
    icon: "Terminal",
  },
  { name: "just lint-all", doc: "Run all 7 linters on the current repo", icon: "Terminal" },
];

export function JustfilePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRecipe, setSelectedRecipe] = useState("");
  const [repoName, setRepoName] = useState("");
  const [copied, setCopied] = useState(false);
  const [expandedCat, setExpandedCat] = useState<string | null>("mcd");

  const filtered = Object.entries(
    RECIPES.reduce<Record<string, Recipe[]>>((acc, r) => {
      if (
        !searchQuery ||
        r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.doc.toLowerCase().includes(searchQuery.toLowerCase())
      ) {
        (acc[r.category] = acc[r.category] || []).push(r);
      }
      return acc;
    }, {}),
  );

  const runRecipe = () => {
    if (!selectedRecipe) return;
    const needsRepo = RECIPES.find((r) => r.name === selectedRecipe)?.args.includes("repo");
    const cmd =
      needsRepo && repoName ? `just ${selectedRecipe} ${repoName}` : `just ${selectedRecipe}`;
    navigator.clipboard.writeText(cmd).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 max-w-6xl"
    >
      <div className="mb-6 flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
            <Terminal size={20} className="text-blue-400" />
            Fleet Justfile
          </h1>
          <p className="text-sm text-slate-400 mt-0.5 max-w-2xl">
            Fleet-wide task runner. All recipes delegate to{" "}
            <code className="font-mono text-xs text-slate-500">scripts/just/*.ps1</code> for
            reliable PowerShell execution.
          </p>
        </div>
      </div>

      {/* Run bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 mb-6 flex items-center gap-4 flex-wrap">
        <div className="min-w-[180px] flex-1">
          <label className="block text-xs text-slate-500 mb-1 font-medium">Recipe</label>
          <select
            value={selectedRecipe}
            onChange={(e) => setSelectedRecipe(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
          >
            <option value="">-- Choose a recipe --</option>
            {RECIPES.map((r) => (
              <option key={r.name} value={r.name}>
                {r.name}
                {r.args.length > 0 ? ` <${r.args.join("> <")}>` : ""}
              </option>
            ))}
          </select>
        </div>
        {selectedRecipe &&
          RECIPES.find((r) => r.name === selectedRecipe)?.args.includes("repo") && (
            <div className="min-w-[160px]">
              <label className="block text-xs text-slate-500 mb-1 font-medium">Repo</label>
              <input
                type="text"
                value={repoName}
                onChange={(e) => setRepoName(e.target.value)}
                placeholder="repo-name"
                className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>
          )}
        <button
          type="button"
          onClick={runRecipe}
          disabled={!selectedRecipe}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-colors mt-5"
        >
          {copied ? <CheckCircle2 size={16} className="text-green-300" /> : <Copy size={16} />}
          {copied ? "Copied!" : "Copy Command"}
        </button>
        {selectedRecipe && (
          <span className="text-xs text-slate-500 mt-5 font-mono bg-slate-950 px-2 py-1 rounded border border-slate-700">
            {RECIPES.find((r) => r.name === selectedRecipe)?.args.includes("repo") && repoName
              ? `just ${selectedRecipe} ${repoName}`
              : `just ${selectedRecipe}`}
          </span>
        )}
      </div>

      {/* Notable macros */}
      <div className="mb-6">
        <h2 className="text-sm font-semibold text-slate-300 mb-3">Notable Fleet Macros</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {NOTABLE_RECIPES.map((nr) => (
            <button
              key={nr.name}
              type="button"
              onClick={() => {
                navigator.clipboard.writeText(nr.name);
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              }}
              className="bg-slate-900 border border-slate-800 hover:border-blue-500/40 rounded-lg p-3 text-left transition-colors group"
            >
              <div className="text-xs font-mono text-blue-400 group-hover:text-blue-300 mb-1">
                {nr.name}
              </div>
              <div className="text-xs text-slate-500">{nr.doc}</div>
            </button>
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
          placeholder="Search recipes..."
          className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* Recipes by category */}
      <div className="space-y-2">
        {filtered.map(([cat, recipes]) => (
          <div
            key={cat}
            className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden"
          >
            <button
              type="button"
              onClick={() => setExpandedCat(expandedCat === cat ? null : cat)}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-slate-800/50 transition-colors"
            >
              <span className="text-sm font-medium text-slate-200">{CATEGORIES[cat] ?? cat}</span>
              <span className="text-xs text-slate-500">{recipes.length} recipes</span>
              <span className="text-xs text-slate-600 ml-auto">
                {expandedCat === cat ? "collapse" : "expand"}
              </span>
            </button>
            {expandedCat === cat && (
              <div className="px-4 pb-3 space-y-1">
                {recipes.map((r) => (
                  <div
                    key={r.name}
                    className="flex items-center gap-3 py-1.5 px-2 rounded hover:bg-slate-800/40 transition-colors"
                  >
                    <code className="text-xs font-mono text-blue-400/80 w-40 shrink-0">
                      {r.name}
                      {r.args.length > 0 ? ` <${r.args.join("> <")}>` : ""}
                    </code>
                    <span className="text-xs text-slate-400 flex-1">{r.doc}</span>
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText(`just ${r.name}`);
                        setCopied(true);
                        setTimeout(() => setCopied(false), 1000);
                      }}
                      className="text-slate-600 hover:text-slate-300 p-1"
                      title="Copy command"
                    >
                      <Copy size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 text-xs text-slate-600 flex items-center gap-2">
        <ExternalLink size={12} />
        <span>Canonical justfile:</span>
        <code className="font-mono text-slate-500">mcp-central-docs/justfile</code>
        <span className="ml-2">Imported:</span>
        <code className="font-mono text-slate-500">scripts/just/fleet.just</code>
      </div>
    </motion.div>
  );
}
