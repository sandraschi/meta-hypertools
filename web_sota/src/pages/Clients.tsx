import { CheckCircle, Database, Loader, RefreshCw, XCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, isSuccessResponse } from "../api/client";
import { JsonEditorModal } from "../components/modals/JsonEditorModal";
import { ServerInspectionModal } from "../components/modals/ServerInspectionModal";
import type { IntegrationStatus } from "../types";
import { type McpServerConfig, asMcpServerConfig, asRecord } from "../utils/apiTypes";

interface ClientCheckEntry {
  installed?: boolean;
  config_path?: string;
  mcp_servers?: Record<string, unknown>;
}

interface ClientsProps {
  clients: Record<string, IntegrationStatus>;
  setClients: (clients: Record<string, IntegrationStatus>) => void;
}

export function ClientsPage({ clients, setClients }: ClientsProps) {
  const [checking, setChecking] = useState<Record<string, boolean>>({});
  const checkedRef = useRef(false);

  // Config Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"view" | "edit">("view");
  const [selectedClient, setSelectedClient] = useState<string | null>(null);
  const [configData, setConfigData] = useState<Record<string, unknown> | null>(null);

  // Inspection Modal state
  const [isInspectOpen, setIsInspectOpen] = useState(false);
  const [inspectServer, setInspectServer] = useState<string | null>(null);
  const [inspectConfig, setInspectConfig] = useState<McpServerConfig | null>(null);

  const handleCheckClients = useCallback(async () => {
    setChecking(Object.fromEntries(Object.keys(clients).map((key) => [key, true])));

    try {
      const response = await api.checkClientIntegration({ operation: "check" });
      const newStatus = { ...clients };

      if (isSuccessResponse(response) && response.data) {
        const results = asRecord(response.data) as Record<string, ClientCheckEntry>;
        for (const client of Object.keys(clients)) {
          const clientData = results[client];
          if (clientData) {
            newStatus[client] = {
              connected: clientData.installed === true,
              path: clientData.config_path,
              error: !clientData.installed ? "Not installed" : undefined,
              servers: clientData.mcp_servers,
            };
          } else {
            newStatus[client] = { connected: false, error: "Not detected" };
          }
        }
      } else {
        for (const client of Object.keys(clients)) {
          newStatus[client] = { connected: false, error: response.message || "Check failed" };
        }
      }
      setClients(newStatus);
    } catch (e) {
      const newStatus = { ...clients };
      for (const client of Object.keys(clients)) {
        newStatus[client] = {
          connected: false,
          error: e instanceof Error ? e.message : "Unknown error",
        };
      }
      setClients(newStatus);
    } finally {
      setChecking({});
    }
  }, [clients, setClients]);

  // Only run once on mount to avoid infinite loop (clients ref changes trigger re-render)
  useEffect(() => {
    if (!checkedRef.current) {
      checkedRef.current = true;
      handleCheckClients();
    }
  }, [handleCheckClients]);

  const handleViewJson = async (clientName: string) => {
    setSelectedClient(clientName);
    setModalMode("view");
    try {
      const response = await api.getClientConfig(clientName);
      if (isSuccessResponse(response)) {
        setConfigData(asRecord(asRecord(response.data).config));
        setIsModalOpen(true);
      }
    } catch (_error) {}
  };

  const handleConfigure = async (clientName: string) => {
    setSelectedClient(clientName);
    setModalMode("edit");
    try {
      const response = await api.getClientConfig(clientName);
      if (isSuccessResponse(response)) {
        setConfigData(asRecord(asRecord(response.data).config));
        setIsModalOpen(true);
      }
    } catch (_error) {}
  };

  const handleInspect = (serverName: string, config: unknown) => {
    const parsed = asMcpServerConfig(config);
    if (!parsed) return;
    setInspectServer(serverName);
    setInspectConfig(parsed);
    setIsInspectOpen(true);
  };

  const handleSaveConfig = async (clientName: string, updatedData: Record<string, unknown>) => {
    const response = await api.updateClientConfig(clientName, updatedData);
    if (!isSuccessResponse(response)) {
      throw new Error(response.message || "Failed to update configuration");
    }
    handleCheckClients();
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-900/50 border border-slate-700 rounded-2xl p-6">
        <div className="flex items-center gap-2 text-xs font-semibold text-blue-400 mb-3">
          <Database size={14} /> Client Integrations
        </div>
        <h1 className="text-2xl font-bold text-slate-100 mb-2">Client Integrations</h1>
        <p className="text-sm text-slate-400 max-w-2xl">
          Manage MCP integrations across your development environment.
        </p>

        <div className="mt-6 flex items-center justify-between">
          <div className="text-sm font-medium text-slate-400">
            {Object.keys(clients).length} configured clients
          </div>
          <button
            type="button"
            onClick={handleCheckClients}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl transition-colors text-sm"
          >
            <RefreshCw size={14} className="group-hover:rotate-180 transition-transform" />
            Scan clients
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {Object.entries(clients).map(([name, value]) => (
          <div
            key={name}
            className="bg-slate-800/80 border border-slate-700 rounded-xl p-5 flex flex-col"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-slate-700/80">
                  <Database size={18} className="text-slate-300" />
                </div>
                <div>
                  <div className="font-semibold text-slate-200 capitalize">{name}</div>
                  <div className="text-xs text-slate-500">MCP client</div>
                </div>
              </div>
              {checking[name] ? (
                <Loader size={18} className="animate-spin text-blue-400" />
              ) : value.connected ? (
                <CheckCircle size={18} className="text-emerald-400" />
              ) : (
                <XCircle size={18} className="text-slate-600" />
              )}
            </div>

            <div className="space-y-2 flex-1">
              <div className="px-3 py-2 bg-slate-900/60 rounded-lg border border-slate-700">
                <div className="text-xs text-slate-500 mb-0.5">Status</div>
                <div
                  className={
                    value.connected
                      ? "text-emerald-400 text-sm font-medium"
                      : "text-slate-400 text-sm"
                  }
                >
                  {value.connected ? "Connected" : "Offline"}
                </div>
              </div>

              <div className="px-3 py-2 bg-slate-900/60 rounded-lg border border-slate-700">
                <div className="text-xs text-slate-500 mb-0.5">Config path</div>
                <div className="text-slate-500 text-xs font-mono truncate" title={value.path || ""}>
                  {value.path || (checking[name] ? "Scanning..." : "Not found")}
                </div>
              </div>

              {value.error && (
                <div className="px-3 py-2 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-400">
                  {value.error}
                </div>
              )}

              {value.servers && Object.keys(value.servers).length > 0 && (
                <div className="pt-3 border-t border-slate-700">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-xs text-slate-500 font-medium">Servers</div>
                    <div className="text-xs text-slate-500 bg-slate-700 px-2 py-0.5 rounded">
                      {Object.keys(value.servers).length}
                    </div>
                  </div>
                  <div className="space-y-1.5 max-h-36 overflow-y-auto">
                    {Object.entries(value.servers).map(([serverName, config]) => (
                      <div
                        key={serverName}
                        className="flex items-center justify-between bg-slate-900/80 hover:bg-slate-900 px-3 py-2 rounded-lg border border-slate-700 text-sm"
                      >
                        <span className="text-slate-400 truncate max-w-[140px]" title={serverName}>
                          {serverName}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleInspect(serverName, config)}
                          className="px-2 py-1 bg-slate-700 text-slate-400 hover:bg-slate-600 hover:text-slate-200 rounded-md text-xs transition-colors"
                        >
                          Inspect
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-5 pt-4 border-t border-slate-700 flex gap-2">
              <button
                type="button"
                onClick={() => handleConfigure(name)}
                className="flex-1 py-2 bg-blue-500/15 hover:bg-blue-500/25 text-blue-300 text-sm font-medium rounded-lg transition-colors"
              >
                Configure
              </button>
              <button
                type="button"
                onClick={() => handleViewJson(name)}
                className="flex-1 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm rounded-lg transition-colors"
              >
                View JSON
              </button>
            </div>
          </div>
        ))}
      </div>

      <JsonEditorModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        clientName={selectedClient}
        initialData={configData}
        mode={modalMode}
        onSave={handleSaveConfig}
      />

      <ServerInspectionModal
        isOpen={isInspectOpen}
        onClose={() => setIsInspectOpen(false)}
        serverName={inspectServer}
        config={inspectConfig}
      />
    </div>
  );
}
