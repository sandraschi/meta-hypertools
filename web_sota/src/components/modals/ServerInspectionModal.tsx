import { AlertTriangle, Code, Database, FileText, Loader, Terminal, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, isSuccessResponse } from "../../api/client";
import { asArray, asString } from "../../utils/apiTypes";

interface ServerInspectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  serverName: string | null;
  config: {
    command: string;
    args: string[];
    env?: Record<string, string>;
  } | null;
}

export function ServerInspectionModal({
  isOpen,
  onClose,
  serverName,
  config,
}: ServerInspectionModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [activeTab, setActiveTab] = useState<"tools" | "resources" | "prompts" | "raw">("tools");

  const tools = asArray<Record<string, unknown>>(data?.tools);
  const resources = asArray<Record<string, unknown>>(data?.resources);
  const prompts = asArray<Record<string, unknown>>(data?.prompts);

  const handleInspect = useCallback(async () => {
    if (!config) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.inspectServer(config);
      if (isSuccessResponse(response)) {
        setData(response.data as Record<string, unknown>);
      } else {
        setError(response.message || "Inspection failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to inspect server");
    } finally {
      setLoading(false);
    }
  }, [config]);

  useEffect(() => {
    if (isOpen && config) {
      handleInspect();
    } else {
      setData(null);
      setError(null);
    }
  }, [isOpen, config, handleInspect]);

  if (!isOpen || !serverName) return null;

  const tabs = [
    { id: "tools", label: "Tools", icon: <Terminal size={16} /> },
    { id: "resources", label: "Resources", icon: <Database size={16} /> },
    { id: "prompts", label: "Prompts", icon: <FileText size={16} /> },
    { id: "raw", label: "Raw JSON", icon: <Code size={16} /> },
  ] as const;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
      role="presentation"
    >
      <dialog
        className="bg-slate-900 border border-slate-700 w-full max-w-4xl rounded-2xl shadow-2xl flex flex-col max-h-[85vh] open:flex"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "Escape") onClose();
          if (e.key === "Enter" || e.key === " ") e.stopPropagation();
        }}
        tabIndex={-1}
        aria-modal="true"
        aria-labelledby="modal-title"
        open
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800">
          <div>
            <h2
              id="modal-title"
              className="text-xl font-bold text-slate-100 flex items-center gap-2"
            >
              <Database className="text-blue-400" size={24} />
              Viewing Server: {serverName}
            </h2>
            <p className="text-xs text-slate-300 mt-1">
              Inspect capabilities, tools, and resources exposed by this server
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-300 hover:text-slate-300 p-2 hover:bg-slate-800 rounded-lg transition-colors"
            aria-label="Close Modal"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {loading ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-300 gap-4">
              <Loader size={32} className="animate-spin text-blue-500" />
              <p>Connecting to server and fetching capabilities...</p>
            </div>
          ) : error ? (
            <div className="flex-1 flex flex-col items-center justify-center text-red-400 gap-4 p-8 text-center">
              <AlertTriangle size={48} />
              <h3 className="text-lg font-bold">Inspection Failed</h3>
              <p className="text-slate-300 max-w-lg">{error}</p>
              <button
                type="button"
                onClick={handleInspect}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-white mt-4 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : data ? (
            <>
              {/* Tabs */}
              <div className="flex border-b border-slate-800 px-6">
                {tabs.map((tab) => (
                  <button
                    type="button"
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? "border-blue-500 text-blue-400"
                        : "border-transparent text-slate-300 hover:text-slate-300 hover:border-slate-700"
                    }`}
                  >
                    {tab.icon}
                    {tab.label}
                    <span className="ml-1 px-1.5 py-0.5 bg-slate-800 rounded-full text-xs text-slate-300">
                      {tab.id === "raw" ? "" : (data?.[tab.id] as unknown[])?.length || 0}
                    </span>
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-y-auto p-6 bg-slate-950/50">
                {activeTab === "tools" && (
                  <div className="space-y-4">
                    {tools.map((tool) => (
                      <div
                        key={String(tool.name)}
                        className="bg-slate-900 border border-slate-800 rounded-xl p-4"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <h4 className="text-lg font-semibold text-blue-400 font-mono">
                            {asString(tool.name)}
                          </h4>
                        </div>
                        <p className="text-slate-300 text-sm mb-4">{asString(tool.description)}</p>
                        <div className="bg-slate-950 rounded-lg p-3 border border-slate-800">
                          <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                            Input Schema
                          </h5>
                          <pre className="text-xs text-slate-300 font-mono overflow-x-auto">
                            {JSON.stringify(tool.inputSchema, null, 2)}
                          </pre>
                        </div>
                      </div>
                    ))}
                    {tools.length === 0 && (
                      <div className="text-center text-slate-300 py-12">No tools available</div>
                    )}
                  </div>
                )}

                {activeTab === "resources" && (
                  <div className="space-y-4">
                    {resources.map((resource) => (
                      <div
                        key={String(resource.uri)}
                        className="bg-slate-900 border border-slate-800 rounded-xl p-4"
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <Database size={16} className="text-purple-400" />
                          <h4 className="font-semibold text-slate-200">
                            {resource.name as string}
                          </h4>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-slate-300 block text-xs">URI</span>
                            <code className="text-blue-400 bg-blue-900/20 px-1 py-0.5 rounded">
                              {resource.uri as string}
                            </code>
                          </div>
                          <div>
                            <span className="text-slate-300 block text-xs">MIME Type</span>
                            <span className="text-slate-300">{resource.mimeType as string}</span>
                          </div>
                        </div>
                        {typeof resource.description === "string" && resource.description && (
                          <p className="text-slate-300 text-sm mt-3 pt-3 border-t border-slate-800">
                            {resource.description}
                          </p>
                        )}
                      </div>
                    ))}
                    {resources.length === 0 && (
                      <div className="text-center text-slate-300 py-12">No resources available</div>
                    )}
                  </div>
                )}

                {activeTab === "prompts" && (
                  <div className="space-y-4">
                    {prompts.map((prompt) => (
                      <div
                        key={String(prompt.name)}
                        className="bg-slate-900 border border-slate-800 rounded-xl p-4"
                      >
                        <h4 className="text-lg font-semibold text-green-400 mb-2">
                          {prompt.name as string}
                        </h4>
                        <p className="text-slate-300 text-sm mb-4">
                          {prompt.description as string}
                        </p>
                        {Array.isArray(prompt.arguments) && prompt.arguments.length > 0 && (
                          <div className="space-y-2">
                            <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                              Arguments
                            </h5>
                            {((prompt.arguments || []) as Record<string, unknown>[]).map((arg) => (
                              <div
                                key={String(arg.name)}
                                className="flex items-center gap-2 text-sm"
                              >
                                <code className="text-slate-300 bg-slate-800 px-1 rounded">
                                  {arg.name as string}
                                </code>
                                <span className="text-slate-300">
                                  {arg.required ? "(required)" : "(optional)"}
                                </span>
                                <span className="text-slate-300">
                                  - {arg.description as string}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                    {prompts.length === 0 && (
                      <div className="text-center text-slate-300 py-12">No prompts available</div>
                    )}
                  </div>
                )}

                {activeTab === "raw" && (
                  <div className="relative flex-1">
                    <label htmlFor="server-raw-json" className="sr-only">
                      Raw Server Capabilities JSON
                    </label>
                    <textarea
                      id="server-raw-json"
                      readOnly
                      value={JSON.stringify(data, null, 2)}
                      className="w-full h-96 bg-slate-900 border border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-300 focus:outline-none resize-none"
                    />
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>

        <div className="p-4 border-t border-slate-800 bg-slate-900 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors text-sm font-medium"
          >
            Close
          </button>
        </div>
      </dialog>
    </div>
  );
}
