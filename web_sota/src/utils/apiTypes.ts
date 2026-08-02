/** Small helpers for loosely typed API payloads. */

export function asRecord(value: unknown): Record<string, unknown> {
  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

export function asArray<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

export function asString(value: unknown, fallback = ""): string {
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return fallback;
  return String(value);
}

export interface McpServerConfig {
  command: string;
  args: string[];
  env?: Record<string, string>;
}

export function asMcpServerConfig(value: unknown): McpServerConfig | null {
  const rec = asRecord(value);
  if (!rec.command) return null;
  return {
    command: asString(rec.command),
    args: asArray<unknown>(rec.args).map((a) => asString(a)),
    env: rec.env ? (asRecord(rec.env) as Record<string, string>) : undefined,
  };
}
