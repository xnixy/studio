/** Pure helpers and constants for the Create / Play page (no JSX). */
import type {
  PlayAssistOptions,
  PlayGeneration,
  PlayMode,
  PlayModelOption,
  PlayPlatform,
} from "../types";

/**
 * Create quality lanes:
 * - Fast = Seedance 2.0 Fast (default).
 * - Advanced = Seedance 2.5.
 */
export type QualityTier = "fast" | "advanced";

/** Providers that can continue / extend a prior clip in Play. */
export function supportsPlayExtend(provider: string | undefined | null): boolean {
  const p = (provider || "").toLowerCase();
  return p === "seedance";
}

type ExtendSource = { provider?: string | null; model_id?: string | null };

/**
 * Keep the engine that made the clip. Forcing Advanced used to drop Grok
 * (Fast) and land on Seedance even when Grok can extend natively.
 */
export function pickExtendModel(
  models: readonly PlayModelOption[],
  source?: ExtendSource | null,
): PlayModelOption | null {
  const pool = models.filter((m) => supportsPlayExtend(m.provider));
  if (!pool.length) return null;
  if (source?.model_id) {
    const exact = pool.find((m) => m.id === source.model_id);
    if (exact) return exact;
  }
  const p = (source?.provider || "").toLowerCase();
  if (p && supportsPlayExtend(p)) {
    const same = pool.find((m) => (m.provider || "").toLowerCase() === p);
    if (same) return same;
  }
  return (
    pool.find((m) => (m.provider || "").toLowerCase() === "seedance") ||
    pool[0] ||
    null
  );
}

/**
 * Whether a Video-mode model can take a face plate as identity.
 * Clip catalog is Seedance only; all of them take a face.
 */
export function modelSupportsFaceReference(
  model: Pick<PlayModelOption, "id" | "supports_face_reference"> | null | undefined,
): boolean {
  if (!model) return true;
  if (typeof model.supports_face_reference === "boolean") {
    return model.supports_face_reference;
  }
  return true;
}

/** Plain notice when a model change clears the selected face. */
export function faceClearedForModelMessage(modelLabel: string | undefined | null): string {
  const name = (modelLabel || "This model").trim() || "This model";
  return `${name} cannot use a face in Video mode. Avatar cleared. Pick another model to keep a face.`;
}

export const QUALITY_TIERS: readonly {
  id: QualityTier;
  label: string;
  blurb: string;
}[] = [
  { id: "fast", label: "Fast", blurb: "Seedance Fast. Quick 15s takes." },
  { id: "advanced", label: "2.5", blurb: "Seedance 2.5. Up to 30s at 720p." },
] as const;

function byCostThenLabel(a: PlayModelOption, b: PlayModelOption): number {
  const cost = (a.token_cost ?? 1) - (b.token_cost ?? 1);
  if (cost !== 0) return cost;
  return a.label.localeCompare(b.label);
}

/** True when this catalog row is the Fast lane (Seedance Fast, Grok stills). */
export function isFastLaneModel(model: PlayModelOption): boolean {
  if (model.lane) return model.lane === "fast";
  const id = (model.id || "").toLowerCase();
  if (id.includes("fast") || id.includes("mini")) return true;
  return (model.provider || "").toLowerCase() === "xai";
}

/** Grok (or cheapest fallback if Grok is missing from the pool). */
export function pickFastModel(models: readonly PlayModelOption[]): PlayModelOption | null {
  if (!models.length) return null;
  const grok = models.filter(isFastLaneModel).sort(byCostThenLabel);
  if (grok.length) {
    // Prefer a model marked default among Grok, else the cheapest Grok SKU.
    return grok.find((m) => m.default) || grok[0] || null;
  }
  return [...models].sort(byCostThenLabel)[0] ?? null;
}

/**
 * Engines shown only in Advanced (everything that is not the Fast Grok pick).
 * A Grok-only pool (extend from Fast) stays Fast; do not treat it as Advanced.
 */
export function advancedModelPool(models: readonly PlayModelOption[]): PlayModelOption[] {
  if (!models.length) return [];
  const fast = pickFastModel(models);
  const rest = models.filter((m) => m.id !== fast?.id);
  // Extend / single-provider pools: nothing left after removing Grok → use full pool.
  if (!rest.length) return [...models].sort(byCostThenLabel);
  return rest.sort(byCostThenLabel);
}

/** Default Advanced engine: Seedance flagship when present, else highest cost. */
export function pickAdvancedDefault(models: readonly PlayModelOption[]): PlayModelOption | null {
  const pool = advancedModelPool(models);
  if (!pool.length) return pickFastModel(models);
  const preferredIds = [
    "seedance-2-5",
    "seedance-avatar",
    "xai-image-quality",
    "nano-banana-pro",
  ];
  for (const id of preferredIds) {
    const hit = pool.find((m) => m.id === id);
    if (hit) return hit;
  }
  const marked = pool.find((m) => m.default);
  if (marked) return marked;
  return [...pool].sort((a, b) => (b.token_cost ?? 1) - (a.token_cost ?? 1))[0] ?? null;
}

/** Resolve the concrete model for the active quality lane. */
export function pickModelForTier(
  models: readonly PlayModelOption[],
  tier: QualityTier,
  preferredAdvancedId?: string | null,
): PlayModelOption | null {
  if (!models.length) return null;
  if (tier === "fast") return pickFastModel(models);
  const pool = advancedModelPool(models);
  if (preferredAdvancedId) {
    const pinned = pool.find((m) => m.id === preferredAdvancedId);
    if (pinned) return pinned;
  }
  return pickAdvancedDefault(models);
}

