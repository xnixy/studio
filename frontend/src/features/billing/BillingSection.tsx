import {
  CreditCard,
  Image as ImageIcon,
  Sparkles,
  Video,
} from "lucide-react";
import type { ReactNode } from "react";
import { Body1, Caption1, Subtitle2 } from "../../ui/Text";
import { cn } from "../../lib/cn";
import type {
  AddOnType,
  BillingCreditGrant,
  BillingStatus,
  CreditPack,
  CreditPackName,
  PlanName,
  UsageEvent,
} from "../../types";
import {
  Badge,
  Button,
  MessageBar,
  StatCard,
} from "../../ui";

const RECURRING_ADDON_LABELS: Partial<Record<AddOnType, string>> = {
  video_credits: "Clip credits (+5 / mo)",
  image_generations: "Still credits (+3 / mo)",
  avatar_lipsyncs: "Clip credits (+5 / mo)",
  script_generations: "Scripts (+1 / mo)",
  voiceover_minutes: "Voice minutes (+1 min / mo)",
  storage_gb: "Storage (+1 GB)",
  priority_rendering: "Priority rendering",
};

const EVENT_LABELS: Record<string, string> = {
  play_avatar: "Clip",
  play_video: "Clip",
  play_still: "Still",
  play_face: "Face generate",
  play_lipsync: "Clip",
  video_generation: "Video (legacy)",
  image_generation: "Image (legacy)",
  avatar_lipsync: "Clip (legacy)",
  voiceover_seconds: "Voice seconds",
  script_generation: "Script",
};

const styles = {
  root: "mx-auto grid w-full max-w-[72rem] min-w-0 gap-6",
  hero: cn(
    "grid gap-4 rounded-2xl border border-[var(--studio-border)] px-4 py-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-x-8 sm:px-5",
    "bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
    "shadow-[var(--studio-card-shadow)]",
  ),
  heroCopy: "grid min-w-0 gap-2",
  heroEyebrow: "m-0 text-[0.72rem] font-bold uppercase tracking-wider text-[var(--studio-brand)]",
  heroTitleRow: "flex min-w-0 flex-wrap items-center gap-2",
  heroTitle: "m-0 text-xl font-bold tracking-tight text-[var(--studio-fg)] sm:text-2xl",
  heroPrice: "m-0 text-base font-semibold tabular-nums text-[var(--studio-fg)]",
  heroMeta: "m-0 text-[0.8rem] leading-snug text-[var(--studio-fg-muted)]",
  heroActions: "flex shrink-0 flex-wrap items-center gap-2 sm:justify-end",
  metrics: "grid grid-cols-2 gap-3 sm:grid-cols-4",
  twoCol: "grid gap-4 lg:grid-cols-2 lg:items-start",
  block: cn(
    "grid min-w-0 gap-4 rounded-2xl border border-[var(--studio-border)] px-4 py-4 sm:px-5",
    "bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
    "shadow-[var(--studio-card-shadow)]",
  ),
  blockHead: "grid gap-1",
  blockTitle: "m-0",
  blockLead: "m-0 text-[0.8rem] leading-snug text-[var(--studio-fg-muted)]",
  meterList: "grid gap-4 sm:grid-cols-2",
  meter: "grid gap-1.5",
  meterTop: "flex items-baseline justify-between gap-2.5",
  meterLabel: "m-0 text-sm font-semibold text-[var(--studio-fg)]",
  meterValue: "m-0 whitespace-nowrap text-[0.8rem] tabular-nums text-[var(--studio-fg-subtle)]",
  packList: "grid gap-2",
  packRow: cn(
    "grid gap-2 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-soft)] px-3.5 py-3",
    "sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center",
  ),
  packCopy: "grid min-w-0 gap-0.5",
  packName: "m-0 font-semibold text-[var(--studio-fg)]",
  packDesc: "m-0 text-[0.8rem] leading-snug text-[var(--studio-fg-subtle)]",
  packPrice: "m-0 font-bold tabular-nums text-[var(--studio-fg)]",
  planGrid: "grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4",
  planCard: cn(
    "flex h-full min-w-0 flex-col gap-3 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-fill-soft)] p-4",
    "transition-[border-color,box-shadow] duration-150 ease-out",
  ),
  planCardCurrent:
    "border-[var(--studio-brand)] bg-[var(--studio-fill)] shadow-[inset_0_0_0_1px_var(--studio-brand)]",
  planHead: "flex items-start justify-between gap-2",
  planName: "m-0 text-base font-bold text-[var(--studio-fg)]",
  planPrice: "m-0 text-2xl font-bold tracking-tight tabular-nums text-[var(--studio-fg)]",
  planUnit: "text-[0.8rem] font-normal text-[var(--studio-fg-subtle)]",
  planFacts: "m-0 grid list-none gap-1.5 p-0",
  planFact: "flex justify-between gap-2 text-[0.8rem] text-[var(--studio-fg-subtle)]",
  planFactValue: "font-semibold tabular-nums text-[var(--studio-fg)]",
  planCta: "mt-auto w-full",
  list: "m-0 grid list-none gap-2 p-0",
  listItem: cn(
    "flex flex-wrap items-center justify-between gap-2.5 rounded-xl border border-[var(--studio-border)]",
    "bg-[var(--studio-fill-soft)] px-3 py-2.5",
  ),
  listMain: "grid min-w-0 gap-0.5",
  tableWrap: "w-full overflow-x-auto rounded-xl border border-[var(--studio-border)]",
  table: "w-full border-collapse text-[0.8rem]",
  th: "border-b border-[var(--studio-border)] bg-[var(--studio-fill-soft)] px-3 py-2.5 text-left font-semibold text-[var(--studio-fg-subtle)]",
  td: "border-b border-[var(--studio-border)] px-3 py-2.5 align-top text-[var(--studio-fg)]",
  empty: "m-0 text-sm text-[var(--studio-fg-subtle)]",
  center: "grid justify-items-start gap-2.5 py-3",
  boostNote: "m-0 rounded-lg border border-[var(--studio-border)] bg-[var(--studio-fill-soft)] px-3 py-2 text-[0.8rem] text-[var(--studio-fg-muted)]",
} as const;

