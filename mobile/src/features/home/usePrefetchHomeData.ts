import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api/client";
import { fetchPlayGenerationsList, playGenerationsKey } from "@/src/lib/playList";

/** Warm Home / Library / Faces caches as soon as the workspace id exists. */
export function usePrefetchHomeData(workspaceId: string | null, enabled: boolean) {
  const qc = useQueryClient();

  useEffect(() => {
    if (!enabled || !workspaceId) return;
    void qc.prefetchQuery({
      queryKey: playGenerationsKey(workspaceId),
      queryFn: () => fetchPlayGenerationsList(qc, workspaceId),
      staleTime: 60_000,
    });
    void qc.prefetchQuery({
      queryKey: ["play-faces", workspaceId],
      queryFn: () => api.listPlayFaces(workspaceId),
      staleTime: 60_000,
    });
    void qc.prefetchQuery({
      queryKey: ["billing", workspaceId],
      queryFn: () => api.billingStatus(workspaceId),
      staleTime: 60_000,
    });
  }, [enabled, qc, workspaceId]);
}
