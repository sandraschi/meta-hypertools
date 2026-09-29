import { logger } from "../utils/logger";

export interface LLMConfig {
  provider: string;
  baseUrl: string;
  model: string;
}

export interface LLMProviderInfo {
  id: string;
  label: string;
  base_url: string;
  models: string[];
  needs_key: boolean;
}

export interface LLMModel {
  id: string;
  object: string;
  created: number;
  owned_by: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  trace?: ChatTraceEntry[];
}

export interface ChatTraceEntry {
  name: string;
  args: unknown;
  ok: boolean;
  preview: string;
}

export interface ChatPersonality {
  id: string;
  label: string;
  prompt: string;
}

export interface ChatToolInfo {
  name: string;
  description: string;
}

export interface ChatContext {
  personalities: ChatPersonality[];
  tools: ChatToolInfo[];
  tool_count: number;
  orientation: string;
}

export interface AgentReply {
  reply: string;
  trace: ChatTraceEntry[];
  iterations: number;
  needs_confirmation?: boolean;
  run_id?: string;
  pending?: PendingCall[];
}

export interface PendingCall {
  id: string;
  name: string;
  arguments: unknown;
}

const DEFAULT_CONFIG: LLMConfig = {
  provider: "ollama",
  baseUrl: "http://localhost:11434",
  model: "",
};

const API_BASE_URL =
  (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_BASE_URL || "";

/** MetaMCP API bridge — same-origin in dev via Vite proxy to :10718 */
function llmApiUrl(path: string): string {
  const base = API_BASE_URL.replace(/\/$/, "");
  return base ? `${base}/api/v1/llm${path}` : `/api/v1/llm${path}`;
}

function chatApiUrl(path: string): string {
  const base = API_BASE_URL.replace(/\/$/, "");
  return base ? `${base}/api/v1/chat${path}` : `/api/v1/chat${path}`;
}

class LLMService {
  private config: LLMConfig;
  private lastDiscoveryError: string | null = null;

  constructor() {
    this.config = this.loadConfig();
  }

  private loadConfig(): LLMConfig {
    const saved = localStorage.getItem("meta_mcp_llm_config");
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Partial<LLMConfig>;
        const model = (parsed.model ?? "").trim();
        return {
          ...DEFAULT_CONFIG,
          ...parsed,
          // Legacy default before discovery existed — force re-pick via Settings
          model: model === "llama3" ? "" : model,
        };
      } catch (e) {
        logger.error("Failed to parse saved LLM config", { error: e });
      }
    }
    return { ...DEFAULT_CONFIG };
  }

  saveConfig(config: LLMConfig) {
    this.config = {
      ...config,
      model: (config.model || "").trim(),
      baseUrl: (config.baseUrl || "").trim(),
    };
    localStorage.setItem("meta_mcp_llm_config", JSON.stringify(this.config));
    logger.info("LLM Config saved", this.config);
  }

  getConfig(): LLMConfig {
    return this.config;
  }

  getLastDiscoveryError(): string | null {
    return this.lastDiscoveryError;
  }

  isConfigured(): boolean {
    return Boolean(this.config.baseUrl.trim() && this.config.model.trim());
  }

  async listModels(): Promise<LLMModel[]> {
    this.lastDiscoveryError = null;
    try {
      const response = await fetch(llmApiUrl("/models"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: this.config.provider,
          base_url: this.config.baseUrl,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        const detail =
          typeof data?.detail === "string" ? data.detail : data?.message || response.statusText;
        throw new Error(detail);
      }
      const models = (data?.data?.models ?? data?.models ?? []) as LLMModel[];
      if (!Array.isArray(models)) {
        return [];
      }
      return models.filter((m) => m?.id);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.lastDiscoveryError = msg;
      logger.error("Failed to list LLM models", { error });
      throw error;
    }
  }

  async completion(prompt: string): Promise<string> {
    return this.chat([{ role: "user", content: prompt }]);
  }

  async chat(messages: ChatMessage[]): Promise<string> {
    if (!this.isConfigured()) {
      throw new Error(
        "No model selected. Open Settings → Local LLM, run Discovery, pick a model, and save.",
      );
    }
    try {
      const response = await fetch(llmApiUrl("/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: this.config.provider,
          base_url: this.config.baseUrl,
          model: this.config.model,
          messages,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        const detail =
          typeof data?.detail === "string" ? data.detail : data?.message || response.statusText;
        throw new Error(detail);
      }
      const content = data?.data?.content ?? data?.content ?? "";
      return typeof content === "string" ? content : "";
    } catch (error) {
      logger.error("LLM chat failed", { error });
      throw error;
    }
  }

  async getChatContext(): Promise<ChatContext | null> {
    try {
      const response = await fetch(chatApiUrl("/context"));
      if (!response.ok) return null;
      const data = await response.json();
      const ctx = (data?.data ?? data) as Partial<ChatContext>;
      if (!Array.isArray(ctx.personalities)) return null;
      return {
        personalities: ctx.personalities,
        tools: Array.isArray(ctx.tools) ? ctx.tools : [],
        tool_count: Number(ctx.tool_count ?? ctx.tools?.length ?? 0),
        orientation: typeof ctx.orientation === "string" ? ctx.orientation : "",
      };
    } catch (error) {
      logger.error("Failed to load chat context", { error });
      return null;
    }
  }

  async agent(
    messages: ChatMessage[],
    personalityId: string,
    maxIterations = 5,
  ): Promise<AgentReply> {
    if (!this.isConfigured()) {
      throw new Error(
        "No model selected. Open Settings → Local LLM, run Discovery, pick a model, and save.",
      );
    }
    try {
      const response = await fetch(chatApiUrl("/agent"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: this.config.provider,
          base_url: this.config.baseUrl,
          model: this.config.model,
          messages: messages.map(({ role, content }) => ({ role, content })),
          personality_id: personalityId,
          max_iterations: maxIterations,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        const detail =
          typeof data?.detail === "string" ? data.detail : data?.message || response.statusText;
        throw new Error(detail);
      }
      const d = (data?.data ?? data) as Partial<AgentReply>;
      return {
        reply: typeof d.reply === "string" ? d.reply : "",
        trace: Array.isArray(d.trace) ? d.trace : [],
        iterations: Number(d.iterations ?? 0),
        needs_confirmation: d.needs_confirmation === true,
        run_id: typeof d.run_id === "string" ? d.run_id : undefined,
        pending: Array.isArray(d.pending) ? d.pending : [],
      };
    } catch (error) {
      logger.error("Agent chat failed", { error });
      throw error;
    }
  }

  async confirmAgent(runId: string, approved: string[]): Promise<AgentReply> {
    try {
      const response = await fetch(chatApiUrl("/agent/confirm"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runId, approved }),
      });
      const data = await response.json();
      if (!response.ok) {
        const detail =
          typeof data?.detail === "string" ? data.detail : data?.message || response.statusText;
        throw new Error(detail);
      }
      const d = (data?.data ?? data) as Partial<AgentReply>;
      return {
        reply: typeof d.reply === "string" ? d.reply : "",
        trace: Array.isArray(d.trace) ? d.trace : [],
        iterations: Number(d.iterations ?? 0),
        needs_confirmation: d.needs_confirmation === true,
        run_id: typeof d.run_id === "string" ? d.run_id : undefined,
        pending: Array.isArray(d.pending) ? d.pending : [],
      };
    } catch (error) {
      logger.error("Agent confirm failed", { error });
      throw error;
    }
  }
}

export const llmService = new LLMService();
