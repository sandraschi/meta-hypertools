import { motion } from "framer-motion";
import {
  Activity,
  BarChart3,
  BookOpen,
  Bot,
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
  MessageCircle,
  NotebookText,
  Package,
  PanelLeftClose,
  Rocket,
  ScrollText,
  Server,
  Settings,
  Shield,
  Terminal,
  Wrench,
} from "lucide-react";
import { useState } from "react";

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
}

export function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    { id: "dashboard", label: "Dashboard", icon: Home },
    { id: "assess-reports", label: "Assess Reports", icon: ClipboardList },
    { id: "assfix-sop", label: "Assfix SOP", icon: ClipboardCheck },
    { id: "session-docs", label: "Session Docs", icon: NotebookText },
    { id: "justfile", label: "Fleet Justfile", icon: ScrollText },
    { id: "fleet", label: "Fleet Status", icon: Activity },
    { id: "fleet-ops", label: "Fleet Ops", icon: Rocket },
    { id: "agent-hub", label: "Fritz / RoboFang", icon: Bot },
    { id: "chat", label: "Chat", icon: MessageCircle },
    { id: "servers", label: "Server Registry", icon: Server },
    { id: "clients", label: "Clients", icon: Database },
    { id: "toolchains", label: "Toolchains", icon: Layers },
    { id: "builders", label: "Builders", icon: Hammer },
    { id: "tools", label: "Tools", icon: Terminal },
    { id: "harness", label: "Harness Generator", icon: Wrench },
    { id: "tool-lab", label: "Tool Sandbox", icon: FlaskConical },
    { id: "tauri-build", label: "Tauri Build", icon: Package },
    { id: "repo-inspiration", label: "Repo Inspiration", icon: BookOpen },
    { id: "analysis", label: "SOTA Check", icon: BarChart3 },
    { id: "config-audit", label: "Config Audit", icon: FileText },
    { id: "scrubbers", label: "Scrubbers", icon: Shield },
    { id: "settings", label: "Settings", icon: Settings },
    { id: "logs", label: "Logs", icon: Terminal },
    { id: "help", label: "Help", icon: HelpCircle },
    { id: "about", label: "About", icon: Info },
  ];

  return (
    <motion.div
      animate={{ width: collapsed ? 64 : 260 }}
      className="h-screen bg-[#0a0a0f] border-r border-slate-800 flex flex-col z-20 shrink-0 overflow-hidden"
    >
      <div className="h-14 flex items-center justify-between px-4 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Activity className="w-5 h-5 text-blue-400 shrink-0" />
          {!collapsed && (
            <span className="font-semibold text-sm text-slate-200 whitespace-nowrap">meta-mcp</span>
          )}
        </div>
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-md text-slate-500 hover:bg-slate-800 hover:text-slate-300 transition-colors shrink-0"
          title={collapsed ? "Expand" : "Collapse"}
        >
          <PanelLeftClose size={16} />
        </button>
      </div>

      <div className="flex-1 py-3 flex flex-col gap-0.5 px-2 overflow-y-auto no-scrollbar">
        {menuItems.map((item) => {
          const isActive = currentPage === item.id;
          const Icon = item.icon;
          return (
            <button
              type="button"
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`
                flex items-center gap-3 px-2.5 py-2 rounded-lg transition-colors text-sm whitespace-nowrap
                ${
                  isActive
                    ? "bg-blue-500/15 text-blue-300 font-medium"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                }
              `}
            >
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </button>
          );
        })}
      </div>
    </motion.div>
  );
}
