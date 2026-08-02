export interface McpServerConfig {
  command: string;
  args: string[];
  env?: Record<string, string>;
}

export interface DiscoveredServer {
  name: string;
  path: string;
  type: string;
  description?: string;
  execution?: McpServerConfig;
  tools_count?: number;
  status?: "running" | "stopped" | "unknown";
}

export interface McpTool {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  server: string;
}

export interface IntegrationStatus {
  connected: boolean;
  path?: string;
  error?: string;
  servers?: Record<string, unknown>;
}

export interface ClientStatusResponse {
  installed: boolean;
  config_path?: string;
  mcp_servers?: Record<string, unknown>;
}

export interface Toolchain {
  name: string;
  description?: string;
  servers: string[];
}