function meterColor(used: number, max: number): "brand" | "warning" | "error" {
  const pct = used / Math.max(1, max);
  if (pct >= 0.95) return "error";
  if (pct >= 0.8) return "warning";
  return "brand";
}

function UsageRow({
  label,
  used,
  max,
  remainingLabel,
}: {
  label: string;
  used: number;
  max: number;
  remainingLabel: string;
}) {
  const s = styles;
  const cap = Math.max(1, max);
  const value = Math.min(used, cap);
  const tone = meterColor(used, cap);
  return (
    <div className={s.meter}>
      <div className={s.meterTop}>
        <p className={s.meterLabel}>{label}</p>
        <p className={s.meterValue}>
          {used} / {max} · {remainingLabel}
        </p>
      </div>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--studio-fill-soft)]"
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={cap}
        aria-label={label}
      >
        <div
          className={
            tone === "error"
              ? "h-full rounded-full bg-[var(--color-danger)] transition-[width]"
              : tone === "warning"
                ? "h-full rounded-full bg-[var(--color-warning)] transition-[width]"
                : "h-full rounded-full bg-[var(--studio-brand)] transition-[width]"
          }
          style={{ width: `${(value / cap) * 100}%` }}
        />
      </div>
    </div>
  );
}

function Block({
  title,
  lead,
  children,
  className,
}: {
  title: string;
  lead?: string;
  children: ReactNode;
  className?: string;
}) {
  const s = styles;
  return (
    <section className={cn(s.block, className)}>
      <header className={s.blockHead}>
        <Subtitle2 as="h3" className={s.blockTitle}>
          {title}
        </Subtitle2>
        {lead ? <p className={s.blockLead}>{lead}</p> : null}
      </header>
      {children}
    </section>
  );
}

function pool(used: number, remaining: number) {
  const u = Math.max(0, used);
  const r = Math.max(0, remaining);
  return { used: u, remaining: r, max: Math.max(0, u + r) };
}

function eventLabel(eventType: string): string {
  return EVENT_LABELS[eventType] || eventType.replace(/_/g, " ");
}

