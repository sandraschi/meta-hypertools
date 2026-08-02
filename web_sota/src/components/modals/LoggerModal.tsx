import { AnimatePresence, motion } from "framer-motion";
import { Download, Terminal, XCircle } from "lucide-react";
import { useEffect, useRef } from "react";

interface LoggerModalProps {
  isOpen: boolean;
  onClose: () => void;
  logs: string[];
}

export function LoggerModal({ isOpen, onClose, logs }: LoggerModalProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={onClose}
          onKeyDown={(e) => {
            if (e.key === "Escape") onClose();
          }}
          role="presentation"
        >
          <motion.dialog
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="w-full max-w-4xl bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] block open:flex"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") e.stopPropagation();
            }}
            tabIndex={-1}
            aria-modal="true"
            open
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-slate-800 rounded-lg">
                  <Terminal className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-200">System Logs</h3>
                  <p className="text-xs text-slate-300 font-mono">stderr / stdout stream</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const blob = new Blob([logs.join("\n")], { type: "text/plain" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `metamcp-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.txt`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="p-2 text-slate-300 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
                  title="Download Logs"
                >
                  <Download size={18} />
                </button>
                <button
                  type="button"
                  onClick={() => onClose()}
                  className="p-2 text-slate-300 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                  title="Close"
                >
                  <XCircle size={20} />
                </button>
              </div>
            </div>

            {/* Log Content */}
            <div className="flex-1 overflow-auto p-4 bg-black/50 font-mono text-xs md:text-sm text-slate-300 space-y-1">
              {logs.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-2 opacity-50">
                  <Terminal size={48} />
                  <p>No logs available to display</p>
                </div>
              ) : (
                logs.map((log, index) => (
                  <div
                    key={`log-${index}-${log.length}`}
                    className="flex gap-3 hover:bg-slate-800/30 px-2 py-0.5 rounded transition-colors group"
                  >
                    <span className="text-slate-600 shrink-0 select-none w-8 text-right">
                      {index + 1}
                    </span>
                    <span className="break-all group-hover:text-slate-100">{log}</span>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-slate-800 bg-slate-950 text-xs text-slate-300 flex justify-between items-center">
              <span>{logs.length} lines · Download to save full log</span>
              <span>Client-side buffer (max 1000)</span>
            </div>
          </motion.dialog>
        </div>
      )}
    </AnimatePresence>
  );
}
