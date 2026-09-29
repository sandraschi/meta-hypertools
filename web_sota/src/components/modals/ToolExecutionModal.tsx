import {
  AlertTriangle,
  CheckCircle,
  FileJson,
  FormInput,
  Loader,
  Play,
  Terminal,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api, isSuccessResponse } from "../../api/client";
import type { ToolWithServer } from "../../pages/Tools";
import { DynamicForm } from "../common/DynamicForm";
import { JsonView } from "../common/JsonView";

interface ToolExecutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  tool: ToolWithServer | null;
}

export function ToolExecutionModal({ isOpen, onClose, tool }: ToolExecutionModalProps) {
  const [mode, setMode] = useState<"form" | "json">("form");
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [jsonParams, setJsonParams] = useState("{}");
  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<unknown | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Reset state when tool changes
  useEffect(() => {
    if (isOpen && tool) {
      setParams({});
      setJsonParams("{}");
      setResult(null);
      setError(null);
      setMode("form");
    }
  }, [isOpen, tool]);

  // Sync params when mode changes
  useEffect(() => {
    if (mode === "json") {
      setJsonParams(JSON.stringify(params, null, 2));
    } else {
      try {
        const parsed = JSON.parse(jsonParams);
        setParams(parsed);
      } catch (_e) {
        // Keep current params if JSON is invalid, maybe warn?
      }
    }
  }, [mode, params, jsonParams]);

  if (!isOpen || !tool) return null;

  const handleExecute = async () => {
    setIsExecuting(true);
    setResult(null);
    setError(null);

    try {
      let finalParams = params;
      if (mode === "json") {
        try {
          finalParams = JSON.parse(jsonParams);
        } catch (_e) {
          throw new Error("Invalid JSON parameters");
        }
      }

      const response = await api.executeTool(tool.server, tool.name, finalParams);

      if (isSuccessResponse(response)) {
        setResult(response.result || response.data);
      } else {
        setError(response.message || "Execution failed");
        if (response.errors) {
          setError(response.errors.join("\n"));
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown execution error");
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
      role="presentation"
    >
      <dialog
        className="bg-slate-900 border border-slate-700 w-full max-w-2xl rounded-2xl shadow-2xl flex flex-col max-h-[85vh] block open:flex"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") e.stopPropagation();
        }}
        tabIndex={-1}
        aria-modal="true"
        open
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-slate-800 rounded-xl text-purple-400">
              <Terminal size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-100">{tool.name}</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className="px-2 py-0.5 bg-slate-800 rounded text-[10px] text-slate-300 font-mono border border-slate-700">
                  {tool.server}
                </span>
                <span className="text-xs text-slate-300">JSON-RPC Tool Execution</span>
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-300 hover:text-slate-300 transition-colors p-2 hover:bg-slate-800 rounded-lg"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Mode Toggle & Input */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label htmlFor="tool-input-params" className="text-sm font-medium text-slate-300">
                Input Parameters
              </label>
              <div className="flex bg-slate-950 rounded-lg p-1 border border-slate-800">
                <button
                  type="button"
                  onClick={() => setMode("form")}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${
                    mode === "form"
                      ? "bg-slate-800 text-slate-200 shadow-sm"
                      : "text-slate-300 hover:text-slate-300"
                  }`}
                >
                  <FormInput size={12} /> Form
                </button>
                <button
                  type="button"
                  onClick={() => setMode("json")}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${
                    mode === "json"
                      ? "bg-slate-800 text-slate-200 shadow-sm"
                      : "text-slate-300 hover:text-slate-300"
                  }`}
                >
                  <FileJson size={12} /> JSON
                </button>
              </div>
            </div>

            {mode === "form" ? (
              <div className="bg-slate-950/30 border border-slate-800/50 rounded-xl p-4">
                <DynamicForm schema={tool.parameters} value={params} onChange={setParams} />
              </div>
            ) : (
              <div className="space-y-2">
                <textarea
                  id="tool-input-params"
                  value={jsonParams}
                  onChange={(e) => setJsonParams(e.target.value)}
                  className="w-full h-48 bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-sm text-slate-300 focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 outline-none resize-none"
                  placeholder="{}"
                />
                {/* JSON Validation Error */}
                {(() => {
                  try {
                    JSON.parse(jsonParams);
                    return null;
                  } catch (_e) {
                    return (
                      <div className="text-xs text-red-400 flex items-center gap-1.5">
                        <AlertTriangle size={12} /> Invalid JSON format
                      </div>
                    );
                  }
                })()}
              </div>
            )}
          </div>

          {/* Result Output */}
          {(result || error) && (
            <div
              className={`rounded-xl border p-4 space-y-2 animate-in slide-in-from-top-2 duration-300 ${error ? "bg-red-950/20 border-red-900/30" : "bg-green-950/20 border-green-900/30"}`}
            >
              <div className="flex items-center gap-2 text-sm font-medium">
                {error ? (
                  <div className="flex items-center gap-2 text-red-400">
                    <AlertTriangle size={16} /> Execution Failed
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-green-400">
                    <CheckCircle size={16} /> Success
                  </div>
                )}
              </div>
              {error ? (
                <pre
                  className={`text-xs font-mono whitespace-pre-wrap overflow-x-auto p-2 rounded-lg bg-black/40 ${error ? "text-red-300" : "text-green-300"}`}
                >
                  {error}
                </pre>
              ) : (
                <JsonView
                  value={result}
                  className="text-xs p-2 rounded-lg bg-black/40 text-green-300"
                />
              )}
            </div>
          )}

          {/* Schema Reference (Always visible functionality for power users) */}
          <div className="space-y-2 pt-4 border-t border-slate-800">
            <details className="group">
              <summary className="text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-slate-300 list-none flex items-center gap-2">
                <div className="transition-transform group-open:rotate-90">▶</div>
                Parameters Schema Reference
              </summary>
              <JsonView
                value={tool.parameters}
                className="mt-2 text-[10px] text-slate-300 bg-slate-950/50 p-3 rounded-lg max-h-32 overflow-y-auto"
              />
            </details>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-800 bg-slate-900/50 flex justify-end gap-3 rounded-b-2xl">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-slate-300 hover:text-slate-200 hover:bg-slate-800 rounded-lg text-sm font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleExecute}
            disabled={isExecuting}
            className="px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white rounded-lg text-sm font-medium shadow-lg shadow-purple-900/20 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isExecuting ? (
              <>
                <Loader size={16} className="animate-spin" />
                Executing...
              </>
            ) : (
              <>
                <Play size={16} />
                Run Tool
              </>
            )}
          </button>
        </div>
      </dialog>
    </div>
  );
}
