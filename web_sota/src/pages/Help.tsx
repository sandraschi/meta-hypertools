import { motion } from "framer-motion";
import {
  Activity,
  BarChart3,
  BookOpen,
  Bot,
  Box,
  Cpu,
  FileSearch,
  Hammer,
  HelpCircle,
  Layers,
  MessageCircle,
  ScanSearch,
  Server,
  Shield,
  Sparkles,
  Terminal,
} from "lucide-react";
import { useState } from "react";

type Tab = {
  id: string;
  label: string;
  icon: typeof HelpCircle;
};

const TABS: Tab[] = [
  { id: "overview", label: "Overview", icon: HelpCircle },
  { id: "servers", label: "Servers & Toolchains", icon: Server },
  { id: "fleet", label: "Fleet Probes", icon: Activity },
  { id: "builders", label: "Builders", icon: Hammer },
  { id: "analyze", label: "Analyzers & Scrubbers", icon: BarChart3 },
  { id: "harness", label: "Harness", icon: Box },
  { id: "config-audit", label: "Config Audit", icon: FileSearch },
  { id: "inspire", label: "Repo Inspiration", icon: Sparkles },
  { id: "agents", label: "Agent Hub", icon: Bot },
  { id: "api", label: "API Reference", icon: Terminal },
  { id: "quickstart", label: "Quick Start", icon: BookOpen },
];

export function HelpPage() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      <header>
        <motion.h1
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-600 mb-2"
        >
          MetaMCP System Documentation
        </motion.h1>
        <p className="text-slate-300">
          Fleet orchestration hub — 80+ MCP tools for server management, fleet probes, scaffolding,
          analysis, repo inspiration, and agent coordination.
        </p>
      </header>

      {/* Horizontal tab bar */}
      <div className="flex overflow-x-auto gap-1 pb-2 border-b border-white/10 no-scrollbar">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-bold whitespace-nowrap transition-all shrink-0 ${
                active
                  ? "bg-blue-500/20 text-blue-300 border border-blue-500/30 shadow-[0_0_20px_rgba(59,130,246,0.15)]"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        {activeTab === "overview" && <OverviewTab />}
        {activeTab === "servers" && <ServersTab />}
        {activeTab === "fleet" && <FleetTab />}
        {activeTab === "builders" && <BuildersTab />}
        {activeTab === "analyze" && <AnalyzeTab />}
        {activeTab === "inspire" && <InspireTab />}
        {activeTab === "harness" && <HarnessTab />}
        {activeTab === "config-audit" && <ConfigAuditHelpTab />}
        {activeTab === "agents" && <AgentsTab />}
        {activeTab === "api" && <ApiTab />}
        {activeTab === "quickstart" && <QuickStartTab />}
      </motion.div>
    </div>
  );
}

// ── Tab Components ──

function OverviewTab() {
  return (
    <div className="space-y-6">
      <SectionCard title="What is MetaMCP?" icon={HelpCircle} color="text-blue-400">
        <p className="text-slate-300 leading-relaxed mb-4">
          MetaMCP is the fleet orchestration hub — a MCP server that manages all other MCP servers
          in the sandraschi fleet. It provides <strong className="text-white">55 MCP tools</strong>{" "}
          (15 portmanteau + 40 domain-specific) across 17 suites, and a web dashboard.
        </p>
        <p className="text-slate-300 leading-relaxed">
          Built on FastMCP 3.4 with FastAPI. All domain tools are consolidated as portmanteau tools
          with <code className="text-blue-300">operation: Literal[...]</code> discriminators. Use{" "}
          <code className="text-blue-300">help()</code> to list all tools, or browse the dashboard.
        </p>
      </SectionCard>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MetricCard label="MCP Tool Suites" value="17" color="text-blue-400" />
        <MetricCard label="Portmanteau Tools" value="15" color="text-purple-400" />
        <MetricCard label="Total Tools" value="55" color="text-cyan-400" />
        <MetricCard label="Port" value="10718" color="text-green-400" />
      </div>

      <SectionCard title="Architecture" icon={Layers} color="text-purple-400">
        <div className="space-y-3 text-slate-300 text-sm">
          <p>
            <strong className="text-white">FastMCP 3.4</strong> — All MCP tools registered via{" "}
            <code className="text-blue-300">MetaMCPRegistry</code> with 16 modular suites
            (diagnostics, analysis, discovery, scaffolding, server management, tool execution,
            client management, repo analysis, token analysis, repo packing, repo inspiration,
            toolchains, scheduler, heartbeat, meta_dev, fleet).
          </p>
          <p>
            <strong className="text-white">FastAPI REST</strong> — Serves the web dashboard, logs,
            and API endpoints at port 10718. Frontend is React/Vite served as static files or via
            Vite dev server at 10719.
          </p>
          <p>
            <strong className="text-white">Dual transport</strong> — MCP stdio for IDE clients
            (Cursor, Claude Desktop) and HTTP via <code className="text-blue-300">/mcp</code> mount
            for the webapp. Both use the same FastMCP instance.
          </p>
          <p>
            <strong className="text-white">In-memory log ring</strong> — Last 2000 log entries
            captured by <code className="text-blue-300">MemoryLogHandler</code>, queryable via{" "}
            <code className="text-blue-300">/api/logs</code>. Serves the Logs page and export
            (JSON/CSV).
          </p>
        </div>
      </SectionCard>
    </div>
  );
}

