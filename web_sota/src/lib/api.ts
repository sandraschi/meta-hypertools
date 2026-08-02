const API_BASE =
  (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_BASE_URL || "";
export { API_BASE };
