import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  Brain,
  CheckCircle,
  Gamepad2,
  Globe,
  Layout,
  Loader2,
  type LucideIcon,
  Rocket,
  Server,
  ShoppingBag,
  Terminal,
  X,
} from "lucide-react";
import { useState } from "react";
import { api, getErrorMessage, isSuccessResponse } from "../api/client";
import { logger } from "../utils/logger";

const AI_INTEGRATIONS = [
  { id: "opencode", name: "OpenCode", desc: "Provider-agnostic agent CLI" },
  { id: "claude", name: "Claude Code", desc: "Anthropic's agent CLI" },
  { id: "copilot", name: "GitHub Copilot", desc: "GitHub's AI assistant" },
  { id: "cursor", name: "Cursor", desc: "AI-first IDE" },
  { id: "gemini", name: "Gemini CLI", desc: "Google's Gemini CLI" },
];

interface BuilderCardProps {
  title: string;
  description: string;
  icon: LucideIcon;
  color: string;
  outputs?: string;
  onClick: () => void;
}

function BuilderCard({
  title,
  description,
  icon: Icon,
  color,
  outputs,
  onClick,
}: BuilderCardProps) {
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 cursor-pointer hover:border-slate-700 hover:bg-slate-900 transition-all group relative overflow-hidden flex flex-col"
      onClick={onClick}
    >
      <div
        className={`absolute top-0 right-0 w-24 h-24 bg-${color}-500/10 rounded-bl-full -mr-4 -mt-4 transition-all group-hover:bg-${color}-500/20`}
      />

      <div
        className={`w-12 h-12 rounded-lg bg-${color}-500/10 flex items-center justify-center mb-4 text-${color}-400 group-hover:text-${color}-300 transition-colors`}
      >
        <Icon size={24} />
      </div>

      <h3 className="text-lg font-semibold text-slate-200 mb-2 group-hover:text-white">{title}</h3>
      <p className="text-sm text-slate-400 leading-relaxed flex-1">{description}</p>
      {outputs && (
        <div className="mt-3 flex items-center gap-1.5">
          <span className="text-[10px] font-mono text-slate-600 bg-slate-800 px-2 py-0.5 rounded">
            {outputs}
          </span>
        </div>
      )}
    </motion.div>
  );
}

interface BuildModalProps {
  isOpen: boolean;
  onClose: () => void;
  builderType: string;
  builderName: string;
}