function ServersTab() {
  return (
    <div className="space-y-6">
      <SectionCard title="Server Registry" icon={Server} color="text-purple-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          Start, stop, inspect, and list MCP servers from the dashboard or via MCP tools. The{" "}
          <strong className="text-white">Servers</strong> page shows all running servers with their
          PIDs and ports.
        </p>
        <Table
          headers={["MCP Tool", "Action", "Parameters"]}
          rows={[
            ["start_mcp_server", "Start a server by path", "server_path, server_type"],
            ["stop_mcp_server", "Stop a running server", "server_id"],
            ["list_mcp_servers", "List all running servers", "none"],
            ["show_server_status", "Get detailed status", "server_id"],
          ]}
        />
      </SectionCard>

      <SectionCard title="Toolchains" icon={Layers} color="text-indigo-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          Group MCP servers into presets and apply them to IDEs in one click. Supports Cursor,
          Windsurf, Zed, Claude Desktop, Antigravity, and opencode client configs.
        </p>
        <Table
          headers={["MCP Tool", "Action"]}
          rows={[
            ["create_mcp_toolchain", "Create preset from server list"],
            ["apply_mcp_toolchain", "Apply preset to IDE client"],
            ["list_mcp_toolchains", "List saved presets"],
            ["delete_mcp_toolchain", "Delete preset"],
          ]}
        />
      </SectionCard>

      <SectionCard title="Client Management" icon={Shield} color="text-teal-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          Read, update, validate, and backup MCP configuration files for all supported IDEs. The{" "}
          <strong className="text-white">Clients</strong> page provides a visual diff editor.
        </p>
        <Table
          headers={["Tool", "Description"]}
          rows={[
            ["read_client_config", "Read any client's mcp.json config"],
            ["update_client_config", "Update with merge + backup"],
            ["add/remove_mcp_server", "Add/remove servers from client config"],
            ["validate_client_config", "Validate config structure"],
          ]}
        />
      </SectionCard>
    </div>
  );
}

