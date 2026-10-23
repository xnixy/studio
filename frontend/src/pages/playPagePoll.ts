/** Poll a Play generation until ready/failed and update the create thread. */
import type { Dispatch, SetStateAction } from "react";
import { api } from "../api";
import type { ThreadItem } from "./playPageModel";

const FAST_ATTEMPTS = 48; // ~2 min at 2.5s
const SLOW_ATTEMPTS = 120; // continue after soft timeout (~extra 10+ min with backoff)
const FAST_MS = 2500;
const SLOW_MS = 5000;

function isTerminal(status: string | undefined | null): boolean {
  const s = (status || "").toLowerCase();
  return s === "ready" || s === "failed" || s === "expired" || s === "error";
}

export async function pollPlayGenerationUntilReady(
  token: string,
  assetId: string,
  setThread: Dispatch<SetStateAction<ThreadItem[]>>,
): Promise<void> {
  let midNudge = false;
  let softTimeoutShown = false;
  const total = FAST_ATTEMPTS + SLOW_ATTEMPTS;

  for (let i = 0; i < total; i++) {
    const delay = i < FAST_ATTEMPTS ? FAST_MS : SLOW_MS;
    await new Promise((r) => setTimeout(r, delay));

    let status = "";
    let url: string | null = null;
    let errorMessage: string | null = null;
    let mapped: Awaited<ReturnType<typeof api.getPlayGeneration>> | null = null;

    // Prefer provider advance, but never skip GET if poll fails (web used to stall forever).
    try {
      await api.pollVideoAsset(token, assetId, { timeoutMs: 90_000 });
    } catch {
      /* worker may own poll; still read DB below */
    }

    try {
      mapped = await api.getPlayGeneration(token, assetId);
      status = (mapped.status || "").toLowerCase();
      url = mapped.url || null;
      errorMessage = mapped.error_message || null;
    } catch {
      continue;
    }

    setThread((prev) => {
      const next = prev.map((item) =>
        item.kind === "gen" && item.generation.id === assetId
          ? {
              ...item,
              generation: {
                ...mapped!,
                status: mapped!.status,
                url: url || mapped!.url || null,
                error_message: errorMessage || mapped!.error_message,
              },
            }
          : item,
      );

      if (status === "ready") {
        const hasDone = next.some((x) => x.kind === "system" && x.id === `s-done-${assetId}`);
        const cleaned = next.filter(
          (x) =>
            !(
              x.kind === "system" &&
              (x.id === `s-wait-${assetId}` ||
                x.id === `s-timeout-${assetId}` ||
                x.id === `s-nudge-${assetId}`)
            ),
        );
        return hasDone
          ? cleaned
          : [
              ...cleaned,
              {
                kind: "system" as const,
                id: `s-done-${assetId}`,
                text: "Ready. Open this clip to edit the prompt or make a new version.",
              },
            ];
      }

      if (status === "failed" || status === "error" || status === "expired") {
        // The card already shows the reason with its own retry actions, so an
        // error bubble underneath just repeated the same sentence.
        return next.filter(
          (x) =>
            !(
              x.kind === "system" &&
              (x.id === `s-wait-${assetId}` ||
                x.id === `s-timeout-${assetId}` ||
                x.id === `s-nudge-${assetId}` ||
                x.id === `s-fail-${assetId}`)
            ),
        );
      }

      if (!midNudge && i >= 4) {
        midNudge = true;
        const hasNudge = next.some((x) => x.kind === "system" && x.id === `s-nudge-${assetId}`);
        if (!hasNudge) {
          return [
            ...next,
            {
              kind: "system" as const,
              id: `s-nudge-${assetId}`,
              text: "Still rendering. Almost there.",
            },
          ];
        }
      }

      if (!softTimeoutShown && i >= FAST_ATTEMPTS - 1) {
        softTimeoutShown = true;
        const hasTimeout = next.some((x) => x.kind === "system" && x.id === `s-timeout-${assetId}`);
        if (!hasTimeout) {
          return [
            ...next,
            {
              kind: "system" as const,
              id: `s-timeout-${assetId}`,
              text: "This is taking longer than usual. Still checking in the background…",
            },
          ];
        }
      }

      return next;
    });

    if (isTerminal(status)) return;
  }

  setThread((prev) => {
    const hasTimeout = prev.some((x) => x.kind === "system" && x.id === `s-timeout-${assetId}`);
    if (hasTimeout) return prev;
    return [
      ...prev,
      {
        kind: "system",
        id: `s-timeout-${assetId}`,
        text: "This is taking longer than usual. Check Library in a minute, or try again.",
      },
    ];
  });
}
