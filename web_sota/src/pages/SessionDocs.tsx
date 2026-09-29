import {
  ArrowLeft,
  FileText,
  LayoutGrid,
  List,
  RefreshCw,
  Search,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api, isSuccessResponse } from "../api/client";

interface SessionDocMeta {
  name: string;
  size_bytes: number;
  modified: string;
}

type ViewMode = "grid" | "list";
type SortMode = "date-desc" | "date-asc" | "name-asc" | "name-desc" | "size-desc" | "size-asc";

const VIEW_KEY = "metamcp_sessiondocs_view";
const PAGE_SIZE = 20;

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function docDate(d: SessionDocMeta): string {
  const m = /^(\d{4}-\d{2}-\d{2})/.exec(d.name);
  if (m) return m[1];
  return d.modified.slice(0, 10);
}

function defaultCutoff(): string {
  const d = new Date();
  d.setDate(d.getDate() - 30);
  return d.toISOString().slice(0, 10);
}

function MarkdownView({ content }: { content: string }) {
  return (
    <div className="prose prose-invert max-w-none prose-headings:text-white prose-a:text-blue-400 prose-code:text-amber-300 prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-800 prose-li:text-slate-300 prose-p:text-slate-300">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}

export function SessionDocsPage() {
  const [docs, setDocs] = useState<SessionDocMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState<string>("");
  const [contentLoading, setContentLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortMode>("date-desc");
  const [page, setPage] = useState(1);
  const [view, setView] = useState<ViewMode>(() => {
    try {
      return (localStorage.getItem(VIEW_KEY) as ViewMode) === "grid" ? "grid" : "list";
    } catch {
      return "list";
    }
  });
  const [cutoff, setCutoff] = useState(defaultCutoff);
  const [pruning, setPruning] = useState(false);
  const [pruneMsg, setPruneMsg] = useState<string | null>(null);
  const [pruneAllowed, setPruneAllowed] = useState(true);

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
      const resp = await api.listSessionDocs();
      if (isSuccessResponse(resp) && resp.data) {
        setDocs(resp.data.docs ?? []);
        setPruneAllowed(resp.data.prune_allowed !== false);
      } else {
        setError("Failed to load session docs list");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load session docs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadList();
  }, [loadList]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const rows = docs.filter((d) => !needle || d.name.toLowerCase().includes(needle));
    switch (sort) {
      case "date-asc":
        rows.sort((a, b) => docDate(a).localeCompare(docDate(b)) || a.name.localeCompare(b.name));
        break;
      case "name-asc":
        rows.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case "name-desc":
        rows.sort((a, b) => b.name.localeCompare(a.name));
        break;
      case "size-desc":
        rows.sort((a, b) => b.size_bytes - a.size_bytes);
        break;
      case "size-asc":
        rows.sort((a, b) => a.size_bytes - b.size_bytes);
        break;
      default: // date-desc
        rows.sort((a, b) => docDate(b).localeCompare(docDate(a)) || a.name.localeCompare(b.name));
        break;
    }
    return rows;
  }, [docs, query, sort]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const pageRows = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const ancientCount = useMemo(
    () => (cutoff ? docs.filter((d) => docDate(d) < cutoff).length : 0),
    [docs, cutoff],
  );

  const prune = async () => {
    if (!cutoff || ancientCount === 0 || pruning) return;
    const ok = window.confirm(
      `Delete ${ancientCount} session doc(s) older than ${cutoff}? This cannot be undone.`,
    );
    if (!ok) return;
    setPruning(true);
    setPruneMsg(null);
    try {
      const resp = await api.pruneSessionDocs(cutoff);
      if (isSuccessResponse(resp) && resp.data) {
        setPruneMsg(`Deleted ${resp.data.deleted_count}, kept ${resp.data.kept_count}.`);
        await loadList();
      } else {
        setPruneMsg("Delete failed (server rejected the request).");
      }
    } catch (err) {
      setPruneMsg(err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setPruning(false);
    }
  };

  const openDoc = async (name: string) => {
    setSelected(name);
    setContentLoading(true);
    setError(null);
    try {
      const resp = await api.readSessionDoc(name);
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
            All session docs
          </button>
          <span className="text-xs text-slate-300 font-mono">{selected}</span>
        </div>
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
          <h1 className="text-xl font-bold text-white">Session Docs</h1>
          <p className="text-sm text-slate-300 mt-1">
            Fleet session logs ({docs.length} docs)
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
          Loading session docs...
        </div>
      ) : docs.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 py-16 text-center text-slate-300">
          No session docs found.
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative flex-1 min-w-[180px]">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-300" />
              <input
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setPage(1);
                }}
                placeholder="Search docs..."
                className="w-full rounded-lg border border-slate-700 bg-slate-900/60 pl-9 pr-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
              />
            </div>
            <select
              value={sort}
              onChange={(e) => {
                setSort(e.target.value as SortMode);
                setPage(1);
              }}
              className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="date-desc">Newest first</option>
              <option value="date-asc">Oldest first</option>
              <option value="name-asc">Name A–Z</option>
              <option value="name-desc">Name Z–A</option>
              <option value="size-desc">Largest first</option>
              <option value="size-asc">Smallest first</option>
            </select>
            <span className="text-xs text-slate-300">
              {filtered.length} of {docs.length}
            </span>
          </div>

          {filtered.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 py-16 text-center text-slate-300">
              No docs match.
            </div>
          ) : view === "grid" ? (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {pageRows.map((doc) => (
                <button
                  key={doc.name}
                  type="button"
                  onClick={() => openDoc(doc.name)}
                  className="flex flex-col rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-left hover:border-blue-500/50 hover:bg-slate-800/60 transition-colors"
                >
                  <div className="flex items-start gap-2.5">
                    <FileText size={16} className="text-blue-400 shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1 text-sm font-semibold text-slate-100 leading-snug break-all">
                      {doc.name}
                    </div>
                  </div>
                  <div className="mt-auto pt-3 flex items-center gap-2 text-xs text-slate-300">
                    <span>{doc.modified.slice(0, 10)}</span>
                    <span className="ml-auto">{fmtSize(doc.size_bytes)}</span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="grid gap-2">
              {pageRows.map((doc) => (
                <button
                  key={doc.name}
                  type="button"
                  onClick={() => openDoc(doc.name)}
                  className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3 text-left hover:border-slate-600 hover:bg-slate-800/60 transition-colors"
                >
                  <FileText size={16} className="text-slate-300 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-slate-200 truncate">{doc.name}</div>
                    <div className="text-xs text-slate-300 mt-0.5">
                      {doc.modified} · {fmtSize(doc.size_bytes)}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {pageCount > 1 && (
            <div className="flex items-center justify-center gap-2 text-sm text-slate-300">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={safePage <= 1}
                className="px-3 py-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 transition-colors disabled:opacity-40"
              >
                Prev
              </button>
              <span>
                Page {safePage} of {pageCount}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                disabled={safePage >= pageCount}
                className="px-3 py-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 transition-colors disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}

          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
            <div className="text-sm font-semibold text-slate-200 mb-1">Prune ancient docs</div>
            {pruneAllowed ? (
              <>
                <p className="text-sm text-slate-300 mb-3">
                  Deletes top-level docs older than the cutoff. Subdirectories are never touched.
                </p>
                <div className="flex items-center gap-2 flex-wrap">
                  <label htmlFor="prune-cutoff" className="text-xs text-slate-300">
                    Older than
                  </label>
                  <input
                    id="prune-cutoff"
                    type="date"
                    value={cutoff}
                    onChange={(e) => setCutoff(e.target.value)}
                    className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                  <span className="text-xs text-slate-300">
                    {ancientCount} doc{ancientCount === 1 ? "" : "s"} match
                  </span>
                  <button
                    type="button"
                    onClick={prune}
                    disabled={pruning || ancientCount === 0}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm bg-red-600/20 text-red-300 border border-red-500/30 hover:bg-red-600/30 transition-colors disabled:opacity-40"
                  >
                    <Trash2 size={14} />
                    {pruning ? "Deleting..." : "Delete"}
                  </button>
                  {pruneMsg && <span className="text-xs text-slate-300">{pruneMsg}</span>}
                </div>
              </>
            ) : (
              <p className="text-xs text-slate-300">
                Pruning is disabled for the shared handbook log. Set SESSION_DOCS_DIR to manage
                deletions in a private archive.
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