export function BillingSection({
  billing,
  billingLoading,
  billingError,
  onRetryBilling,
  usage,
  packs,
  grants,
  addons,
  canManage,
  busy,
  onCheckout,
  onPortal,
  onBuyPack,
  onCancelAddon,
  addonError,
}: {
  billing: BillingStatus | null;
  billingLoading: boolean;
  billingError: string | null;
  onRetryBilling: () => void;
  usage: UsageEvent[];
  packs: CreditPack[];
  grants: BillingCreditGrant[];
  addons: { id: string; addon_type: AddOnType; quantity: number; monthly_total_cents: number; status: string }[];
  canManage: boolean;
  busy: boolean;
  onCheckout: (plan: PlanName) => void;
  onPortal: () => void;
  onBuyPack: (pack: CreditPackName) => void;
  onCancelAddon: (type: AddOnType) => void;
  addonError?: string | null;
}) {
  if (billingError) {
    return (
      <div className={styles.center}>
        <MessageBar intent="error">{billingError}</MessageBar>
        <Button size="small" type="button" onClick={onRetryBilling}>
          Retry loading billing
        </Button>
      </div>
    );
  }

  if (!billing) {
    return (
      <div className={styles.center}>
        <Body1 className={styles.empty}>
          {billingLoading ? "Loading billing…" : "Couldn’t load billing right now."}
        </Body1>
        {!billingLoading ? (
          <Button size="small" type="button" onClick={onRetryBilling}>
            Retry
          </Button>
        ) : null}
      </div>
    );
  }

  const catalog = billing.plans || [];
  const current =
    catalog.find((plan) => plan.name === billing.plan) ||
    catalog.find((plan) => plan.name === "free") ||
    catalog[0];
  if (!current) {
    return <Body1 className={styles.empty}>No plans available.</Body1>;
  }

  // Prefer the combined Clip pool; older APIs still send play_* or video_generations.
  const clip = pool(
    billing.play_clip_used ?? billing.play_avatar_used ?? billing.video_generations_used ?? 0,
    billing.play_clip_remaining ?? billing.play_avatar_remaining ?? billing.video_generations_remaining ?? 0,
  );
  const stills = pool(
    billing.play_still_used ?? billing.image_generations_used ?? 0,
    billing.play_still_remaining ?? billing.image_generations_remaining ?? 0,
  );
  const faces = pool(billing.play_face_used ?? 0, billing.play_face_remaining ?? 0);
  const voiceUsedMin = Math.round(billing.voiceover_seconds_used / 60);
  const voiceRemainingMin = Math.round(billing.voiceover_seconds_remaining / 60);
  const voiceMaxMin = Math.max(0, voiceUsedMin + voiceRemainingMin);

  const paidPlan = billing.plan !== "free";
  const activeAddons = addons.filter((a) => a.status === "active");
  const periodEnd = new Date(billing.period_end).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const priceLabel =
    current.price_monthly > 0 ? `$${current.price_monthly / 100}/mo` : "$0/mo";
  const statusLabel = billing.cancel_at_period_end
    ? "Cancels at period end"
    : billing.status.replace(/_/g, " ");
  const metaBits = [
    statusLabel,
    billing.cancel_at_period_end ? null : `Resets ${periodEnd}`,
    !billing.stripe_configured ? "Stripe not configured" : null,
  ].filter(Boolean);
  const upgradeTarget = billing.suggested_upgrade || "starter";
  const extrasActive = activeAddons.length > 0 || grants.length > 0;

  return (
    <div className={styles.root}>
      <section className={styles.hero} aria-label="Current plan">
        <div className={styles.heroCopy}>
          <p className={styles.heroEyebrow}>Current plan</p>
          <div className={styles.heroTitleRow}>
            <h2 className={styles.heroTitle}>{current.label}</h2>
            <Badge appearance="filled" color="brand" size="small">
              {billing.plan === current.name ? "Active" : billing.plan}
            </Badge>
          </div>
          <p className={styles.heroPrice}>{priceLabel}</p>
          <p className={styles.heroMeta}>{metaBits.join(" · ")}</p>
        </div>
        <div className={styles.heroActions}>
          {canManage ? (
            <>
              {billing.plan !== "studio" ? (
                <Button
                  type="button"
                  disabled={busy || !billing.stripe_configured}
                  onClick={() => onCheckout(upgradeTarget)}
                >
                  {paidPlan ? "Change plan" : "Upgrade plan"}
                </Button>
              ) : null}
              <Button
                variant="secondary"
                type="button"
                disabled={busy || !billing.stripe_configured}
                onClick={onPortal}
                icon={<CreditCard size={16} />}
              >
                {paidPlan ? "Manage subscription" : "Billing portal"}
              </Button>
            </>
          ) : (
            <Caption1 className={styles.empty}>Billing is managed on this account.</Caption1>
          )}
        </div>
      </section>

      <section className={styles.metrics} aria-label="Credits left by Create function">
        <StatCard icon={<Video size={18} />} label="Clip left" value={clip.remaining} />
        <StatCard icon={<ImageIcon size={18} />} label="Stills left" value={stills.remaining} />
        <StatCard icon={<Sparkles size={18} />} label="Faces left" value={faces.remaining} />
      </section>

      <Block
        title="Usage this period"
        lead="Talking and Scene share one Clip pool. Stills and Faces stay separate. Longer clips and higher quality cost more per run. Caps include plan, support boosts, and packs."
      >
        {extrasActive ? (
          <p className={styles.boostNote}>
            Extra credits this period:{" "}
            {[
              activeAddons.length ? `${activeAddons.length} monthly boost${activeAddons.length === 1 ? "" : "s"}` : null,
              grants.length ? `${grants.length} pack grant${grants.length === 1 ? "" : "s"}` : null,
            ]
              .filter(Boolean)
              .join(" · ")}
            . Included in the bars below.
          </p>
        ) : null}
        <div className={styles.meterList}>
          <UsageRow
            label="Clip"
            used={clip.used}
            max={clip.max}
            remainingLabel={`${clip.remaining} left`}
          />
          <UsageRow
            label="Stills"
            used={stills.used}
            max={stills.max}
            remainingLabel={`${stills.remaining} left`}
          />
          <UsageRow
            label="Face generates"
            used={faces.used}
            max={faces.max}
            remainingLabel={`${faces.remaining} left`}
          />
          <UsageRow
            label="Voice (TTS minutes)"
            used={voiceUsedMin}
            max={voiceMaxMin}
            remainingLabel={`${voiceRemainingMin} min left`}
          />
        </div>
      </Block>

      <div className={styles.twoCol}>
        <Block
          title="Credit packs"
          lead={
            paidPlan
              ? "One-time top-ups for this month. Create shows This run cost before you generate."
              : "Upgrade to a paid plan before buying packs."
          }
        >
          {packs.length ? (
            <div className={styles.packList}>
              {packs.map((pack) => (
                <article className={styles.packRow} key={pack.name}>
                  <div className={styles.packCopy}>
                    <p className={styles.packName}>{pack.label}</p>
                    <p className={styles.packDesc}>{pack.description}</p>
                    <p className={styles.packPrice}>${(pack.price_cents / 100).toFixed(0)}</p>
                  </div>
                  {canManage ? (
                    <Button
                      size="small"
                      variant="secondary"
                      type="button"
                      disabled={busy || !paidPlan || !pack.stripe_configured}
                      onClick={() => onBuyPack(pack.name)}
                    >
                      {!paidPlan ? "Upgrade first" : pack.stripe_configured ? "Buy" : "N/A"}
                    </Button>
                  ) : null}
                </article>
              ))}
            </div>
          ) : (
            <p className={styles.empty}>No packs configured.</p>
          )}
          {grants.length ? (
            <ul className={styles.list} aria-label="Active packs this month">
              {grants.map((g) => (
                <li className={styles.listItem} key={g.id}>
                  <div className={styles.listMain}>
                    <strong>{g.label}</strong>
                    <Caption1>
                      ${(g.amount_cents / 100).toFixed(2)} · until{" "}
                      {new Date(g.period_end).toLocaleDateString()}
                    </Caption1>
                  </div>
                  <Badge appearance="tint" color="success" size="small">
                    active
                  </Badge>
                </li>
              ))}
            </ul>
          ) : null}
        </Block>

        <Block
          title="Monthly boosts"
          lead="Support-granted recurring boosts. For more credits yourself, buy a pack or upgrade."
        >
          {addonError ? <MessageBar intent="error">{addonError}</MessageBar> : null}
          <ul className={styles.list}>
            {activeAddons.map((addon) => (
              <li className={styles.listItem} key={addon.id}>
                <div className={styles.listMain}>
                  <strong>{RECURRING_ADDON_LABELS[addon.addon_type] || addon.addon_type}</strong>
                  <Caption1>
                    qty {addon.quantity} · ~${(addon.monthly_total_cents / 100).toFixed(2)}/mo
                  </Caption1>
                </div>
                {canManage ? (
                  <Button
                    variant="secondary"
                    size="small"
                    type="button"
                    disabled={busy}
                    onClick={() => onCancelAddon(addon.addon_type)}
                  >
                    Cancel
                  </Button>
                ) : null}
              </li>
            ))}
            {!activeAddons.length ? (
              <li className={styles.empty}>
                No active boosts. Use credit packs for more credits this month.
              </li>
            ) : null}
          </ul>
        </Block>
      </div>

      <Block
        title="Plans"
        lead="Monthly sample of clip, still, and face credits. Volume via packs."
      >
        <div className={styles.planGrid}>
          {catalog.map((plan) => {
            const isCurrent = plan.name === billing.plan || plan.name === current.name;
            const isPaid = plan.name !== "free";
            return (
              <article
                key={plan.name}
                className={cn(styles.planCard, isCurrent && styles.planCardCurrent)}
              >
                <div className={styles.planHead}>
                  <h4 className={styles.planName}>{plan.label}</h4>
                  {isCurrent ? (
                    <Badge appearance="filled" color="brand" size="small">
                      Current
                    </Badge>
                  ) : null}
                </div>
                <p className={styles.planPrice}>
                  {plan.price_monthly ? (
                    <>
                      ${plan.price_monthly / 100}
                      <span className={styles.planUnit}>/mo</span>
                    </>
                  ) : (
                    <>
                      $0
                      <span className={styles.planUnit}>/mo</span>
                    </>
                  )}
                </p>
                <ul className={styles.planFacts}>
                  <li className={styles.planFact}>
                    <span>Clip</span>
                    <span className={styles.planFactValue}>
                      {plan.play_clip_limit ??
                        ((plan.play_avatar_limit ?? 0) + (plan.play_video_limit ?? 0) ||
                          plan.video_credit_limit) ??
                        "—"}
                    </span>
                  </li>
                  <li className={styles.planFact}>
                    <span>Stills</span>
                    <span className={styles.planFactValue}>
                      {plan.play_still_limit ?? plan.image_generation_limit ?? "—"}
                    </span>
                  </li>
                  <li className={styles.planFact}>
                    <span>Faces</span>
                    <span className={styles.planFactValue}>{plan.play_face_limit ?? "—"}</span>
                  </li>
                </ul>
                {canManage ? (
                  isPaid ? (
                    <Button
                      className={styles.planCta}
                      size="small"
                      variant={isCurrent ? "secondary" : "primary"}
                      type="button"
                      disabled={busy || isCurrent || !billing.stripe_configured}
                      onClick={() => onCheckout(plan.name)}
                    >
                      {isCurrent ? "Current plan" : "Choose"}
                    </Button>
                  ) : (
                    <Caption1 className={cn(styles.planCta, styles.empty)}>
                      {isCurrent ? "Your current plan" : "Included free"}
                    </Caption1>
                  )
                ) : null}
              </article>
            );
          })}
        </div>
      </Block>

      <Block title="Recent usage" lead="What this account spent lately, by Create function.">
        {usage.length ? (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>Function</th>
                  <th className={styles.th}>Tokens</th>
                  <th className={styles.th}>Status</th>
                </tr>
              </thead>
              <tbody>
                {usage.slice(0, 12).map((event) => (
                  <tr key={event.id}>
                    <td className={styles.td}>{eventLabel(event.event_type)}</td>
                    <td className={styles.td}>{event.quantity}</td>
                    <td className={styles.td}>
                      <Badge appearance="outline" color="subtle" size="small">
                        {event.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className={styles.empty}>Nothing used this period yet.</p>
        )}
      </Block>
    </div>
  );
}
