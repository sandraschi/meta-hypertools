import { motion } from "framer-motion";
import { Bot, CalendarClock, Loader2, Mail, Play, RefreshCw, Sparkles, Zap } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useState } from "react";
import { asArray, asRecord, asString } from "../utils/apiTypes";

const API = "/api/v1/agent-hub";

type Tab = "fritz" | "robofang";

interface FritzFlow {
  key?: string;
  label?: string;
  description?: string;
  default_recurrence?: string;
  category?: string;
}

interface FritzTask {
  id?: string;
  task?: string;
  recurrence?: string;
  completed?: boolean;
}

interface RobofangRoutine {
  id?: string;
  name?: string;
  time_local?: string;
  recurrence?: string;
  enabled?: boolean;
  action_type?: string;
}

const COWORKER_LABELS: Record<string, string> = {
  coworker_fleet_pulse: "Morning Fleet Pulse",
  coworker_inbox_briefing: "Inbox Briefing",
  coworker_day_prep: "Office Day Prep",
  coworker_docs_drift: "Docs Drift Audit",
  coworker_weekly_report_pdf: "Weekly Report PDF",
  coworker_board_pack: "Monthly Board Pack",
  coworker_cursor_spend_watch: "Cursor Spend Watch",
  coworker_artifact_pack: "Artifact Pack",
  coworker_bootstrap: "Bootstrap Schedules",
};

