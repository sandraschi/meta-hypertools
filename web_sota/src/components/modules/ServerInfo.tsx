import { Activity, Clock, Server, Tag } from "lucide-react";

export interface ServerInfoData {
  id: string;
  name: string;
  status: "online" | "offline" | "error";
  type: string;
  version: string;
  uptime?: string;
  last_seen: string;
}

export function ServerInfo({ data }: { data: ServerInfoData }) {
  const isOnline = data.status === "online";

  return (
    <div className="glass-panel p-5 hover:bg-white/[0.05] transition-all duration-300 group shadow-lg shadow-black/20 relative overflow-hidden">
      {/* Subtle glow effect behind the card */}
      <div
        className={`absolute -inset-10 opacity-0 group-hover:opacity-20 blur-2xl transition-opacity duration-700 bg-gradient-to-r ${isOnline ? "from-green-500/30" : "from-red-500/30"}`}
      />

      <div className="flex justify-between items-start mb-4 relative">
        <div className="flex items-center gap-3">
          <div
            className={`p-2.5 rounded-xl border ${isOnline ? "bg-green-500/10 text-green-400 border-green-500/20 shadow-[0_0_15px_rgba(74,222,128,0.2)]" : "bg-red-500/10 text-red-400 border-red-500/20"}`}
          >
            <Server size={20} />
          </div>
          <div>
            <h3 className="font-bold text-lg text-white group-hover:text-blue-400 transition-colors tracking-tight">
              {data.name}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span
                className={`flex items-center gap-1.5 text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                  isOnline
                    ? "bg-green-500/10 text-green-400 border border-green-500/20 tracking-wider"
                    : "bg-red-500/10 text-red-400 border border-red-500/20 tracking-wider"
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full shadow-[0_0_8px_currentColor] ${isOnline ? "bg-green-400 animate-pulse" : "bg-red-400"}`}
                />
                {data.status}
              </span>
              <span className="text-[10px] uppercase tracking-wider text-[#94a3b8] font-bold bg-white/5 px-2 py-0.5 rounded-full border border-white/5">
                v{data.version}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm relative">
        <div className="bg-black/20 p-3 rounded-xl border border-white/5 group-hover:border-white/10 transition-colors">
          <div className="flex items-center gap-2 text-[#94a3b8] mb-1">
            <Tag size={12} />
            <span className="text-[10px] font-bold uppercase tracking-wider">Type</span>
          </div>
          <span className="text-white font-medium text-sm">{data.type}</span>
        </div>
        <div className="bg-black/20 p-3 rounded-xl border border-white/5 group-hover:border-white/10 transition-colors">
          <div className="flex items-center gap-2 text-[#94a3b8] mb-1">
            <Clock size={12} />
            <span className="text-[10px] font-bold uppercase tracking-wider">Last Seen</span>
          </div>
          <span className="text-white font-medium text-sm">{data.last_seen}</span>
        </div>
      </div>

      {data.uptime && (
        <div className="mt-4 flex items-center gap-2 text-xs text-[#94a3b8] bg-black/20 p-2.5 rounded-xl justify-center border border-white/5 relative">
          <Activity size={14} className="text-blue-400" />
          <span className="font-medium tracking-wide">
            Uptime: <span className="text-white font-mono tracking-normal">{data.uptime}</span>
          </span>
        </div>
      )}
    </div>
  );
}
