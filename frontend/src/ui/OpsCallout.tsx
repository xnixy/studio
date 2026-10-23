import type { ReactNode } from "react";
import { Button, LinkButton } from "./Button";

/** Shared empty / cold-start block for ops pages. */
export function OpsCallout({
  title,
  body,
  primary,
  secondary,
  children,
}: {
  title: string;
  body?: ReactNode;
  primary?: { label: string; onClick?: () => void; to?: string; disabled?: boolean; icon?: ReactNode };
  secondary?: { label: string; onClick?: () => void; to?: string };
  children?: ReactNode;
}) {
  return (
    <div className="grid gap-3 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-4 shadow-[var(--studio-card-shadow)] backdrop-blur-md">
      <strong className="text-sm font-semibold text-[var(--studio-fg)]">{title}</strong>
      {body != null ? <div className="text-sm text-[var(--studio-fg-muted)]">{body}</div> : null}
      {primary || secondary ? (
        <div className="flex flex-wrap items-center gap-2">
          {primary ? (
            primary.to ? (
              <LinkButton size="small" to={primary.to}>
                {primary.icon}
                {primary.label}
              </LinkButton>
            ) : (
              <Button size="small" type="button" disabled={primary.disabled} onClick={primary.onClick}>
                {primary.icon}
                {primary.label}
              </Button>
            )
          ) : null}
          {secondary ? (
            secondary.to ? (
              <LinkButton variant="secondary" size="small" to={secondary.to}>
                {secondary.label}
              </LinkButton>
            ) : (
              <Button variant="secondary" size="small" type="button" onClick={secondary.onClick}>
                {secondary.label}
              </Button>
            )
          ) : null}
        </div>
      ) : null}
      {children}
    </div>
  );
}

/** Lightweight loading placeholder rows. */
export function OpsSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="grid gap-2" aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-10 min-w-0 animate-pulse rounded-lg bg-[var(--studio-fill-soft)]" />
      ))}
    </div>
  );
}
