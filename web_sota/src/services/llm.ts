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
}

export const llmService = new LLMService();
