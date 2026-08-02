import { AlertCircle, CheckCircle2, Loader, Server, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, isSuccessResponse } from "../../api/client";
import type { DiscoveredServer } from "../../types";
import { logger } from "../../utils/logger";

interface ClientInfo {
  id: string;
  name: string;
  status: string;
  installed: boolean;
  mcp_configured: boolean;
  config_path: string;
}

interface ServerConnectionModalProps {
  server: DiscoveredServer;
  onClose: () => void;
  onConnect?: () => void;
}

export function ServerConnectionModal({ server, onClose, onConnect }: ServerConnectionModalProps) {
  const [clients, setClients] = useState<ClientInfo[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<string>("");
  const [isLoadingClients, setIsLoadingClients] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [config, setConfig] = useState({
    command: server.execution?.command || "uv",
    args: server.execution?.args?.join(" ") || `run ${server.name}`,
    env: JSON.stringify(server.execution?.env || {}, null, 2),
  });

  const fetchClients = useCallback(async () => {
    setIsLoadingClients(true);
    try {
      const response = await api.checkClientIntegration({ operation: "check" });
      if (isSuccessResponse(response)) {
        // Filter for installed clients
        const installed = Object.entries(response.data || {})
          .map(
            ([id, data]: [string, Record<string, unknown>]) =>
              ({ id, ...data }) as unknown as ClientInfo,
          )
          .filter((c: ClientInfo) => c.installed);
        setClients(installed);
        if (installed.length > 0) {
          setSelectedClientId(installed[0].id);
        }
      }
    } catch (err) {
      setError("Failed to load clients");
      logger.error("Failed to load clients", err);
    } finally {
      setIsLoadingClients(false);
    }
  }, []);

  useEffect(() => {
    fetchClients();
  }, [fetchClients]);

  const handleSave = async () => {
    if (!selectedClientId) return;

    setIsSaving(true);
    setError(null);
    setSuccess(null);

    try {
      // 1. Get current config
      const configResp = await api.getClientConfig(selectedClientId);
      if (!isSuccessResponse(configResp)) {
        throw new Error("Failed to fetch client config");
      }

      const currentConfig = (configResp.data ?? {}) as Record<string, unknown>;
      const currentServers = (currentConfig.mcpServers ?? {}) as Record<string, unknown>;

      // 2. Prepare new server entry
      const argsList =
        config.args.match(/(?:[^\s"]+|"[^"]*")+/g)?.map((a) => a.replace(/"/g, "")) || [];
      let envObj = {};
      try {
        envObj = JSON.parse(config.env);
      } catch (_e) {
        // ignore env parse error for now or handle better
      }

      const newServerConfig = {
        command: config.command,
        args: argsList,
        env: Object.keys(envObj).length > 0 ? envObj : undefined,
      };

      // 3. Update config
      const updatedServers = {
        ...currentServers,
        [server.name]: newServerConfig,
      };

      const updateResp = await api.updateClientConfig(selectedClientId, {
        mcpServers: updatedServers,
      });

      if (isSuccessResponse(updateResp)) {
        setSuccess(
          `Successfully connected ${server.name} to ${clients.find((c) => c.id === selectedClientId)?.name}`,
        );
        setTimeout(() => {
          onConnect?.();
          onClose();
        }, 1500);
      } else {
        throw new Error(updateResp.message || "Failed to update config");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect server");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
      role="presentation"
    >
      <dialog
        className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl flex flex-col overflow-hidden block open:flex"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") e.stopPropagation();
        }}
        tabIndex={-1}
        aria-modal="true"
        open
      >
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex justify-between items-center bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
              <Server size={20} />
            </div>
            <div>
              <h3 className="font-bold text-slate-100">Connect Server</h3>
              <p className="text-xs text-slate-300">Configure {server.name}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-300 hover:text-slate-300 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6">
          {/* Client Selection */}
          <div className="space-y-2">
            <label
              htmlFor="target-client"
              className="text-xs font-semibold text-slate-300 uppercase tracking-wider"
            >
              Target Client
            </label>
            {isLoadingClients ? (
              <div className="h-10 bg-slate-800/50 animate-pulse rounded-lg" />
            ) : (
              <select
                id="target-client"
                value={selectedClientId}
                onChange={(e) => setSelectedClientId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-lg px-3 py-2.5 focus:border-blue-500 focus:outline-none transition-colors appearance-none"
              >
                {clients.map((client) => (
                  <option key={client.id} value={client.id}>
                    {client.name} {client.mcp_configured ? "(Configured)" : ""}
                  </option>
                ))}
                {clients.length === 0 && <option disabled>No compatible clients found</option>}
              </select>
            )}
          </div>

          {/* Command Configuration */}
          <div className="space-y-4">
            <div className="space-y-2">
              <label
                htmlFor="conn-command"
                className="text-xs font-semibold text-slate-300 uppercase tracking-wider"
              >
                Command
              </label>
              <input
                id="conn-command"
                type="text"
                value={config.command}
                onChange={(e) => setConfig((prev) => ({ ...prev, command: e.target.value }))}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-lg px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none"
                placeholder="e.g. node, uv, python"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="conn-args"
                className="text-xs font-semibold text-slate-300 uppercase tracking-wider"
              >
                Arguments
              </label>
              <input
                id="conn-args"
                type="text"
                value={config.args}
                onChange={(e) => setConfig((prev) => ({ ...prev, args: e.target.value }))}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-lg px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none"
                placeholder="e.g. build/index.js"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="conn-env"
                className="text-xs font-semibold text-slate-300 uppercase tracking-wider"
              >
                Environment Variables (JSON)
              </label>
              <textarea
                id="conn-env"
                value={config.env}
                onChange={(e) => setConfig((prev) => ({ ...prev, env: e.target.value }))}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-lg px-3 py-2 font-mono text-xs focus:border-blue-500 focus:outline-none min-h-[80px]"
                placeholder="{}"
              />
            </div>
          </div>

          {/* Messages */}
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm flex items-center gap-2">
              <AlertCircle size={16} />
              {error}
            </div>
          )}
          {success && (
            <div className="p-3 bg-green-500/10 border border-green-500/20 text-green-400 rounded-lg text-sm flex items-center gap-2">
              <CheckCircle2 size={16} />
              {success}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-slate-800 bg-slate-950/50 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-slate-300 hover:text-slate-200 hover:bg-slate-800/50 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving || !selectedClientId}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-all flex items-center gap-2 shadow-lg shadow-blue-500/20"
          >
            {isSaving ? <Loader className="animate-spin" size={16} /> : <CheckCircle2 size={16} />}
            Save Connection
          </button>
        </div>
      </dialog>
    </div>
  );
}
