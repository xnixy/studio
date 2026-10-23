import type { ReactNode } from "react";
import { cn } from "../lib/cn";
import { tw } from "./tw";

export function Page({
  children,
  className,
  wide,
}: {
  children: ReactNode;
  className?: string;
  /** Wider rail for card grids and dense ops tables. Default suits reading-width pages. */
  wide?: boolean;
}) {
  return <div className={cn(wide ? tw.pageWide : tw.page, className)}>{children}</div>;
}

export function PageHeader({
  title,
  subtitle,
  path,
  actions,
  children,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  path?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <header className={tw.pageHeader}>
      <div className="grid min-w-0 flex-[1_1_12rem] gap-0.5">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <h1 className={tw.pageTitle}>{title}</h1>
          {path != null ? <span className="text-[0.8rem] text-[var(--studio-fg-subtle)]">{path}</span> : null}
        </div>
        {subtitle != null ? (
          typeof subtitle === "string" ? (
            <p className={cn(tw.pageMuted, "m-0 text-[0.8rem] leading-snug")}>{subtitle}</p>
          ) : (
            subtitle
          )
        ) : null}
        {children}
      </div>
      {actions ? (
        <div className="flex w-full min-w-0 flex-wrap items-stretch gap-2 text-[0.78rem] text-[var(--studio-fg-muted)] sm:w-auto sm:items-center sm:justify-end [&_a]:min-w-0 [&_button]:min-w-0 sm:[&_button]:min-w-[auto]">
          {actions}
        </div>
      ) : null}
    </header>
  );
}

export function PageBoard({
  children,
  narrow,
  plain: _plain,
  className,
}: {
  children: ReactNode;
  narrow?: boolean;
  plain?: boolean;
  className?: string;
}) {
  return (
    <div className={cn(tw.pageBoard, narrow && "mx-auto w-full max-w-lg", className)}>
      {children}
    </div>
  );
}

export function PageSection({ children, className }: { children: ReactNode; className?: string }) {
  return <section className={cn(tw.pageSection, className)}>{children}</section>;
}

export function PageForm({
  children,
  onSubmit,
  className,
  noValidate,
}: {
  children: ReactNode;
  onSubmit?: (event: React.FormEvent) => void;
  className?: string;
  noValidate?: boolean;
}) {
  return (
    <form className={cn("grid gap-3", className)} onSubmit={onSubmit} noValidate={noValidate}>
      {children}
    </form>
  );
}

export function PageFormActions({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-2">{children}</div>;
}

export function PageMuted({ children }: { children: ReactNode }) {
  return <p className={tw.pageMuted}>{children}</p>;
}

export function PageLabel({ children }: { children: ReactNode }) {
  return <p className={tw.pageLabel}>{children}</p>;
}

export function PageEmpty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel-soft))] p-5 text-center text-[var(--studio-fg-muted)] backdrop-blur-md">
      {children}
    </div>
  );
}

export function PageGrid2({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("grid gap-3 md:grid-cols-[minmax(0,1.1fr)_minmax(16rem,0.9fr)] md:items-start", className)}>
      {children}
    </div>
  );
}

export function PageStack({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("grid gap-3", className)}>{children}</div>;
}

export function OpsGrid({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("grid items-start gap-3 [grid-template-columns:repeat(auto-fit,minmax(18rem,1fr))]", className)}>
      {children}
    </div>
  );
}

export function OpsPanel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "ops-panel grid min-w-0 content-start gap-2.5 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] px-4 py-3.5 shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function OpsList({ children, className }: { children: ReactNode; className?: string }) {
  return <ul className={cn("ops-list m-0 grid list-none gap-2 p-0", className)}>{children}</ul>;
}

export function OpsListItem({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <li className={cn("grid gap-1.5 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] px-3 py-2.5", className)}>
      {children}
    </li>
  );
}

export function OpsEmptyState({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("rounded-lg border border-dashed border-[var(--studio-border)] p-5 text-center text-[var(--studio-fg-muted)]", className)}>{children}</div>;
}
