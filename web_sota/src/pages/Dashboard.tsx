import { motion } from "framer-motion";
import {
  Box,
  Bug,
  Cpu,
  FileSearch,
  Hammer,
  Layers,
  Network,
  Rocket,
  Server,
  Shield,
  Terminal,
  Wand2,
  Zap,
} from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import type { McpTool } from "../types";
import type { IntegrationStatus } from "../types";

interface DashboardProps {
  servers: Record<string, Record<string, unknown>>;
  clients: Record<string, IntegrationStatus>;
  tools: McpTool[];
  onNavigate: (page: string) => void;
}

interface CategoryDef {
  label: string;
  icon: React.ElementType;
  color: string;
  shadow: string;
  patterns: string[];
  description: string;
  navigateTo: string;
}

const CATEGORIES: Record<string, CategoryDef> = {
  scaffolding: {
    label: "Project Scaffolding",
    icon: Hammer,
    color: "from-emerald-500",
    shadow: "shadow-emerald-500/20",
    patterns: ["scaffold_"],
    description: "Generate fullstack apps, MCP servers, landing pages, games & more",
    navigateTo: "builders",
  },
  analysis: {
    label: "Code Analysis",
    icon: FileSearch,
    color: "from-blue-500",
    shadow: "shadow-blue-500/20",
    patterns: [
      "analyze_",
      "show_mcp_status",
      "deep_scan_repo",
      "audit_mcp_",
      "scan_mcp_",
      "validate_mcp_",
      "check_context",
    ],
    description: "Scan repos, detect runts, audit implementations, analyze tokens",
    navigateTo: "analysis",
  },
  fleet: {
    label: "Server & Fleet",
    icon: Server,
    color: "from-purple-600",
    shadow: "shadow-purple-600/20",
    patterns: [
      "list_mcp_servers",
      "start_mcp_server",
      "stop_mcp_server",
      "show_server_status",
      "get_fleet",
      "launch_fleet",
      "stop_fleet",
      "ping_fleet",
      "probe_fleet",
      "heartbeat_pulse",
      "config_proactive",
    ],
    description: "Start/stop servers, fleet health, auto-restart monitoring",
    navigateTo: "fleet",
  },
  clients: {
    label: "Client Configs",
    icon: Network,
    color: "from-amber-500",
    shadow: "shadow-amber-500/20",
    patterns: [
      "read_client",
      "update_client",
      "add_mcp_server",
      "remove_mcp_server",
      "validate_client",
      "list_client_configs",
    ],
    description: "Manage IDE integrations: Claude, Cursor, Windsurf, Antigravity",
    navigateTo: "clients",
  },
  toolchains: {
    label: "Toolchains & Execution",
    icon: Layers,
    color: "from-[#ff0055]",
    shadow: "shadow-[#ff0055]/20",
    patterns: [
      "list_mcp_toolchains",
      "create_mcp_toolchain",
      "delete_mcp_toolchain",
      "apply_mcp_toolchain",
      "show_available_servers",
      "execute_mcp_tool",
      "validate_tool_schema",
      "show_tool_history",
    ],
    description: "Create, apply, and sync curated MCP server presets",
    navigateTo: "toolchains",
  },
  repo_ops: {
    label: "Repository Ops",
    icon: Box,
    color: "from-violet-500",
    shadow: "shadow-violet-500/20",
    patterns: [
      "pack_",
      "diff_mcp",
      "export_mcp",
      "find_orphan",
      "tail_log",
      "verify_system",
      "summarize_server",
      "digest_mcp",
      "audit_secret",
      "audit_mcp_surface",
    ],
    description: "Pack repos, diff configs, export snippets, audit secrets",
    navigateTo: "tools",
  },
  diagnostics: {
    label: "Diagnostics",
    icon: Bug,
    color: "from-rose-500",
    shadow: "shadow-rose-500/20",
    patterns: [
      "show_mcp_overview",
      "list_mcp_tools",
      "find_mcp_tools",
      "open_mcp_launcher",
      "refresh_mcp_fleet",
      "discovery_ops",
      "audit_ide_integration",
    ],
    description: "Tool discovery, fleet launcher, platform overview, server scanning",
    navigateTo: "tools",
  },
  security: {
    label: "Security",
    icon: Shield,
    color: "from-red-500",
    shadow: "shadow-red-500/20",
    patterns: ["verify_exploit", "generate_patch", "benny_handshake"],
    description: "Verify exploits, generate patches, physical auth",
    navigateTo: "tools",
  },
  scheduling: {
    label: "Automation",
    icon: Cpu,
    color: "from-cyan-500",
    shadow: "shadow-cyan-500/20",
    patterns: ["schedule_", "list_scheduled", "cancel_scheduled"],
    description: "Schedule recurring MCP tasks at fixed intervals",
    navigateTo: "tools",
  },
};