function FleetTab() {
  return (
    <div className="space-y-6">
      <SectionCard title="Fleet Startup Probe" icon={Activity} color="text-yellow-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          Tests every fleet repo: parse-check <code className="text-blue-300">start.ps1</code>,
          start the app, probe the backend health endpoint, and verify the frontend Vite proxy
          responds. Outcomes: <code className="text-green-400">stack_ok</code>,{" "}
          <code className="text-yellow-400">stack_degraded</code>,
          <code className="text-red-400">start_failed</code>,{" "}
          <code className="text-red-400">pages_404</code>.
        </p>
        <Table
          headers={["Tool", "Description"]}
          rows={[
            ["fleet_startup_probe", "Run probe across all repos (background)"],
            ["fleet_startup_probe_report", "Get latest report"],
            ["launch_fleet_app", "Start a single app by ID"],
            ["stop_fleet_app", "Kill app by port"],
          ]}
        />
      </SectionCard>

      <SectionCard title="Cold-Install Probe (Phase 2b)" icon={Box} color="text-orange-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          Checks whether a fresh install would succeed: reads INSTALL.md, checks dependencies,
          optionally runs mcpb smoke tests (Claude Desktop) and sandbox installs (via
          virtualization-mcp).
        </p>
        <Table
          headers={["Tool", "Description"]}
          rows={[
            ["fleet_cold_install_probe", "Run cold-install preflight + optional execute"],
            ["fleet_cold_install_probe_report", "Get latest report"],
          ]}
        />
      </SectionCard>

      <SectionCard title="Fleet Runtime" icon={Cpu} color="text-green-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          Monitor fleet health, ping all servers, and audit port usage across the 10700-11500 range.
          The <strong className="text-white">Fleet Status</strong> dashboard shows live server
          status.
        </p>
        <Table
          headers={["Tool", "Description"]}
          rows={[
            ["fleet_ops", "Audit, ping, probe (portmanteau)"],
            ["heartbeat_ops", "Pulse, liveness, proactive (portmanteau)"],
            ["meta_dev_ops", "Probe, diff, audit (portmanteau)"],
          ]}
        />
      </SectionCard>
    </div>
  );
}

function BuildersTab() {
  return (
    <div className="space-y-6">
      <SectionCard title="Spec Kit (SDD Scaffolding)" icon={Hammer} color="text-cyan-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          The <strong className="text-white">Spec Kit builder</strong> integrates GitHub's
          open-source Spec-Driven Development toolkit (
          <a
            href="https://github.com/github/spec-kit"
            className="text-cyan-400 underline"
            target="_blank"
            rel="noreferrer"
          >
            github/spec-kit
          </a>
          , MIT). It runs
          <code className="text-cyan-400 bg-slate-800 px-1 rounded mx-1">specify init</code>
          with structured SDD phases:
        </p>
        <ol className="list-decimal list-inside text-slate-300 space-y-1 text-sm mb-4">
          <li>
            <strong className="text-white">constitution</strong> — project principles &amp;
            governance
          </li>
          <li>
            <strong className="text-white">specify</strong> — functional requirements (what, not
            how)
          </li>
          <li>
            <strong className="text-white">clarify</strong> — structured Q&amp;A for underspecified
            areas
          </li>
          <li>
            <strong className="text-white">plan</strong> — tech stack, data model, API contracts
          </li>
          <li>
            <strong className="text-white">tasks</strong> — dependency-ordered implementation tasks
          </li>
          <li>
            <strong className="text-white">implement</strong> — execute all tasks in order
          </li>
        </ol>
        <p className="text-slate-300 text-sm mb-3">
          Available AI integrations: <strong className="text-white">OpenCode</strong> (fleet
          default), Claude Code, GitHub Copilot, Cursor, Gemini CLI. Installs{" "}
          <code className="text-cyan-400">/speckit.*</code> slash commands into the agent's config
          directory.
        </p>
        <p className="text-slate-300 text-sm">
          Specs persist as Markdown in the <code className="text-cyan-400">specs/</code> directory —
          surviving agent context resets, IDE switches, and team changes. Learn more:{" "}
          <a
            href="https://github.github.io/spec-kit/"
            className="text-cyan-400 underline"
            target="_blank"
            rel="noreferrer"
          >
            spec-kit docs
          </a>{" "}
          |{" "}
          <a
            href="https://github.com/github/spec-kit"
            className="text-cyan-400 underline"
            target="_blank"
            rel="noreferrer"
          >
            GitHub repo
          </a>
        </p>
        <Table
          headers={["Tool", "What it creates"]}
          rows={[["scaffold_ops(operation='spec_kit')", "SDD scaffold with /speckit.* workflow"]]}
        />
      </SectionCard>

      <SectionCard title="MCP Server Scaffold" icon={Hammer} color="text-cyan-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          The <strong className="text-white">scaffold_ops</strong> portmanteau tool creates a
          complete SOTA 2026-compliant MCP server in seconds. Generates 40 files including:
        </p>
        <ul className="list-disc list-inside text-slate-300 space-y-1 text-sm mb-4">
          <li>FastMCP 3.4+ dual transport (stdio + HTTP)</li>
          <li>Multi-provider LLM config (Ollama, LM Studio, OpenAI, Anthropic, Google)</li>
          <li>Unified LLM client + MCP chat tool + REST API endpoints</li>
          <li>Prefab UI cards, agentic workflow (SEP-1577), CodeMode</li>
          <li>justfile, llms.txt, glama.json, .env.example, run_server.py</li>
          <li>Windows CI, tests, PyInstaller entry point</li>
        </ul>
        <p className="text-slate-300 text-sm">
          Dashboard <strong className="text-white">Builders</strong> page provides a wizard
          interface.
        </p>
        <Table
          headers={["Tool", "What it creates"]}
          rows={[["scaffold_ops", "Multi-op scaffold (portmanteau)"]]}
        />
      </SectionCard>
    </div>
  );
}

