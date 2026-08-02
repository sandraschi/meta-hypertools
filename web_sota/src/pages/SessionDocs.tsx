import { ArrowLeft, FileText, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api, isSuccessResponse } from "../api/client";

interface SessionDocMeta {
  name: string;
  size_bytes: number;
  modified: string;
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.listSessionDocs();
      if (isSuccessResponse(resp) && resp.data) {
        setDocs(resp.data.docs ?? []);
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
            className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft size={14} />
            All session docs
          </button>
          <span className="text-xs text-slate-500 font-mono">{selected}</span>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
          {contentLoading ? (
            <div className="flex items-center justify-center h-32 text-slate-500">
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Session Docs</h1>
          <p className="text-sm text-slate-500 mt-1">
            Fleet session logs from mcp-agent-session-summaries
          </p>
        </div>
        <button
          type="button"
          onClick={loadList}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title="Refresh"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40 text-slate-500">
          <span className="animate-spin mr-2 h-5 w-5 border-b-2 border-current rounded-full" />
          Loading session docs...
        </div>
      ) : docs.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 py-16 text-center text-slate-500">
          No session docs found.
        </div>
      ) : (
        <div className="grid gap-2">
          {docs.map((doc) => (
            <button
              key={doc.name}
              type="button"
              onClick={() => openDoc(doc.name)}
              className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3 text-left hover:border-slate-600 hover:bg-slate-800/60 transition-colors"
            >
              <FileText size={16} className="text-slate-500 shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-sm text-slate-200 truncate">{doc.name}</div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {doc.modified} · {fmtSize(doc.size_bytes)}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
