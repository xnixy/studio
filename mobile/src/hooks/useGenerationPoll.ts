import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { PlayGeneration } from "../api/types";

const TERMINAL = new Set(["ready", "failed", "error", "cancelled", "expired"]);

/** Poll in-flight generations until ready/failed. */
export function useGenerationPoll(
  generations: PlayGeneration[] | undefined,
  workspaceId: string | null,
) {
  const qc = useQueryClient();
  /** Live timers only: id is present while a poll loop is scheduled/running. */
  const activeTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  useEffect(() => {
    if (!workspaceId || !generations?.length) return;

    const pending = generations.filter((g) => !TERMINAL.has((g.status || "").toLowerCase()));
    if (!pending.length) return;

    let cancelled = false;

    const clearTimer = (id: string) => {
      const t = activeTimers.current.get(id);
      if (t) clearTimeout(t);
      activeTimers.current.delete(id);
    };

    const schedule = (id: string, delay: number, fn: () => void) => {
      clearTimer(id);
      const handle = setTimeout(fn, delay);
      activeTimers.current.set(id, handle);
    };

    for (const gen of pending) {
      if (activeTimers.current.has(gen.id)) continue;

      const tick = async (attempt: number) => {
        if (cancelled) {
          clearTimer(gen.id);
          return;
        }
        try {
          const latest = await api.getPlayGeneration(gen.id);
          const status = (latest.status || "").toLowerCase();
          // Patch the list in place so we do not force a full re-sign refresh of every thumb.
          qc.setQueryData<PlayGeneration[]>(["play-generations", workspaceId], (prev) => {
            if (!prev?.length) return prev;
            return prev.map((row) => (row.id === latest.id ? { ...row, ...latest } : row));
          });
          // Only stop on terminal status (not merely a partial URL).
          if (TERMINAL.has(status)) {
            clearTimer(gen.id);
            return;
          }
          try {
            await api.pollVideoAsset(gen.id);
          } catch {
            // ignore poll failures; list refetch still helps
          }
        } catch {
          // keep trying
        }
        if (cancelled) {
          clearTimer(gen.id);
          return;
        }
        if (attempt > 60) {
          clearTimer(gen.id);
          return;
        }
        const delay = Math.min(2500 + attempt * 500, 8000);
        schedule(gen.id, delay, () => void tick(attempt + 1));
      };

      schedule(gen.id, 1500, () => void tick(0));
    }

    return () => {
      cancelled = true;
      // Drop timers so a re-run of the effect can restart polls for still-pending gens.
      for (const id of [...activeTimers.current.keys()]) {
        clearTimer(id);
      }
    };
  }, [generations, workspaceId, qc]);
}
