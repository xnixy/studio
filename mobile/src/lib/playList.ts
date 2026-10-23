import type { QueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { PlayGeneration } from "../api/types";
import { preserveSignedMediaUrls } from "./media";

export function playGenerationsKey(workspaceId: string | null) {
  return ["play-generations", workspaceId] as const;
}

/** Shared list fetch so Home, Library, and prefetch keep the same signed URLs. */
export async function fetchPlayGenerationsList(qc: QueryClient, workspaceId: string) {
  const next = await api.listPlayGenerations(workspaceId);
  const prev = qc.getQueryData<PlayGeneration[]>(playGenerationsKey(workspaceId));
  return preserveSignedMediaUrls(prev, next);
}
