/**
 * Create quality lanes: Fast (Grok, default) vs Advanced (engine picker).
 * Advanced is locked on free plans with an upgrade CTA.
 */
import { useMemo } from "react";
import { Link } from "react-router-dom";
import type { PlayModelOption } from "../../types";
import { cn } from "../../lib/cn";
import {
  QUALITY_TIERS,
  advancedModelPool,
  modelSummaryLine,
  pickAdvancedDefault,
  pickFastModel,
  pickModelForTier,
  type QualityTier,
} from "../../pages/playPageModel";

type Props = {
  models: readonly PlayModelOption[];
  modelId: string;
  qualityTier: QualityTier;
  onTierChange: (tier: QualityTier) => void;
  onModelChange: (modelId: string) => void;
  /** When false, Advanced shows lock + upgrade (free plan). */
  advancedUnlocked?: boolean;
  onAdvancedLocked?: () => void;
  className?: string;
};

export function ModelQualityPicker({
  models,
  modelId,
  qualityTier,
  onTierChange,
  onModelChange,
  advancedUnlocked = true,
  onAdvancedLocked,
  className,
}: Props) {
  const fastModel = useMemo(() => pickFastModel(models), [models]);
  const advancedPool = useMemo(() => advancedModelPool(models), [models]);
  const hasAdvancedChoice =
    advancedPool.length > 0 && Boolean(fastModel) && advancedPool.some((m) => m.id !== fastModel?.id);

  const active = useMemo(() => {
    return (
      models.find((x) => x.id === modelId) ||
      pickModelForTier(models, qualityTier, modelId) ||
      models[0] ||
      null
    );
  }, [models, modelId, qualityTier]);

  const summary = modelSummaryLine(active);
  const blurb = QUALITY_TIERS.find((t) => t.id === qualityTier)?.blurb ?? "";

  if (!models.length) return null;

  // Single catalog entry (e.g. lip-sync only): no quality switcher.
  if (models.length === 1 || !hasAdvancedChoice) {
    return (
      <div className={cn("grid gap-1", className)}>
        <p className="m-0 text-[0.72rem] font-bold uppercase tracking-wide text-[var(--studio-fg-subtle)]">
          Model
        </p>
        <p className="m-0 text-[0.8rem] text-[var(--studio-fg-muted)]">{summary || models[0]?.label}</p>
      </div>
    );
  }

  return (
    <div className={cn("grid gap-1.5", className)}>
      <p className="m-0 text-[0.72rem] font-bold uppercase tracking-wide text-[var(--studio-fg-subtle)]">
        Quality
      </p>

      <div
        className="inline-flex max-w-full flex-wrap gap-1 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-1"
        role="radiogroup"
        aria-label="Quality"
      >
        {QUALITY_TIERS.map((tier) => {
          const locked = tier.id === "advanced" && !advancedUnlocked;
          const pick = tier.id === "fast" ? fastModel : pickAdvancedDefault(models);
          const on = qualityTier === tier.id && !locked;
          return (
            <button
              key={tier.id}
              type="button"
              role="radio"
              aria-checked={on}
              title={locked ? "Upgrade to Starter to unlock Advanced engines" : tier.blurb}
              disabled={!pick && !locked}
              className={cn(
                "min-h-10 min-w-[5.5rem] flex-1 rounded-xl border px-3 py-2 text-sm font-semibold transition-colors",
                on
                  ? "border-[var(--studio-brand)] bg-[var(--studio-chip-on,var(--studio-fill))] text-[var(--studio-brand)]"
                  : "border-transparent text-[var(--studio-fg-muted)] hover:text-[var(--studio-fg)]",
                locked && "opacity-75",
              )}
              onClick={() => {
                if (locked) {
                  onAdvancedLocked?.();
                  return;
                }
                onTierChange(tier.id);
              }}
            >
              <span className="block leading-tight">
                {tier.label}
                {locked ? " · Starter" : ""}
              </span>
              <span
                className={cn(
                  "mt-0.5 block text-[0.68rem] font-medium leading-tight",
                  on ? "text-[var(--studio-brand)] opacity-80" : "text-[var(--studio-fg-subtle)]",
                )}
              >
                {tier.id === "fast" ? "Grok" : locked ? "Upgrade" : "Pick engine"}
              </span>
            </button>
          );
        })}
      </div>

      <p className="m-0 text-[0.75rem] text-[var(--studio-fg-muted)]">
        {!advancedUnlocked
          ? "Free includes Grok Fast stills. Upgrade for Nano Banana."
          : blurb}
        {advancedUnlocked && summary ? ` · ${summary}` : ""}
      </p>

      {!advancedUnlocked ? (
        <p className="m-0 text-[0.8rem]">
          <Link className="font-semibold text-[var(--studio-brand)] no-underline hover:underline" to="/billing">
            Upgrade to Starter
          </Link>
          <span className="text-[var(--studio-fg-muted)]"> to unlock Advanced models.</span>
        </p>
      ) : null}

      {qualityTier === "advanced" && advancedUnlocked ? (
        <div className="grid gap-1.5 pt-0.5">
          <p className="m-0 text-[0.72rem] font-bold uppercase tracking-wide text-[var(--studio-fg-subtle)]">
            Engine
          </p>
          <div className="flex flex-wrap gap-1.5" role="listbox" aria-label="Engine">
            {advancedPool.map((m) => {
              const on = m.id === modelId;
              return (
                <button
                  key={m.id}
                  type="button"
                  role="option"
                  aria-selected={on}
                  title={m.blurb}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-[0.78rem] font-semibold transition-colors",
                    on
                      ? "border-[var(--studio-brand)] bg-[var(--studio-chip-on,var(--studio-fill))] text-[var(--studio-brand)]"
                      : "border-transparent bg-[var(--studio-chip-off,var(--studio-fill-quiet))] text-[var(--studio-fg-muted)] hover:text-[var(--studio-fg)]",
                  )}
                  onClick={() => onModelChange(m.id)}
                >
                  {m.label}
                  {m.token_cost > 1 ? ` · ${m.token_cost}` : ""}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
