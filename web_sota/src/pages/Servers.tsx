import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  Box,
  ExternalLink,
  Folder,
  Loader,
  RefreshCw,
  Server,
  Settings,
  Terminal,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, isSuccessResponse } from "../api/client";
import { ServerConnectionModal } from "../components/modals/ServerConnectionModal";
import type { DiscoveredServer } from "../types";
import { asArray, asRecord } from "../utils/apiTypes";
import { logger } from "../utils/logger";

export function ServersPage() {
  const [servers, setServers] = useState<DiscoveredServer[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedServer, setSelectedServer] = useState<DiscoveredServer | null>(null);
  const [showConnectionModal, setShowConnectionModal] = useState(false);

  const handleScan = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const rootPath = localStorage.getItem("meta_mcp_root_path") || "";
      logger.info(`Scanning for servers in: ${rootPath}`);

      const response = await api.discoverServers({
        operation: "scan_root",
        discovery_path: rootPath,
      });

      if (isSuccessResponse(response)) {
        const rawData = response.result ?? response.data;
        const found = Array.isArray(rawData)
          ? rawData
          : asArray<DiscoveredServer>(asRecord(rawData).servers);
        setServers(found);
        logger.info(`Discovered ${found.length} servers in ${rootPath}`);
      } else {
        throw new Error(response.message || "Failed to discover servers");
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error during discovery";
      setError(msg);
      logger.error("Server discovery failed", { error: err });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    handleScan();
  }, [handleScan]);

  return (
    <div className="space-y-8 h-full flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Hero Section */}
      <div className="glass-panel p-10 relative overflow-hidden bg-white/[0.01] border-white/5 flex items-center justify-between">
        <div className="absolute top-0 right-0 p-8 opacity-20 pointer-events-none">
          <Server size={120} className="text-blue-400 animate-pulse" />
        </div>
        <div>
          <h1 className="text-3xl font-black mb-2 bg-gradient-to-r from-white via-white to-white/40 bg-clip-text text-transparent">
            Server Fleet Hub
          </h1>
          <p className="text-[#94a3b8] max-w-xl">
            Discover, monitor, and manage the unified MCP ecosystem. Connect remote execution
            endpoints and analyze capabilities.
          </p>
        </div>
        <button
          type="button"
          onClick={handleScan}
          disabled={isLoading}
          className="relative px-6 py-3 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 rounded-xl font-bold transition-all duration-300 disabled:opacity-50 flex items-center gap-3 border border-blue-500/30 shadow-[0_0_20px_rgba(0,243,255,0.1)] hover:shadow-[0_0_30px_rgba(0,243,255,0.2)]"
        >
          {isLoading ? <Loader className="animate-spin" size={18} /> : <RefreshCw size={18} />}
          Scan Network grid
        </button>
      </div>

      {/* Error State */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="glass-panel p-4 bg-red-500/10 border-red-500/20 flex items-center gap-3 text-red-400 font-medium"
          >
            <AlertCircle size={20} />
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Content Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {servers.map((server, idx) => (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            key={server.path || server.name || idx}
            onClick={() => setSelectedServer(server)}
            className="glass-panel p-6 bg-white/[0.02] border-white/5 hover:bg-white/[0.05] cursor-pointer transition-all duration-300 group shadow-xl relative overflow-hidden"
          >
            {/* Hover Gradient Effect */}
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/0 via-[#00f3ff]/0 to-[#00f3ff]/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />

            <div className="flex items-start justify-between relative z-10">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-white/5 rounded-xl text-white group-hover:text-blue-400 transition-colors shadow-inner border border-white/5">
                  <Box size={22} />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-white group-hover:text-blue-400 transition-colors tracking-tight">
                    {server.name}
                  </h3>
                  <p className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider mt-0.5">
                    {server.type}
                  </p>
                </div>
              </div>
              <div
                className={`w-3 h-3 rounded-full ${server.status === "running" ? "bg-green-400 shadow-[0_0_10px_rgba(74,222,128,0.5)] animate-pulse" : "bg-[#888888]/50"}`}
              />
            </div>

            <p className="text-sm text-[#94a3b8] line-clamp-2 min-h-[2.5em] mt-5 mb-5 relative z-10 leading-relaxed font-medium">
              {server.description || "No description capability profile provided."}
            </p>

            <div className="flex items-center justify-between pt-5 border-t border-white/5 relative z-10">
              <div className="flex items-center gap-4 text-xs font-bold uppercase tracking-wider text-[#94a3b8]">
                <span className="flex items-center gap-2 bg-black/20 px-3 py-1.5 rounded-lg border border-white/5 shadow-inner">
                  <Terminal size={14} className="text-blue-400" />
                  {server.tools_count || 0} tools
                </span>
              </div>
              <ExternalLink
                size={16}
                className="text-[#94a3b8] group-hover:text-blue-400 transition-colors"
              />
            </div>
          </motion.div>
        ))}

        {!isLoading && servers.length === 0 && !error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="col-span-full py-24 text-center glass-panel bg-white/[0.01] border-white/5"
          >
            <Folder className="mx-auto w-16 h-16 mb-5 text-white/60" />
            <p className="text-xl font-bold text-white tracking-tight">
              No Servers Discovered in Fleet
            </p>
            <p className="text-[#94a3b8] mt-2 font-medium">
              Scan the root grid directory to populate the registry
            </p>
          </motion.div>
        )}
      </div>

      {/* Details Modal */}
      <AnimatePresence>
        {selectedServer && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4"
            onClick={() => setSelectedServer(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="glass-panel bg-slate-950/80 border-white/10 rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden shadow-2xl flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-8 border-b border-white/5 flex justify-between items-start bg-white/[0.02]">
                <div className="flex items-center gap-5">
                  <div className="p-4 bg-blue-500/10 text-blue-400 rounded-2xl border border-blue-500/20 shadow-[0_0_20px_rgba(0,243,255,0.15)]">
                    <Box size={36} />
                  </div>
                  <div>
                    <h2 className="text-3xl font-black text-white tracking-tight">
                      {selectedServer.name}
                    </h2>
                    <code className="text-xs text-blue-400 bg-blue-500/5 px-3 py-1.5 rounded-lg border border-blue-500/10 mt-2 block w-fit font-mono">
                      {selectedServer.path}
                    </code>
                  </div>
                </div>
                <button
                  type="button"
                  className="text-[#94a3b8] hover:text-white p-2 transition-colors"
                  onClick={() => setSelectedServer(null)}
                >
                  ✕
                </button>
              </div>

              <div className="p-8 overflow-y-auto space-y-8 bg-black/20">
                <div>
                  <h4 className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-widest mb-3">
                    System Profile
                  </h4>
                  <p className="text-white/80 leading-relaxed font-medium text-lg">
                    {selectedServer.description || "No system profile available for this node."}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-5">
                  <div className="glass-panel p-5 bg-white/[0.02] border-white/5">
                    <div className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-widest mb-2">
                      Telemetry Status
                    </div>
                    <div
                      className={`text-xl font-black capitalize flex items-center gap-2 ${selectedServer.status === "running" ? "text-green-400" : "text-[#94a3b8]"}`}
                    >
                      <span
                        className={`w-2 h-2 rounded-full ${selectedServer.status === "running" ? "bg-green-400 animate-pulse" : "bg-[#888888]"}`}
                      />
                      {selectedServer.status || "Offline"}
                    </div>
                  </div>
                  <div className="glass-panel p-5 bg-white/[0.02] border-white/5">
                    <div className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-widest mb-2">
                      Capabilities count
                    </div>
                    <div className="text-2xl font-black text-white">
                      {selectedServer.tools_count || 0}
                    </div>
                  </div>
                </div>

                <div className="flex gap-4 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowConnectionModal(true)}
                    className="flex-1 py-4 bg-gradient-to-r from-blue-500 to-purple-600 hover:opacity-90 text-black rounded-xl font-black tracking-wide transition-opacity shadow-[0_0_20px_rgba(0,243,255,0.3)]"
                  >
                    Execute Connection Binding
                  </button>
                  <button
                    type="button"
                    className="p-4 border border-white/10 hover:bg-white/5 rounded-xl text-white transition-colors glass-panel bg-white/[0.02]"
                  >
                    <Settings size={22} className="text-[#94a3b8]" />
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Connection Modal */}
      <AnimatePresence>
        {selectedServer && showConnectionModal && (
          <ServerConnectionModal
            server={selectedServer}
            onClose={() => setShowConnectionModal(false)}
            onConnect={() => {
              handleScan();
              setShowConnectionModal(false);
              setSelectedServer(null);
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
