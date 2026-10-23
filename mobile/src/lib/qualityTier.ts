/** Quality lanes for Create: Fast (Seedance 2.0 Fast) vs 2.5. */

export type QualityTier = "fast" | "advanced";

/** Providers that can continue / extend a prior clip. */
export function supportsPlayExtend(provider: string | undefined | null): boolean {
  const p = (provider || "").toLowerCase();
  return p === "seedance";
}

type ExtendSource = { provider?: string | null; model_id?: string | null };

/**
 * Keep the engine that made the clip. Forcing Advanced used to drop Grok
 * (Fast) and land on Seedance even when Grok can extend natively.
 */
export function pickExtendModel<T extends TierModel>(
  models: readonly T[],
  source?: ExtendSource | null,
): T | null {
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
export function modelSupportsFaceReference(model: {
  id: string;
  supports_face_reference?: boolean;
} | null | undefined): boolean {
  if (!model) return true;
  if (typeof model.supports_face_reference === "boolean") {
    return model.supports_face_reference;
  }
  return true;
}

/** Plain notice when a model change clears the selected face. */
export function faceClearedForModelMessage(modelLabel: string | undefined | null): string {
  const name = (modelLabel || "This model").trim() || "This model";
  return `${name} cannot use a face in Video mode. Face cleared. Pick another model to keep a face.`;
}

export type TierModel = {
  id: string;
  label: string;
  token_cost: number;
  default?: boolean;
  provider?: string;
  max_duration_seconds?: number | null;
  blurb?: string;
  lane?: "fast" | "advanced";
  locked?: boolean;
  requires_plan?: string | null;
};

export const QUALITY_TIERS: readonly {
  id: QualityTier;
  label: string;
  blurb: string;
}[] = [
  { id: "fast", label: "Fast", blurb: "Seedance Fast. Quick drafts." },
  { id: "advanced", label: "2.5", blurb: "Seedance 2.5. Up to 30s at 720p." },
] as const;

function byCostThenLabel(a: TierModel, b: TierModel): number {
  const cost = (a.token_cost ?? 1) - (b.token_cost ?? 1);
  if (cost !== 0) return cost;
  return a.label.localeCompare(b.label);
}

export function isFastLaneModel(model: TierModel): boolean {
  if (model.lane) return model.lane === "fast";
  const id = (model.id || "").toLowerCase();
  if (id.includes("fast") || id.includes("mini")) return true;
  return (model.provider || "").toLowerCase() === "xai";
}

export function pickFastModel<T extends TierModel>(models: readonly T[]): T | null {
  if (!models.length) return null;
  const grok = models.filter(isFastLaneModel).sort(byCostThenLabel);
  if (grok.length) return grok.find((m) => m.default) || grok[0] || null;
  return [...models].sort(byCostThenLabel)[0] ?? null;
}

export function advancedModelPool<T extends TierModel>(models: readonly T[]): T[] {
  if (!models.length) return [];
  const fast = pickFastModel(models);
  const rest = models.filter((m) => m.id !== fast?.id);
  if (!rest.length) return [...models].sort(byCostThenLabel);
  return rest.sort(byCostThenLabel);
}

export function pickAdvancedDefault<T extends TierModel>(models: readonly T[]): T | null {
  const pool = advancedModelPool(models);
  if (!pool.length) return pickFastModel(models);
  const preferredIds = [
    "seedance-2-5",
    "seedance-avatar",
    "seedance-photo",
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

export function pickModelForTier<T extends TierModel>(
  models: readonly T[],
  tier: QualityTier,
  preferredAdvancedId?: string | null,
): T | null {
  if (!models.length) return null;
  if (tier === "fast") return pickFastModel(models);
  const pool = advancedModelPool(models);
  if (preferredAdvancedId) {
    const pinned = pool.find((m) => m.id === preferredAdvancedId);
    if (pinned) return pinned;
  }
  return pickAdvancedDefault(models);
}

export function tierForModel<T extends TierModel>(
  models: readonly T[],
  modelId: string | undefined | null,
): QualityTier {
  if (!modelId || !models.length) return "fast";
  const fast = pickFastModel(models);
  if (fast && modelId === fast.id) return "fast";
  return "advanced";
}
