import { motion } from "framer-motion";
import { AlertTriangle, Home, RefreshCw } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";
import { logger } from "../utils/logger";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    logger.error("ErrorBoundary caught an error", {
      error: error.message,
      stack: errorInfo.componentStack,
    });
    this.setState({
      error,
      errorInfo,
    });
  }

  private handleRefresh = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = "/";
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#050505] text-white flex items-center justify-center p-4">
          <motion.div
            className="glass-panel p-8 max-w-lg w-full text-center"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            <motion.div
              className="w-16 h-16 mx-auto mb-6 bg-gradient-to-br from-red-500/20 to-red-600/20 rounded-full flex items-center justify-center"
              animate={{
                rotate: [0, 5, -5, 0],
                scale: [1, 1.05, 1],
              }}
              transition={{
                duration: 2,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
              }}
            >
              <AlertTriangle size={32} className="text-red-500" />
            </motion.div>

            <h1 className="text-2xl font-bold mb-4 bg-gradient-to-r from-red-400 to-red-600 bg-clip-text text-transparent">
              Something went wrong
            </h1>

            <p className="text-muted mb-6">
              We encountered an unexpected error. This has been logged and we'll look into it.
            </p>

            <div className="space-y-3 mb-6">
              <button
                type="button"
                onClick={this.handleRefresh}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                <RefreshCw size={16} />
                Refresh Page
              </button>

              <button
                type="button"
                onClick={this.handleGoHome}
                className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-colors flex items-center justify-center gap-2"
              >
                <Home size={16} />
                Go Home
              </button>
            </div>

            {true && this.state.error && (
              <details className="text-left bg-black/20 rounded-lg p-4">
                <summary className="cursor-pointer font-medium mb-2">
                  Error Details (Development Only)
                </summary>
                <pre className="text-xs text-red-300 overflow-auto whitespace-pre-wrap">
                  {this.state.error?.toString() || "Unknown error"}
                  {this.state.errorInfo?.componentStack || ""}
                </pre>
              </details>
            )}

            <div className="text-xs text-muted mt-4">
              If this problem persists, please contact support.
            </div>
          </motion.div>
        </div>
      );
    }

    return this.props.children;
  }
}
