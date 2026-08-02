import { useCallback, useState } from "react";
import { type ApiResponse, api, getErrorMessage, isSuccessResponse } from "../api/client";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  success: boolean;
}

interface UseApiReturn<T, A extends unknown[]> extends UseApiState<T> {
  execute: (...args: A) => Promise<void>;
  reset: () => void;
}

/**
 * Custom hook for API operations with loading states
 */
export function useApi<T = unknown, A extends unknown[] = unknown[]>(
  apiFunction: (...args: A) => Promise<ApiResponse<T>>,
  initialData: T | null = null,
): UseApiReturn<T, A> {
  const [state, setState] = useState<UseApiState<T>>({
    data: initialData,
    loading: false,
    error: null,
    success: false,
  });

  const execute = useCallback(
    async (...args: A) => {
      setState((prev) => ({ ...prev, loading: true, error: null, success: false }));

      try {
        const response = await apiFunction(...args);

        if (isSuccessResponse(response)) {
          setState({
            data: (response.data as T | undefined) ?? null,
            loading: false,
            error: null,
            success: true,
          });
        } else {
          setState({
            data: null,
            loading: false,
            error: getErrorMessage(response),
            success: false,
          });
        }
      } catch (error) {
        setState({
          data: null,
          loading: false,
          error: error instanceof Error ? error.message : "An unknown error occurred",
          success: false,
        });
      }
    },
    [apiFunction],
  );

  const reset = useCallback(() => {
    setState({
      data: initialData,
      loading: false,
      error: null,
      success: false,
    });
  }, [initialData]);

  return {
    ...state,
    execute,
    reset,
  };
}

/**
 * Hook for health checking
 */
export function useHealthCheck() {
  return useApi(api.getDetailedHealth);
}

/**
 * Hook for listing available tools
 */
export function useToolsList() {
  return useApi(api.listTools);
}

/**
 * Hook for EmojiBuster operations
 */
export function useEmojiBuster() {
  return useApi(api.runEmojiBuster);
}

/**
 * Hook for PowerShell operations
 */
export function usePowerShell() {
  return useApi(api.runPowerShellTools);
}

/**
 * Hook for Runt Analyzer operations
 */
export function useRuntAnalyzer() {
  return useApi(api.runRuntAnalyzer);
}

/**
 * Hook for repository status
 */
export function useRepoStatus() {
  return useApi(api.getRepoStatus);
}

/**
 * Hook for server discovery
 */
export function useServerDiscovery() {
  return useApi(api.discoverServers);
}

/**
 * Hook for client integration checking
 */
export function useClientIntegration() {
  return useApi(api.checkClientIntegration);
}

/**
 * Hook for project scaffolding
 */
export function useProjectScaffolding() {
  return useApi(api.createProject);
}