function AnalyzeTab() {
  return (
    <div className="space-y-6">
      <SectionCard title="Fleet Analysis" icon={BarChart3} color="text-violet-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          Full-spectrum fleet health analysis: classify repos by SOTA compliance, detect runts,
          export to mcp-central-docs. The <strong className="text-white">Analysis</strong> page adds
          LLM-assisted review of findings.
        </p>
        <Table
          headers={["Tool", "Description"]}
          rows={[
            ["analyze_mcp_runts", "Scan for outdated repos needing modernization"],
            ["show_mcp_status", "Detailed SOTA compliance for one repo"],
            ["analyze_fleet", "Multi-dimensional fleet analysis"],
            ["publish_analysis_to_mcd", "Export to central docs"],
          ]}
        />
      </SectionCard>

      <SectionCard title="Scrubbers" icon={ScanSearch} color="text-amber-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          Code quality and safety utilities that run across fleet repos.
        </p>
        <Table
          headers={["Tool", "Description"]}
          rows={[
            ["scan_mcp_unicode", "EmojiBuster — remove crash-causing Unicode"],
            ["validate_mcp_pwsh", "Catch Linux aliases in PowerShell scripts"],
            ["validate_mcp_justfile", "Check justfile fleet standard compliance"],
            ["audit_mcp_implementation", "Flag stub/mock patterns"],
            ["audit_secret_redaction", "Redact secrets before sharing"],
          ]}
        />
      </SectionCard>

      <SectionCard title="Token & Code Analysis" icon={Terminal} color="text-green-400">
        <Table
          headers={["Tool", "Description"]}
          rows={[
            ["analyze_file_tokens", "Count tokens in a file"],
            ["analyze_dir_tokens", "Audit token usage across a directory"],
            ["check_context_limits", "Check token count vs LLM context windows"],
            ["audit_mcp_surface", "Count FastMCP decorators in a repo"],
            ["find_orphan_tools", "Find unused tool functions"],
          ]}
        />
      </SectionCard>
    </div>
  );
}

function InspireTab() {
  return (
    <div className="space-y-6">
      <SectionCard title="Repo Inspiration" icon={Sparkles} color="text-pink-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          Study any public GitHub repository without cloning. Uses the GitHub API to fetch file
          trees, read source files, build architecture study packs, and run multi-step agentic
          workflows.
        </p>
        <Table
          headers={["Tool", "Description"]}
          rows={[
            ["inspire_repo", "Portmanteau: structure, files, patterns, help"],
            ["inspire_repo_structure", "Filtered file tree (no noise)"],
            ["inspire_repo_files", "Read source files (capped for token safety)"],
            ["inspire_repo_patterns", "Architecture study pack with analysis prompt"],
            [
              "inspire_repo_workflow",
              "Agentic multi-step: structure → files → patterns → synthesis",
            ],
            ["inspire_repo_structure_card", "Prefab card for quick browsing"],
          ]}
        />
        <p className="text-slate-300 text-sm mt-3">
          Uses Gitingest for efficient tree fetching. Set{" "}
          <code className="text-blue-300">GITHUB_TOKEN</code> for higher rate limits. The{" "}
          <strong className="text-white">Repo Inspiration</strong> dashboard page provides a UI for
          browsing.
        </p>
      </SectionCard>

      <SectionCard title="Repository Packing" icon={Box} color="text-orange-400">
        <Table
          headers={["Tool", "Description"]}
          rows={[
            ["pack_mcp_repository", "Pack repo into XML/JSON for AI context"],
            ["pack_repo_ai_optimized", "Auto-select files to fit token limit"],
          ]}
        />
      </SectionCard>
    </div>
  );
}

