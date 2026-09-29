import { useCallback, useEffect, useState } from "react";
import { api, isSuccessResponse } from "./api/client";
// Import Modern Pages
import { AppsHub } from "./components/AppsHub";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Layout } from "./components/layout/Layout";
import { HelpModal } from "./components/modals/HelpModal";
import { LoggerModal } from "./components/modals/LoggerModal";

import { AboutPage } from "./pages/About";
import { AgentHubPage } from "./pages/AgentHub";
import { AnalysisPage } from "./pages/Analysis";
import { AssessReportsPage } from "./pages/AssessReports";
import { AssfixSOPPage } from "./pages/AssfixSOP";
import { BuildersPage } from "./pages/Builders";
import { ChatPage } from "./pages/Chat";
import { ClientsPage } from "./pages/Clients";
import { ConfigAuditPage } from "./pages/ConfigAudit";
import { DashboardPage } from "./pages/Dashboard";
import { FleetDashboard } from "./pages/FleetDashboard";
import { FleetOps } from "./pages/FleetOps";
import { HarnessPage } from "./pages/Harness";
import { HelpPage } from "./pages/Help";
import { JustfilePage } from "./pages/JustfilePage";
import { LogsPage } from "./pages/LogsPage";
import { RepoInspirationPage } from "./pages/RepoInspiration";
import { ScrubbersPage } from "./pages/Scrubbers";
import { ServersPage } from "./pages/Servers";
import { SessionDocsPage } from "./pages/SessionDocs";
import { SettingsPage } from "./pages/Settings";
import { StandardsPage } from "./pages/Standards";
import TauriBuildPage from "./pages/TauriBuild";
import { ToolLabPage } from "./pages/ToolLab";
import { ToolchainsPage } from "./pages/Toolchains";
import { ToolsPage } from "./pages/Tools";
import { type LogEntry, logger } from "./utils/logger";

import type { IntegrationStatus, McpTool } from "./types";

