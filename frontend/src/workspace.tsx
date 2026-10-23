import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "./api";
import { useAuth } from "./auth";
import { canFetchWorkspaces, workspacesQueryKey } from "./lib/accountSession";
import type { Workspace } from "./types";

/**
 * Single personal space per user.
 * Multi-workspace / team switching was removed; this still holds workspace_id for billing & media.
 */
interface WorkspaceContextValue {
  /** Always 0 or 1 entry in the solo product. */
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  activeWorkspaceId: string | null;
  loading: boolean;
  error: string | null;
  can: (permission: string) => boolean;
  refresh: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const userId = auth.user?.id ?? null;
  const emailVerified = Boolean(auth.user?.email_verified);
  const query = useQuery({
    // Key by verified. Register issues a session immediately; GET /workspaces
    // 403s until confirm. A failed query on this provider used to stick after
    // verify, so Create sat on "Account is still loading".
    queryKey: workspacesQueryKey(userId, emailVerified),
    queryFn: () => api.listWorkspaces(auth.accessToken!),
    enabled: canFetchWorkspaces({
      accessToken: auth.accessToken,
      userId,
      emailVerified,
    }),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        return false;
      }
      return failureCount < 2;
    },
  });
  const workspaces = query.data || [];
  // Solo: always the first (and only) personal workspace.
  const activeWorkspace = workspaces[0] || null;

  useEffect(() => {
    if (!activeWorkspace) return;
    try {
      if (!auth.user?.id) return;
      localStorage.setItem(`studio-workspace:${auth.user.id}`, activeWorkspace.id);
    } catch {
      /* ignore quota / private mode */
    }
  }, [activeWorkspace, auth.user]);

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      workspaces,
      activeWorkspace,
      activeWorkspaceId: activeWorkspace?.id || null,
      loading: Boolean(
        emailVerified && !activeWorkspace && (query.isLoading || query.isFetching),
      ),
      error: query.error instanceof Error ? query.error.message : null,
      can: (permission) => {
        if (!activeWorkspace) return false;
        if (activeWorkspace.permissions?.includes(permission)) return true;
        // Personal space owner has full access.
        if (activeWorkspace.role === "owner") return true;
        return false;
      },
      refresh: async () => {
        await queryClient.invalidateQueries({ queryKey: ["workspaces", "workspaces"] });
      },
    }),
    [
      activeWorkspace,
      emailVerified,
      query.error,
      query.isFetching,
      query.isLoading,
      queryClient,
      workspaces,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used inside WorkspaceProvider");
  }
  return context;
}
