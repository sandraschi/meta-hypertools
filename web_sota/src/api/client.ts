import { logger } from "../utils/logger";

/**
 * MetaMCP Frontend API Client
 * Handles communication with the MetaMCP backend REST API
 */

const API_BASE_URL =
  (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_BASE_URL || "";

const MCP_SERVER_ID = "meta-mcp";

export interface ApiResponse<T = unknown> {
  success: boolean;
  message: string;
  data?: T;
  result?: unknown;
  errors?: string[];
  metadata?: {
    service: string;
    timestamp: number;
  };
}

// Generic API client class
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;

    const config: RequestInit = {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      // Add timeout to prevent hanging requests
      signal: AbortSignal.timeout(45000), // 45 second timeout
      ...options,
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        let detail = response.statusText;
        try {
          const body = await response.json();
          if (body.detail) detail = body.detail;
          else if (body.message) detail = body.message;
        } catch {
          // response body isn't JSON — use statusText
        }
        throw new Error(`HTTP ${response.status}: ${detail}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      logger.error("API request failed", { endpoint, error: errorMsg });

      let errorMessage = "Unknown error occurred";
      if (error instanceof Error) {
        if (error.name === "TimeoutError") {
          errorMessage = "Request timed out. The operation may be taking too long.";
        } else if (error.name === "AbortError") {
          errorMessage = "Request was cancelled or timed out.";
        } else {
          errorMessage = error.message;
        }
      }

      return {
        success: false,
        message: errorMessage,
        errors: [errorMessage],
      };
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }
}

// Create singleton instance
const apiClient = new ApiClient();

// Tool-specific API methods
export const api = {
  // Health and status
  async getHealth(): Promise<ApiResponse> {
    return apiClient.get("/health");
  },

  async getDetailedHealth(): Promise<ApiResponse> {
    return apiClient.get("/api/v1/health/detailed");
  },

  async listTools(): Promise<ApiResponse> {
    return apiClient.get("/api/v1/tools/list");
  },

  /** Live FastMCP tool list with JSON Schema (for DynamicForm / Tool Lab). */
  async getMcpCatalog(): Promise<ApiResponse> {
    return apiClient.get("/api/v1/mcp/catalog");
  },

  // Generic tool execution
  async executeTool(
    serverId: string,
    toolName: string,
    params: Record<string, unknown> = {},
  ): Promise<ApiResponse> {
    return apiClient.post("/api/v1/tools/execute", {
      server_id: serverId,
      tool_name: toolName,
      parameters: params,
    });
  },

  // Diagnostics tools
  async runEmojiBuster(params: {
    operation: string;
    repo_path?: string;
    scan_mode?: string;
    auto_fix?: boolean;
    backup?: boolean;
  }): Promise<ApiResponse> {
    return apiClient.post("/api/v1/diagnostics/emojibuster", params);
  },

  async runPowerShellTools(params: {
    operation: string;
    repo_path?: string;
    scan_mode?: string;
    include_aliases?: boolean;
  }): Promise<ApiResponse> {
    return apiClient.post("/api/v1/diagnostics/powershell", params);
  },

  async validateJustfile(params: {
    repo_path: string;
    fix?: boolean;
  }): Promise<ApiResponse> {
    return apiClient.post("/api/v1/diagnostics/justfile", params);
  },

  // Analysis tools
  async runRuntAnalyzer(params: {
    operation: string;
    repo_path?: string;
    scan_mode?: string;
    include_dependencies?: boolean;
  }): Promise<ApiResponse> {
    return apiClient.post("/api/v1/analysis/runt-analyzer", params);
  },

  // Session docs (mcp-agent-session-summaries bridge)
  async listSessionDocs(): Promise<
    ApiResponse<{ docs: Array<{ name: string; size_bytes: number; modified: string }> }>
  > {
    return apiClient.get("/api/v1/session-docs");
  },

  async readSessionDoc(name: string): Promise<ApiResponse<{ content: string }>> {
    return apiClient.get(`/api/v1/session-docs/${encodeURIComponent(name)}`);
  },

  // Server Management
  async listRunningServers(): Promise<ApiResponse> {
    return apiClient.post("/api/v1/tools/execute", {
      server_id: MCP_SERVER_ID,
      tool_name: "list_mcp_servers",
      parameters: {},
    });
  },

  async stopMcpServer(serverId: string): Promise<ApiResponse> {
    return apiClient.post("/api/v1/tools/execute", {
      server_id: MCP_SERVER_ID,
      tool_name: "stop_mcp_server",
      parameters: { server_id: serverId },
    });
  },

  async getRepoStatus(params: { operation: string; repo_path?: string }): Promise<ApiResponse> {
    return apiClient.post("/api/v1/analysis/repo-status", params);
  },

  // Discovery tools
  async discoverServers(params: {
    operation: string;
    client_type?: string;
    discovery_path?: string;
  }): Promise<ApiResponse> {
    return apiClient.post("/api/v1/discovery/servers", params);
  },

  async checkClientIntegration(params: {
    operation: string;
    client_type?: string;
  }): Promise<ApiResponse> {
    return apiClient.post("/api/v1/discovery/client-integration", params);
  },

  // Scaffolding tools
  async createProject(params: {
    template_type: string;
    project_name: string;
    output_path: string;
    features?: Record<string, unknown>;
  }): Promise<ApiResponse> {
    return apiClient.post("/api/v1/scaffolding/create", params);
  },

  async scaffoldTauriNsis(params: {
    repo_root: string;
    repo_name: string;
    backend_port: number;
    frontend_port?: number;
    mode: string;
  }): Promise<ApiResponse> {
    return this.executeTool("meta_mcp", "scaffold_tauri_nsis", params);
  },

  // Repository analysis tools
  async scanRepository(params: {
    repo_path: string;
    deep_analysis?: boolean;
  }): Promise<ApiResponse> {
    return apiClient.post("/api/v1/repos/scan", params);
  },

  // Client Management
  async getClientConfig(clientName: string): Promise<ApiResponse> {
    return apiClient.get(`/api/v1/clients/${clientName}/config`);
  },

  async updateClientConfig(
    clientName: string,
    updates: Record<string, unknown>,
    backup = true,
  ): Promise<ApiResponse> {
    return apiClient.post(`/api/v1/clients/${clientName}/config?backup=${backup}`, updates);
  },

  async validateClientConfig(clientName: string): Promise<ApiResponse> {
    return apiClient.post(`/api/v1/clients/${clientName}/validate`);
  },

  // Server Inspection
  async inspectServer(params: {
    command: string;
    args: string[];
    env?: Record<string, string>;
  }): Promise<ApiResponse> {
    return apiClient.post("/api/v1/servers/inspect", params);
  },
};

// Utility functions
export const isSuccessResponse = (response: ApiResponse): boolean => {
  return response.success === true;
};

export const getErrorMessage = (response: ApiResponse): string => {
  if (response.errors && response.errors.length > 0) {
    return response.errors[0];
  }
  return response.message || "An unknown error occurred";
};

export const getSuccessMessage = (response: ApiResponse): string => {
  return response.message || "Operation completed successfully";
};

// Type guards
export const isApiResponse = (obj: unknown): obj is ApiResponse => {
  return (
    obj !== null &&
    typeof obj === "object" &&
    "success" in (obj as Record<string, unknown>) &&
    "message" in (obj as Record<string, unknown>)
  );
};

export default api;
