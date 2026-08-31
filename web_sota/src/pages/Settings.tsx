import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  Brain,
  CheckCircle,
  Database,
  Folder,
  RefreshCw,
  Save,
  Settings as SettingsIcon,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import { type LLMConfig, type LLMModel, type LLMProviderInfo, llmService } from "../services/llm";
import { logger } from "../utils/logger";

export const DEFAULT_ROOT_PATH = "";

function LLMSettingsSection() {
  const [config, setConfig] = useState<LLMConfig>(llmService.getConfig());
  const [models, setModels] = useState<LLMModel[]>([]);
  const [providers, setProviders] = useState<LLMProviderInfo[]>([]);
  const [providerMap, setProviderMap] = useState<Record<string, LLMProviderInfo>>({});
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "success">("idle");
  const [discoveryDone, setDiscoveryDone] = useState(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/llm/providers`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => {
        const list = d.providers || [];
        setProviders(list);
        const map: Record<string, LLMProviderInfo> = {};
        for (const p of list) {
          map[p.id] = p;
        }
        setProviderMap(map);
      })
      .catch((e) =>
        setDiscoveryError(e instanceof Error ? e.message : "Failed to discover LLM providers"),
      );
  }, []);

  const handleChange = (field: keyof LLMConfig, value: string) => {
    const newConfig = { ...config, [field]: value };
    if (field === "provider") {
      const p = providerMap[value];
      newConfig.baseUrl = p ? p.base_url : "http://localhost:11434";
      newConfig.model = "";
    }
    setConfig(newConfig);
    setSaveStatus("idle");
    setDiscoveryDone(false);
    setDiscoveryError(null);
  };

  const handleSave = () => {
    if (!config.model.trim()) {
      setDiscoveryError("Select a model before saving.");
      return;
    }
    llmService.saveConfig(config);
    setSaveStatus("success");
    setTimeout(() => setSaveStatus("idle"), 2000);
  };

  const fetchModels = useCallback(async () => {
    setIsLoadingModels(true);
    setDiscoveryError(null);
    try {
      llmService.saveConfig(config);
      const list = await llmService.listModels();
      setModels(list);
      setDiscoveryDone(list.length > 0);
      if (list.length > 0) {
        const ids = list.map((m) => m.id);
        setConfig((prev) => {
          if (prev.model && ids.includes(prev.model)) {
            return prev;
          }
          return { ...prev, model: list[0].id };
        });
      } else {
        setDiscoveryError(
          "No models returned. Start Ollama (ollama serve) or LM Studio and pull a model.",
        );
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setDiscoveryError(msg);
      setDiscoveryDone(false);
      setModels([]);
      logger.error("Failed to fetch models", { error: err });
    } finally {
      setIsLoadingModels(false);
    }
  }, [config]);

  useEffect(() => {
    void fetchModels();
  }, [fetchModels]);

  const modelIds = models.map((m) => m.id);
  const modelReady = config.model.trim().length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      className="glass-panel overflow-hidden bg-black/40 border-white/5 relative group shadow-2xl rounded-3xl"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-purple-600/5 via-transparent to-[#00f3ff]/5 opacity-0 group-hover:opacity-100 transition-opacity duration-1000 pointer-events-none" />

      <div className="px-10 py-8 border-b border-white/5 bg-white/[0.02] flex items-center justify-between relative z-10 backdrop-blur-xl">
        <div className="flex items-center gap-5">
          <div className="p-3 bg-gradient-to-br from-purple-600/20 to-purple-600/10 rounded-2xl border border-purple-600/30 shadow-[0_0_20px_rgba(189,0,255,0.1)] group-hover:scale-110 transition-transform duration-500">
            <Brain className="text-purple-400 w-6 h-6 shadow-glow" />
          </div>
          <div>
            <h3 className="font-black text-xl text-white tracking-tighter">Local LLM</h3>
            <p className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-widest mt-0.5">
              Ollama / LM Studio via MetaMCP API (no browser CORS)
            </p>
          </div>
        </div>
      </div>

      <div className="p-10 space-y-10 relative z-10 bg-black/20">
        {discoveryError && (
          <p className="text-sm text-amber-300 border border-amber-900/50 bg-amber-950/30 rounded-xl px-4 py-3 flex items-start gap-2">
            <AlertCircle size={18} className="shrink-0 mt-0.5" />
            <span>{discoveryError}</span>
          </p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
          <div className="space-y-4">
            <label
              htmlFor="llm-provider"
              className="text-[10px] font-black text-[#94a3b8] uppercase tracking-[0.2em] px-1 flex items-center gap-2"
            >
              <ShieldCheck size={12} className="text-purple-400" /> Provider
            </label>
            <select
              id="llm-provider"
              title="Select Local Inference Provider"
              value={config.provider}
              onChange={(e) => handleChange("provider", e.target.value)}
              className="w-full bg-black/60 border border-white/10 rounded-2xl px-6 py-4 text-white font-bold tracking-tight focus:ring-2 focus:ring-[#bd00ff]/30 outline-none appearance-none cursor-pointer"
            >
              {providers.length === 0 && <option value="ollama">Ollama (11434)</option>}
              {providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label} {p.models.length > 0 ? `(${p.models.length} models)` : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-4">
            <label
              htmlFor="llm-base-url"
              className="text-[10px] font-black text-[#94a3b8] uppercase tracking-[0.2em] px-1 flex items-center gap-2"
            >
              <Database size={12} className="text-blue-400" /> Endpoint
            </label>
            <input
              id="llm-base-url"
              type="text"
              value={config.baseUrl}
              onChange={(e) => handleChange("baseUrl", e.target.value)}
              onBlur={fetchModels}
              className="w-full bg-black/60 border border-white/10 rounded-2xl px-6 py-4 text-blue-400 font-mono text-xs focus:ring-2 focus:ring-[#00f3ff]/30 outline-none"
              placeholder={providerMap[config.provider]?.base_url || "http://localhost:11434"}
            />
          </div>
        </div>

        <div className="space-y-4">
          <label
            htmlFor="llm-model"
            className="text-[10px] font-black text-[#94a3b8] uppercase tracking-[0.2em] px-1 flex items-center gap-2"
          >
            <Zap size={12} className="text-purple-400" /> Model
          </label>
          <div className="flex gap-4 flex-wrap">
            <select
              id="llm-model"
              title="Select model"
              value={modelIds.includes(config.model) ? config.model : ""}
              onChange={(e) => handleChange("model", e.target.value)}
              disabled={modelIds.length === 0}
              className="flex-1 min-w-[200px] bg-black/60 border border-white/10 rounded-2xl px-6 py-4 text-white font-mono text-sm focus:ring-2 focus:ring-[#bd00ff]/30 outline-none appearance-none cursor-pointer disabled:opacity-40"
            >
              <option value="">
                {modelIds.length === 0 ? "Run Discovery to load models…" : "Select a model…"}
              </option>
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id}
                </option>
              ))}
            </select>

            {modelIds.length === 0 && (
              <input
                type="text"
                aria-label="Manual model name"
                value={config.model}
                onChange={(e) => handleChange("model", e.target.value)}
                className="flex-1 min-w-[200px] bg-black/60 border border-white/10 rounded-2xl px-6 py-4 text-blue-400 font-mono text-sm outline-none"
                placeholder="manual model name if discovery failed"
              />
            )}

            <button
              type="button"
              onClick={fetchModels}
              disabled={isLoadingModels}
              className="px-6 py-4 bg-white/5 text-white border border-white/10 rounded-2xl hover:bg-white/10 disabled:opacity-50 font-bold text-xs uppercase tracking-wider flex items-center gap-2"
            >
              {isLoadingModels ? (
                <RefreshCw className="animate-spin w-4 h-4" />
              ) : (
                <RefreshCw className="w-4 h-4 text-blue-400" />
              )}
              {discoveryDone ? `Refresh (${models.length})` : "Discovery"}
            </button>
          </div>
          {modelReady && (
            <p className="text-[11px] text-green-500/90 font-mono">Active: {config.model}</p>
          )}
        </div>
      </div>

      <div className="px-10 py-6 border-t border-white/5 bg-black/40 relative z-10 flex items-center justify-between">
        <span
          className={`text-[9px] font-black uppercase tracking-widest ${
            discoveryDone && modelReady ? "text-green-500" : "text-red-500"
          }`}
        >
          {discoveryDone && modelReady
            ? "Ready for Chat"
            : discoveryDone
              ? "Pick a model and save"
              : "Run Discovery"}
        </span>
        <button
          type="button"
          onClick={handleSave}
          disabled={!modelReady}
          className={`flex items-center gap-3 px-10 py-4 rounded-2xl font-black text-xs uppercase tracking-wider transition-all ${
            saveStatus === "success"
              ? "bg-green-500 text-black"
              : "bg-white text-black hover:scale-105 disabled:opacity-40"
          }`}
        >
          {saveStatus === "success" ? (
            <>
              <CheckCircle size={18} /> Saved
            </>
          ) : (
            <>
              <Save size={18} /> Save config
            </>
          )}
        </button>
      </div>
    </motion.div>
  );
}

export function SettingsPage() {
  const [rootPath, setRootPath] = useState(DEFAULT_ROOT_PATH);
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const savedPath = localStorage.getItem("meta_mcp_root_path");
    if (savedPath) {
      setRootPath(savedPath);
    }
  }, []);

  const handleSave = () => {
    setIsLoading(true);
    setSuccessMessage(null);
    setErrorMessage(null);

    try {
      if (!rootPath.trim()) {
        throw new Error("Root Directory path cannot be empty");
      }

      localStorage.setItem("meta_mcp_root_path", rootPath);
      logger.info(`Settings updated: rootPath=${rootPath}`);
      setSuccessMessage("FLIGHT DATA SYNCHRONIZED: Fleet origin re-indexed.");
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "FAILED: Data binding corrupted.";
      setErrorMessage(msg);
      logger.error("Failed to save settings", { error: err });
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    if (confirm("TEARDOWN_CONFIRMATION: Purge all environmental bindings?")) {
      setRootPath(DEFAULT_ROOT_PATH);
      localStorage.setItem("meta_mcp_root_path", DEFAULT_ROOT_PATH);
      setSuccessMessage("ORIGIN RESTORED");
      setTimeout(() => setSuccessMessage(null), 3000);
    }
  };

  return (
    <div className="space-y-12 max-w-5xl mx-auto pb-32 animate-in fade-in slide-in-from-bottom-6 duration-1000">
      <div className="relative group">
        <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 via-[#bd00ff] to-[#00f3ff] rounded-3xl blur opacity-10 group-hover:opacity-20 transition duration-1000 group-hover:duration-200" />
        <div className="glass-panel p-16 relative overflow-hidden bg-black/60 border-white/5 shadow-2xl rounded-3xl">
          <div className="absolute top-1/2 right-10 -translate-y-1/2 opacity-5 pointer-events-none group-hover:scale-110 transition-transform duration-1000">
            <SettingsIcon size={240} className="text-blue-400 animate-pulse" strokeWidth={1} />
          </div>
          <div className="relative z-10 max-w-2xl">
            <div className="flex items-center gap-3 mb-6">
              <span className="w-12 h-1 bg-blue-500 inline-block shadow-[0_0_10px_#00f3ff]" />
              <span className="text-[10px] font-black text-blue-400 uppercase tracking-[0.5em] italic">
                Environmental Bindings
              </span>
            </div>
            <h1 className="text-6xl font-black mb-6 text-white tracking-tighter uppercase italic leading-[0.9]">
              System <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-purple-600">
                Configuration
              </span>
            </h1>
            <p className="text-[#94a3b8] font-bold text-lg leading-relaxed uppercase tracking-tight max-w-xl">
              Fleet discovery path and local LLM for Chat / Analysis.
            </p>
          </div>
        </div>
      </div>

      <LLMSettingsSection />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="glass-panel overflow-hidden bg-black/40 border-white/5 group relative rounded-3xl shadow-2xl"
      >
        <div className="px-10 py-8 border-b border-white/5 bg-white/[0.02] flex items-center justify-between relative z-10 backdrop-blur-xl">
          <div className="flex items-center gap-5">
            <div className="p-3 bg-gradient-to-br from-blue-500/20 to-[#00f3ff]/5 rounded-2xl border border-blue-500/30">
              <Folder className="text-blue-400 w-6 h-6" />
            </div>
            <div>
              <h3 className="font-black text-xl text-white tracking-tighter uppercase italic">
                Fleet Discovery Origin
              </h3>
              <p className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-widest mt-0.5">
                Auto-scan
              </p>
            </div>
          </div>
        </div>

        <div className="p-10 space-y-10 relative z-10 bg-black/20">
          <div className="space-y-4">
            <label
              htmlFor="fleet-root-path"
              className="text-[10px] font-black text-[#94a3b8] uppercase tracking-[0.2em] px-1"
            >
              Absolute System Path
            </label>
            <input
              id="fleet-root-path"
              type="text"
              value={rootPath}
              onChange={(e) => setRootPath(e.target.value)}
              className="w-full bg-black/60 border border-white/10 rounded-2xl px-8 py-5 text-blue-400 font-mono text-sm outline-none"
              placeholder="/path/to/repos"
            />
          </div>
        </div>

        <div className="px-10 py-6 border-t border-white/5 bg-black/40 flex items-center justify-between relative z-10">
          <button
            type="button"
            onClick={handleReset}
            className="text-[10px] font-black text-[#94a3b8] hover:text-[#ff0055] uppercase tracking-[0.2em] px-6 py-3"
          >
            Emergency Purge
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={isLoading}
            className="flex items-center gap-3 px-12 py-5 bg-gradient-to-r from-blue-500 to-purple-600 text-black rounded-2xl font-black uppercase tracking-wider text-xs disabled:opacity-30"
          >
            {isLoading ? <RefreshCw className="animate-spin" size={18} /> : <Save size={18} />}
            Synchronize Core
          </button>
        </div>
      </motion.div>

      <AnimatePresence>
        {successMessage && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="fixed bottom-10 right-10 p-6 glass-panel bg-green-500/10 border-green-500/20 text-green-400 rounded-3xl flex items-center gap-5 z-50"
          >
            <CheckCircle size={24} />
            <span className="font-black uppercase tracking-widest text-[10px]">
              {successMessage}
            </span>
          </motion.div>
        )}
        {errorMessage && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="fixed bottom-10 right-10 p-6 glass-panel bg-[#ff0055]/10 border-[#ff0055]/20 text-[#ff0055] rounded-3xl flex items-center gap-5 z-50"
          >
            <AlertCircle size={24} />
            <span className="font-black uppercase tracking-widest text-[10px]">{errorMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