function matchCategory(toolName: string): string | null {
  for (const [key, cat] of Object.entries(CATEGORIES)) {
    for (const pattern of cat.patterns) {
      if (toolName.startsWith(pattern) || toolName === pattern) return key;
    }
  }
  return null;
}

export function DashboardPage({ servers, tools, onNavigate }: DashboardProps) {
  const navigate = onNavigate;
  const [localTools, setLocalTools] = useState<McpTool[]>(tools);
  const [catalogError, setCatalogError] = useState<string | null>(null);

  useEffect(() => {
    if (tools.length > 0) {
      setLocalTools(tools);
      return;
    }
    setCatalogError(null);
    fetch(`${API_BASE}/api/v1/mcp/catalog`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((resp) => {
        if (resp.success) {
          const data = resp.result ?? resp.data;
          const raw = (data?.tools ?? []) as Array<{ name: string; description?: string }>;
          setLocalTools(
            raw.map((t: { name: string; description?: string }) => ({
              name: t.name,
              description: t.description || "",
              parameters: {},
              server: "metaops",
            })),
          );
        }
      })
      .catch((e) => setCatalogError(e instanceof Error ? e.message : "Failed to load tools"));
  }, [tools]);

  const activeTools = localTools.length > 0 ? localTools : tools;
  const serversList = Object.values(servers);
  const activeServers = serversList.filter((s) => s.status === "online").length;
  const totalServers = serversList.length;
  const totalTools = activeTools.length;

  // Capability counts by category
  const categoryCounts: Record<string, number> = {};
  for (const tool of activeTools) {
    const cat = matchCategory(tool.name);
    if (cat) categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
  }

  // Quick actions — direct-to-page navigation + tool calls
  const quickActions = [
    {
      label: "SOTA Compliance",
      icon: FileSearch,
      onClick: () => navigate("analysis"),
      color: "from-blue-500",
      hint: "40+ standards, runt detection, score",
    },
    {
      label: "Scaffold Project",
      icon: Wand2,
      onClick: () => navigate("builders"),
      color: "from-emerald-500",
      hint: "Fullstack app, MCP server, game",
    },
    {
      label: "Browse Tools",
      icon: Terminal,
      onClick: () => navigate("tools"),
      color: "from-purple-600",
      hint: `${totalTools} capabilities`,
    },
    {
      label: "Manage Toolchains",
      icon: Layers,
      onClick: () => navigate("toolchains"),
      color: "from-[#ff0055]",
      hint: "Curated MCP presets",
    },
    {
      label: "Fleet Status",
      icon: Rocket,
      onClick: () => navigate("fleet"),
      color: "from-amber-500",
      hint: "Health, boot, zombie audit",
    },
    {
      label: "Config Audit",
      icon: Shield,
      onClick: () => navigate("config-audit"),
      color: "from-violet-500",
      hint: "llms.txt, .env, glama.json, .cursorrules",
    },
  ];

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-6 duration-1000">
      {/* Hero Section */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-2xl p-6">
        <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 mb-4">
          <Zap size={14} /> Fleet Operational
        </div>
        <h1 className="text-2xl font-bold text-slate-100 mb-6">MetaMCP Orchestrator</h1>

        {/* Live KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700">
            <p className="text-slate-300 text-xs font-medium mb-1">Registered Tools</p>
            <p className="text-2xl font-bold text-slate-100">
              {catalogError ? (
                <span className="text-red-400 text-sm" title={catalogError}>
                  ? error
                </span>
              ) : (
                totalTools
              )}
            </p>
          </div>
          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700">
            <p className="text-slate-300 text-xs font-medium mb-1">Active Servers</p>
            <p
              className={`text-2xl font-bold ${activeServers > 0 ? "text-emerald-400" : "text-red-400"}`}
            >
              {activeServers}
              <span className="text-sm text-slate-300 ml-1">/{totalServers}</span>
            </p>
          </div>
          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700">
            <p className="text-slate-300 text-xs font-medium mb-1">Categories</p>
            <p className="text-2xl font-bold text-slate-100">{Object.keys(CATEGORIES).length}</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700">
            <p className="text-slate-300 text-xs font-medium mb-1">Tool Suites</p>
            <p className="text-2xl font-bold text-slate-100">
              {Object.keys(categoryCounts).length}
            </p>
          </div>
        </div>

        <p className="text-slate-300 max-w-2xl text-sm leading-relaxed">
          Scaffold fullstack apps and MCP servers. Analyze repositories for runts, stub
          implementations, and token bloat. Manage IDE client configs, toolchain presets, and
          fleet-wide server health.
        </p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {quickActions.map((action) => (
          <button
            type="button"
            key={action.label}
            onClick={action.onClick}
            className={
              "bg-slate-800/80 border border-slate-700 hover:bg-slate-700/80 rounded-xl p-4 transition-colors text-left cursor-pointer"
            }
          >
            <action.icon size={20} className="text-slate-300 mb-2" />
            <div className="text-sm font-semibold text-slate-200">{action.label}</div>
            <div className="text-xs text-slate-300 mt-0.5">{action.hint}</div>
          </button>
        ))}
      </div>

      {/* Capability Categories */}
      <div>
        <h2 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
          <Zap size={18} className="text-blue-400" />
          Capability Registry
          <span className="text-xs text-slate-300 ml-2">
            {totalTools} tools / {Object.keys(CATEGORIES).length} categories
          </span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {Object.entries(CATEGORIES).map(([key, cat], idx) => {
            const count = categoryCounts[key] || 0;
            return (
              <motion.button
                key={key}
                type="button"
                onClick={() => navigate(cat.navigateTo)}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05, duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
                className="bg-slate-800/80 border border-slate-700 hover:bg-slate-700/80 rounded-xl p-5 transition-colors text-left cursor-pointer w-full"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-slate-700/80">
                    <cat.icon size={18} className="text-slate-300" />
                  </div>
                  <div className="text-base font-semibold text-slate-200">{cat.label}</div>
                </div>
                <div className="text-2xl font-bold text-slate-100 mb-1">
                  {count}
                  <span className="text-sm font-normal text-slate-300 ml-1">tools</span>
                </div>
                <div className="text-sm text-slate-300 leading-relaxed">{cat.description}</div>
              </motion.button>
            );
          })}
        </div>
      </div>

      {/* Fleet Status */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
            <Server size={18} className="text-blue-400" />
            Fleet Registry
            <span className="text-xs text-slate-300 ml-2">
              {activeServers} / {totalServers} online
            </span>
          </h2>
          <button
            type="button"
            onClick={() => navigate("servers")}
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            Manage Servers
          </button>
        </div>

        {serversList.length === 0 ? (
          <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-8 text-center">
            <Server size={36} className="mx-auto mb-4 text-slate-600" />
            <p className="text-base font-semibold text-slate-300 mb-1">
              No MCP servers registered yet
            </p>
            <p className="text-sm text-slate-300 mb-4">
              Discover servers or add them to client configs.
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => navigate("servers")}
                className="px-4 py-2 bg-blue-500/20 border border-blue-500/30 rounded-lg text-sm font-medium text-blue-300 hover:bg-blue-500/30 transition-colors"
              >
                Server Manager
              </button>
              <button
                type="button"
                onClick={() => navigate("clients")}
                className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-600 transition-colors"
              >
                Client Configs
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {Object.entries(servers)
              .slice(0, 8)
              .map(([id, data], idx) => (
                <motion.div
                  key={id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05, duration: 0.3 }}
                  className="bg-slate-800/80 border border-slate-700 hover:bg-slate-700/80 rounded-xl p-4 transition-colors cursor-pointer"
                  onClick={() => navigate("servers")}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div
                      className={`w-2 h-2 rounded-full ${data.status === "online" ? "bg-emerald-500" : "bg-red-500"}`}
                    />
                    <span className="text-sm font-medium text-slate-200 truncate">{id}</span>
                  </div>
                  <div className="text-xs text-slate-300">
                    {typeof data.status === "string" ? data.status : "unknown"}
                  </div>
                </motion.div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}