export const AgentHubPage: React.FC = () => {
  const [tab, setTab] = useState<Tab>("fritz");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deliverEmail, setDeliverEmail] = useState(true);
  const [fritz, setFritz] = useState<Record<string, unknown> | null>(null);
  const [robofang, setRobofang] = useState<Record<string, unknown> | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const loadFritz = useCallback(async () => {
    const res = await fetch(`${API}/fritz`);
    if (!res.ok) throw new Error(`Fritz HTTP ${res.status}`);
    const json = await res.json();
    setFritz(asRecord(json.data));
    return Boolean(json.success);
  }, []);

  const loadRobofang = useCallback(async () => {
    const res = await fetch(`${API}/robofang`);
    if (!res.ok) throw new Error(`RoboFang HTTP ${res.status}`);
    const json = await res.json();
    setRobofang(asRecord(json.data));
    return Boolean(json.success);
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (tab === "fritz") {
        const ok = await loadFritz();
        if (!ok) setError("Fritz offline — start fleet-agent-mcp (:10996)");
      } else {
        const ok = await loadRobofang();
        if (!ok) setError("RoboFang offline — start robofang-hub (:10870)");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Agent hub request failed");
    } finally {
      setLoading(false);
    }
  }, [tab, loadFritz, loadRobofang]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const runCoworker = async (tool: string) => {
    setRunning(tool);
    setLastResult(null);
    try {
      const res = await fetch(`${API}/fritz/coworker`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool, deliver: deliverEmail }),
      });
      const json = await res.json();
      setLastResult(asString(json.message, JSON.stringify(json, null, 2)));
      await loadFritz();
    } catch (e) {
      setLastResult(e instanceof Error ? e.message : "Run failed");
    } finally {
      setRunning(null);
    }
  };

  const runRoutine = async (routineId: string) => {
    setRunning(routineId);
    setLastResult(null);
    try {
      const res = await fetch(`${API}/robofang/routine/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ routine_id: routineId }),
      });
      const json = await res.json();
      setLastResult(asString(json.message, JSON.stringify(json, null, 2)));
      await loadRobofang();
    } catch (e) {
      setLastResult(e instanceof Error ? e.message : "Run failed");
    } finally {
      setRunning(null);
    }
  };

  const fritzWhoami = asRecord(fritz?.whoami);
  const fritzFlows = asArray<FritzFlow>(asRecord(fritz?.flows).active);
  const taskPayload = asRecord(fritz?.tasks);
  const fritzTasks = asArray<FritzTask>(taskPayload.tasks ?? taskPayload.data ?? taskPayload);
  const robofangStatus = asRecord(robofang?.status);
  const robofangRoutines = asArray<RobofangRoutine>(asRecord(robofang?.routines).routines);
  const robofangHands = asArray<Record<string, unknown>>(asRecord(robofang?.hands).hands);

  return (
    <div className="space-y-8 pb-12">
      <header className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
        <div>
          <h2 className="text-4xl font-black bg-gradient-to-r from-white via-white to-white/40 bg-clip-text text-transparent flex items-center gap-3">
            <Bot className="text-purple-400" size={32} />
            Fritz & RoboFang
          </h2>
          <p className="text-white/60 mt-1 font-medium">
            Coworker automations (fleet-agent :10996) and RoboFang routines (:10870).
          </p>
          <div className="flex gap-2 mt-4 bg-white/5 p-1 rounded-2xl border border-white/10 w-fit">
            {(["fritz", "robofang"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                  tab === t
                    ? "bg-white/10 text-white border border-white/10"
                    : "text-[#94a3b8] hover:text-white"
                }`}
              >
                {t === "fritz" ? "Fritz" : "RoboFang"}
              </button>
            ))}
          </div>
        </div>
        <button
          type="button"
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-2 px-5 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-xs font-black uppercase tracking-widest"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </header>

      {error && (
        <div className="glass-panel p-4 border-amber-500/30 bg-amber-500/10 text-amber-200 text-sm">
          {error}
        </div>
      )}

      {lastResult && (
        <div className="glass-panel p-4 border-green-500/20 bg-green-500/5 text-green-200 text-sm font-mono whitespace-pre-wrap">
          {lastResult}
        </div>
      )}

      {tab === "fritz" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="glass-panel p-6 border-white/5">
              <div className="text-[10px] font-black uppercase tracking-widest text-[#94a3b8] mb-2">
                Agent
              </div>
              <div className="text-xl font-bold text-white">
                {asString(fritzWhoami.name, "Fritz")}
              </div>
              <div className="text-sm text-white/50 mt-1">
                {asString(fritzWhoami.role, "fleet-agent-mcp")}
              </div>
            </div>
            <div className="glass-panel p-6 border-white/5">
              <div className="text-[10px] font-black uppercase tracking-widest text-[#94a3b8] mb-2">
                Endpoint
              </div>
              <div className="text-sm font-mono text-blue-400">{asString(fritz?.base_url)}</div>
            </div>
            <div className="glass-panel p-6 border-white/5">
              <div className="text-[10px] font-black uppercase tracking-widest text-[#94a3b8] mb-2">
                Pulse tasks
              </div>
              <div className="text-3xl font-black text-white">{fritzTasks.length}</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-white/70">
              <input
                type="checkbox"
                checked={deliverEmail}
                onChange={(e) => setDeliverEmail(e.target.checked)}
                className="rounded"
              />
              <Mail size={14} />
              Deliver via email when SMTP configured
            </label>
          </div>

          <section>
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Zap size={18} className="text-amber-400" />
              Coworker flows — run now
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {(fritzFlows.length
                ? fritzFlows.map((f) => ({
                    tool: `coworker_${asString(f.key)}`,
                    label: f.label,
                    description: f.description,
                    recurrence: f.default_recurrence,
                  }))
                : Object.entries(COWORKER_LABELS).map(([tool, label]) => ({
                    tool,
                    label,
                    description: "",
                    recurrence: "",
                  }))
              ).map((flow) => (
                <motion.div
                  key={flow.tool}
                  className="glass-panel p-5 border-white/5 flex flex-col gap-3"
                  whileHover={{ scale: 1.01 }}
                >
                  <div className="font-bold text-white">{flow.label ?? flow.tool}</div>
                  {flow.description && (
                    <p className="text-sm text-white/50 flex-1">{flow.description}</p>
                  )}
                  {flow.recurrence && (
                    <div className="text-[10px] font-black uppercase tracking-widest text-[#94a3b8] flex items-center gap-1">
                      <CalendarClock size={12} />
                      {flow.recurrence}
                    </div>
                  )}
                  <button
                    type="button"
                    disabled={running !== null}
                    onClick={() => runCoworker(flow.tool)}
                    className="flex items-center justify-center gap-2 py-2 bg-purple-600/20 hover:bg-purple-600/30 border border-purple-600/30 rounded-lg text-xs font-black uppercase tracking-widest disabled:opacity-50"
                  >
                    {running === flow.tool ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Play size={14} />
                    )}
                    Run
                  </button>
                </motion.div>
              ))}
            </div>
          </section>

          {fritzTasks.length > 0 && (
            <section>
              <h3 className="text-lg font-bold text-white mb-4">Scheduled pulse tasks</h3>
              <div className="space-y-2">
                {fritzTasks.slice(0, 12).map((task) => (
                  <div
                    key={String(task.id ?? task.task)}
                    className="glass-panel px-4 py-3 border-white/5 flex justify-between items-center text-sm"
                  >
                    <span className="text-white/80 truncate">{asString(task.task)}</span>
                    <span className="text-[#94a3b8] text-xs font-mono shrink-0 ml-4">
                      {asString(task.recurrence)}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {tab === "robofang" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="glass-panel p-6 border-white/5">
              <div className="text-[10px] font-black uppercase tracking-widest text-[#94a3b8] mb-2">
                Version
              </div>
              <div className="text-xl font-bold text-white">
                {asString(robofangStatus.version, "—")}
              </div>
            </div>
            <div className="glass-panel p-6 border-white/5">
              <div className="text-[10px] font-black uppercase tracking-widest text-[#94a3b8] mb-2">
                Hands
              </div>
              <div className="text-3xl font-black text-white">{robofangHands.length}</div>
            </div>
            <div className="glass-panel p-6 border-white/5">
              <div className="text-[10px] font-black uppercase tracking-widest text-[#94a3b8] mb-2">
                Routines
              </div>
              <div className="text-3xl font-black text-white">{robofangRoutines.length}</div>
            </div>
            <div className="glass-panel p-6 border-white/5">
              <div className="text-[10px] font-black uppercase tracking-widest text-[#94a3b8] mb-2">
                Endpoint
              </div>
              <div className="text-sm font-mono text-blue-400">{asString(robofang?.base_url)}</div>
            </div>
          </div>

          <section>
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Sparkles size={18} className="text-blue-400" />
              Routines
            </h3>
            {robofangRoutines.length === 0 ? (
              <p className="text-white/40 text-sm">No routines registered or RoboFang offline.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {robofangRoutines.map((r) => (
                  <div
                    key={String(r.id)}
                    className="glass-panel p-5 border-white/5 flex flex-col gap-3"
                  >
                    <div className="font-bold text-white">{asString(r.name, r.id)}</div>
                    <div className="text-xs text-white/50 font-mono">
                      {asString(r.time_local)} · {asString(r.recurrence)} ·{" "}
                      {asString(r.action_type)}
                    </div>
                    <button
                      type="button"
                      disabled={running !== null || r.enabled === false}
                      onClick={() => runRoutine(String(r.id))}
                      className="flex items-center justify-center gap-2 py-2 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 rounded-lg text-xs font-black uppercase tracking-widest disabled:opacity-50"
                    >
                      {running === r.id ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Play size={14} />
                      )}
                      Run now
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
};
