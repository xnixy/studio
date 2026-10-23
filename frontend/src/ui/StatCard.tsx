import type { ReactNode } from "react";
import { cn } from "../lib/cn";
import { tw } from "./tw";

export function StatCard({
  icon,
  label,
  value,
  className,
}: {
  icon?: ReactNode;
  label: ReactNode;
  value: ReactNode;
  className?: string;
}) {
  return (
    <article className={cn(tw.statCard, className)}>
      {icon != null ? (
        <span
          className="row-span-2 inline-grid h-9 w-9 shrink-0 place-items-center rounded-md border border-[var(--studio-border)] bg-[var(--studio-fill-soft)] text-[var(--studio-brand)]"
          aria-hidden="true"
        >
          {icon}
        </span>
      ) : null}
      <strong className="m-0 truncate text-2xl font-bold leading-tight tracking-tight tabular-nums">
        {value}
      </strong>
      <p className="m-0 truncate text-[0.8rem] font-medium text-[var(--studio-fg-muted)]">{label}</p>
    </article>
  );
}
