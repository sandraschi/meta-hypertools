import { motion } from "framer-motion";
import {
  Activity,
  BarChart3,
  BookOpen,
  Bot,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  ClipboardList,
  Database,
  FileText,
  FlaskConical,
  Hammer,
  HelpCircle,
  Home,
  Info,
  Layers,
  type LucideIcon,
  MessageCircle,
  NotebookText,
  Package,
  PanelLeftClose,
  PanelLeftOpen,
  Rocket,
  ScrollText,
  Server,
  Settings,
  Shield,
  Terminal,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
}

interface NavGroup {
  id: string;
  label: string;
  icon: LucideIcon;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    id: "overview",
    label: "Overview & AI",
    icon: Home,
    items: [
      { id: "dashboard", label: "Dashboard", icon: Home },
      { id: "chat", label: "Agent Chat", icon: MessageCircle },
      { id: "agent-hub", label: "Fritz / RoboFang", icon: Bot },
      { id: "session-docs", label: "Session Docs", icon: NotebookText },
    ],
  },
  {
    id: "fleet",
    label: "Fleet & Operations",
    icon: Rocket,
    items: [
      { id: "fleet", label: "Fleet Status", icon: Activity },
      { id: "fleet-ops", label: "Fleet Ops & Scripts", icon: Rocket },
      { id: "justfile", label: "Fleet Justfile", icon: ScrollText },
      { id: "assess-reports", label: "Assess Reports", icon: ClipboardList },
      { id: "assfix-sop", label: "Assfix SOP", icon: ClipboardCheck },
    ],
  },
  {
    id: "mcp",
    label: "MCP Registry & Tools",
    icon: Server,
    items: [
      { id: "servers", label: "Server Registry", icon: Server },
      { id: "clients", label: "Client Integrations", icon: Database },
      { id: "toolchains", label: "Toolchains", icon: Layers },
      { id: "tools", label: "Tools Catalog", icon: Terminal },
      { id: "tool-lab", label: "Tool Sandbox", icon: FlaskConical },
      { id: "harness", label: "Harness Generator", icon: Wrench },
    ],
  },
  {
    id: "analysis",
    label: "Analysis & Diagnostics",
    icon: BarChart3,
    items: [
      { id: "analysis", label: "SOTA Check", icon: BarChart3 },
      { id: "config-audit", label: "Config Audit", icon: FileText },
      { id: "scrubbers", label: "Unicode & Scrubbers", icon: Shield },
      { id: "logs", label: "System Logs", icon: Terminal },
    ],
  },
  {
    id: "builders",
    label: "Builders & Dev",
    icon: Hammer,
    items: [
      { id: "builders", label: "Scaffolding Wizard", icon: Hammer },
      { id: "tauri-build", label: "Tauri Native Build", icon: Package },
      { id: "repo-inspiration", label: "Repo Inspiration", icon: BookOpen },
    ],
  },
  {
    id: "system",
    label: "System",
    icon: Settings,
    items: [
      { id: "settings", label: "Settings", icon: Settings },
      { id: "help", label: "Help & Shortcuts", icon: HelpCircle },
      { id: "about", label: "About MetaMCP", icon: Info },
    ],
  },
];

const COLLAPSED_GROUPS_KEY = "metamcp_sidebar_collapsed_groups";

export function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>(() => {
    try {
      const stored = localStorage.getItem(COLLAPSED_GROUPS_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(COLLAPSED_GROUPS_KEY, JSON.stringify(collapsedGroups));
    } catch {
      // ignore localstorage errors
    }
  }, [collapsedGroups]);

  const toggleGroup = (groupId: string) => {
    setCollapsedGroups((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }));
  };

  return (
    <motion.div
      animate={{ width: sidebarCollapsed ? 70 : 275 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="h-screen bg-[#090a10] border-r border-slate-800/80 flex flex-col z-20 shrink-0 select-none"
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800/80 shrink-0 bg-[#0c0d14]">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-[0_0_12px_rgba(59,130,246,0.5)] shrink-0">
            <Activity className="w-4 h-4 text-white" />
          </div>
          {!sidebarCollapsed && (
            <div className="flex flex-col min-w-0">
              <span className="font-bold text-sm text-slate-100 tracking-tight flex items-center gap-1.5">
                MetaMCP{" "}
                <span className="text-[11px] font-semibold text-blue-400 bg-blue-500/15 px-1.5 py-0.5 rounded">
                  v2.5
                </span>
              </span>
              <span className="text-xs text-slate-400 truncate">Fleet Control Center</span>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shrink-0"
          title={sidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          aria-label={sidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {sidebarCollapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
        </button>
      </div>

      {/* Navigation Groups */}
      <div className="flex-1 py-3 px-2.5 overflow-y-auto no-scrollbar space-y-3">
        {NAV_GROUPS.map((group) => {
          const isGroupCollapsed = Boolean(collapsedGroups[group.id]);
          const hasActiveChild = group.items.some((item) => item.id === currentPage);

          return (
            <div key={group.id} className="space-y-0.5">
              {/* Group Header */}
              {!sidebarCollapsed ? (
                <button
                  type="button"
                  onClick={() => toggleGroup(group.id)}
                  className={`
                    w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs font-bold uppercase tracking-wider transition-colors
                    ${hasActiveChild ? "text-blue-300" : "text-slate-400 hover:text-slate-200"}
                  `}
                >
                  <span className="flex items-center gap-2">
                    <span>{group.label}</span>
                    <span className="text-[11px] text-slate-400 font-semibold bg-slate-800/80 px-1.5 py-0.2 rounded-full">
                      {group.items.length}
                    </span>
                  </span>
                  {isGroupCollapsed ? (
                    <ChevronRight size={14} className="text-slate-400" />
                  ) : (
                    <ChevronDown size={14} className="text-slate-400" />
                  )}
                </button>
              ) : (
                <div className="h-px bg-slate-800 my-2 mx-1" />
              )}

              {/* Group Items */}
              {(!isGroupCollapsed || sidebarCollapsed) && (
                <div className="space-y-0.5">
                  {group.items.map((item) => {
                    const isActive = currentPage === item.id;
                    const Icon = item.icon;

                    return (
                      <button
                        type="button"
                        key={item.id}
                        onClick={() => onNavigate(item.id)}
                        title={sidebarCollapsed ? item.label : undefined}
                        className={`
                          w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all text-left
                          ${
                            isActive
                              ? "bg-blue-600/20 text-blue-200 border border-blue-500/30 shadow-[0_0_12px_rgba(59,130,246,0.15)] font-semibold"
                              : "text-slate-300 hover:text-white hover:bg-slate-800/60"
                          }
                        `}
                      >
                        <Icon
                          size={18}
                          className={`shrink-0 ${isActive ? "text-blue-400" : "text-slate-400"}`}
                        />
                        {!sidebarCollapsed && <span className="truncate flex-1">{item.label}</span>}
                        {!sidebarCollapsed && item.badge && (
                          <span className="text-[11px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 shrink-0">
                            {item.badge}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}
