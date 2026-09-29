import {
  AlertCircle,
  Download,
  Loader2,
  MessageCircle,
  Send,
  Settings,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  type ChatMessage as LLMChatMessage,
  type ChatPersonality,
  type PendingCall,
  llmService,
} from "../services/llm";
import { logger } from "../utils/logger";

const LS_KEY = "meta-mcp-chat-history";
const PERS_KEY = "meta-mcp-chat-personality";
const AGENT_KEY = "meta-mcp-chat-agent";

const FALLBACK_ORIENTATION =
  "You are MetaMCP, the fleet control-center assistant. Answer from evidence, be concise.";

const FALLBACK_PERSONALITIES: ChatPersonality[] = [
  {
    id: "mcp-expert",
    label: "MCP Expert",
    prompt:
      "You are an expert on MCP servers and this fleet. Explain what tools do and teach as you go.",
  },
  {
    id: "fleet-operator",
    label: "Fleet Operator",
    prompt: "You are a fleet operator. Act first, explain briefly after. Keep answers terse.",
  },
  {
    id: "analyst",
    label: "Analyst",
    prompt: "You are a careful analyst. Gather evidence before concluding. Cite tool names and scores.",
  },
];

interface ChatPageProps {
  onNavigateToSettings?: () => void;
}

const EXAMPLE_PROMPTS = [
  {
    group: "Discovery",
    items: ["List all connected MCP servers", "Show tool inventory", "What servers are online?"],
  },
  {
    group: "Meta",
    items: [
      "How does proxy routing work?",
      "Explain the gateway pattern",
      "View server health stats",
    ],
  },
  {
    group: "Debug",
    items: [
      "Check a server's tool list",
      "Test server connectivity",
      "Find which server handles this",
    ],
  },
];

function loadHistory(): LLMChatMessage[] {
  try {
    const d = localStorage.getItem(LS_KEY);
    return d ? JSON.parse(d) : [];
  } catch {
    return [];
  }
}
function saveHistory(msgs: LLMChatMessage[]) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(msgs.slice(-100)));
  } catch {}
}
function loadPersonality(): string {
  try {
    return localStorage.getItem(PERS_KEY) || "mcp-expert";
  } catch {
    return "mcp-expert";
  }
}