function BuildModal({ isOpen, onClose, builderType, builderName }: BuildModalProps) {
  const [projectName, setProjectName] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName || !outputPath) return;

    setIsSubmitting(true);
    setStatus("idle");
    setMessage("");

    try {
      const response = await api.createProject({
        template_type: builderType,
        project_name: projectName,
        output_path: outputPath,
      });

      if (isSuccessResponse(response)) {
        setStatus("success");
        setMessage(`Successfully created ${builderName} project!`);
        logger.info(`Created project: ${projectName} (${builderType}) at ${outputPath}`);
        setTimeout(() => {
          onClose();
          setStatus("idle");
          setProjectName("");
          setOutputPath("");
          setMessage("");
        }, 2000);
      } else {
        setStatus("error");
        setMessage(getErrorMessage(response));
        logger.error(`Failed to create project: ${getErrorMessage(response)}`);
      }
    } catch (err) {
      setStatus("error");
      setMessage("An unexpected error occurred.");
      logger.error(`Error creating project: ${err}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden"
        >
          <div className="flex items-center justify-between p-6 border-b border-slate-800">
            <h3 className="text-xl font-semibold text-slate-200">Build {builderName}</h3>
            <button
              type="button"
              onClick={onClose}
              className="text-slate-300 hover:text-white transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <div className="space-y-2">
              <label htmlFor="project-name" className="text-sm font-medium text-slate-300">
                Project Name
              </label>
              <input
                id="project-name"
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="my-awesome-project"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all placeholder:text-slate-600"
                required
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="output-path" className="text-sm font-medium text-slate-300">
                Output Path
              </label>
              <input
                id="output-path"
                type="text"
                value={outputPath}
                onChange={(e) => setOutputPath(e.target.value)}
                placeholder="/path/to/repos"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all placeholder:text-slate-600"
                required
              />
              <p className="text-xs text-slate-300">
                The project folder will be created inside this directory.
              </p>
            </div>

            {status === "error" && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex items-center gap-2">
                <AlertTriangle size={16} />
                {message}
              </div>
            )}

            {status === "success" && (
              <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400 text-sm flex items-center gap-2">
                <CheckCircle size={16} />
                {message}
              </div>
            )}

            <div className="pt-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || status === "success"}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    Building...
                  </>
                ) : status === "success" ? (
                  "Built!"
                ) : (
                  "Create Project"
                )}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

interface SpecKitModalProps {
  isOpen: boolean;
  onClose: () => void;
}

function SpecKitModal({ isOpen, onClose }: SpecKitModalProps) {
  const [projectName, setProjectName] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [integration, setIntegration] = useState("opencode");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName || !outputPath) return;

    setIsSubmitting(true);
    setStatus("idle");
    setMessage("");

    try {
      const response = await api.createProject({
        template_type: "spec_kit",
        project_name: projectName,
        output_path: outputPath,
        features: { ai_integration: integration },
      });

      if (isSuccessResponse(response)) {
        setStatus("success");
        setMessage(
          `Spec Kit project "${projectName}" scaffolded with ${AI_INTEGRATIONS.find((i) => i.id === integration)?.name}!`,
        );
        logger.info(
          `Spec Kit: created ${projectName} (integration: ${integration}) at ${outputPath}`,
        );
        setTimeout(() => {
          onClose();
          setStatus("idle");
          setProjectName("");
          setOutputPath("");
          setMessage("");
        }, 2500);
      } else {
        setStatus("error");
        setMessage(getErrorMessage(response));
        logger.error(`Spec Kit: failed to create project: ${getErrorMessage(response)}`);
      }
    } catch (err) {
      setStatus("error");
      setMessage("An unexpected error occurred.");
      logger.error(`Spec Kit: error creating project: ${err}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden"
        >
          <div className="flex items-center justify-between p-6 border-b border-slate-800">
            <div>
              <h3 className="text-xl font-semibold text-slate-200">Spec Kit Scaffold</h3>
              <p className="text-xs text-slate-300 mt-1">
                Runs <code className="text-cyan-400 bg-slate-800 px-1 rounded">specify init</code>{" "}
                with structured SDD workflow
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="text-slate-300 hover:text-white transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <div className="space-y-2">
              <label htmlFor="spec-project-name" className="text-sm font-medium text-slate-300">
                Project Name
              </label>
              <input
                id="spec-project-name"
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="my-new-server"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all placeholder:text-slate-600"
                required
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="spec-output-path" className="text-sm font-medium text-slate-300">
                Output Path
              </label>
              <input
                id="spec-output-path"
                type="text"
                value={outputPath}
                onChange={(e) => setOutputPath(e.target.value)}
                placeholder="D:\\Dev\\repos"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all placeholder:text-slate-600"
                required
              />
              <p className="text-xs text-slate-300">
                Directory where the project folder will be created.
              </p>
            </div>

            <div className="space-y-2">
              <label htmlFor="spec-ai" className="text-sm font-medium text-slate-300">
                AI Coding Agent
              </label>
              <select
                id="spec-ai"
                value={integration}
                onChange={(e) => setIntegration(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
              >
                {AI_INTEGRATIONS.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.name} — {opt.desc}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-300">
                Installs <code className="text-cyan-400">/speckit.*</code> slash commands for the
                selected agent.
              </p>
            </div>

            <div className="p-3 bg-cyan-500/10 border border-cyan-500/20 rounded-lg text-sm text-cyan-300">
              <strong>Spec-Driven Development phases:</strong> constitution → specify → clarify →
              plan → tasks → implement. Specs persist as Markdown in{" "}
              <code className="text-cyan-400">specs/</code> directory.
            </div>

            {status === "error" && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex items-center gap-2">
                <AlertTriangle size={16} />
                {message}
              </div>
            )}

            {status === "success" && (
              <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400 text-sm flex items-center gap-2">
                <CheckCircle size={16} />
                {message}
              </div>
            )}

            <div className="pt-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || status === "success"}
                className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    Scaffolding...
                  </>
                ) : status === "success" ? (
                  "Done!"
                ) : (
                  "Run specify init"
                )}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

export function BuildersPage() {
  const [selectedBuilder, setSelectedBuilder] = useState<{ type: string; name: string } | null>(
    null,
  );
  const [showSpecKit, setShowSpecKit] = useState(false);

  const builders = [
    {
      type: "spec_kit",
      name: "Spec Kit (SDD)",
      description:
        "Spec-Driven Development scaffold: constitution → specs → plan → tasks → implement. Installs /speckit.* slash commands for your AI agent.",
      icon: Rocket,
      color: "cyan",
      isSpecKit: true,
      outputs: "specs/ dir, config files",
    },
    {
      type: "mcp_server",
      name: "MCP Server",
      description:
        "SOTA FastMCP 3.4+ server with dual transport, Prefab cards, skills, prompts, health API, MCPB packaging, CI/CD, and optional Tauri/NSIS desktop wrapper.",
      icon: Server,
      color: "blue",
      outputs: "Full repo with src/, tests/, CI, docs",
    },
    {
      type: "tiiny_site",
      name: "Tiiny.host Static Page",
      description:
        "Scaffold a single-page HTML site with dark theme and optional deployment to tiiny.host free tier. Gets a {name}.tiiny.host URL in seconds.",
      icon: Globe,
      color: "sky",
      outputs: "index.html, styles.css",
    },
    {
      type: "landing_page",
      name: "Landing Page",
      description:
        "Premium dark-theme marketing site with 5 pages (hero, how it works, download, donate, bio), particle canvas, glassmorphism, and CSS noise texture.",
      icon: Layout,
      color: "purple",
      outputs: "5 HTML pages + CSS + JS",
    },
    {
      type: "fullstack",
      name: "Fullstack App",
      description:
        "React + FastAPI app with optional AI, MCP, PWA, and monitoring. Runs via a PowerShell build script.",
      icon: Terminal,
      color: "indigo",
      outputs: "React frontend + FastAPI backend",
    },
    {
      type: "webshop",
      name: "Webshop",
      description:
        "E-commerce storefront with product catalog and cart. Based on the Medusa template.",
      icon: ShoppingBag,
      color: "emerald",
      outputs: "Full e-commerce app",
    },
    {
      type: "game",
      name: "Browser Game",
      description:
        "Retro browser game from a template: asteroids, blackjack, chess, pacman, tetris, breakout, or pong.",
      icon: Gamepad2,
      color: "rose",
      outputs: "index.html + JS game",
    },
    {
      type: "wisdom_tree",
      name: "Wisdom Tree",
      description:
        "Interactive knowledge graph visualization for exploring complex topic relationships. Uses a technical-roadmap or custom template.",
      icon: Brain,
      color: "amber",
      outputs: "Interactive graph UI",
    },
  ];

  return (
    <div className="h-full flex flex-col p-8 overflow-y-auto">
      <div className="mb-10">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400 mb-3">
          Project Builders
        </h1>
        <p className="text-slate-300 text-lg max-w-2xl">
          Rapidly scaffold new projects using our specialized templates. Select a builder below to
          get started.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {builders.map((builder) => (
          <BuilderCard
            key={builder.type}
            title={builder.name}
            description={builder.description}
            icon={builder.icon}
            color={builder.color}
            outputs={
              "outputs" in builder ? (builder as unknown as { outputs: string }).outputs : undefined
            }
            onClick={() =>
              "isSpecKit" in builder && builder.isSpecKit
                ? setShowSpecKit(true)
                : setSelectedBuilder({ type: builder.type, name: builder.name })
            }
          />
        ))}
      </div>

      <SpecKitModal isOpen={showSpecKit} onClose={() => setShowSpecKit(false)} />

      {selectedBuilder && (
        <BuildModal
          isOpen={!!selectedBuilder}
          onClose={() => setSelectedBuilder(null)}
          builderType={selectedBuilder.type}
          builderName={selectedBuilder.name}
        />
      )}
    </div>
  );
}
