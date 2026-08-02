import { AnimatePresence, motion } from "framer-motion";
import { Command, HelpCircle, Keyboard, XCircle } from "lucide-react";

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function HelpModal({ isOpen, onClose }: HelpModalProps) {
  const shortcuts = [
    { keys: ["⌘", "K"], description: "Quick Search" },
    { keys: ["⌘", "/"], description: "Toggle Logs" },
    { keys: ["Esc"], description: "Close Modals" },
    { keys: ["?"], description: "Show Help" },
  ];

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
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden block open:block"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") e.stopPropagation();
            }}
            tabIndex={-1}
            aria-modal="true"
            open
          >
            <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-950">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <HelpCircle className="w-6 h-6 text-blue-400" />
                </div>
                <h2 className="text-xl font-semibold text-slate-200">Keyboard Shortcuts</h2>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="p-2 text-slate-300 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
              >
                <XCircle size={24} />
              </button>
            </div>

            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              {shortcuts.map((item) => (
                <div
                  key={item.description}
                  className="flex items-center justify-between p-4 rounded-lg bg-slate-950/50 border border-slate-800"
                >
                  <div className="flex items-center gap-3 text-slate-300">
                    <Keyboard className="w-4 h-4 text-slate-300" />
                    <span>{item.description}</span>
                  </div>
                  <div className="flex gap-1">
                    {item.keys.map((key) => (
                      <kbd
                        key={key}
                        className="px-2 py-1 bg-slate-800 border border-slate-700 rounded-md text-slate-300 text-xs font-mono min-w-[24px] text-center shadow-sm"
                      >
                        {key}
                      </kbd>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="p-6 border-t border-slate-800 bg-slate-950/30">
              <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
                <Command className="w-4 h-4 text-purple-400" />
                MetaMCP Architecture
              </h3>
              <p className="text-sm text-slate-300 leading-relaxed">
                This dashboard connects to the local{" "}
                <code className="bg-slate-800 px-1 py-0.5 rounded text-blue-300">meta-mcp</code>{" "}
                server instance. Actions performed here are executed directly on your host machine
                via the FastMCP protocol.
              </p>
            </div>
          </motion.dialog>
        </div>
      )}
    </AnimatePresence>
  );
}