function App() {
  // Navigation State
  const [currentPage, setCurrentPage] = useState("dashboard");

  // Modal State
  const [showLogger, setShowLogger] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  // Data State
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [servers, setServers] = useState<Record<string, Record<string, unknown>>>({});
  const [clients, setClients] = useState<Record<string, IntegrationStatus>>({
    claude: { connected: false },
    cursor: { connected: false },
    windsurf: { connected: false },
    zed: { connected: false },
    antigravity: { connected: false },
    opencode: { connected: false },
    vscode: { connected: false },
  });
  const [tools, setTools] = useState<McpTool[]>([]);

  // Logs State (Shared)
  const [logs, setLogs] = useState<string[]>([]);

  const loadDashboardData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const serversResp = await api.executeTool("metaops", "discovery_ops", {
        operation: "servers",
      });
      if (isSuccessResponse(serversResp)) {
        const payload = serversResp.result ?? serversResp.data;
        const inner =
          payload && typeof payload === "object" && "data" in payload
            ? (payload as { data: { servers?: unknown[] } }).data
            : payload;
        const serverList = (
          Array.isArray(inner)
            ? inner
            : ((inner as { servers?: unknown[] } | undefined)?.servers ?? [])
        ) as Record<string, unknown>[];

        const serverMap: Record<string, Record<string, unknown>> = {};
        for (const s of serverList) {
          const key = String(s.server_id ?? s.id ?? s.name ?? "unknown");
          serverMap[key] = s;
        }
        setServers(serverMap);
      }

      const catalogResp = await api.getMcpCatalog();
      if (isSuccessResponse(catalogResp)) {
        const data = catalogResp.result ?? catalogResp.data;
        interface RawTool {
          name: string;
          description?: string;
          parameters?: Record<string, unknown>;
          inputSchema?: Record<string, unknown>;
        }
        const rawTools = ((data as { tools?: RawTool[] })?.tools ?? []) as RawTool[];
        const normalizedTools: McpTool[] = rawTools.map((t: RawTool) => ({
          name: t.name,
          description: t.description || "",
          parameters: (t.parameters ?? t.inputSchema ?? {}) as Record<string, unknown>,
          server: "metaops",
        }));
        setTools(normalizedTools);
      }
    } catch (err: unknown) {
      logger.error(`Connection failure: ${err}`);
      setError("Failed to connect to MetaMCP server. Is the backend running?");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();

    const handleLog = (entry: LogEntry) => {
      const timestamp = new Date(entry.timestamp).toLocaleTimeString();
      const contextStr = entry.context ? JSON.stringify(entry.context) : "";
      const logLine = `[${timestamp}] [${entry.level}] ${entry.message} ${contextStr}`;
      setLogs((prev) => [...prev, logLine]);
    };

    logger.on("log", handleLog);

    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "/") {
        e.preventDefault();
        setShowLogger((prev) => !prev);
      }
      if (e.key === "?") {
        if (!["INPUT", "TEXTAREA"].includes((e.target as HTMLElement).tagName)) {
          setShowHelp(true);
        }
      }
    };

    const handleRunEmojiBuster = () => {
      setCurrentPage("scrubbers");
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("run-emoji-buster", handleRunEmojiBuster);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("run-emoji-buster", handleRunEmojiBuster);
      logger.off("log", handleLog);
    };
  }, [loadDashboardData]);

  const renderPage = () => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-64 text-slate-300">
          <div className="animate-spin mr-2 h-5 w-5 border-b-2 border-current rounded-full" />
          Loading system status...
        </div>
      );
    }

    if (error && !["apps", "fleet", "agent-hub"].includes(currentPage)) {
      return (
        <div className="flex flex-col items-center justify-center h-64 text-red-400">
          <p className="mb-4">{error}</p>
          <button
            type="button"
            onClick={() => loadDashboardData()}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded text-sm transition-colors"
          >
            Retry Connection
          </button>
        </div>
      );
    }

    switch (currentPage) {
      case "dashboard":
        return (
          <DashboardPage
            servers={servers}
            clients={clients}
            tools={tools}
            onNavigate={setCurrentPage}
          />
        );
      case "apps":
        return <AppsHub />;
      case "harness":
        return <HarnessPage />;
      case "fleet":
        return <FleetDashboard />;
      case "fleet-ops":
        return <FleetOps />;
      case "agent-hub":
        return <AgentHubPage />;
      case "servers":
        return <ServersPage />;
      case "clients":
        return <ClientsPage clients={clients} setClients={setClients} />;
      case "builders":
        return <BuildersPage />;
      case "tools":
        return <ToolsPage tools={tools} />;
      case "tool-lab":
        return <ToolLabPage tools={tools} />;
      case "repo-inspiration":
        return <RepoInspirationPage />;
      case "scrubbers":
        return <ScrubbersPage />;
      case "tauri-build":
        return <TauriBuildPage />;
      case "toolchains":
        return <ToolchainsPage />;
      case "analysis":
        return <AnalysisPage />;
      case "assess-reports":
        return <AssessReportsPage />;
      case "assfix-sop":
        return <AssfixSOPPage />;
      case "session-docs":
        return <SessionDocsPage />;
      case "standards":
        return <StandardsPage />;
      case "justfile":
        return <JustfilePage />;
      case "settings":
        return <SettingsPage />;
      case "logs":
        return <LogsPage />;
      case "help":
        return <HelpPage />;
      case "about":
        return <AboutPage />;
      case "chat":
        return <ChatPage onNavigateToSettings={() => setCurrentPage("settings")} />;
      case "config-audit":
        return <ConfigAuditPage />;
      default:
        return (
          <div className="flex flex-col items-center justify-center h-64 text-slate-300">
            <p>
              Work in progress. Module <strong>{currentPage}</strong> coming soon.
            </p>
          </div>
        );
    }
  };

  return (
    <ErrorBoundary>
      <Layout
        currentPage={currentPage}
        onNavigate={setCurrentPage}
        onShowLogger={() => setShowLogger(true)}
        onShowHelp={() => setShowHelp(true)}
      >
        {renderPage()}
      </Layout>

      <LoggerModal isOpen={showLogger} onClose={() => setShowLogger(false)} logs={logs} />

      <HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />
    </ErrorBoundary>
  );
}

export default App;
