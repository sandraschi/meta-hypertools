import { ArrowLeft, BookOpen, FileText, LayoutGrid, List, RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api, isSuccessResponse } from "../api/client";

interface StandardMeta {
  path: string;
  name: string;
  title: string;
  category: string;
  status: string;
  audience: string;
  last_updated: string;
  size_bytes: number;
  modified: string;
}

type ViewMode = "grid" | "list";
const VIEW_KEY = "metamcp_standards_view";

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function statusStyle(status: string): string {
  const s = status.toLowerCase();
  if (s === "active") return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
  if (s === "review") return "bg-amber-500/15 text-amber-300 border-amber-500/30";
  if (s === "deprecated") return "bg-red-500/15 text-red-300 border-red-500/30";
  if (s) return "bg-slate-500/15 text-slate-300 border-slate-500/30";
  return "bg-slate-800 text-slate-300 border-slate-700";
}

function MarkdownView({ content }: { content: string }) {
  return (
    <div className="prose prose-invert max-w-none prose-headings:text-white prose-a:text-blue-400 prose-code:text-amber-300 prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-800 prose-li:text-slate-300 prose-p:text-slate-300">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}

export function StandardsPage() {
  const [standards, setStandards] = useState<StandardMeta[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [available, setAvailable] = useState(true);
  const [hint, setHint] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [view, setView] = useState<ViewMode>(() => {
    try {
      return (localStorage.getItem(VIEW_KEY) as ViewMode) === "list" ? "list" : "grid";
    } catch {
      return "grid";
    }
  });
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [contentLoading, setContentLoading] = useState(false);

  const setViewMode = (mode: ViewMode) => {
    setView(mode);
    try {
      localStorage.setItem(VIEW_KEY, mode);
    } catch {
      // ignore localstorage errors
    }
  };

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.listStandards();
      if (isSuccessResponse(resp) && resp.data) {
        setAvailable(resp.data.available !== false);
        setStandards(resp.data.standards ?? []);
        setCategories(resp.data.categories ?? []);
        setHint(resp.data.hint ?? "");
      } else {
        setError("Failed to load standards list");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load standards");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadList();
  }, [loadList]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return standards.filter((s) => {
      if (category && s.category !== category) return false;
      if (
        needle &&
        !s.title.toLowerCase().includes(needle) &&
        !s.path.toLowerCase().includes(needle)
      )
        return false;
      return true;
    });
  }, [standards, query, category]);

  const openStandard = async (path: string) => {
    setSelected(path);
    setContentLoading(true);
    setError(null);
    try {
      const resp = await api.readStandard(path);
      if (isSuccessResponse(resp) && resp.data) {
        setContent(resp.data.content ?? "");
      } else {
        setContent("(failed to load content)");
      }
    } catch (err) {
      setContent(err instanceof Error ? err.message : "(failed to load content)");
    } finally {
      setContentLoading(false);
    }
  };

  const selectedMeta = selected ? standards.find((s) => s.path === selected) : undefined;

  if (selected) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => setSelected(null)}
            className="flex items-center gap-2 text-sm text-slate-300 hover:text-white transition-colors"
          >
            <ArrowLeft size={14} />
            All standards
          </button>
          <span className="text-xs text-slate-300 font-mono">{selected}</span>
        </div>
        {selectedMeta && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-lg font-bold text-white">{selectedMeta.title}</span>
            {selectedMeta.status && (
              <span
                className={`text-[11px] px-2 py-0.5 rounded-full border font-semibold ${statusStyle(selectedMeta.status)}`}
              >
                {selectedMeta.status}
              </span>
            )}
            {selectedMeta.category && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30 font-semibold">
                {selectedMeta.category}
              </span>
            )}
            {selectedMeta.last_updated && (
              <span className="text-xs text-slate-300">updated {selectedMeta.last_updated}</span>
            )}
          </div>
        )}
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
          {contentLoading ? (
            <div className="flex items-center justify-center h-32 text-slate-300">
              <span className="animate-spin mr-2 h-4 w-4 border-b-2 border-current rounded-full" />
              Loading...
            </div>
          ) : (
            <MarkdownView content={content} />
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Fleet Standards</h1>
          <p className="text-sm text-slate-300 mt-1">
            {available
              ? `${standards.length} standards from mcp-central-docs`
              : "Handbook not connected"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-slate-700 overflow-hidden">
            <button
              type="button"
              onClick={() => setViewMode("grid")}
              title="Grid view"
              aria-label="Grid view"
              className={`p-2 transition-colors ${view === "grid" ? "bg-blue-600/30 text-blue-200" : "text-slate-300 hover:text-white hover:bg-slate-800"}`}
            >
              <LayoutGrid size={16} />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("list")}
              title="List view"
              aria-label="List view"
              className={`p-2 transition-colors ${view === "list" ? "bg-blue-600/30 text-blue-200" : "text-slate-300 hover:text-white hover:bg-slate-800"}`}
            >
              <List size={16} />
            </button>
          </div>
          <button
            type="button"
            onClick={loadList}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40 text-slate-300">
          <span className="animate-spin mr-2 h-5 w-5 border-b-2 border-current rounded-full" />
          Loading standards...
        </div>
      ) : !available ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 py-16 text-center">
          <BookOpen size={28} className="mx-auto text-slate-600 mb-3" />
          <p className="text-slate-300 text-sm">{hint || "Handbook not found."}</p>
          <p className="text-slate-300 text-sm mt-2">
            Set MCP_CENTRAL_DOCS_ROOT in Settings to point at your handbook clone.
          </p>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative flex-1 min-w-[200px]">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-300"
              />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search standards..."
                className="w-full rounded-lg border border-slate-700 bg-slate-900/60 pl-9 pr-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
              />
            </div>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <span className="text-xs text-slate-300">
              {filtered.length} of {standards.length}
            </span>
          </div>

          {filtered.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 py-16 text-center text-slate-300">
              No standards match.
            </div>
          ) : view === "grid" ? (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {filtered.map((s) => (
                <button
                  key={s.path}
                  type="button"
                  onClick={() => openStandard(s.path)}
                  className="flex flex-col rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-left hover:border-blue-500/50 hover:bg-slate-800/60 transition-colors"
                >
                  <div className="flex items-start gap-2.5">
                    <BookOpen size={16} className="text-blue-400 shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1 text-sm font-semibold text-slate-100 leading-snug">
                      {s.title}
                    </div>
                  </div>
                  <div className="mt-1 text-xs text-slate-300 font-mono truncate">{s.path}</div>
                  <div className="mt-auto pt-3 flex flex-wrap items-center gap-1.5">
                    {s.status && (
                      <span
                        className={`text-[11px] px-1.5 py-0.5 rounded border font-semibold ${statusStyle(s.status)}`}
                      >
                        {s.status}
                      </span>
                    )}
                    {s.category && (
                      <span className="text-[11px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                        {s.category}
                      </span>
                    )}
                    <span className="ml-auto text-[11px] text-slate-300">
                      {fmtSize(s.size_bytes)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="grid gap-2">
              {filtered.map((s) => (
                <button
                  key={s.path}
                  type="button"
                  onClick={() => openStandard(s.path)}
                  className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3 text-left hover:border-slate-600 hover:bg-slate-800/60 transition-colors"
                >
                  <FileText size={16} className="text-slate-300 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-slate-200 truncate">{s.title}</div>
                    <div className="text-xs text-slate-300 mt-0.5 font-mono truncate">{s.path}</div>
                  </div>
                  {s.status && (
                    <span
                      className={`text-[11px] px-1.5 py-0.5 rounded border font-semibold shrink-0 ${statusStyle(s.status)}`}
                    >
                      {s.status}
                    </span>
                  )}
                  {s.category && (
                    <span className="text-[11px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 shrink-0 hidden sm:inline">
                      {s.category}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
