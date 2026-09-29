import { Box, ChevronDown, ChevronRight, Play, Terminal } from "lucide-react";
import { useState } from "react";
import { JsonView } from "../common/JsonView";

export interface ToolInfoData {
  name: string;
  description: string;
  parameters: Record<string, unknown>; // Using structured record for JSON schema
}

interface ToolInfoProps {
  data: ToolInfoData;
  onExecute?: (tool: ToolInfoData) => void;
}

export function ToolInfo({ data, onExecute }: ToolInfoProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`glass-panel flex flex-col h-full hover:bg-white/[0.05] transition-all duration-300 group shadow-xl relative overflow-hidden ${expanded ? "ring-1 ring-[#bd00ff]/30 bg-white/[0.04]" : "bg-white/[0.02] border-white/5"}`}
    >
      {/* Subtle glow effect behind the card */}
      <div
        className={
          "absolute -inset-10 opacity-0 group-hover:opacity-20 blur-2xl transition-opacity duration-700 bg-gradient-to-br from-purple-600/30 to-transparent pointer-events-none"
        }
      />

      <div className="p-6 flex-1 relative z-10">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white/5 rounded-xl text-white group-hover:text-purple-400 transition-colors shadow-inner border border-white/5">
              <Box size={22} />
            </div>
            <h4 className="font-bold text-lg text-white group-hover:text-purple-400 transition-colors tracking-tight">
              {data.name}
            </h4>
          </div>
        </div>

        <p className="text-sm text-[#94a3b8] leading-relaxed line-clamp-3 min-h-[3.5rem] font-medium">
          {data.description || "No description capability profile provided."}
        </p>
      </div>

      <div className="bg-black/20 px-6 py-4 border-t border-white/5 flex flex-col gap-4 relative z-10 shadow-inner">
        <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-[#94a3b8]">
          <div className="flex items-center gap-2 bg-white/5 px-3 py-1.5 rounded-lg border border-white/5">
            <Terminal size={14} className="text-blue-400" />
            <span>JSON-RPC Target</span>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => onExecute?.(data)}
              className="flex items-center gap-1.5 text-white hover:text-green-400 transition-colors focus:outline-none bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-lg border border-white/5"
              title="Execute Tool Binding"
            >
              <Play size={14} className="text-green-400" /> <span className="mt-0.5">Run</span>
            </button>
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className={`flex items-center gap-1.5 transition-colors focus:outline-none bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-lg border border-white/5 ${expanded ? "text-blue-400" : "text-white hover:text-purple-400"}`}
            >
              <span className="mt-0.5">{expanded ? "Hide Schema" : "Inspect"}</span>{" "}
              {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
          </div>
        </div>

        {/* Expanded Details */}
        {expanded && (
          <div className="pt-4 mt-2 border-t border-white/5 animate-in slide-in-from-top-2 duration-300 fade-in">
            <p className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-widest mb-3">
              Invocation Schema Profile
            </p>
            <JsonView
              value={data.parameters}
              className="text-xs text-blue-400 bg-black/40 p-4 rounded-xl border border-white/5 shadow-inner"
            />
          </div>
        )}
      </div>
    </div>
  );
}
