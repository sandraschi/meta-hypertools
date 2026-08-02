import { AlertTriangle, CheckCircle, ShieldCheck } from "lucide-react";

export interface HealthStatusData {
  healthy: boolean;
  status: string;
  diagnostics: { healthy: boolean; status: string };
  analysis: { healthy: boolean; status: string };
  discovery: { healthy: boolean; status: string };
  scaffolding: { healthy: boolean; status: string };
}

export function HealthStatus({ data }: { data: HealthStatusData }) {
  if (!data) return null;

  const modules = [
    { key: "diagnostics", label: "Diagnostics", icon: ShieldCheck },
    { key: "analysis", label: "Code Analysis", icon: CheckCircle },
    { key: "discovery", label: "Discovery", icon: AlertTriangle },
    { key: "scaffolding", label: "Scaffolding", icon: CheckCircle },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {modules.map((mod) => {
        // @ts-expect-error
        const info = data[mod.key];
        const isHealthy = info?.healthy;

        return (
          <div
            key={mod.key}
            className={`bg-slate-900 border ${isHealthy ? "border-slate-800" : "border-red-500/30"} rounded-xl p-4 flex items-center justify-between`}
          >
            <div className="flex items-center gap-3">
              <div
                className={`p-2 rounded-lg ${isHealthy ? "bg-blue-500/10 text-blue-400" : "bg-red-500/10 text-red-500"}`}
              >
                <mod.icon size={20} />
              </div>
              <div>
                <h4 className="font-medium text-slate-200 text-sm">{mod.label}</h4>
                <p className={`text-xs ${isHealthy ? "text-green-400" : "text-red-400"}`}>
                  {isHealthy ? "Operational" : "Issues Detected"}
                </p>
              </div>
            </div>
            <div
              className={`w-2 h-2 rounded-full ${isHealthy ? "bg-green-500 animate-pulse" : "bg-red-500"}`}
            />
          </div>
        );
      })}
    </div>
  );
}
