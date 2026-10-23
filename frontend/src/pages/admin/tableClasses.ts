import { tw } from "../../ui/tw";

/** Shared dense admin table classes. */
export const adminTable = {
  wrap: tw.tableWrap,
  table: tw.table,
  th: tw.th,
  td: tw.td,
  tdMuted: tw.tdMuted,
  empty: tw.tableEmpty,
  lead: "m-0 mb-3 text-[0.88rem] leading-snug text-[var(--studio-fg-muted)]",
  stack: "grid gap-3.5",
  code: "rounded bg-[var(--studio-fill-soft)] px-1 font-mono text-[0.85em]",
  subtle: "text-[0.75rem] text-[var(--studio-fg-subtle)]",
} as const;