function HarnessTab() {
  return (
    <div className="space-y-6">
      <SectionCard title="Harness Generation" icon={Box} color="text-cyan-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          Auto-generate FastMCP 3.4+ servers from existing Python source code. AST-based analysis
          extracts function signatures, groups them by domain, and creates portmanteau tools with
          SOTA-compliant docstrings.
        </p>
        <Table
          headers={["Tool", "Description"]}
          rows={[
            [
              "harness_analyze",
              "AST source analysis -> ToolSurfaceSpec (function signatures, domain groups, backend detection)",
            ],
            [
              "harness_generate",
              "Spec -> complete FastMCP server (portmanteau tools, Prefab cards, SKILL.md, dual transport)",
            ],
            [
              "harness_refine",
              "Gap analysis: diff generated server vs source, non-destructive incremental tool addition",
            ],
          ]}
        />
      </SectionCard>
      <SectionCard title="Workflow" icon={Layers} color="text-cyan-400">
        <ol className="list-decimal list-inside text-slate-300 space-y-2 text-sm">
          <li>
            <strong className="text-white">Analyze</strong> — point harness_analyze at a Python
            codebase (local path or GitHub URL)
          </li>
          <li>
            <strong className="text-white">Preview</strong> — inspect the ToolSurfaceSpec: tool
            groups, operations, backend strategy
          </li>
          <li>
            <strong className="text-white">Generate</strong> — harness_generate produces 23 files:
            portmanteau tools, prefabs, SKILL.md, tests
          </li>
          <li>
            <strong className="text-white">Refine</strong> — harness_refine detects gaps between
            generated server and updated source
          </li>
        </ol>
      </SectionCard>
    </div>
  );
}

function ConfigAuditHelpTab() {
  return (
    <div className="space-y-6">
      <SectionCard title="Fleet Config Audit" icon={FileSearch} color="text-amber-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          Scans all fleet repos for agent behavioral files, discovery documents, and metadata —
          answering what exists, where, what's stale, and what's missing.
        </p>
        <Table
          headers={["Config file", "Category", "Purpose"]}
          rows={[
            ["CLAUDE.md", "Agent behavior", "Claude Code / opencode per-repo instructions"],
            ["AGENTS.md", "Agent behavior", "Fleet agent instruction file"],
            [".cursorrules", "Agent behavior", "Cursor IDE rules (repo root)"],
            ["llms.txt", "Discovery", "Required LLM discovery index"],
            ["llms-full.txt", "Discovery", "Required full documentation for LLMs"],
            ["glama.json", "Discovery", "Glama registry manifest"],
            [".env.example", "Metadata", "Environment variable template"],
            ["CHANGELOG.md", "Metadata", "Release history"],
          ]}
        />
      </SectionCard>
      <SectionCard title="Priority Chain" icon={Layers} color="text-amber-400">
        <p className="text-slate-300 text-sm mb-3">
          Override order for behavioral files (highest to lowest):
        </p>
        <ol className="list-decimal list-inside text-slate-300 space-y-1 text-sm">
          <li>Session prompt (inline instructions)</li>
          <li>&lt;repo&gt;/CLAUDE.md (per-repo)</li>
          <li>&lt;repo&gt;/.cursorrules (per-IDE)</li>
          <li>&lt;repo&gt;/AGENTS.md (per-repo)</li>
          <li>~/.claude/CLAUDE.md (global fallback)</li>
        </ol>
      </SectionCard>
    </div>
  );
}

