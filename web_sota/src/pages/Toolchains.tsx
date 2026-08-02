import { motion } from "framer-motion";
import { AlertCircle, Layers, Play, Plus, Save, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, isSuccessResponse } from "../api/client";
import type { Toolchain } from "../types";
import { asArray, asRecord, asString } from "../utils/apiTypes";

export function ToolchainsPage() {
  const [toolchains, setToolchains] = useState<Record<string, Toolchain>>({});
  const [availableServers, setAvailableServers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formServers, setFormServers] = useState<string[]>([]);

  // Apply state
  const [applying, setApplying] = useState<string | null>(null);
  const [applyClient, setApplyClient] = useState<string>("cursor");

  const clientsList = ["cursor", "windsurf", "zed", "claude", "antigravity", "opencode"];

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const tcResp = await api.executeTool("metaops", "list_mcp_toolchains", {});
      const srvResp = await api.executeTool("metaops", "show_available_servers", {});

      if (isSuccessResponse(tcResp) && isSuccessResponse(srvResp)) {
        const tcPayload = asRecord(tcResp.result ?? tcResp.data);
        const srvPayload = asRecord(srvResp.result ?? srvResp.data);
        setToolchains((tcPayload.toolchains ?? {}) as Record<string, Toolchain>);
        setAvailableServers(asArray<string>(srvPayload.servers));
      } else {
        setError("Failed to load toolchains or servers.");
      }
    } catch (err: unknown) {
      setError((err as Error).message || "An error occurred while loading data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateToolchain = async () => {
    if (!formName) return;
    try {
      await api.executeTool("metaops", "create_mcp_toolchain", {
        name: formName,
        servers: formServers,
        description: formDescription,
      });
      setShowForm(false);
      setFormName("");
      setFormDescription("");
      setFormServers([]);
      await loadData();
    } catch (err: unknown) {
      alert(`Error creating toolchain: ${(err as Error).message}`);
    }
  };

  const handleDeleteToolchain = async (name: string) => {
    if (!confirm(`Are you sure you want to delete preset '${name}'?`)) return;
    try {
      await api.executeTool("metaops", "delete_mcp_toolchain", { name });
      await loadData();
    } catch (err: unknown) {
      alert(`Error deleting toolchain: ${(err as Error).message}`);
    }
  };

  const handleApplyToolchain = async (toolchainName: string) => {
    setApplying(toolchainName);
    try {
      const resp = await api.executeTool("metaops", "apply_mcp_toolchain", {
        toolchain_name: toolchainName,
        client_name: applyClient,
      });
      if (isSuccessResponse(resp)) {
        const applyPayload = asRecord(resp.result ?? resp.data);
        alert(`Successfully applied: ${asString(applyPayload.message, "Done")}`);
      } else {
        alert("Failed to apply toolchain.");
      }
    } catch (err: unknown) {
      alert(`Error applying toolchain: ${(err as Error).message}`);
    } finally {
      setApplying(null);
    }
  };

  if (loading) {
    return <div className="p-8 text-slate-300">Loading toolchains...</div>;
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-teal-400 mb-2">
            Toolchains & Presets
          </h1>
          <p className="text-slate-300">
            Manage curated collections of MCP servers and rapidly deploy them to IDE clients.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg transition-colors font-semibold"
        >
          <Plus size={18} />
          New Preset
        </button>
      </div>

      {error && (
        <div className="bg-red-900/40 border border-red-500/50 text-red-200 p-4 rounded-lg mb-8 flex items-start gap-3">
          <AlertCircle className="shrink-0 mt-0.5" />
          <p>{error}</p>
        </div>
      )}

      {showForm && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-slate-900 border border-slate-700 rounded-xl p-6 mb-8 shadow-xl"
        >
          <h2 className="text-xl font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <Layers className="text-blue-400" />
            Create Toolchain Preset
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label
                htmlFor="preset-name"
                className="block text-sm font-medium text-slate-300 mb-1"
              >
                Preset Name
              </label>
              <input
                id="preset-name"
                type="text"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white outline-none focus:border-blue-500 transition-colors"
                placeholder="e.g., frontend-dev-stack"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
              />
            </div>
            <div>
              <label
                htmlFor="preset-description"
                className="block text-sm font-medium text-slate-300 mb-1"
              >
                Description (Optional)
              </label>
              <input
                id="preset-description"
                type="text"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white outline-none focus:border-blue-500 transition-colors"
                placeholder="A brief description of this preset"
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
              />
            </div>
          </div>

          <div className="mt-6">
            <p className="block text-sm font-medium text-slate-300 mb-3">
              Select Servers for this Preset
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3 max-h-64 overflow-y-auto pr-2 custom-scrollbar">
              {availableServers.map((server) => (
                <div
                  key={server}
                  className="flex items-center gap-3 p-3 bg-slate-800/50 border border-slate-700/50 rounded-lg group hover:bg-slate-800 transition-colors"
                >
                  <input
                    id={`srv-${server}`}
                    type="checkbox"
                    className="w-4 h-4 rounded border-slate-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-900 bg-slate-900"
                    checked={formServers.includes(server)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFormServers((prev) => [...prev, server]);
                      } else {
                        setFormServers((prev) => prev.filter((s) => s !== server));
                      }
                    }}
                  />
                  <label
                    htmlFor={`srv-${server}`}
                    className="text-slate-300 font-mono text-sm truncate cursor-pointer flex-1"
                    title={server}
                  >
                    {server}
                  </label>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleCreateToolchain}
              disabled={!formName || formServers.length === 0}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900/50 disabled:text-slate-300 text-white px-5 py-2 rounded-lg transition-colors font-medium"
            >
              <Save size={18} />
              Save Preset
            </button>
          </div>
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {Object.values(toolchains).map((tc) => (
          <div
            key={tc.name}
            className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden hover:border-slate-700 transition-colors group flex flex-col"
          >
            <div className="p-6 border-b border-slate-800 flex-1">
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <Layers className="text-teal-400 w-5 h-5" />
                  {tc.name}
                </h3>
                <button
                  type="button"
                  onClick={() => handleDeleteToolchain(tc.name)}
                  className="text-slate-300 hover:text-red-400 transition-colors p-1"
                  title="Delete Preset"
                >
                  <Trash2 size={16} />
                </button>
              </div>
              {tc.description && <p className="text-slate-300 text-sm mb-4">{tc.description}</p>}

              <div className="mt-4">
                <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Included Servers ({tc.servers.length})
                </div>
                <div className="flex flex-wrap gap-2">
                  {tc.servers.map((s: string) => (
                    <span
                      key={s}
                      className="px-2 py-1 bg-slate-800 text-slate-300 text-xs font-mono rounded border border-slate-700"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="bg-slate-950 p-4 border-t border-slate-800 flex items-center justify-between gap-4">
              <div className="flex items-center gap-2 flex-1">
                <select
                  aria-label="Select target client"
                  className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-blue-500 transition-colors flex-1"
                  value={applyClient}
                  onChange={(e) => setApplyClient(e.target.value)}
                >
                  {clientsList.map((c) => (
                    <option key={c} value={c}>
                      Apply to {c.charAt(0).toUpperCase() + c.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={() => handleApplyToolchain(tc.name)}
                disabled={applying === tc.name}
                className="flex items-center gap-2 bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600 hover:text-white px-4 py-2 justify-center rounded-lg transition-colors font-medium text-sm whitespace-nowrap"
              >
                {applying === tc.name ? (
                  <div className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Play size={16} />
                )}
                Apply Preset
              </button>
            </div>
          </div>
        ))}

        {Object.keys(toolchains).length === 0 && !showForm && (
          <div className="col-span-full py-16 text-center text-slate-300 bg-slate-900/50 rounded-xl border border-dashed border-slate-800">
            <Layers className="w-12 h-12 mx-auto mb-4 text-slate-700" />
            <h3 className="text-lg font-medium text-slate-300 mb-2">No Toolchain Presets Found</h3>
            <p className="max-w-md mx-auto">
              Create your first preset to quickly swap between different sets of MCP servers for
              your various development workflows.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