function MessageBubble({
  role,
  content,
  trace,
}: {
  role: LLMChatMessage["role"];
  content: string;
  trace?: LLMChatMessage["trace"];
}) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-xl px-4 py-2.5 ${
          isUser
            ? "bg-blue-600/20 border border-blue-500/30 text-slate-200"
            : "bg-slate-800 border border-slate-700 text-slate-200"
        }`}
      >
        <p className="text-sm whitespace-pre-wrap break-words">{content}</p>
        {!isUser && trace && trace.length > 0 && (
          <details className="mt-2 text-xs">
            <summary className="cursor-pointer text-slate-400 hover:text-slate-200">
              Used {trace.length} tool{trace.length === 1 ? "" : "s"}
            </summary>
            <div className="mt-1.5 space-y-1.5">
              {trace.map((t, i) => (
                <div key={i} className="rounded bg-slate-950/70 border border-slate-800 p-2 font-mono">
                  <div className="flex items-center gap-1.5">
                    <span className={`inline-block w-1.5 h-1.5 rounded-full ${t.ok ? "bg-green-400" : "bg-red-400"}`} />
                    <span className="text-blue-300">{t.name}</span>
                  </div>
                  <div className="text-slate-500 truncate mt-0.5">
                    {JSON.stringify(t.args)}
                  </div>
                  <div className="text-slate-400 whitespace-pre-wrap break-words mt-0.5">{t.preview}</div>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}

export function ChatPage({ onNavigateToSettings }: ChatPageProps) {
  const [messages, setMessages] = useState<LLMChatMessage[]>(() => loadHistory());
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [llmReady, setLlmReady] = useState(llmService.isConfigured());
  const [statusNote, setStatusNote] = useState<string | null>(null);
  const [personalityId, setPersonalityId] = useState(() => loadPersonality());
  const [personalities, setPersonalities] = useState<ChatPersonality[]>(FALLBACK_PERSONALITIES);
  const [orientation, setOrientation] = useState(FALLBACK_ORIENTATION);
  const [toolCount, setToolCount] = useState(0);
  const [pending, setPending] = useState<{ runId: string; calls: PendingCall[]; draft: string } | null>(null);
  const [approvedIds, setApprovedIds] = useState<string[]>([]);
  const [agentMode, setAgentMode] = useState(() => {
    try {
      return localStorage.getItem(AGENT_KEY) !== "off";
    } catch {
      return true;
    }
  });
  const scrollRef = useRef<HTMLDivElement>(null);

  const config = llmService.getConfig();

  const setAgentModeStored = (on: boolean) => {
    setAgentMode(on);
    try {
      localStorage.setItem(AGENT_KEY, on ? "on" : "off");
    } catch {
      // ignore localstorage errors
    }
  };

  const refreshLlmStatus = useCallback(async () => {
    const cfg = llmService.getConfig();
    if (!llmService.isConfigured()) {
      setLlmReady(false);
      setStatusNote(null);
      return;
    }
    try {
      const models = await llmService.listModels();
      const ids = models.map((m) => m.id);
      if (ids.length > 0 && !ids.includes(cfg.model)) {
        setLlmReady(false);
        setStatusNote(`Saved model "${cfg.model}" not found. Open Settings and re-run Discovery.`);
        return;
      }
      setLlmReady(true);
      setStatusNote(null);
    } catch (e) {
      setLlmReady(false);
      setStatusNote(
        e instanceof Error ? e.message : "Cannot reach local LLM — check Settings → Discovery",
      );
    }
  }, []);

  useEffect(() => {
    void refreshLlmStatus();
    void llmService.getChatContext().then((ctx) => {
      if (!ctx) return;
      if (ctx.personalities.length > 0) setPersonalities(ctx.personalities);
      if (ctx.orientation) setOrientation(ctx.orientation);
      setToolCount(ctx.tool_count);
    });
  }, [refreshLlmStatus]);
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
    saveHistory(messages);
  }, [messages]);
  useEffect(() => {
    localStorage.setItem(PERS_KEY, personalityId);
  }, [personalityId]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading || !llmReady) return;

    setInput("");
    setError(null);
    const userMsg: LLMChatMessage = { role: "user", content: text };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setIsLoading(true);

    try {
      if (agentMode) {
        const clean = nextMessages
          .filter((m) => m.role === "user" || m.role === "assistant")
          .map(({ role, content }) => ({ role, content }));
        const res = await llmService.agent(clean, personalityId);
        if (res.needs_confirmation && res.run_id) {
          setPending({ runId: res.run_id, calls: res.pending ?? [], draft: res.reply });
          setApprovedIds((res.pending ?? []).map((c) => c.id));
          setMessages((prev) => [...prev, { role: "assistant", content: res.reply, trace: res.trace }]);
        } else {
          setMessages((prev) => [...prev, { role: "assistant", content: res.reply, trace: res.trace }]);
        }
      } else {
        const persona = personalities.find((p) => p.id === personalityId) ?? personalities[0];
        const system: LLMChatMessage = {
          role: "system",
          content: `${orientation}\n\n## Role\n${persona?.prompt ?? ""}`,
        };
        const clean = nextMessages.map(({ role, content }) => ({ role, content }));
        const reply = await llmService.chat([system, ...clean]);
        setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Request failed";
      setError(msg);
      logger.error("Chat request failed", { error: err });
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async (approved: string[]) => {
    if (!pending || isLoading) return;
    const runId = pending.runId;
    setPending(null);
    setIsLoading(true);
    setError(null);
    try {
      const res = await llmService.confirmAgent(runId, approved);
      if (res.needs_confirmation && res.run_id) {
        setPending({ runId: res.run_id, calls: res.pending ?? [], draft: res.reply });
        setApprovedIds((res.pending ?? []).map((c) => c.id));
      }
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply, trace: res.trace }]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Request failed";
      setError(msg);
      logger.error("Chat confirm failed", { error: err });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const exportChat = () => {
    const text = messages
      .map((m) => `${m.role === "user" ? "You" : "Assistant"}: ${m.content}`)
      .join("\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `meta-mcp-chat-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]" data-testid="chat-page">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-semibold text-slate-200 flex items-center gap-2">
            <MessageCircle className="text-purple-500" size={20} />
            Local LLM Chat
          </h2>
          <span
            className="text-xs text-purple-400 bg-purple-900/30 px-2 py-0.5 rounded border border-purple-800/50"
            data-testid="skill-badge"
            title={toolCount > 0 ? `${toolCount} fleet tools available to the agent` : "Tool catalog not loaded yet"}
          >
            meta-mcp{toolCount > 0 ? ` · ${toolCount} tools` : ""}
          </span>
        </div>
        <div className="flex items-center gap-3 text-sm" data-testid="chat-controls">
          <button
            type="button"
            onClick={() => setAgentModeStored(!agentMode)}
            title={agentMode ? "Agent mode: model can call fleet tools" : "Plain chat: no tool calls"}
            className={`text-xs px-2 py-1 rounded-md border transition-colors ${
              agentMode
                ? "text-emerald-300 bg-emerald-900/30 border-emerald-800/50"
                : "text-slate-400 bg-slate-800 border-slate-700 hover:text-white"
            }`}
            data-testid="agent-toggle"
          >
            {agentMode ? "Agent on" : "Agent off"}
          </button>
          <span
            className={`inline-block w-2 h-2 rounded-full ${llmReady ? "bg-green-500" : "bg-red-500"}`}
            data-testid="backend-dot"
          />
          <span className={`font-mono ${llmReady ? "text-green-400" : "text-amber-400"}`}>
            {config.provider} @ {config.baseUrl}
            {config.model ? ` / ${config.model}` : " / no model"}
          </span>
          <select
            value={personalityId}
            onChange={(e) => setPersonalityId(e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-200"
            data-testid="personality-select"
          >
            {personalities.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={exportChat}
            disabled={messages.length === 0}
            className="text-xs text-slate-400 hover:text-white p-1"
            data-testid="chat-export"
          >
            <Download size={14} />
          </button>
          <button
            type="button"
            onClick={() => setMessages([])}
            disabled={messages.length === 0}
            className="text-xs text-red-400 hover:text-red-300 p-1"
            data-testid="chat-clear"
          >
            <Trash2 size={14} />
          </button>
          {onNavigateToSettings && (
            <button
              type="button"
              onClick={onNavigateToSettings}
              className="flex items-center gap-1 text-slate-300 hover:text-purple-400 transition-colors"
            >
              <Settings size={16} />
              Settings
            </button>
          )}
        </div>
      </div>

      {!llmReady && (
        <div className="mb-4 p-4 rounded-xl border border-amber-800/50 bg-amber-950/30 text-amber-200 text-sm flex items-start gap-3">
          <AlertCircle size={20} className="shrink-0" />
          <div>
            <p className="font-medium">Local LLM not ready</p>
            <p className="text-xs mt-1 text-amber-200/80">
              Open <strong>Settings</strong>, run <strong>Discovery</strong>, choose a model from
              the dropdown, then <strong>Save config</strong>. MetaMCP proxies requests to Ollama
              (no browser CORS).
            </p>
            {statusNote && <p className="text-xs mt-2 font-mono text-red-300">{statusNote}</p>}
            {onNavigateToSettings && (
              <button
                type="button"
                onClick={onNavigateToSettings}
                className="mt-3 text-xs font-bold uppercase tracking-wider text-blue-400 hover:underline"
              >
                Go to Settings
              </button>
            )}
          </div>
        </div>
      )}

      <div
        className="flex-1 overflow-y-auto space-y-4 p-4 bg-slate-950/50 border border-slate-800 rounded-xl min-h-0"
        data-testid="dashboard"
      >
        <div className="space-y-4" data-testid="chat-messages">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 text-center py-12">
              <MessageCircle size={48} className="mb-4 opacity-50" />
              {llmReady ? (
                <p className="text-sm">
                  {agentMode
                    ? "Ask anything — the agent can call fleet tools to find out."
                    : "Ask anything — replies use your selected local model."}
                </p>
              ) : (
                <p className="text-sm max-w-md">Configure a model in Settings before chatting.</p>
              )}
            </div>
          )}
          {messages.map((m, i) => (
            <MessageBubble
              key={`${m.role}-${i}-${m.content.substring(0, 10)}`}
              role={m.role}
              content={m.content}
              trace={m.trace}
            />
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 flex items-center gap-2">
                <Loader2 className="animate-spin" size={16} />
                <span className="text-slate-300 text-sm">Thinking...</span>
              </div>
            </div>
          )}
          {pending && (
            <div className="rounded-xl border border-amber-700/50 bg-amber-950/30 p-4">
              <div className="text-sm font-semibold text-amber-200 mb-1">
                Agent wants to run {pending.calls.length} mutating call
                {pending.calls.length === 1 ? "" : "s"}
              </div>
              {pending.draft && (
                <p className="text-xs text-slate-400 mb-3 whitespace-pre-wrap">{pending.draft}</p>
              )}
              <div className="space-y-1.5 mb-3">
                {pending.calls.map((c) => (
                  <label
                    key={c.id}
                    className="flex items-start gap-2 rounded-lg bg-slate-950/70 border border-slate-800 p-2.5 cursor-pointer text-xs font-mono"
                  >
                    <input
                      type="checkbox"
                      checked={approvedIds.includes(c.id)}
                      onChange={(e) =>
                        setApprovedIds((prev) =>
                          e.target.checked ? [...prev, c.id] : prev.filter((id) => id !== c.id),
                        )
                      }
                      className="mt-0.5 accent-amber-500"
                    />
                    <span className="min-w-0">
                      <span className="text-blue-300">{c.name}</span>{" "}
                      <span className="text-slate-500 break-all">{JSON.stringify(c.arguments)}</span>
                    </span>
                  </label>
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleConfirm(approvedIds)}
                  disabled={isLoading || approvedIds.length === 0}
                  className="px-4 py-2 rounded-lg text-sm font-semibold bg-amber-600 hover:bg-amber-500 text-white transition-colors disabled:opacity-50"
                >
                  Approve selected ({approvedIds.length})
                </button>
                <button
                  type="button"
                  onClick={() => handleConfirm([])}
                  disabled={isLoading}
                  className="px-4 py-2 rounded-lg text-sm text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  Deny all
                </button>
              </div>
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </div>

      {error && (
        <div className="mt-2 flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      <div className="mt-4">
        <div className="flex flex-wrap gap-1 mb-2" data-testid="example-prompts">
          {EXAMPLE_PROMPTS.map((g) =>
            g.items.map((p, i) => (
              <button
                key={`${g.group}-${i}`}
                type="button"
                onClick={() => setInput(p)}
                className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700 transition-colors"
              >
                {p}
              </button>
            )),
          )}
        </div>
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={llmReady ? "Type a message..." : "Configure model in Settings first..."}
            rows={2}
            disabled={isLoading || !llmReady}
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-500 focus:ring-2 focus:ring-purple-500/50 outline-none resize-none disabled:opacity-50"
            data-testid="chat-input"
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={isLoading || !input.trim() || !llmReady}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 rounded-xl text-white font-medium transition-colors flex items-center gap-2"
            data-testid="chat-send"
          >
            <Send size={18} />
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