function AgentsTab() {
  return (
    <div className="space-y-6">
      <SectionCard title="Fritz (fleet-agent-mcp)" icon={Bot} color="text-fuchsia-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          Fritz is the fleet conductor agent at <code className="text-blue-300">:10996</code>. The
          <strong className="text-white"> Agent Hub</strong> page proxies its coworker flows:
        </p>
        <ul className="list-disc list-inside text-slate-300 space-y-1 text-sm mb-3">
          <li>
            <strong className="text-white">fleet_pulse</strong> — Daily fleet health report
          </li>
          <li>
            <strong className="text-white">inbox_briefing</strong> — GitHub inbox summary
          </li>
          <li>
            <strong className="text-white">cursor_spend_watch</strong> — Cursor token usage
            guardrails
          </li>
          <li>
            <strong className="text-white">pdf_pack</strong> — Digest generation
          </li>
        </ul>
        <Table
          headers={["Tool", "Description"]}
          rows={[
            ["agent_hub/fritz", "Fritz overview: status, tasks, coworker flows"],
            ["agent_hub/fritz/coworker", "Run a coworker flow now"],
          ]}
        />
      </SectionCard>

      <SectionCard title="RoboFang" icon={Bot} color="text-fuchsia-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          RoboFang at <code className="text-blue-300">:10870</code> provides physical robot
          routines. The Agent Hub page shows hands (hardware status) and routines.
        </p>
        <Table
          headers={["Tool", "Description"]}
          rows={[
            ["agent_hub/robofang", "RoboFang overview: health, hands, routines"],
            ["agent_hub/robofang/routine/run", "Run a routine now"],
          ]}
        />
      </SectionCard>

      <SectionCard title="LLM Provider Bridge" icon={MessageCircle} color="text-teal-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          The dashboard proxies LLM model discovery and chat through the backend (avoids CORS
          issues). Detects Ollama and LM Studio on localhost automatically.
        </p>
        <Table
          headers={["Endpoint", "Description"]}
          rows={[
            ["/api/llm/providers", "Auto-detect local LLM providers + models"],
            ["POST /api/v1/llm/models", "List models from a provider"],
            ["POST /api/v1/llm/chat", "Chat with LLM (proxied)"],
          ]}
        />
      </SectionCard>
    </div>
  );
}

