import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Globe,
  Play,
  RefreshCw,
  Search,
  Square,
  Zap,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FleetBadgeFilterChips, FleetStatusBadgeRow } from "../components/FleetStatusBadge";
import { deriveRuntimeBadges, runtimeMatchesBadgeFilter } from "../utils/fleetStatusBadges";
import { FleetColdInstall } from "./FleetColdInstall";
import { FleetStartupProbe } from "./FleetStartupProbe";

// Interfaces for our new runtime data
interface FleetRuntimeData {
  success: boolean;
  data: {
    total_apps: number;
    healthy: number;
    deficient: number;
    offline: number;
    http_404?: number;
    http_500?: number;
    unavailable?: number;
    zombies: number;
    apps: AppRuntimeStatus[];
    zombie_ports: number[];
  };
}

interface AppRuntimeStatus {
  id: string;
  label: string;
  port: number;
  status: "healthy" | "deficient" | "offline" | "unknown";
  health_code?: number | null;
  tags?: string[];
  health_info?: {
    url: string;
    data?: unknown;
  };
  error?: string;
}

export const FleetDashboard: React.FC = () => {
  const [tab, setTab] = useState<"runtime" | "probe" | "cold-install">("runtime");
  const [auditData, setAuditData] = useState<FleetRuntimeData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const API_BASE = "/api/v1/fleet";

  const fetchRuntimeData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/runtime`);
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const json = await res.json();
      setAuditData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Runtime discovery failure");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuntimeData();
    // Polling every 10 seconds for live status
    const interval = setInterval(fetchRuntimeData, 15000);
    return () => clearInterval(interval);
  }, [fetchRuntimeData]);

  const handleAction = async (action: "start" | "stop", appId: string) => {
    setActionLoading(`${action}-${appId}`);
    try {
      const res = await fetch(`${API_BASE}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ app_id: appId }),
      });
      const result = await res.json();
      if (result.success) {
        // Trigger immediate refresh after action
        setTimeout(fetchRuntimeData, 2000);
      }
    } catch (_e) {
    } finally {
      setActionLoading(null);
    }
  };

  const filteredApps =
    auditData?.data.apps
      .filter((app) => {
        const matchesSearch =
          app.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
          app.id.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesFilter = runtimeMatchesBadgeFilter(app, filterStatus);
        return matchesSearch && matchesFilter;
      })
      .sort((a, b) => a.label.localeCompare(b.label)) || [];

  const runtimeFilters = useMemo(
    () => [
      { id: "all", label: "all" },
      { id: "healthy", label: "healthy" },
      { id: "offline", label: "offline" },
      { id: "404", label: "404" },
      { id: "500", label: "500" },
      { id: "unavailable", label: "unavailable" },
      { id: "deficient", label: "deficient" },
    ],
    [],
  );

  const getStatusStyles = (status: string) => {
    switch (status) {
      case "healthy":
        return "bg-green-500/10 text-green-400 border-green-500/20";
      case "deficient":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "offline":
        return "bg-white/5 text-[#94a3b8] border-white/10";
      default:
        return "bg-white/5 text-white/50 border-white/10";
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "healthy":
        return (
          <div className="flex items-center gap-1.5">
            <CheckCircle2 size={12} /> Healthy
          </div>
        );
      case "deficient":
        return (
          <div className="flex items-center gap-1.5">
            <AlertTriangle size={12} /> Deficient
          </div>
        );
      case "offline":
        return (
          <div className="flex items-center gap-1.5">
            <Square size={10} /> Offline
          </div>
        );
      default:
        return status;
    }
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-6">
        <div className="glass-panel p-8 bg-red-500/10 border-red-500/20 text-red-200 text-center max-w-md">
          <AlertTriangle className="mx-auto mb-4 text-red-400" size={48} />
          <h3 className="text-xl font-bold mb-2">Fleet Runtime Disconnected</h3>
          <p className="text-sm opacity-80">{error}</p>
          <button
            type="button"
            onClick={fetchRuntimeData}
            className="mt-6 px-6 py-2 bg-red-500/20 hover:bg-red-500/30 rounded-lg transition-all font-bold"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-12">
      {/* Header section */}
      <header className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
        <div>
          <h2 className="text-4xl font-black bg-gradient-to-r from-white via-white to-white/40 bg-clip-text text-transparent flex items-center gap-3">
            <Zap className="text-amber-400" fill="currentColor" size={32} />
            Fleet Control
          </h2>
          <p className="text-white/60 mt-1 font-medium">
            Runtime audit (warm), cold-start probe, and cold-install (INSTALL.md + mcpb).
          </p>
          <div className="flex gap-2 mt-4 bg-white/5 p-1 rounded-2xl border border-white/10 w-fit">
            {(["runtime", "probe", "cold-install"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                  tab === t ? "bg-white/10 text-white" : "text-white/40 hover:text-white"
                }`}
              >
                {t === "runtime" ? "Runtime" : t === "probe" ? "Cold start" : "Cold install"}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchRuntimeData}
            className={`p-2.5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-all ${loading ? "animate-spin" : ""}`}
          >
            <RefreshCw size={20} />
          </button>
          <div className="h-10 w-px bg-white/10 mx-2" />
          <div className="flex items-center gap-2 bg-blue-500/20 border border-blue-500/30 px-4 py-2 rounded-xl text-blue-300 font-bold text-sm">
            <Activity size={16} className="animate-pulse" />
            Live Hub
          </div>
        </div>
      </header>

      {tab === "probe" ? (
        <FleetStartupProbe />
      ) : tab === "cold-install" ? (
        <FleetColdInstall />
      ) : (
        <>
          {/* Stats Overview */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            {[
              {
                label: "Healthy",
                val: auditData?.data.healthy || 0,
                color: "text-green-400",
                bg: "from-green-500/20",
              },
              {
                label: "Offline",
                val: auditData?.data.offline || 0,
                color: "text-white/60",
                bg: "from-white/10",
              },
              {
                label: "404",
                val: auditData?.data.http_404 || 0,
                color: "text-orange-400",
                bg: "from-orange-500/20",
              },
              {
                label: "500",
                val: auditData?.data.http_500 || 0,
                color: "text-red-400",
                bg: "from-red-500/20",
              },
              {
                label: "Unavailable",
                val: auditData?.data.unavailable || 0,
                color: "text-red-300",
                bg: "from-red-500/15",
              },
              {
                label: "Deficient",
                val: auditData?.data.deficient || 0,
                color: "text-amber-400",
                bg: "from-amber-500/20",
              },
              {
                label: "Zombies",
                val: auditData?.data.zombies || 0,
                color: "text-purple-400",
                bg: "from-purple-500/20",
              },
            ].map((stat) => (
              <div
                key={stat.label}
                className={`glass-panel p-5 bg-gradient-to-br ${stat.bg} to-transparent border-white/5`}
              >
                <p className="text-[10px] uppercase tracking-[0.2em] font-black opacity-40 mb-1">
                  {stat.label}
                </p>
                <p className={`text-4xl font-black ${stat.color}`}>{stat.val}</p>
              </div>
            ))}
          </div>

          {/* Controls Row */}
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search
                className="absolute left-4 top-1/2 -translate-y-1/2 text-white/60"
                size={18}
              />
              <input
                type="text"
                placeholder="Search by app ID or name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-white focus:outline-none focus:border-blue-500/50 transition-all"
              />
            </div>
            <FleetBadgeFilterChips
              filters={runtimeFilters}
              active={filterStatus}
              onChange={setFilterStatus}
            />
          </div>

          {/* Main Content Grid */}
          {loading && !auditData ? (
            <div className="flex flex-col items-center justify-center h-64 space-y-4 text-white/50">
              <Activity className="animate-pulse text-blue-400" size={48} />
              <p className="font-medium">Auditing Fleet Runtime Status...</p>
            </div>
          ) : (
            <motion.div layout className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              <AnimatePresence mode="popLayout">
                {filteredApps.map((app) => (
                  <motion.div
                    layout
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    key={app.id}
                    className={`glass-panel p-6 border transition-all flex flex-col gap-5 group relative overflow-hidden ${
                      app.status === "healthy"
                        ? "hover:border-green-500/30"
                        : app.status === "deficient"
                          ? "hover:border-amber-500/30"
                          : "hover:border-white/20"
                    }`}
                  >
                    {/* Background Glow Effect */}
                    <div
                      className={`absolute -right-8 -top-8 w-24 h-24 blur-[60px] opacity-20 pointer-events-none rounded-full ${
                        app.status === "healthy"
                          ? "bg-green-500"
                          : app.status === "deficient"
                            ? "bg-amber-500"
                            : "bg-white"
                      }`}
                    />

                    <div className="flex justify-between items-start z-10">
                      <div className="space-y-1">
                        <h4 className="font-black text-xl text-white tracking-tight">
                          {app.label}
                        </h4>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] bg-white/5 px-2 py-0.5 rounded text-white/60 font-mono tracking-tighter">
                            ID: {app.id}
                          </span>
                          <span className="text-[10px] bg-blue-500/10 px-2 py-0.5 rounded text-blue-400 font-mono">
                            PORT: {app.port}
                          </span>
                        </div>
                      </div>
                      <div
                        className={`px-2.5 py-1 text-[10px] font-black rounded-lg border uppercase tracking-widest ${getStatusStyles(app.status)}`}
                      >
                        {renderStatusBadge(app.status)}
                      </div>
                    </div>

                    <FleetStatusBadgeRow badges={deriveRuntimeBadges(app)} />

                    {/* Tags */}
                    <div className="flex flex-wrap gap-1.5 z-10">
                      {app.tags?.map((tag) => (
                        <span
                          key={tag}
                          className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-white/50 font-bold uppercase tracking-wider"
                        >
                          {tag}
                        </span>
                      ))}
                      {!app.tags?.length && (
                        <span className="text-[9px] opacity-20 italic">No tags</span>
                      )}
                    </div>

                    {/* Error message if deficient */}
                    {app.status === "deficient" && app.error && (
                      <div className="text-[10px] text-amber-500 bg-amber-500/10 p-2 rounded-lg border border-amber-500/20 flex gap-2 items-start">
                        <AlertTriangle size={14} className="shrink-0" />
                        <span>{app.error}</span>
                      </div>
                    )}

                    {/* Card Actions */}
                    <div className="mt-auto pt-4 flex gap-2 border-t border-white/5 z-10">
                      {app.status === "offline" ? (
                        <button
                          type="button"
                          onClick={() => handleAction("start", app.id)}
                          disabled={actionLoading === `start-${app.id}`}
                          className="flex-1 bg-green-500/20 hover:bg-green-500/30 text-green-400 py-2.5 rounded-xl font-black text-xs uppercase tracking-widest transition-all flex items-center justify-center gap-2 border border-green-500/20"
                        >
                          {actionLoading === `start-${app.id}` ? (
                            <Activity size={14} className="animate-spin" />
                          ) : (
                            <Play size={14} fill="currentColor" />
                          )}
                          {actionLoading === `start-${app.id}` ? "Launching..." : "Start"}
                        </button>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => window.open(`http://localhost:${app.port}`, "_blank")}
                            className="flex-1 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 py-2.5 rounded-xl font-black text-xs uppercase tracking-widest transition-all flex items-center justify-center gap-2 border border-blue-500/20"
                          >
                            <Globe size={14} /> Open
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              if (confirm(`Are you sure you want to STOP ${app.label}?`)) {
                                handleAction("stop", app.id);
                              }
                            }}
                            disabled={actionLoading === `stop-${app.id}`}
                            className="flex-1 bg-red-500/10 hover:bg-red-500/20 text-red-500/60 hover:text-red-500 py-2.5 rounded-xl font-black text-xs uppercase tracking-widest transition-all flex items-center justify-center gap-2 border border-red-500/5 hover:border-red-500/30"
                          >
                            {actionLoading === `stop-${app.id}` ? (
                              <Activity size={14} className="animate-spin" />
                            ) : (
                              <Square size={12} fill="currentColor" />
                            )}
                            Stop
                          </button>
                        </>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </motion.div>
          )}

          {/* Empty State */}
          {!loading && filteredApps.length === 0 && (
            <div className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-white/5 rounded-3xl text-white/60">
              <Search size={48} className="mb-4 opacity-10" />
              <p className="font-bold text-lg">No matching applications found</p>
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  setFilterStatus("all");
                }}
                className="mt-2 text-blue-400 hover:text-blue-300 transition-colors text-sm font-bold"
              >
                Clear all filters
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};
