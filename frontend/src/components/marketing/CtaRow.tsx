import type { ReactNode } from "react";
import { LinkButton } from "../../ui";
import { useMarketingStyles } from "../../ui/marketingStyles";

export function CtaRow({
  primaryTo,
  primaryLabel,
  secondaryTo,
  secondaryLabel,
  tertiaryTo,
  tertiaryLabel,
}: {
  primaryTo: string;
  primaryLabel: ReactNode;
  secondaryTo?: string;
  secondaryLabel?: ReactNode;
  tertiaryTo?: string;
  tertiaryLabel?: ReactNode;
  className?: string;
}) {
  const styles = useMarketingStyles();
  return (
    <div className={styles.ctaRow}>
      <LinkButton to={primaryTo}>{primaryLabel}</LinkButton>
      {secondaryTo && secondaryLabel ? (
        <LinkButton to={secondaryTo} variant="secondary">
          {secondaryLabel}
        </LinkButton>
      ) : null}
      {tertiaryTo && tertiaryLabel ? (
        <LinkButton to={tertiaryTo} variant="secondary">
          {tertiaryLabel}
        </LinkButton>
      ) : null}
    </div>
  );
}
