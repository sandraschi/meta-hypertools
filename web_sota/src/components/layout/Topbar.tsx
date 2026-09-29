import {
  AlertTriangle,
  Bell,
  HelpCircle,
  Loader2,
  Moon,
  ScrollText,
  Search,
  Sun,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { asArray, asRecord } from "../../utils/apiTypes";
import { logger } from "../../utils/logger";
import { BackendDot } from "../common/BackendDot";

// EXPERIMENTAL light mode (invert hack). Not fleet standard - see index.css.
// Toggling `.dark` off the root flips the invert filter; persisted so the
// choice survives reloads. Delete this + the CSS block to revert.
const THEME_KEY = "meta-hypertools-light-mode";

function useExperimentalTheme() {
  const [light, setLight] = useState(() => {
    try {
      return localStorage.getItem(THEME_KEY) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", !light);
    try {
      localStorage.setItem(THEME_KEY, light ? "1" : "0");
    } catch {
      // ignore storage errors
    }
  }, [light]);

  return { light, toggle: () => setLight((v) => !v) };
}

interface TopbarProps {
  title: string;
  onShowLogger: () => void;
  onShowHelp: () => void;
}

export function Topbar({ title, onShowLogger, onShowHelp }: TopbarProps) {
  const [isStopping, setIsStopping] = useState(false);
  const { light, toggle } = useExperimentalTheme();

  const handleEmergencyStop = async () => {
    if (
      !confirm("EMERGENCY STOP: This will attempt to stop ALL running MCP servers. Are you sure?")
    ) {
      return;
    }

    setIsStopping(true);
    logger.warn("Initiating EMERGENCY STOP of all servers...");

    try {
      // 1. List running servers
      const listRes = await api.listRunningServers();
      if (!listRes.success || !listRes.result) {
        logger.error("Failed to list running servers during emergency stop");
        return;
      }

      const raw = listRes.result ?? listRes.data;
      const servers = asArray<{ id?: string; name?: string }>(
        Array.isArray(raw) ? raw : asArray(asRecord(raw).servers),
      );
      if (servers.length === 0) {
        logger.info("No running servers found to stop.");
        alert("No running servers found.");
        return;
      }

      // 2. Stop each server
      let stoppedCount = 0;
      for (const server of servers) {
        logger.info(`Stopping server: ${server.id || server.name}...`);
        try {
          await api.stopMcpServer(server.id ?? server.name ?? "");
          stoppedCount++;
        } catch (err) {
          logger.error(`Failed to stop server ${server.id}`, { error: err });
        }
      }

      logger.info(`Emergency Stop Complete. Stopped ${stoppedCount} servers.`);
      alert(`Emergency Stop Complete. ${stoppedCount} servers stopped.`);
    } catch (error) {
      logger.error("Critical error during Emergency Stop", { error });
      alert("Emergency Stop Failed! check logs.");
    } finally {
      setIsStopping(false);
    }
  };

  return (
    <div className="h-24 border-b border-white/5 bg-zinc-950/90 backdrop-blur-2xl flex items-center justify-between px-10 sticky top-0 z-10 shadow-[0_10px_40px_rgba(0,0,0,0.5)]">
      {/* Breadcrumb / Title */}
      <div className="flex items-center gap-6">
        <div className="h-8 w-1.5 bg-gradient-to-b from-blue-500 to-purple-600 rounded-full shadow-[0_0_15px_rgba(0,243,255,0.5)]" />
        <h1 className="text-3xl font-black text-white tracking-tighter uppercase">{title}</h1>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-6">
        <BackendDot />
        {/* Search Bar */}
        <div className="relative hidden xl:block group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8] group-focus-within:text-blue-400 transition-colors" />
          <input
            type="text"
            placeholder="SEARCH CORE INFRASTRUCTURE..."
            onChange={(e) => {
              const query = e.target.value.toLowerCase().trim();
              if (query) {
                logger.info(`Search query: ${query}`);
              }
            }}
            className="bg-black/60 border border-white/5 text-white text-[10px] font-black tracking-widest uppercase rounded-xl pl-12 pr-6 py-3 w-80 focus:outline-none focus:ring-2 focus:ring-[#00f3ff]/50 focus:border-blue-500/50 transition-all shadow-inner"
          />
        </div>

        <div className="flex items-center gap-2 bg-white/5 p-1.5 rounded-2xl border border-white/5 shadow-inner">
          {/* Day mode toggle */}
          <button
            type="button"
            onClick={toggle}
            className="p-3 text-[#94a3b8] hover:text-[#00f3ff] hover:bg-white/5 rounded-xl transition-all group"
            title={
              light
                ? "Switch to dark (experimental light mode)"
                : "Switch to light (experimental, ugly)"
            }
            aria-label="Toggle light mode (experimental)"
          >
            {light ? (
              <Moon className="w-5 h-5 group-hover:scale-110 transition-transform" />
            ) : (
              <Sun className="w-5 h-5 group-hover:scale-110 transition-transform" />
            )}
          </button>

          {/* Logger Toggle */}
          <button
            type="button"
            onClick={onShowLogger}
            className="p-3 text-[#94a3b8] hover:text-blue-400 hover:bg-white/5 rounded-xl transition-all group"
            title="System Logs"
          >
            <ScrollText className="w-5 h-5 group-hover:scale-110 transition-transform" />
          </button>

          {/* Help Toggle */}
          <button
            type="button"
            onClick={onShowHelp}
            className="p-3 text-[#94a3b8] hover:text-[#22c55e] hover:bg-white/5 rounded-xl transition-all group"
            title="Help & Shortcuts"
          >
            <HelpCircle className="w-5 h-5 group-hover:scale-110 transition-transform" />
          </button>

          {/* Notifications */}
          <button
            type="button"
            title="Quick Notifications"
            className="relative p-3 text-[#94a3b8] hover:text-white hover:bg-white/5 rounded-xl transition-all group"
          >
            <Bell className="w-5 h-5 group-hover:scale-110 transition-transform" />
            <span className="absolute top-3 right-3 w-2.5 h-2.5 bg-[#ff0055] rounded-full border-2 border-black animate-pulse shadow-[0_0_10px_rgba(255,0,85,0.5)]" />
          </button>
        </div>

        {/* Emergency Stop */}
        <button
          type="button"
          onClick={handleEmergencyStop}
          disabled={isStopping}
          className="flex items-center gap-3 px-6 py-3 bg-[#ff0055]/10 text-[#ff0055] border border-[#ff0055]/20 rounded-xl hover:bg-[#ff0055]/20 transition-all text-xs font-black uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed group shadow-lg"
        >
          {isStopping ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <AlertTriangle className="w-4 h-4 group-hover:animate-bounce" />
          )}
          <span className="hidden lg:inline">{isStopping ? "HALTING..." : "Emergency STOP"}</span>
        </button>
      </div>
    </div>
  );
}
