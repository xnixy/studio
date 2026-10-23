import { Clapperboard, Lock, ArrowRight, Sparkles } from "lucide-react";
import { Body1, Title2 } from "../ui/Text";
import type { PlanFeature } from "../planFeatures";
import { featureLabel } from "../planFeatures";
import { LinkButton, Page, PageBoard, PageFormActions, PageLabel, PageMuted, PageSection } from "../ui";

export function PlanFeatureGate({
  feature,
  planLabel,
  suggestedUpgrade,
  children,
}: {
  feature: PlanFeature;
  planLabel?: string;
  suggestedUpgrade?: string | null;
  children?: React.ReactNode;
}) {
  return (
    <Page>
      <div className="mx-auto w-full max-w-xl">
        <PageBoard>
          <PageSection>
            <div
              className="mb-1 inline-grid h-10 w-10 place-items-center rounded-lg border border-[var(--studio-border)] bg-[var(--studio-fill-soft)] text-[var(--studio-brand)]"
              aria-hidden
            >
              <Lock size={22} />
            </div>
            <PageLabel>Plan</PageLabel>
            <Title2 as="h1">{featureLabel(feature)} needs a higher plan</Title2>
            <Body1>
              Your account is on <strong>{planLabel || "Free"}</strong>.{" "}
              <strong>{featureLabel(feature)}</strong> unlocks on a paid plan.
            </Body1>
            <ul className="m-0 grid list-none gap-2 p-0">
              <li className="flex items-center gap-2 text-sm text-[var(--studio-fg-muted)]">
                <Clapperboard size={16} /> Keep shipping clips on Create
              </li>
              <li className="flex items-center gap-2 text-sm text-[var(--studio-fg-muted)]">
                <Sparkles size={16} /> Upgrade for more credits and features
              </li>
            </ul>
            <PageFormActions>
              <LinkButton to="/billing" icon={<ArrowRight size={16} />} iconPosition="after">
                Compare plans
              </LinkButton>
              <LinkButton to="/play" variant="secondary">
                Back to Create
              </LinkButton>
            </PageFormActions>
            {suggestedUpgrade ? (
              <PageMuted>
                Suggested next step: <strong>{suggestedUpgrade}</strong>
              </PageMuted>
            ) : null}
            {children}
          </PageSection>
        </PageBoard>
      </div>
    </Page>
  );
}