function ApiTab() {
  return (
    <div className="space-y-6">
      <SectionCard title="REST API Endpoints" icon={Terminal} color="text-green-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          All endpoints are served at <code className="text-blue-300">http://127.0.0.1:10718</code>.
          The Vite dev server proxies <code className="text-blue-300">/api</code> and{" "}
          <code className="text-blue-300">/mcp</code> to the backend.
        </p>

        <h4 className="text-white font-semibold mt-6 mb-2">Health & Diagnostics</h4>
        <Table
          headers={["Method", "Path", "Description"]}
          rows={[
            ["GET", "/health", "Basic health check"],
            ["GET", "/api/v1/health/detailed", "Per-service health status"],
            ["GET", "/api/logs", "Query log entries (paginated, filterable)"],
            ["GET", "/api/logs/stats", "Log statistics by level/kind"],
            ["DELETE", "/api/logs", "Clear all log entries"],
            ["GET", "/api/logs/export", "Export logs as JSON or CSV"],
          ]}
        />

        <h4 className="text-white font-semibold mt-6 mb-2">Tools & Execution</h4>
        <Table
          headers={["Method", "Path", "Description"]}
          rows={[
            ["GET", "/api/v1/tools/list", "Static tool catalog"],
            ["GET", "/api/v1/mcp/catalog", "Live tool catalog with JSON Schema"],
            ["POST", "/api/v1/tools/execute", "Execute a tool (local MetaMCP)"],
            ["POST", "/api/v1/tools/validate", "Validate tool parameters"],
            ["GET", "/api/v1/tools/history", "Tool execution history"],
            ["GET", "/api/v1/servers/{id}/tools", "List tools on a server"],
          ]}
        />

        <h4 className="text-white font-semibold mt-6 mb-2">Server Management</h4>
        <Table
          headers={["Method", "Path", "Description"]}
          rows={[
            ["POST", "/api/v1/servers/start", "Start an MCP server"],
            ["POST", "/api/v1/servers/stop", "Stop an MCP server"],
            ["GET", "/api/v1/servers/list", "List running servers"],
            ["GET", "/api/v1/servers/{id}/status", "Server status"],
            ["POST", "/api/v1/servers/inspect", "Inspect server config"],
          ]}
        />

        <h4 className="text-white font-semibold mt-6 mb-2">Fleet & Probes</h4>
        <Table
          headers={["Method", "Path", "Description"]}
          rows={[
            ["GET", "/api/v1/fleet/runtime", "Audit fleet runtime"],
            ["POST", "/api/v1/fleet/start", "Start a fleet app"],
            ["POST", "/api/v1/fleet/stop", "Stop a fleet app"],
            ["POST", "/api/v1/fleet/startup-probe/run", "Run fleet startup probe"],
            ["POST", "/api/v1/fleet/cold-install/run", "Run cold-install probe"],
          ]}
        />

        <h4 className="text-white font-semibold mt-6 mb-2">Clients & Toolchains</h4>
        <Table
          headers={["Method", "Path", "Description"]}
          rows={[
            ["GET", "/api/v1/clients/{name}/config", "Read client config"],
            ["POST", "/api/v1/clients/{name}/config", "Update client config"],
            ["POST", "/api/v1/clients/{name}/servers", "Add server to client"],
            ["DELETE", "/api/v1/clients/{name}/servers/{server}", "Remove server"],
            ["GET", "/api/v1/clients/configs", "List all clients"],
            ["GET", "/api/v1/toolchains/list", "List toolchain presets"],
            ["POST", "/api/v1/toolchains/create", "Create toolchain"],
            ["POST", "/api/v1/toolchains/apply", "Apply toolchain to client"],
          ]}
        />

        <h4 className="text-white font-semibold mt-6 mb-2">LLM Bridge</h4>
        <Table
          headers={["Method", "Path", "Description"]}
          rows={[
            ["GET", "/api/llm/providers", "Auto-detect local LLM providers"],
            ["POST", "/api/v1/llm/models", "List models from provider"],
            ["POST", "/api/v1/llm/chat", "Chat with LLM"],
          ]}
        />

        <h4 className="text-white font-semibold mt-6 mb-2">Agent Hub</h4>
        <Table
          headers={["Method", "Path", "Description"]}
          rows={[
            ["GET", "/api/v1/agent-hub/fritz", "Fritz overview"],
            ["POST", "/api/v1/agent-hub/fritz/coworker", "Run coworker flow"],
            ["GET", "/api/v1/agent-hub/robofang", "RoboFang overview"],
            ["POST", "/api/v1/agent-hub/robofang/routine/run", "Run routine"],
          ]}
        />

        <h4 className="text-white font-semibold mt-6 mb-2">Scaffolding & Analysis</h4>
        <Table
          headers={["Method", "Path", "Description"]}
          rows={[
            ["POST", "/api/v1/scaffolding/create", "Create project scaffold"],
            ["POST", "/api/v1/diagnostics/emojibuster", "Unicode safety scan"],
            ["POST", "/api/v1/diagnostics/powershell", "PowerShell validator"],
            ["POST", "/api/v1/analysis/runt-analyzer", "Runt analysis"],
            ["POST", "/api/v1/repos/scan", "Deep repo scan"],
            ["POST", "/api/v1/repos/pack", "Pack repo for AI"],
            ["GET", "/api/v1/analysis/fleet", "Fleet-wide analysis"],
          ]}
        />

        <h4 className="text-white font-semibold mt-6 mb-2">Scheduler & Heartbeat</h4>
        <Table
          headers={["Method", "Path", "Description"]}
          rows={[
            ["GET", "/api/v1/scheduler/tasks", "List scheduled tasks"],
            ["POST", "/api/v1/scheduler/tasks", "Register task"],
            ["DELETE", "/api/v1/scheduler/tasks/{id}", "Cancel task"],
            ["GET", "/api/v1/heartbeat/pulse", "System pulse"],
            ["GET", "/api/v1/heartbeat/ping", "Ping fleet"],
          ]}
        />
      </SectionCard>

      <SectionCard title="Logs API Format" icon={Terminal} color="text-cyan-400">
        <p className="text-slate-300 leading-relaxed mb-3">
          The <code className="text-blue-300">/api/logs</code> endpoint supports filtering,
          pagination, and live tailing.
        </p>
        <Table
          headers={["Parameter", "Type", "Description"]}
          rows={[
            ["limit", "int (1-500)", "Page size (default 50)"],
            ["offset", "int", "Page offset (default 0)"],
            ["level", "DEBUG|INFO|WARNING|ERROR", "Minimum log level filter"],
            ["kind", "string", "Filter by kind (e.g. tool_call)"],
            ["search", "string", "Substring match on detail field"],
            ["sort", "asc|desc", "Sort order (default desc)"],
            ["after_id", "string", "Tail: only entries newer than this ID"],
          ]}
        />
      </SectionCard>
    </div>
  );
}

