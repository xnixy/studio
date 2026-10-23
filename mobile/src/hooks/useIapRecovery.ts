import { useEffect, useRef } from "react";
import { AppState, type AppStateStatus, Platform } from "react-native";
import { useQueryClient } from "@tanstack/react-query";
import { processUnfinishedPurchases, setIapWorkspaceId } from "../iap/store";

/**
 * Recover StoreKit purchases left unfinished (app killed mid-confirm).
 * Runs after auth+workspace are ready and again when the app becomes active.
 */
export function useIapRecovery(workspaceId: string | null, isAuthenticated: boolean) {
  const qc = useQueryClient();
  const running = useRef(false);

  useEffect(() => {
    if (Platform.OS !== "ios" || !isAuthenticated || !workspaceId) {
      setIapWorkspaceId(null);
      return;
    }

    setIapWorkspaceId(workspaceId);

    const run = async () => {
      if (running.current) return;
      running.current = true;
      try {
        const n = await processUnfinishedPurchases(workspaceId);
        if (n > 0) {
          await qc.invalidateQueries({ queryKey: ["billing", workspaceId] });
        }
      } finally {
        running.current = false;
      }
    };

    void run();

    const onChange = (state: AppStateStatus) => {
      if (state === "active") void run();
    };
    const sub = AppState.addEventListener("change", onChange);
    return () => sub.remove();
  }, [workspaceId, isAuthenticated, qc]);
}