/** Infer lane from a model id (Fast Grok pick → Fast, anything else → Advanced). */
export function tierForModel(
  models: readonly PlayModelOption[],
  modelId: string | undefined | null,
): QualityTier {
  if (!modelId || !models.length) return "fast";
  const fast = pickFastModel(models);
  if (fast && modelId === fast.id) return "fast";
  // Extend pools (Seedance-only) and every non-Fast pick live under Advanced.
  return "advanced";
}

/** Short footer line for the active model. */
export function modelSummaryLine(model: PlayModelOption | null | undefined): string {
  if (!model) return "";
  const tok = model.token_cost ?? 1;
  const max = model.max_duration_seconds;
  const parts = [model.label, `${tok} credit${tok === 1 ? "" : "s"}`];
  if (typeof max === "number" && max > 0) parts.push(`up to ${max}s`);
  return parts.join(" · ");
}

export const FACE_STORAGE_KEY = "studio-active-face";
export const VOICE_STORAGE_KEY = "studio-active-voice";

/** Default length chips. Provider-specific lists are filtered in the page. */
export const DURATION_OPTIONS = [4, 5, 6, 8, 10, 12, 15] as const;
/** Veo (Gemini) only accepts these lengths. */
export const VEO_DURATION_OPTIONS = [4, 6, 8] as const;
/** Seedance 2.0 is 15s; 2.5 video is 30s. Talking Seedance stays 15s via maxDuration. */
export const SEEDANCE_DURATION_OPTIONS = [4, 5, 6, 8, 10, 12, 15, 20, 25, 30] as const;
/** Grok video: continuous seconds; product chips match common lengths. */
export const GROK_DURATION_OPTIONS = [5, 8, 10, 12, 15] as const;
/** Kling v3: 3 to 15s. Older Kling (2.6) snaps to 5/10 on the server. */
export const KLING_DURATION_OPTIONS = [5, 6, 8, 10, 12, 15] as const;
export const RESOLUTION_OPTIONS = ["480p", "720p", "1080p", "4k"] as const;

/** Seedance 2.5 catalog ids (Talking / Scene) cap at 720p. */
export function isSeedance25Model(modelId?: string | null): boolean {
  const id = (modelId || "").toLowerCase();
  return (
    id === "seedance-2-5" ||
    id === "seedance-avatar" ||
    id === "seedance-photo" ||
    id.includes("2-5") ||
    id.includes("2.5")
  );
}

/** Snap a length to a provider's allowed discrete chips. Ties round up. */
export function snapDurationToChoices(seconds: number, choices: readonly number[]): number {
  if (!choices.length) return seconds;
  return choices.reduce((best, choice) => {
    const d = Math.abs(choice - seconds);
    const bestD = Math.abs(best - seconds);
    return d < bestD || (d === bestD && choice > best) ? choice : best;
  });
}

/** Length options the selected provider will actually honor. */
export function durationOptionsForProvider(
  provider: string | undefined | null,
  opts?: { modelId?: string | null; maxDuration?: number | null },
): readonly number[] {
  const p = (provider || "").toLowerCase();
  if (p === "gemini") return VEO_DURATION_OPTIONS;
  if (p === "seedance") {
    const max = opts?.maxDuration ?? 15;
    return SEEDANCE_DURATION_OPTIONS.filter((d) => d <= max);
  }
  if (p === "xai") return GROK_DURATION_OPTIONS;
  if (p === "kling") {
    const mid = (opts?.modelId || "").toLowerCase();
    // Kling 2.x classic endpoints only accept 5 or 10 seconds.
    if (mid.includes("v2-6") || mid.includes("v2.6") || mid.includes("v1")) {
      return [5, 10] as const;
    }
    const max = opts?.maxDuration ?? 15;
    return KLING_DURATION_OPTIONS.filter((d) => d <= max);
  }
  return DURATION_OPTIONS;
}

export function resolutionOptionsForProvider(
  provider: string | undefined | null,
  opts?: { modelId?: string | null },
): readonly string[] {
  const p = (provider || "").toLowerCase();
  if (p === "seedance") {
    if (isSeedance25Model(opts?.modelId)) return ["480p", "720p"] as const;
    return RESOLUTION_OPTIONS;
  }
  if (p === "gemini" || p === "kling") return ["720p", "1080p"] as const;
  if (p === "xai") return ["480p", "720p"] as const;
  return ["720p"] as const;
}

export function parseMode(raw: string | null): PlayMode | null {
  if (raw === "lipsync") return "avatar";
  if (raw === "avatar" || raw === "video" || raw === "image") return raw;
  return null;
}

/** Talking / Scene / Still for Create. Old Photo rows are Talking. */
export function clipModality(mode: string | null | undefined): PlayMode {
  if (mode === "image") return "image";
  if (mode === "avatar" || mode === "lipsync") return "avatar";
  return "video";
}

export type ThreadItem =
  | { kind: "user"; id: string; text: string; mode: PlayMode; platform: PlayPlatform }
  | { kind: "system"; id: string; text: string; tone?: "chat" | "error" }
  /** Waiting on the pre-flight. Replaced by its reply, so it is never left behind. */
  | { kind: "thinking"; id: string }
  /**
   * What is about to be generated, laid out to be read rather than filled in.
   * The line lives here and nowhere else, so there is one place to check it.
   */
  | {
      kind: "draft";
      id: string;
      line: string;
      scene: string;
      summary: string[];
      options?: PlayAssistOptions | null;
    }
  | { kind: "gen"; id: string; generation: PlayGeneration; note?: string | null };
