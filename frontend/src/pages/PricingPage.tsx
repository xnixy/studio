import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { cn } from "../lib/cn";
import { Badge } from "../ui";
import { Caption1 } from "../ui/Text";
import { CtaRow } from "../components/marketing/CtaRow";
import { MarketingPageLayout, MarketingPanel } from "../components/marketing/MarketingPageLayout";
import { usePageMeta } from "../components/marketing/usePageMeta";
import { MARKETING_PLAN_FOOTNOTE, MARKETING_PLANS, TYPICAL_CREDIT_SPENDS } from "../marketing/plans";
import { useMarketingStyles } from "../ui/marketingStyles";

const pricingFaq = [
  {
    question: "Do I pay to create an account?",
    answer: "No. Create a free account first. Plans and billing show up in Billing after you sign in.",
  },
  {
    question: "What is a credit?",
    answer:
      "A credit is one unit of your monthly making budget. Clip and stills are separate pools. Talking and Scene share the Clip pool. A fast still is 1 still credit. A Talking Fast clip at about 5s is 8 clip credits. Seedance 2.5 spends more. The composer shows the number before you spend it.",
  },
  {
    question: "Does my own voice cost extra?",
    answer:
      "Talking with a built-in voice spends clip credits only. Talking with your clone adds a few voice seconds. Scene with a Face, a spoken line, and your clone spends clip credits plus the same voice seconds.",
  },
  {
    question: "What if I run out mid-month?",
    answer:
      "Buy a pack for the current month. Packs top up clip or stills without changing your plan.",
  },
];

export function PricingPage() {
  const styles = useMarketingStyles();
  const [openItems, setOpenItems] = useState<string[]>(["0"]);

  usePageMeta(
    "Pricing · Free, Starter, Creator & Studio · Studio",
    "Studio pricing: Free, Starter ($39), Creator ($99), Studio ($179). Clip and still credits. Clone Talking spends talking plus a few voice seconds. Packs for a busy month.",
  );

  return (
    <MarketingPageLayout
      eyebrow="Pricing"
      title="Pick a plan"
      lede="Every plan makes everything: Talking, Scene, and stills. Talking and Scene share one Clip credit pool. Better models and longer lines cost more per run. Packs cover a busy week without moving you up a tier."
      width="wide"
      actions={
        <CtaRow
          primaryTo="/contact?intent=pricing"
          primaryLabel={
            <>
              Ask about plans
              <ArrowRight size={16} />
            </>
          }
          secondaryTo="/register"
          secondaryLabel="Create account"
        />
      }
    >
      <div className={styles.planGrid}>
        {MARKETING_PLANS.map((plan) => (
          <article key={plan.name} className={styles.planCard}>
            <Badge appearance="outline" color="brand" size="small">
              {plan.name === "free"
                ? "Try"
                : plan.name === "studio"
                  ? "Volume"
                  : plan.name === "creator"
                    ? "Daily"
                    : "Solo"}
            </Badge>
            <h2 className={styles.featureTitle}>{plan.label}</h2>
            <div className={styles.price}>
              {plan.priceMonthly === 0 ? (
                <span className={styles.priceValue}>$0</span>
              ) : (
                <>
                  <span className={styles.priceValue}>${plan.priceMonthly}</span>
                  <Caption1>/mo</Caption1>
                </>
              )}
            </div>
            <p className={styles.featureBody}>{plan.fit}</p>
            <ul className={styles.list}>
              {plan.highlights.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>

      <div className="grid gap-3">
        <h2 className="m-0 text-lg font-bold text-[var(--studio-fg)]">What a run spends</h2>
        <p className="m-0 text-sm text-[var(--studio-fg-muted)]">
          Length follows the spoken line. One take is 15s Fast or 30s on 2.5. Longer talk is Extend. Seedance Fast is the default. 2.5
          costs more.
        </p>
        <dl className={styles.propList}>
          {TYPICAL_CREDIT_SPENDS.map((row) => (
            <div key={row.job} className={styles.propItem}>
              <dt className={styles.propTerm}>{row.job}</dt>
              <dd className={styles.propDesc}>{row.spend}</dd>
            </div>
          ))}
        </dl>
      </div>

      <MarketingPanel>
        <p className={styles.footnote}>{MARKETING_PLAN_FOOTNOTE}</p>
        <p className="m-0 mt-2 text-sm text-[var(--studio-fg-muted)]">
          Fast models stretch the month. Seedance 2.5 and the top still models spend more per run because they cost
          more to run. How Create works is on{" "}
          <Link className="font-semibold text-[var(--studio-brand)] no-underline hover:underline" to="/about">
            about
          </Link>
          {" "}
          and in the{" "}
          <Link className="font-semibold text-[var(--studio-brand)] no-underline hover:underline" to="/docs/models-and-tokens">
            credits guide
          </Link>
          .
        </p>
      </MarketingPanel>

      <div className="grid gap-3">
        <h2 className="m-0 text-lg font-bold text-[var(--studio-fg)]">Pricing FAQ</h2>
        <div className={styles.faq}>
          {pricingFaq.map((item, index) => {
            const value = String(index);
            const isOpen = openItems.includes(value);
            return (
              <details
                key={item.question}
                className={cn(styles.faqItem, isOpen && styles.faqItemOpen)}
                open={isOpen}
                onToggle={(ev) => {
                  const nextOpen = (ev.currentTarget as HTMLDetailsElement).open;
                  setOpenItems((prev) => {
                    const set = new Set(prev);
                    if (nextOpen) set.add(value);
                    else set.delete(value);
                    return Array.from(set);
                  });
                }}
              >
                <summary className={cn(styles.faqHeader, styles.faqHeaderButton)}>
                  <span className={styles.faqQuestion}>{item.question}</span>
                </summary>
                <div className={styles.faqPanel}>
                  <p className={styles.faqAnswer}>{item.answer}</p>
                </div>
              </details>
            );
          })}
        </div>
      </div>
    </MarketingPageLayout>
  );
}
