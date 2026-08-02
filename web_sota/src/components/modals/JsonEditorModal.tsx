import { AlertTriangle, CheckCircle, FileJson, Loader, Save, X } from "lucide-react";
import { useEffect, useState } from "react";

interface JsonEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  clientName: string | null;
  initialData: Record<string, unknown> | null;
  mode: "view" | "edit";
  onSave?: (clientName: string, updatedData: Record<string, unknown>) => Promise<void>;
}

export function JsonEditorModal({
  isOpen,
  onClose,
  clientName,
  initialData,
  mode,
  onSave,
}: JsonEditorModalProps) {
  const [jsonText, setJsonText] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (initialData) {
      setJsonText(JSON.stringify(initialData, null, 2));
    } else {
      setJsonText("");
    }
    setSuccess(false);
    setError(null);
  }, [initialData]);

  if (!isOpen || !clientName) return null;

  const handleSave = async () => {
    if (!onSave) return;

    setIsSaving(true);
    setError(null);
    setSuccess(false);

    try {
      let parsedData: unknown;
      try {
        parsedData = JSON.parse(jsonText);
      } catch (_e) {
        throw new Error("Invalid JSON format");
      }

      if (typeof parsedData !== "object" || parsedData === null || Array.isArray(parsedData)) {
        throw new Error("Configuration must be a JSON object");
      }
      await onSave(clientName, parsedData as Record<string, unknown>);
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save configuration");
    } finally {
      setIsSaving(false);
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
        className="bg-slate-900 border border-slate-700 w-full max-w-2xl rounded-2xl shadow-2xl flex flex-col max-h-[85vh] open:flex"
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
            <div className="p-3 bg-slate-800 rounded-xl text-blue-400">
              <FileJson size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-100">
                {mode === "edit" ? "Configure" : "View Configuration"}: {clientName}
              </h2>
              <p className="text-xs text-slate-300 mt-1">
                {mode === "edit"
                  ? "Update client-specific MCP settings"
                  : "Current active configuration"}
              </p>
            </div>
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
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <div className="relative group flex-1">
            <label htmlFor="json-config-editor" className="sr-only">
              Configuration JSON
            </label>
            <textarea
              id="json-config-editor"
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
              readOnly={mode === "view"}
              className={`w-full h-full min-h-[400px] bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-sm text-slate-300 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none resize-none transition-all ${mode === "view" ? "cursor-default" : ""}`}
              placeholder="{}"
            />
            {mode === "view" && (
              <div className="absolute top-2 right-2 px-2 py-1 bg-slate-800/80 rounded text-[10px] text-slate-300 font-medium uppercase tracking-wider backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity">
                Read Only
              </div>
            )}
          </div>

          {/* Status Feedback */}
          {(error || success) && (
            <div
              className={`rounded-xl border p-4 flex items-center gap-3 animate-in slide-in-from-top-2 duration-300 ${error ? "bg-red-950/20 border-red-900/30 text-red-400" : "bg-green-950/20 border-green-900/30 text-green-400"}`}
            >
              {error ? <AlertTriangle size={18} /> : <CheckCircle size={18} />}
              <span className="text-sm font-medium">
                {error || "Configuration saved successfully!"}
              </span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-800 bg-slate-900/50 flex justify-end gap-3 rounded-b-2xl">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors text-sm font-medium"
          >
            {mode === "edit" ? "Cancel" : "Close"}
          </button>
          {mode === "edit" && (
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-lg text-sm font-medium shadow-lg shadow-blue-900/20 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isSaving ? (
                <>
                  <Loader size={16} className="animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save size={16} />
                  Save Changes
                </>
              )}
            </button>
          )}
        </div>
      </dialog>
    </div>
  );
}
