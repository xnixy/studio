import type { ReactNode } from "react";
import { Caption1, Text, Title2 } from "../../ui/Text";
import { cn } from "../../lib/cn";

export function MarketingSection({
  id,
  label,
  title,
  children,
  className,
}: {
  id?: string;
  label?: string;
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      id={id}
      className={cn(
        "grid gap-3 rounded-2xl border border-[var(--studio-border)] p-4 sm:px-[18px]",
        "bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-md shadow-[var(--studio-card-shadow)]",
        "shadow-[var(--studio-card-shadow)]",
        "",
        className,
      )}
    >
      {label ? (
        <Caption1 className="uppercase tracking-[0.06em] text-[var(--studio-brand)]">
          <Text weight="semibold">{label}</Text>
        </Caption1>
      ) : null}
      {title ? <Title2 as="h2">{title}</Title2> : null}
      {children}
    </section>
  );
}
