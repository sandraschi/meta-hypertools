import { Search, Terminal } from "lucide-react";
import { useState } from "react";
import { ToolExecutionModal } from "../components/modals/ToolExecutionModal";
import { ToolInfo, type ToolInfoData } from "../components/modules/ToolInfo";

// Define the extended type that includes 'server'
export interface ToolWithServer extends ToolInfoData {
  server: string;
}

interface ToolsPageProps {
  tools: ToolWithServer[];
}

export function ToolsPage({ tools }: ToolsPageProps) {
  const [search, setSearch] = useState("");
  const [selectedTool, setSelectedTool] = useState<ToolWithServer | null>(null);

  const filteredTools = tools.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description.toLowerCase().includes(search.toLowerCase()) ||
      t.server?.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-8 h-full flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Hero Section */}
      <div className="glass-panel p-10 relative overflow-hidden bg-white/[0.01] border-white/5 flex items-center justify-between">
        <div className="absolute top-0 right-0 p-8 opacity-20 pointer-events-none">
          <Terminal size={120} className="text-purple-400 animate-pulse" />
        </div>
        <div>
          <h1 className="text-3xl font-black mb-2 bg-gradient-to-r from-white via-white to-white/40 bg-clip-text text-transparent">
            Global Capabilities Registry
          </h1>
          <p className="text-[#94a3b8] max-w-xl">
            Browse, inspect, and manually invoke tools exposed by your connected MCP grid. Execute
            raw JSON-RPC bindings directly against target nodes.
          </p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="glass-panel p-6 bg-white/[0.02] border-white/5 flex items-center gap-4 sticky top-6 z-30 shadow-2xl backdrop-blur-xl">
        <Search size={24} className="text-purple-400" />
        <input
          type="text"
          placeholder="Query capabilities by name, description, or hosting server node..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-transparent border-none focus:ring-0 text-white w-full placeholder:text-[#94a3b8] outline-none font-medium text-lg"
        />
        <div className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-widest bg-black/20 px-3 py-1.5 rounded-lg border border-white/5 whitespace-nowrap">
          {filteredTools.length} / {tools.length} discovered
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 pb-12">
        {filteredTools.map((tool, idx) => (
          <div
            key={`${tool.server}-${tool.name}`}
            className="relative h-full animate-in fade-in slide-in-from-bottom-4"
            style={{ animationDelay: `${idx * 50}ms`, animationFillMode: "backwards" }}
          >
            {/* Server Badge */}
            <div className="absolute -top-3 -right-3 z-20 px-3 py-1 bg-purple-600/20 backdrop-blur-md rounded-lg text-[10px] text-white font-bold font-mono border border-purple-600/30 shadow-[0_0_15px_rgba(189,0,255,0.3)]">
              {tool.server}
            </div>
            <ToolInfo data={tool} onExecute={() => setSelectedTool(tool)} />
          </div>
        ))}
      </div>

      {filteredTools.length === 0 && (
        <div className="col-span-full py-24 text-center glass-panel bg-white/[0.01] border-white/5">
          <Terminal className="mx-auto w-16 h-16 mb-5 text-white/60" />
          <p className="text-xl font-bold text-white tracking-tight">No capabilities found</p>
          <p className="text-[#94a3b8] mt-2 font-medium">Try adjusting your query string.</p>
        </div>
      )}

      <ToolExecutionModal
        isOpen={selectedTool !== null}
        onClose={() => setSelectedTool(null)}
        tool={selectedTool}
      />
    </div>
  );
}
