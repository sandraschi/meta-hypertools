import { motion } from "framer-motion";
import { Github, Globe, Heart, Info, ShieldCheck, Zap } from "lucide-react";

export function AboutPage() {
  return (
    <div className="space-y-12 max-w-3xl mx-auto py-8">
      <div className="text-center space-y-4">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="inline-block p-4 rounded-3xl bg-blue-500/10 mb-4"
        >
          <Zap className="text-blue-500 w-12 h-12" />
        </motion.div>
        <h1 className="text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-300 to-slate-500">
          MetaMCP Registry & Orchestrator
        </h1>
        <p className="text-xl text-slate-300 font-medium">Version 1.4.0 — Professional Edition</p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <section className="p-8 rounded-3xl bg-slate-900/50 border border-slate-800 backdrop-blur-xl">
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
            <Info className="text-blue-400" />
            Platform Mission
          </h2>
          <p className="text-slate-300 leading-relaxed text-lg">
            MetaMCP is designed to bridge the gap between fragmented MCP servers and industrial
            development environments. Providing a robust, data-centric dashboard for the centralized
            management of metadata, enabling efficient server orchestration and capability discovery
            across the local fleet.
          </p>
        </section>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800">
            <ShieldCheck className="text-green-400 mb-4" size={32} />
            <h3 className="text-lg font-bold text-white mb-2">Build Standards</h3>
            <p className="text-slate-300 text-sm">
              Adheres to FastMCP 3.2.0+ standards with full support for SEP-1577 sampling and
              agentic observability tasks.
            </p>
          </div>
          <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800">
            <Globe className="text-purple-400 mb-4" size={32} />
            <h3 className="text-lg font-bold text-white mb-2">Fleet Integration</h3>
            <p className="text-slate-300 text-sm">
              Seamlessly integrates with the wider MCP ecosystem, providing a unified management
              interface for local MCP node orchestration.
            </p>
          </div>
        </div>
      </div>

      <footer className="pt-12 border-t border-slate-800 flex flex-col items-center gap-6">
        <div className="flex gap-8">
          <a
            href="https://github.com/sandraschi"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-300 hover:text-white transition-colors flex items-center gap-2"
          >
            <Github size={20} />
            <span>GitHub</span>
          </a>
          <a
            href="#!"
            className="text-slate-300 hover:text-white transition-colors flex items-center gap-2"
          >
            <Globe size={20} />
            <span>Registry</span>
          </a>
        </div>
        <div className="flex items-center gap-2 text-slate-300 text-sm">
          <span>Hand-crafted in Vienna</span>
          <Heart size={14} className="text-red-500 fill-red-500" />
          <span>2026</span>
        </div>
      </footer>
    </div>
  );
}
