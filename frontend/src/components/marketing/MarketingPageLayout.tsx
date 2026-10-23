import type { ReactNode } from "react";
import { Body1, Caption1, Text, Title1 } from "../../ui/Text";
import { cn } from "../../lib/cn";
import { useMarketingStyles } from "../../ui/marketingStyles";

type Width = "narrow" | "default" | "wide";

/** Content widths inside the shared 90rem marketing rail. */
const widthClass: Record<Width, string> = {
  /** Forms / contact — match auth card width family. */
  narrow: "max-w-lg",
  /** About and long-form marketing. */
  default: "max-w-5xl",
  wide: "max-w-[90rem]",
};

/** Shared glass page card used by marketing + legal public pages. */
export const marketingPageCardClass = cn(
  "grid min-w-0 gap-4 rounded-[22px] border border-[var(--studio-border)] p-5 sm:px-[22px] sm:py-5",
  "bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  "shadow-[var(--studio-card-shadow)]",
  "text-[var(--studio-fg)]",
);

export function MarketingPageLayout({
  title,
  eyebrow,
  lede,
  width = "default",
  children,
  actions,
}: {
  title: string;
  eyebrow?: string;
  lede?: string;
  width?: Width;
  children: ReactNode;
  actions?: ReactNode;
}) {
  const m = useMarketingStyles();
  return (
    <div className={cn("mx-auto box-border grid w-full gap-8", widthClass[width])}>
      <div className={marketingPageCardClass}>
        <header className="grid gap-2">
          {eyebrow ? (
            <Caption1>
              <Text weight="semibold" style={{ letterSpacing: "0.04em", textTransform: "uppercase" }}>
                {eyebrow}
              </Text>
            </Caption1>
          ) : null}
          <Title1 as="h1">{title}</Title1>
          {lede ? <Body1 className={m.lede}>{lede}</Body1> : null}
          {actions ? <div className={m.ctaRow}>{actions}</div> : null}
        </header>
        <div className="grid gap-4">{children}</div>
      </div>
    </div>
  );
}

/** Optional glass section card for public pages. */
export function MarketingPanel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "grid gap-3 rounded-2xl border border-[var(--studio-border)] p-4 sm:px-[18px]",
        "bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-md shadow-[var(--studio-card-shadow)]",
        className,
      )}
    >
      {children}
    </div>
  );
}
