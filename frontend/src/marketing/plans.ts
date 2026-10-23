/** Public marketing plan teaser. Matches backend play_* limits. */

export interface MarketingPlan {
  name: string;
  label: string;
  /** Monthly USD (whole dollars). Free is 0. */
  priceMonthly: number;
  fit: string;
  highlights: string[];
}

/**
 * Commercial story:
 * - Open registration.
 * - Free + three paid tiers (Starter / Creator / Studio).
 * - All tiers include clip and still credits.
 * - Talking and Scene share one Clip credit pool (leftover Photo caps fold in).
 * - Packs top up the current month.
 */
export const MARKETING_PLANS: MarketingPlan[] = [
  {
    name: "free",
    label: "Free",
    priceMonthly: 0,
    fit: "Enough credits to learn the loop and see if it fits how you work.",
    highlights: [
      "25 clip credits / mo",
      "12 still credits",
      "1 GB storage",
    ],
  },
  {
    name: "starter",
    label: "Starter",
    priceMonthly: 39,
    fit: "Solo makers shipping Reels, Shorts, and feed stills from chat.",
    highlights: [
      "80 clip credits / mo",
      "70 still credits",
      "Credit packs when a week gets heavy",
    ],
  },
  {
    name: "creator",
    label: "Creator",
    priceMonthly: 99,
    fit: "Daily posters who need more clips every week.",
    highlights: [
      "200 clip credits / mo",
      "160 still credits",
      "Higher storage",
    ],
  },
  {
    name: "studio",
    label: "Studio",
    priceMonthly: 179,
    fit: "Heavy volume with priority rendering.",
    highlights: [
      "525 clip credits / mo",
      "400 still credits",
      "Priority rendering · more storage",
    ],
  },
];

/** Typical Create spends. Length follows the spoken line. Longer clips cost more clip credits. */
export const TYPICAL_CREDIT_SPENDS: { job: string; spend: string }[] = [
  { job: "Fast still", spend: "1 still credit" },
  { job: "Quality still (Grok 2.0)", spend: "2 still credits" },
  { job: "Talking Fast, about 5s", spend: "8 clip credits" },
  { job: "Talking Fast, about 8s", spend: "13 clip credits" },
  { job: "Talking with your clone", spend: "Clip credits + a few voice seconds" },
  { job: "Scene Fast, about 5s", spend: "8 clip credits" },
  { job: "Scene with Face, clone, spoken line", spend: "Clip credits + a few voice seconds" },
  { job: "Seedance 2.5, up to 30s", spend: "12 credits at 720p" },
];

export const MARKETING_PLAN_FOOTNOTE =
  "Monthly limits are in credits. Talking and Scene share one Clip pool. Leftover Photo caps fold into Clip. A fast still costs a fraction of a Seedance clip. Length follows the spoken line, so a longer talking clip spends more. Buy a pack when you need more. Prices are monthly USD and can change.";
