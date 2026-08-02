import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle, Info, XCircle } from "lucide-react";
import { useEffect } from "react";

export interface ToastMessage {
  id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  message?: string;
  duration?: number;
}

interface ToastProps extends ToastMessage {
  onRemove: (id: string) => void;
}

const toastIcons = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const toastColors = {
  success: "from-green-500/20 to-green-600/20 border-green-500/30 text-green-400",
  error: "from-red-500/20 to-red-600/20 border-red-500/30 text-red-400",
  warning: "from-yellow-500/20 to-yellow-600/20 border-yellow-500/30 text-yellow-400",
  info: "from-blue-500/20 to-blue-600/20 border-blue-500/30 text-blue-400",
};

export function Toast({ id, type, title, message, duration = 5000, onRemove }: ToastProps) {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => onRemove(id), duration);
      return () => clearTimeout(timer);
    }
  }, [id, duration, onRemove]);

  const Icon = toastIcons[type];

  return (
    <motion.div
      initial={{ opacity: 0, x: 300, scale: 0.3 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 300, scale: 0.5, transition: { duration: 0.2 } }}
      className={`glass-panel p-4 min-w-[320px] max-w-[480px] border backdrop-blur-xl bg-gradient-to-r ${toastColors[type]}`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <Icon size={20} />
        </div>

        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-sm">{title}</h4>
          {message && <p className="text-xs opacity-90 mt-1 leading-relaxed">{message}</p>}
        </div>

        <button
          type="button"
          onClick={() => onRemove(id)}
          className="flex-shrink-0 p-1 hover:bg-white/10 rounded transition-colors"
          aria-label="Dismiss notification"
        >
          <span>×</span>
        </button>
      </div>

      {duration > 0 && (
        <motion.div
          className="absolute bottom-0 left-0 h-1 bg-current opacity-50 rounded-b-xl"
          initial={{ width: "100%" }}
          animate={{ width: "0%" }}
          transition={{ duration: duration / 1000, ease: "linear" }}
        />
      )}
    </motion.div>
  );
}

interface ToastContainerProps {
  toasts: ToastMessage[];
  onRemove: (id: string) => void;
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      <AnimatePresence>
        {toasts.map((toast) => (
          <Toast key={toast.id} {...toast} onRemove={onRemove} />
        ))}
      </AnimatePresence>
    </div>
  );
}
