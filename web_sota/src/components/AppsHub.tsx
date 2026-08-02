import { motion } from "framer-motion";
import {
  Activity,
  Cpu,
  ExternalLink,
  Globe,
  Loader2,
  type LucideIcon,
  Music,
  Power,
  RefreshCw,
  Rocket,
  Search,
  Shield,
} from "lucide-react";
import React, { useCallback, useEffect, useState } from "react";

interface FleetApp {
  id: string;
  label: string;
  status: "active" | "inactive";
  port: number | null;
  tags: string[];
  url: string | null;
}

const TAG_ICONS: Record<string, LucideIcon> = {
  infra: Shield,
  ai: Cpu,
  media: Music,
  frontend: Globe,
  modern: Rocket,
  discovered: Search,
};

const TAG_COLORS: Record<string, string> = {
  infra: "text-blue-400 bg-blue-400/10",
  ai: "text-purple-400 bg-purple-400/10",
  media: "text-pink-400 bg-pink-400/10",
  frontend: "text-cyan-400 bg-cyan-400/10",
  modern: "text-amber-400 bg-amber-400/10",
  discovered: "text-slate-300 bg-slate-400/10",
};

export const AppsHub: React.FC = () => {
  const [apps, setApps] = useState<FleetApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [launchingId, setLaunchingId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTag, setActiveTag] = useState<string | null>(null);

  const fetchApps = useCallback(async () => {
    try {
      setError(null);
      const res = await fetch("/api/v1/fleet/runtime");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const rawApps: Record<string, unknown>[] = data?.data?.apps ?? [];
      const mapped: FleetApp[] = rawApps.map((a) => ({
        id: String(a.name || a.id || ""),
        label: String(a.name || a.id || "Unknown"),
        status: a.status === "healthy" || a.status === "active" ? "active" : "inactive",
        port: a.port ? Number(a.port) : null,
        tags: ["discovered"],
        url: a.url ? String(a.url) : null,
      }));
      setApps(mapped);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch fleet status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApps();
    const interval = setInterval(fetchApps, 10000);
    return () => clearInterval(interval);
  }, [fetchApps]);

  const handleLaunch = async (app: FleetApp) => {
    if (app.status === "active" && app.url) {
      window.open(app.url, "_blank");
      return;
    }

    setLaunchingId(app.id);
    try {
      const res = await fetch("/api/v1/fleet/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ app_id: app.id }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      // Poll for status change
      let attempts = 0;
      const checkStatus = setInterval(async () => {
        attempts++;
        try {
          const pollRes = await fetch("/api/v1/fleet/runtime");
          if (!pollRes.ok) throw new Error("Poll failed");
          const pollData = await pollRes.json();
          const updatedApp = (pollData?.data?.apps || []).find(
            (a: Record<string, unknown>) => String(a.name || a.id) === app.id,
          );
          if (
            updatedApp?.status === "healthy" ||
            updatedApp?.status === "active" ||
            attempts > 12
          ) {
            clearInterval(checkStatus);
            setLaunchingId(null);
            const url = updatedApp?.url ? String(updatedApp.url) : null;
            if (updatedApp?.status === "healthy" && url) window.open(url, "_blank");
            fetchApps();
          }
        } catch {
          if (attempts > 12) {
            clearInterval(checkStatus);
            setLaunchingId(null);
          }
        }
      }, 2000);
    } catch (err) {
      setLaunchingId(null);
    }
  };

  const filteredApps = apps.filter((app) => {
    const matchesSearch = app.label.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTag = !activeTag || app.tags.includes(activeTag);
    return matchesSearch && matchesTag;
  });

  const allTags = Array.from(new Set(apps.flatMap((app) => app.tags)));

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-4xl font-black bg-gradient-to-r from-white via-white to-white/40 bg-clip-text text-transparent">
            Apps Hub
          </h1>
          <p className="text-[#94a3b8] mt-2">
            Fleet-wide orchestrated orchestration and control center.
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="relative group">
            <Search
              className="absolute left-4 top-1/2 -translate-y-1/2 text-[#94a3b8] group-focus-within:text-blue-400 transition-colors"
              size={18}
            />
            <input
              type="text"
              placeholder="Search fleet..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-2xl pl-12 pr-6 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#00f3ff]/50 w-full md:w-[300px] transition-all"
            />
          </div>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              fetchApps();
            }}
            className="p-3 glass-panel hover:bg-white/10 transition-colors"
            title="Refresh Status"
          >
            <RefreshCw size={20} className={loading ? "animate-spin text-blue-400" : ""} />
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setActiveTag(null)}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${!activeTag ? "bg-blue-500 text-black shadow-[0_0_15px_rgba(0,243,255,0.3)]" : "bg-white/5 text-[#94a3b8] hover:bg-white/10"}`}
        >
          All Applications
        </button>
        {allTags.sort().map((tag) => (
          <button
            type="button"
            key={tag}
            onClick={() => setActiveTag(tag)}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${activeTag === tag ? "bg-white/20 text-white" : "bg-white/5 text-[#94a3b8] hover:bg-white/10"}`}
          >
            {React.createElement(TAG_ICONS[tag] || Activity, { size: 14 })}
            {tag.charAt(0).toUpperCase() + tag.slice(1)}
          </button>
        ))}
      </div>

      {error && (
        <div className="glass-panel p-4 border border-red-500/30 text-red-300 text-sm flex gap-2">
          <span>{error}</span>
          <button
            type="button"
            onClick={fetchApps}
            className="ml-auto text-blue-400 hover:text-blue-300 underline text-xs"
          >
            Retry
          </button>
        </div>
      )}

      {loading && apps.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-[200px] glass-panel animate-pulse bg-white/5" />
          ))}
        </div>
      ) : filteredApps.length === 0 ? (
        <div className="glass-panel p-20 text-center">
          <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
            <Search size={40} className="text-[#94a3b8]" />
          </div>
          <h3 className="text-xl font-bold mb-2">No applications found</h3>
          <p className="text-[#94a3b8]">
            {error ? "Failed to load fleet data. Retry above." : "Adjust your search or filters."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredApps.map((app) => (
            <motion.div
              layout
              key={app.id}
              className={`glass-panel group relative overflow-hidden transition-all hover:bg-white/[0.07] ${app.status === "active" ? "border-blue-500/30 ring-1 ring-[#00f3ff]/10" : ""}`}
            >
              {app.status === "active" && (
                <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 blur-3xl -mr-16 -mt-16 pointer-events-none" />
              )}

              <div className="p-6 h-full flex flex-col">
                <div className="flex items-start justify-between mb-4">
                  <div className="p-3 bg-white/5 rounded-2xl group-hover:bg-blue-500/10 transition-colors">
                    <Rocket
                      className={app.status === "active" ? "text-blue-400" : "text-[#94a3b8]"}
                      size={24}
                    />
                  </div>
                  <div
                    className={`flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase ${app.status === "active" ? "bg-blue-500/20 text-blue-400" : "bg-white/5 text-[#94a3b8]"}`}
                  >
                    <div
                      className={`w-1.5 h-1.5 rounded-full ${app.status === "active" ? "bg-blue-500 animate-pulse" : "bg-[#888888]"}`}
                    />
                    {app.status}
                  </div>
                </div>

                <div className="mb-4">
                  <h3 className="text-lg font-black group-hover:text-blue-400 transition-colors">
                    {app.label}
                  </h3>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {app.tags.map((tag) => (
                      <span
                        key={tag}
                        className={`px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-widest ${TAG_COLORS[tag] || "bg-white/5 text-[#94a3b8]"}`}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="mt-auto pt-6 flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => handleLaunch(app)}
                    disabled={launchingId === app.id}
                    className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm transition-all active:scale-95 ${
                      app.status === "active"
                        ? "bg-white/10 text-white hover:bg-white/20"
                        : "bg-blue-500 text-black hover:shadow-[0_0_20px_rgba(0,243,255,0.4)]"
                    } disabled:opacity-50`}
                  >
                    {launchingId === app.id ? (
                      <>
                        <Loader2 className="animate-spin" size={16} />
                        Launching...
                      </>
                    ) : app.status === "active" ? (
                      <>
                        <ExternalLink size={16} />
                        Open App
                      </>
                    ) : (
                      <>
                        <Power size={16} />
                        Launch App
                      </>
                    )}
                  </button>

                  {app.port && (
                    <div
                      className="px-3 py-2.5 glass-panel text-[10px] font-mono text-[#94a3b8]"
                      title="Port"
                    >
                      :{app.port}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};
