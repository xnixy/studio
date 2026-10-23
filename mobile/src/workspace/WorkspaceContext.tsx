import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import type { Workspace } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { sessionStorage } from "../auth/storage";
import {
  canFetchWorkspaces,
  resolveActiveWorkspaceId,
  workspacesQueryKey,
} from "./resolveWorkspaceId";

/** One personal space per account. Multi-workspace switching is gone. */
type WorkspaceContextValue = {
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  activeWorkspaceId: string | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const qc = useQueryClient();
  const userId = auth.user?.id ?? null;
  const [hydrated, setHydrated] = useState(false);
  const [stored, setStored] = useState<{ userId: string; workspaceId: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    setHydrated(false);
    setStored(null);
    if (!userId) {
      setHydrated(true);
      return;
    }
    void sessionStorage.getWorkspaceBinding().then((binding) => {
      if (cancelled) return;
      setStored(binding?.userId === userId ? binding : null);
      setHydrated(true);
    });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const emailVerified = Boolean(auth.user?.email_verified);
  const query = useQuery({
    // Keyed by user, not by access token. Tokens rotate on every refresh, and a
    // rotating key minted a fresh cache entry each time: activeWorkspaceId went
    // null, every workspace-scoped query (avatars, clips, models, billing) went
    // disabled and blank, and the tab only recovered on a manual pull. Web has
    // always keyed on the user id.
    //
    // Also key by verified. Register issues a session immediately; GET /workspaces
    // 403s until confirm. A failed query on this provider (root, never remounts)
    // used to stick after verify, so Create showed "No workspace".
    queryKey: workspacesQueryKey(userId, emailVerified),
    queryFn: () => api.listWorkspaces(),
    enabled:
      auth.isAuthenticated &&
      canFetchWorkspaces({
        accessToken: auth.accessToken,
        userId,
        emailVerified,
      }),
    staleTime: 30_000,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        return false;
      }
      return failureCount < 1;
    },
  });

  const workspaces = query.data ?? [];
  const activeWorkspace = workspaces[0] ?? null;
  const activeWorkspaceId = resolveActiveWorkspaceId(
    activeWorkspace?.id,
    stored,
    userId,
  );

  useEffect(() => {
    if (!hydrated || !query.isSuccess || !userId) return;
    if (activeWorkspace) {
      const next = { userId, workspaceId: activeWorkspace.id };
      setStored(next);
      void sessionStorage.setWorkspaceId(activeWorkspace.id, userId);
      return;
    }
    setStored(null);
    void sessionStorage.clearWorkspaceId();
  }, [hydrated, query.isSuccess, activeWorkspace, userId]);

  const refresh = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: ["workspaces"] });
  }, [qc]);

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      workspaces,
      activeWorkspace,
      activeWorkspaceId,
      // Last-used id may start Home / Library fetches only when it belongs to
      // this user. A leftover id from the previous account must not.
      isLoading: Boolean(
        emailVerified && !activeWorkspaceId && (!hydrated || query.isPending || query.isFetching),
      ),
      error: query.error instanceof Error ? query.error.message : null,
      refresh,
    }),
    [
      workspaces,
      activeWorkspace,
      activeWorkspaceId,
      emailVerified,
      hydrated,
      query.isPending,
      query.isFetching,
      query.error,
      refresh,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return ctx;
}
