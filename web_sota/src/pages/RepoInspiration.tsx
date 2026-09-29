import { BookOpen, ChevronDown, ChevronRight, ExternalLink, Loader2, Play, Rocket, Star } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { isSuccessResponse } from "../api/client";
import {
  type InspirationChapter,
  extractInspirationText,
  resolveInspirationChapters,
} from "../utils/splitInspirationChapters";

const API_BASE =
  (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_BASE_URL || "";

type InspireOp = "structure" | "files" | "patterns";
type Profile = "brief" | "standard" | "deep";
type Tab = "study" | "discover";

interface DiscoveredRepo {
  full_name: string;
  url: string;
  description: string;
  default_branch: string;
  stars: number;
  forks: number;
  watchers: number;
  open_issues: number;
  license: string | null;
  archived: boolean;
  language: string | null;
  topics: string[];
  pushed_at: string | null;
  cadence: string;
  rocket: boolean;
}

interface DiscoverPreset {
  id: string;
  label: string;
  q: string;
  language?: string;
  sort?: string;
}

const FAVES_KEY = "metamcp_inspire_faves";

function loadFaves(): Record<string, { url: string; description: string }> {
  try {
    const raw = localStorage.getItem(FAVES_KEY);
    return raw ? (JSON.parse(raw) as Record<string, { url: string; description: string }>) : {};
  } catch {
    return {};
  }
}

function fmtCount(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function cadenceStyle(cadence: string): string {
  if (cadence === "hot") return "bg-red-500/15 text-red-300 border-red-500/30";
  if (cadence === "active") return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
  if (cadence === "quiet") return "bg-amber-500/15 text-amber-300 border-amber-500/30";
  if (cadence === "dormant") return "bg-slate-500/15 text-slate-400 border-slate-600/40";
  return "bg-slate-800 text-slate-500 border-slate-700";
}

async function fetchPresets(): Promise<DiscoverPreset[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/inspire/presets`);
    if (!res.ok) return [];
    const data = await res.json();
    const list = (data?.result?.presets ?? data?.data?.presets ?? []) as DiscoverPreset[];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

async function runDiscover(params: {
  q: string;
  language: string;
  topic: string;
  minStars: string;
  sort: string;
}): Promise<{ ok: boolean; repos: DiscoveredRepo[]; total: number; error?: string }> {
  const qs = new URLSearchParams({
    q: params.q,
    language: params.language,
    topic: params.topic,
    min_stars: params.minStars || "0",
    sort: params.sort,
    order: "desc",
    per_page: "12",
  });
  try {
    const res = await fetch(`${API_BASE}/api/v1/inspire/search?${qs.toString()}`);
    const data = await res.json();
    if (!res.ok || !isSuccessResponse(data)) {
      const msg =
        (data as { message?: string })?.message || `HTTP ${res.status}: ${res.statusText}`;
      return { ok: false, repos: [], total: 0, error: msg };
    }
    const inner = (data.result ?? data.data ?? {}) as {
      repos?: DiscoveredRepo[];
      total_count?: number;
    };
    return { ok: true, repos: inner.repos ?? [], total: inner.total_count ?? 0 };
  } catch (e: unknown) {
    return { ok: false, repos: [], total: 0, error: e instanceof Error ? e.message : String(e) };
  }
}

const OPS: { id: InspireOp; label: string; hint: string }[] = [
  {
    id: "structure",
    label: "Structure",
    hint: "Filtered file tree (profile controls max paths)",
  },
  {
    id: "files",
    label: "Files",
    hint: "Auto-pick or explicit paths (profile caps chars)",
  },
  {
    id: "patterns",
    label: "Patterns",
    hint: "Architecture pack — server chapters when available",
  },
];

const PROFILES: { id: Profile; label: string }[] = [
  { id: "brief", label: "Brief" },
  { id: "standard", label: "Standard" },
  { id: "deep", label: "Deep" },
];

async function runInspireTool(
  operation: InspireOp,
  url: string,
  subpath: string,
  profile: Profile,
  languageHint: string,
): Promise<{ ok: boolean; payload: unknown; error?: string }> {
  const endpoint = `${API_BASE}/api/v1/tools/execute`;
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(180000),
      body: JSON.stringify({
        server_id: "metaops",
        tool_name: "inspire_repo",
        parameters: {
          operation,
          url: url.trim(),
          subpath: subpath.trim() || undefined,
          profile,
          language_hint: languageHint.trim() || undefined,
        },
      }),
    });
    if (!res.ok) {
      return { ok: false, payload: null, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const data = await res.json();
    if (!isSuccessResponse(data)) {
      return { ok: false, payload: data, error: data.message || "Tool failed" };
    }
    return { ok: true, payload: data.result ?? data.data ?? data };
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return { ok: false, payload: null, error: msg };
  }
}

function ChapterPanel({
  chapter,
  forceOpen,
}: {
  chapter: InspirationChapter;
  forceOpen?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const expanded = forceOpen ?? open;
  return (
    <div className="rounded-xl border border-white/10 bg-black/30 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/5 transition-colors"
      >
        {expanded ? (
          <ChevronDown size={18} className="text-purple-400 shrink-0" />
        ) : (
          <ChevronRight size={18} className="text-slate-500 shrink-0" />
        )}
        <span className="flex-1 text-sm font-medium text-white truncate">{chapter.title}</span>
        {chapter.kind && (
          <span className="text-[9px] uppercase tracking-wider text-purple-400/80 shrink-0">
            {chapter.kind}
          </span>
        )}
        <span className="text-[10px] text-slate-500 font-mono shrink-0">
          {chapter.lineCount} lines
        </span>
      </button>
      {expanded && (
        <div className="px-4 pb-4 border-t border-white/5 max-h-[min(70vh,520px)] overflow-y-auto">
          <div className="prose prose-invert prose-sm max-w-none font-mono text-xs text-[#ccc] whitespace-pre-wrap break-words">
            <ReactMarkdown>{chapter.body}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

function pickMeta(payload: unknown): Record<string, unknown> | null {
  if (!payload || typeof payload !== "object") return null;
  const root = payload as Record<string, unknown>;
  const data = (root.data ?? root) as Record<string, unknown>;
  const inner =
    data.data && typeof data.data === "object" ? (data.data as Record<string, unknown>) : data;
  return inner;
}

function DiscoverPanel({ onStudy }: { onStudy: (url: string) => void }) {
  const [presets, setPresets] = useState<DiscoverPreset[]>([]);
  const [q, setQ] = useState("");
  const [language, setLanguage] = useState("");
  const [topic, setTopic] = useState("");
  const [minStars, setMinStars] = useState("");
  const [sort, setSort] = useState("stars");
  const [repos, setRepos] = useState<DiscoveredRepo[]>([]);
  const [total, setTotal] = useState(0);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [faves, setFaves] = useState(loadFaves);
  const [favePick, setFavePick] = useState("");

  useEffect(() => {
    void fetchPresets().then(setPresets);
  }, []);

  const toggleFave = (r: DiscoveredRepo) => {
    setFaves((prev) => {
      const next = { ...prev };
      if (next[r.full_name]) delete next[r.full_name];
      else next[r.full_name] = { url: r.url, description: r.description };
      try {
        localStorage.setItem(FAVES_KEY, JSON.stringify(next));
      } catch {
        // ignore quota errors
      }
      return next;
    });
  };

  const search = async (preset?: DiscoverPreset) => {
    const params = preset
      ? { q: preset.q, language: preset.language ?? "", topic: "", minStars: "", sort: preset.sort ?? "stars" }
      : { q, language, topic, minStars, sort };
    if (!params.q.trim()) {
      setSearchError("Type a query or pick a preset.");
      return;
    }
    setSearching(true);
    setSearchError(null);
    const res = await runDiscover(params);
    setSearching(false);
    if (!res.ok) {
      setSearchError(res.error ?? "Search failed");
      return;
    }
    setRepos(res.repos);
    setTotal(res.total);
  };

  return (
    <div className="glass-panel p-6 border-white/5 space-y-4">
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs font-bold uppercase text-slate-500 tracking-widest mr-1">
          Presets
        </span>
        {presets.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => search(p)}
            disabled={searching}
            className="px-3 py-1.5 rounded-lg text-xs font-bold border border-purple-600/40 text-purple-300 hover:bg-purple-600/20 transition-colors disabled:opacity-50"
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder="Search — e.g. mcp server, tauri markdown, rag chatbot"
          className="md:col-span-2 w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-sm"
        />
        <input
          type="text"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          placeholder="Language (Python, TypeScript, Rust…)"
          className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-sm"
        />
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Topic (model-context-protocol, tauri…)"
          className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-sm"
        />
        <input
          type="number"
          min={0}
          value={minStars}
          onChange={(e) => setMinStars(e.target.value)}
          placeholder="Min stars (e.g. 500)"
          className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-sm"
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-sm"
        >
          <option value="stars">Sort: stars</option>
          <option value="forks">Sort: forks</option>
          <option value="updated">Sort: recently pushed</option>
        </select>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <button
          type="button"
          onClick={() => search()}
          disabled={searching}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-[#0066ff] text-white text-sm font-bold disabled:opacity-50"
        >
          {searching ? <Loader2 className="animate-spin" size={18} /> : <Play size={18} />}
          Search GitHub
        </button>
        {Object.keys(faves).length > 0 && (
          <select
            value={favePick}
            onChange={(e) => {
              const name = e.target.value;
              setFavePick(name);
              const f = faves[name];
              if (f) onStudy(f.url);
            }}
            className="px-3 py-2.5 rounded-xl bg-black/40 border border-amber-500/30 text-amber-300 text-sm"
            title="Starred repos — pick one to study it"
          >
            <option value="">Faves ({Object.keys(faves).length})…</option>
            {Object.keys(faves)
              .sort()
              .map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
          </select>
        )}
        {total > 0 && <span className="text-xs text-slate-500">{total.toLocaleString()} matches</span>}
      </div>

      {searchError && (
        <p className="text-sm text-red-400 border border-red-900/40 bg-red-950/20 rounded-xl p-4">
          {searchError}
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {repos.map((r) => (
          <div key={r.full_name} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <a
                  href={r.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm font-semibold text-slate-100 hover:text-blue-300 truncate block"
                >
                  {r.full_name}
                </a>
                <p className="text-xs text-slate-500 mt-1 line-clamp-2">{r.description || "No description."}</p>
              </div>
              <button
                type="button"
                onClick={() => toggleFave(r)}
                title={faves[r.full_name] ? "Unstar" : "Star as fave"}
                aria-label={faves[r.full_name] ? "Unstar" : "Star as fave"}
                className={`shrink-0 p-1.5 rounded-lg transition-colors ${faves[r.full_name] ? "text-amber-300" : "text-slate-600 hover:text-amber-300"}`}
              >
                <Star size={16} fill={faves[r.full_name] ? "currentColor" : "none"} />
              </button>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[11px]">
              <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-200 font-semibold">
                {"★"} {fmtCount(r.stars)}
              </span>
              <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                forks {fmtCount(r.forks)}
              </span>
              <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                issues {fmtCount(r.open_issues)}
              </span>
              <span className={`px-1.5 py-0.5 rounded border font-semibold ${cadenceStyle(r.cadence)}`}>
                {r.cadence}
              </span>
              {r.rocket && (
                <span className="px-1.5 py-0.5 rounded bg-orange-500/15 text-orange-300 border border-orange-500/30 font-semibold inline-flex items-center gap-1">
                  <Rocket size={11} /> rocket
                </span>
              )}
              {r.archived && (
                <span className="px-1.5 py-0.5 rounded bg-red-500/15 text-red-300 border border-red-500/30">
                  archived
                </span>
              )}
              {r.language && (
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">{r.language}</span>
              )}
              {r.license && r.license !== "NOASSERTION" && (
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">{r.license}</span>
              )}
            </div>
            {r.topics.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {r.topics.slice(0, 5).map((t) => (
                  <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300">
                    {t}
                  </span>
                ))}
              </div>
            )}
            <button
              type="button"
              onClick={() => onStudy(r.url)}
              className="mt-3 text-xs font-bold text-blue-400 hover:underline"
            >
              Study this repo →
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export function RepoInspirationPage() {
  const [tab, setTab] = useState<Tab>("study");
  const [url, setUrl] = useState("https://github.com/sandraschi/speech-mcp");
  const [subpath, setSubpath] = useState("");
  const [languageHint, setLanguageHint] = useState("");
  const [profile, setProfile] = useState<Profile>("standard");
  const [expandAll, setExpandAll] = useState(false);
  const [op, setOp] = useState<InspireOp>("patterns");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rawText, setRawText] = useState("");
  const [payload, setPayload] = useState<unknown>(null);
  const [meta, setMeta] = useState<Record<string, unknown> | null>(null);
  const chapters = useMemo(() => resolveInspirationChapters(payload, rawText), [payload, rawText]);

  const run = async (overrideUrl?: string) => {
    const target = (overrideUrl ?? url).trim();
    if (!target) {
      setError("Enter a GitHub repository URL.");
      return;
    }
    setRunning(true);
    setError(null);
    setRawText("");
    setPayload(null);
    setMeta(null);
    try {
      const {
        ok,
        payload: result,
        error: err,
      } = await runInspireTool(op, target, subpath, profile, languageHint);
      if (!ok) {
        setError(err || extractInspirationText(result));
        return;
      }
      setPayload(result);
      const text = extractInspirationText(result);
      setRawText(text);
      const m = pickMeta(result);
      if (m) {
        setMeta({
          owner: m.owner,
          repo: m.repo,
          branch: m.branch,
          profile: m.profile,
          subpath: m.subpath,
          char_count: m.char_count,
          total_source_files: m.total_source_files,
          tree_cached: m.tree_cached,
          gitingest_url: m.gitingest_url,
          hints: m.hints,
          suggested_subpaths: m.suggested_subpaths,
          suggested_language_hint: m.suggested_language_hint,
          large_repo_mode: m.large_repo_mode,
          tree_truncated_by_github: m.tree_truncated_by_github,
          rate_limit_remaining: m.rate_limit_remaining,
        });
        if (!languageHint && typeof m.suggested_language_hint === "string") {
          setLanguageHint(m.suggested_language_hint);
        }
      }
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="glass-panel p-8 border-white/5 bg-white/[0.01]">
        <div className="flex items-start gap-5">
          <div className="p-4 rounded-2xl bg-[#0066ff]/10 border border-[#0066ff]/25 text-blue-400">
            <BookOpen size={32} />
          </div>
          <div>
            <h1 className="text-2xl font-black text-white tracking-tight">Repo Inspiration</h1>
            <p className="text-sm text-[#888] mt-2 max-w-2xl">
              Study public GitHub repositories without cloning. Uses{" "}
              <code className="text-blue-400">inspire_repo</code> (chapters, profiles, monorepo
              hints). Workflow adapted from{" "}
              <a
                href="https://www.npmjs.com/package/repomuse"
                className="text-blue-400 hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                Repomuse
              </a>{" "}
              (MIT, praveene3127).
            </p>
          </div>
        </div>
      </div>

      <div className="flex gap-2">
        {(["study", "discover"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-xl text-sm font-bold border transition-colors ${
              tab === t
                ? "bg-[#0066ff]/20 border-[#0066ff]/40 text-white"
                : "border-white/10 text-[#888] hover:border-white/20"
            }`}
          >
            {t === "study" ? "Study a repo" : "Discover repos"}
          </button>
        ))}
      </div>

      {tab === "discover" && (
        <DiscoverPanel
          onStudy={(repoUrl) => {
            setUrl(repoUrl);
            setTab("study");
            void run(repoUrl);
          }}
        />
      )}

      {tab === "study" && (
      <div className="glass-panel p-6 border-white/5 space-y-4">
        <label
          htmlFor="repo-url"
          className="text-xs font-bold uppercase text-slate-500 tracking-widest"
        >
          GitHub URL
        </label>
        <input
          id="repo-url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          className="w-full px-4 py-3 rounded-xl bg-black/40 border border-white/10 text-white text-sm font-mono"
        />

        <label
          htmlFor="subpath"
          className="text-xs font-bold uppercase text-slate-500 tracking-widest"
        >
          Subpath (optional)
        </label>
        <input
          id="subpath"
          type="text"
          value={subpath}
          onChange={(e) => setSubpath(e.target.value)}
          placeholder="src"
          className="w-full px-4 py-3 rounded-xl bg-black/40 border border-white/10 text-white text-sm font-mono"
        />

        <label
          htmlFor="language-hint"
          className="text-xs font-bold uppercase text-slate-500 tracking-widest"
        >
          Language hint (optional, files/patterns)
        </label>
        <input
          id="language-hint"
          type="text"
          value={languageHint}
          onChange={(e) => setLanguageHint(e.target.value)}
          placeholder="python"
          className="w-full px-4 py-3 rounded-xl bg-black/40 border border-white/10 text-white text-sm font-mono"
        />

        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-xs font-bold uppercase text-slate-500 tracking-widest mr-2">
            Profile
          </span>
          {PROFILES.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setProfile(p.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-colors ${
                profile === p.id
                  ? "bg-[#0066ff]/20 border-[#0066ff]/40 text-white"
                  : "border-white/10 text-[#888] hover:border-white/20"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          {OPS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setOp(item.id)}
              className={`px-4 py-2 rounded-xl text-xs font-bold border transition-colors ${
                op === item.id
                  ? "bg-purple-600/20 border-purple-600/40 text-white"
                  : "border-white/10 text-[#888] hover:border-white/20"
              }`}
              title={item.hint}
            >
              {item.label}
            </button>
          ))}
        </div>
        <p className="text-[11px] text-slate-500">{OPS.find((o) => o.id === op)?.hint}</p>

        <button
          type="button"
          onClick={() => run()}
          disabled={running}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-[#0066ff] text-white text-sm font-bold disabled:opacity-50"
        >
          {running ? <Loader2 className="animate-spin" size={18} /> : <Play size={18} />}
          Run {op}
        </button>

        {error && (
          <p className="text-sm text-red-400 border border-red-900/40 bg-red-950/20 rounded-xl p-4">
            {error}
          </p>
        )}
      </div>
      )}

      {rawText && (
        <div className="space-y-4">
          {meta?.tree_truncated_by_github === true && (
            <p className="text-sm text-amber-300 border border-amber-900/50 bg-amber-950/30 rounded-xl p-4">
              GitHub truncated the file tree — results may be incomplete. Use a subpath or
              gitingest.
            </p>
          )}
          {meta?.large_repo_mode === true && (
            <p className="text-sm text-amber-200/90 border border-amber-900/40 bg-amber-950/20 rounded-xl p-4">
              Large repository — directory summary and subpath suggestions are in hints below.
            </p>
          )}
          {Array.isArray(meta?.hints) && meta.hints.length > 0 && (
            <ul className="text-xs text-slate-400 border border-white/10 rounded-xl p-4 space-y-2 list-disc list-inside">
              {(meta.hints as string[]).map((h) => (
                <li key={h}>{h}</li>
              ))}
            </ul>
          )}
          {Array.isArray(meta?.suggested_subpaths) &&
            (meta.suggested_subpaths as string[]).length > 0 && (
              <div className="flex flex-wrap gap-2 items-center">
                <span className="text-[10px] uppercase text-slate-500 tracking-widest">
                  Suggested subpaths
                </span>
                {(meta.suggested_subpaths as string[]).map((sp) => (
                  <button
                    key={sp}
                    type="button"
                    onClick={() => setSubpath(sp)}
                    className="px-2 py-1 rounded-lg text-xs font-mono border border-blue-500/30 text-blue-400 hover:bg-blue-500/10"
                  >
                    {sp}
                  </button>
                ))}
              </div>
            )}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
            <div className="lg:col-span-4 glass-panel p-4 border-white/5 flex flex-col max-h-[75vh]">
              <div className="mb-3 pb-3 border-b border-white/5 flex items-center justify-between gap-2">
                <h2 className="text-sm font-bold text-white">Chapters ({chapters.length})</h2>
                <button
                  type="button"
                  onClick={() => setExpandAll((v) => !v)}
                  className="text-[10px] font-bold uppercase text-blue-400 hover:underline"
                >
                  {expandAll ? "Collapse all" : "Expand all"}
                </button>
              </div>
              {meta && (
                <div className="text-[10px] font-mono text-slate-500 mb-3 space-y-1">
                  {meta.owner != null && meta.repo != null ? (
                    <div>
                      {String(meta.owner)}/{String(meta.repo)} @{String(meta.branch ?? "main")}
                      {meta.profile != null ? ` · ${String(meta.profile)}` : ""}
                    </div>
                  ) : null}
                  {meta.subpath != null && String(meta.subpath) !== "" && (
                    <div>subpath: {String(meta.subpath)}</div>
                  )}
                  {meta.char_count != null && (
                    <div>{Number(meta.char_count).toLocaleString()} chars</div>
                  )}
                  {meta.total_source_files != null && (
                    <div>{String(meta.total_source_files)} source files</div>
                  )}
                  {meta.tree_cached === true && <div>tree: cached</div>}
                  {meta.rate_limit_remaining != null && (
                    <div>GitHub rate limit remaining: {String(meta.rate_limit_remaining)}</div>
                  )}
                  {meta.gitingest_url != null && (
                    <a
                      href={String(meta.gitingest_url)}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-400 hover:underline block"
                    >
                      gitingest
                    </a>
                  )}
                </div>
              )}
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {chapters.map((ch) => (
                  <ChapterPanel key={ch.id} chapter={ch} forceOpen={expandAll} />
                ))}
              </div>
              <a
                href={url}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex items-center gap-1 text-[11px] text-blue-400 hover:underline"
              >
                Open on GitHub <ExternalLink size={12} />
              </a>
            </div>

            <div className="lg:col-span-8 glass-panel p-4 border-white/5 flex flex-col max-h-[75vh]">
              <h2 className="text-sm font-bold text-white mb-3 pb-3 border-b border-white/5">
                Full text (scroll)
              </h2>
              <pre className="flex-1 overflow-auto text-[11px] font-mono text-slate-400 whitespace-pre-wrap break-words">
                {rawText}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
