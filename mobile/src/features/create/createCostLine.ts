import type { PlayMode } from "@/src/api/types";
import {
  estimateTalkingDurationSeconds,
} from "./createConstants";

/**
 * Quiet one-line cost copy for the Create composer (no “tok” jargon).
 * Mirrored by frontend/src/features/play/createCostLine.ts. Change both together.
 */
export function createCostLine(opts: {
  mode: PlayMode;
  prompt: string;
  totalCredits: number;
  /** null = Auto length from spoken line (Talking). */
  durationSeconds: number | null;
  /** Snapped Auto seconds for Talking. */
  autoSeconds?: number | null;
  needsDuration: boolean;
  isExtending: boolean;
  isSeedanceModel: boolean;
  /** Seedance 2.5 caps at 720p. */
  isSeedance25?: boolean;
  resolution: string;
  /** False when the engine has one fixed resolution and printing it says nothing. */
  showResolution: boolean;
  generateAudio: boolean;
  batchCount: number;
  hasModel: boolean;
  refsUploading: boolean;
  clonedVoice?: boolean;
  voiceoverSeconds?: number;
}): string {
  const {
    mode,
    prompt,
    totalCredits,
    durationSeconds,
    autoSeconds,
    needsDuration,
    isExtending,
    isSeedanceModel,
    isSeedance25,
    resolution,
    showResolution,
    generateAudio,
    batchCount,
    hasModel,
    refsUploading,
    clonedVoice,
    voiceoverSeconds,
  } = opts;

  const n = Math.max(1, totalCredits);
  const creditWord = n === 1 ? "credit" : "credits";
  const parts: string[] = [];

  if (isExtending) parts.push("Next shot from prior clip");

  if (mode === "avatar" || mode === "lipsync") {
    if (needsDuration) {
      if (durationSeconds == null) {
        const est = autoSeconds ?? estimateTalkingDurationSeconds(prompt);
        parts.push(`Auto ~${est}s`);
      } else {
        parts.push(`${durationSeconds}s`);
      }
    }
    if (isSeedance25) parts.push("720p max");
    parts.push(`Uses ${n} clip ${creditWord}`);
    if (clonedVoice) {
      const vs = Math.max(4, voiceoverSeconds ?? 8);
      parts.push(`+ ~${vs}s voice`);
    }
  } else if (mode === "video") {
    if (needsDuration) {
      parts.push(durationSeconds == null ? "Auto" : `${durationSeconds}s`);
      if (showResolution) parts.push(isSeedance25 ? "720p max" : resolution);
    }
    parts.push(hasModel ? `Uses ${n} clip ${creditWord}` : "");
    if (clonedVoice) {
      const vs = Math.max(4, voiceoverSeconds ?? 8);
      parts.push(`+ ~${vs}s voice`);
    }
  } else if (mode === "image") {
    parts.push(hasModel ? `Uses ${n} still ${creditWord}` : "");
  }

  if (refsUploading) parts.push("uploading references…");

  return parts.filter(Boolean).join(" · ");
}
