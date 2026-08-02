import { type ReactNode, createContext, useCallback, useContext, useEffect, useState } from "react";
import { type ApiResponse, api } from "../api/client";

interface HealthStatus {
  diagnostics: { healthy: boolean; service: string; status: string };
  analysis: { healthy: boolean; service: string; status: string };
  discovery: { healthy: boolean; service: string; status: string };
  scaffolding: { healthy: boolean; service: string; status: string };
}

interface ApiContextType {
  isConnected: boolean;
  healthStatus: HealthStatus | null;
  lastHealthCheck: Date | null;
  serverVersion: string;
  refreshHealth: () => Promise<void>;
  isLoading: boolean;
}

const ApiContext = createContext<ApiContextType | undefined>(undefined);

interface ApiProviderProps {
  children: ReactNode;
}

export function ApiProvider({ children }: ApiProviderProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [lastHealthCheck, setLastHealthCheck] = useState<Date | null>(null);
  const [serverVersion] = useState("1.3.0");
  const [isLoading, setIsLoading] = useState(true);

  const refreshHealth = useCallback(async () => {
    try {
      setIsLoading(true);
      const response: ApiResponse = await api.getDetailedHealth();

      if (response.success && response.data) {
        setHealthStatus(response.data as HealthStatus);
        setIsConnected(true);
        setLastHealthCheck(new Date());
      } else {
        setIsConnected(false);
        setHealthStatus(null);
      }
    } catch (_error) {
      setIsConnected(false);
      setHealthStatus(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial health check and periodic updates
  useEffect(() => {
    refreshHealth();

    // Check health every 30 seconds
    const interval = setInterval(refreshHealth, 30000);

    return () => clearInterval(interval);
  }, [refreshHealth]);

  const value: ApiContextType = {
    isConnected,
    healthStatus,
    lastHealthCheck,
    serverVersion,
    refreshHealth,
    isLoading,
  };

  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}

export function useApiContext(): ApiContextType {
  const context = useContext(ApiContext);
  if (context === undefined) {
    throw new Error("useApiContext must be used within an ApiProvider");
  }
  return context;
}

// Utility hook for service health
export function useServiceHealth(serviceName: keyof HealthStatus) {
  const { healthStatus } = useApiContext();

  if (!healthStatus) {
    return { healthy: false, status: "unknown" };
  }

  return healthStatus[serviceName];
}

// Utility hook for overall system health
export function useSystemHealth() {
  const { healthStatus } = useApiContext();

  if (!healthStatus) {
    return { healthy: false, totalServices: 0, healthyServices: 0 };
  }

  const services = Object.values(healthStatus);
  const healthyServices = services.filter((service) => service.healthy).length;

  return {
    healthy: healthyServices === services.length,
    totalServices: services.length,
    healthyServices,
  };
}
