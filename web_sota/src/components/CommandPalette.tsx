import { AnimatePresence, motion } from "framer-motion";
import { Command, RefreshCw, Search, Settings, Zap } from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useApiContext } from "../context/ApiContext";
import { useToast } from "../context/ToastContext";

interface PaletteCommand {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<Record<string, unknown>>;
  action: () => void;
  category: string;
  keywords?: string[];
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const { refreshHealth } = useApiContext();
  const { info } = useToast();

  // Define available commands
  const commands: PaletteCommand[] = useMemo(
    () => [
      {
        id: "refresh-health",
        title: "Refresh Health Status",
        description: "Check server and service health",
        icon: RefreshCw,
        category: "System",
        keywords: ["health", "status", "check", "server"],
        action: () => {
          refreshHealth();
          info("Refreshing...", "Checking server health status");
          onClose();
        },
      },
      {
        id: "open-settings",
        title: "Open Settings",
        description: "Access application settings and preferences",
        icon: Settings,
        category: "Navigation",
        keywords: ["settings", "preferences", "config"],
        action: () => {
          // This would trigger navigation to settings tab
          window.dispatchEvent(new CustomEvent("navigate-to-settings"));
          onClose();
        },
      },
      {
        id: "run-emoji-buster",
        title: "Run EmojiBuster Scan",
        description: "Scan repositories for Unicode crash risks",
        icon: Zap,
        category: "Tools",
        keywords: ["emoji", "scan", "unicode", "crash"],
        action: () => {
          // This would trigger the emoji buster
          window.dispatchEvent(new CustomEvent("run-emoji-buster"));
          onClose();
        },
      },
      {
        id: "run-server-discovery",
        title: "Discover MCP Servers",
        description: "Find and list available MCP servers",
        icon: Search,
        category: "Tools",
        keywords: ["servers", "discover", "mcp", "find"],
        action: () => {
          // This would trigger server discovery
          window.dispatchEvent(new CustomEvent("run-server-discovery"));
          onClose();
        },
      },
      {
        id: "run-runt-analyzer",
        title: "Run Runt Analyzer",
        description: "Audit project compliance with professional standards",
        icon: Command,
        category: "Tools",
        keywords: ["runt", "analyzer", "audit", "compliance"],
        action: () => {
          // This would trigger runt analyzer
          window.dispatchEvent(new CustomEvent("run-runt-analyzer"));
          onClose();
        },
      },
    ],
    [refreshHealth, info, onClose],
  );

  // Filter commands based on query
  const filteredCommands = useMemo(() => {
    if (!query) return commands;

    const lowercaseQuery = query.toLowerCase();
    return commands.filter(
      (command) =>
        command.title.toLowerCase().includes(lowercaseQuery) ||
        command.description.toLowerCase().includes(lowercaseQuery) ||
        command.category.toLowerCase().includes(lowercaseQuery) ||
        command.keywords?.some((keyword) => keyword.includes(lowercaseQuery)),
    );
  }, [commands, query]);

  // Reset selected index when filtered commands change
  useEffect(() => {
    setSelectedIndex(0);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setSelectedIndex((prev) => (prev < filteredCommands.length - 1 ? prev + 1 : prev));
          break;
        case "ArrowUp":
          e.preventDefault();
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev));
          break;
        case "Enter":
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            filteredCommands[selectedIndex].action();
          }
          break;
        case "Escape":
          e.preventDefault();
          onClose();
          break;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, selectedIndex, filteredCommands, onClose]);

  // Group commands by category
  const groupedCommands = useMemo(() => {
    return filteredCommands.reduce(
      (acc, command) => {
        if (!acc[command.category]) {
          acc[command.category] = [];
        }
        acc[command.category].push(command);
        return acc;
      },
      {} as Record<string, PaletteCommand[]>,
    );
  }, [filteredCommands]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-start justify-center pt-[20vh]"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: -20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: -20 }}
          className="glass-panel w-full max-w-2xl mx-4 max-h-[60vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Search Input */}
          <div className="p-4 border-b border-white/10">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={20} />
              <input
                ref={inputRef}
                type="text"
                placeholder="Type a command or search..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#00f3ff] text-lg"
              />
            </div>
            <div className="flex items-center justify-between mt-2 text-xs text-muted">
              <div className="flex items-center gap-4">
                <span>↑↓ to navigate</span>
                <span>↵ to select</span>
                <span>esc to close</span>
              </div>
              <span>{filteredCommands.length} commands</span>
            </div>
          </div>

          {/* Commands List */}
          <div className="overflow-y-auto max-h-[400px]">
            {Object.entries(groupedCommands).map(([category, categoryCommands]) => (
              <div key={category} className="p-2">
                <div className="px-2 py-1 text-xs font-semibold text-muted uppercase tracking-wide">
                  {category}
                </div>
                {categoryCommands.map((command) => {
                  const globalIndex = filteredCommands.findIndex((c) => c.id === command.id);
                  const Icon = command.icon;

                  return (
                    <motion.button
                      type="button"
                      key={command.id}
                      onClick={command.action}
                      className={`w-full text-left p-3 rounded-lg transition-all duration-200 flex items-center gap-3 ${
                        globalIndex === selectedIndex
                          ? "bg-blue-500/20 border border-blue-500/50"
                          : "hover:bg-white/5"
                      }`}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <div
                        className={`p-2 rounded-lg ${
                          globalIndex === selectedIndex ? "bg-blue-500/20" : "bg-white/10"
                        }`}
                      >
                        <Icon size={16} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium">{command.title}</div>
                        <div className="text-sm text-muted truncate">{command.description}</div>
                      </div>
                      {globalIndex === selectedIndex && (
                        <div className="text-blue-400 font-mono text-sm">↵ Enter</div>
                      )}
                    </motion.button>
                  );
                })}
              </div>
            ))}

            {filteredCommands.length === 0 && (
              <div className="p-8 text-center text-muted">
                <Command size={48} className="mx-auto mb-4 opacity-50" />
                <p>No commands found</p>
                <p className="text-sm">Try a different search term</p>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