function QuickStartTab() {
  return (
    <div className="space-y-6">
      <SectionCard title="Quick Start" icon={BookOpen} color="text-blue-400">
        <div className="space-y-4 text-slate-300 text-sm">
          <div>
            <h4 className="text-white font-semibold mb-1">1. Start the Backend</h4>
            <pre className="bg-black/40 p-3 rounded-xl border border-white/10 text-green-300 text-xs">
              {`cd D:\\Dev\\repos\\meta_mcp
uv run python -m meta_mcp.main  # HTTP on :10718`}
            </pre>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-1">2. Start the Frontend (Vite dev)</h4>
            <pre className="bg-black/40 p-3 rounded-xl border border-white/10 text-green-300 text-xs">
              {`cd D:\\Dev\\repos\\meta_mcp\\web_sota
npm run dev  # Vite dev server on :10719`}
            </pre>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-1">3. Build the Frontend</h4>
            <pre className="bg-black/40 p-3 rounded-xl border border-white/10 text-green-300 text-xs">
              {`cd D:\\Dev\\repos\\meta_mcp\\web_sota
npm run build  # Output to web_sota/dist`}
            </pre>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-1">4. Try the MCP server</h4>
            <pre className="bg-black/40 p-3 rounded-xl border border-white/10 text-green-300 text-xs">
              {`uv run python -m meta_mcp  # stdio for Claude Desktop / Cursor
uv run meta-mcp-server     # alias`}
            </pre>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Key Environment Variables" icon={Shield} color="text-purple-400">
        <Table
          headers={["Variable", "Default", "Purpose"]}
          rows={[
            ["META_TAURI", "0", "Set to 1 for Tauri CORS origins"],
            ["MCP_BRIDGE_URLS", "", "Comma-separated MCP HTTP URLs to proxy"],
            ["MCP_CENTRAL_DOCS_ROOT", "", "Path to mcp-central-docs checkout"],
            ["FRITZ_HTTP_BASE", "", "fleet-agent-mcp HTTP base URL"],
            ["ROBOFANG_HTTP_BASE", "", "RoboFang HTTP base URL"],
            ["GITHUB_TOKEN", "", "GitHub API token (rate limits)"],
            ["PORT", "10718", "FastAPI port"],
            ["HOST", "127.0.0.1", "FastAPI bind address"],
          ]}
        />
      </SectionCard>
    </div>
  );
}

// ── Shared Components ──

function SectionCard({
  title,
  icon: Icon,
  color,
  children,
}: { title: string; icon: typeof HelpCircle; color: string; children: React.ReactNode }) {
  return (
    <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all">
      <div className="flex items-center gap-3 mb-4">
        <div className={`p-2 rounded-xl bg-slate-800 ${color}`}>
          <Icon size={20} />
        </div>
        <h3 className="text-lg font-bold text-white">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function MetricCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
      <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-black ${color}`}>{value}</p>
    </div>
  );
}

function Table({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-white/5">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-white/5">
            {headers.map((h) => (
              <th
                key={h}
                className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-400"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-white/[0.02] transition-colors">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2.5 text-slate-300 font-mono text-xs">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
