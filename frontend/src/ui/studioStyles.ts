import { tw } from "./tw";

/** Studio workspace panels — Tailwind class map. */
export const styles = {
  workspace: "grid min-w-0 gap-3",
  head: "flex flex-wrap items-start justify-between gap-3",
  titleRow: "flex min-w-0 items-center gap-2",
  icon: "text-[var(--studio-brand)]",
  title: "m-0 text-lg font-bold text-[var(--studio-fg)]",
  progress: "flex flex-wrap gap-1.5",
  progressDone: "rounded-full bg-[var(--studio-fill)] px-2 py-0.5 text-[0.72rem] font-semibold text-[var(--studio-brand)]",
  progressCurrent: "rounded-full border border-[var(--studio-border)] bg-[var(--studio-fill)] px-2 py-0.5 text-[0.72rem] font-semibold text-[var(--studio-fg)]",
  guidance: "m-0 text-sm text-[var(--studio-fg-muted)]",
  actions: "flex flex-wrap items-center gap-2",
  busyChip: "inline-flex items-center gap-1.5 rounded-full border border-[var(--studio-border)] bg-[var(--studio-fill-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--studio-fg-muted)]",
  statusBanner: "rounded-xl",
  loadingCard: "grid place-items-center gap-2 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-8 text-sm text-[var(--studio-fg-muted)]",
  stepper: "flex flex-wrap gap-2",
  step: "flex min-w-[8rem] flex-1 cursor-pointer items-start gap-2 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-3 text-left transition-colors hover:border-[var(--studio-border)]",
  stepActive: "border-[var(--studio-border)] bg-[var(--studio-fill-soft)]",
  stepDone: "opacity-90",
  stepIndex: "grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[var(--studio-fill)] text-xs font-bold text-[var(--studio-brand)]",
  stepCopy: "grid min-w-0 gap-0.5",
  stepLabel: "text-sm font-semibold text-[var(--studio-fg)]",
  stepHint: "text-[0.75rem] text-[var(--studio-fg-subtle)]",
  pane: "grid min-w-0 gap-3",
  board: "grid gap-3 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-4 shadow-[var(--studio-card-shadow)] backdrop-blur-md",
  section: "grid gap-2",
  banner:
    "flex flex-wrap items-start justify-between gap-3 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-soft)] px-3.5 py-3",
  label: "m-0 text-[0.72rem] font-bold uppercase tracking-wider text-[var(--studio-brand)]",
  muted: "m-0 text-sm text-[var(--studio-fg-muted)]",
  toolTitle: "m-0 text-sm font-semibold text-[var(--studio-fg)]",
  fields: "grid gap-3",
  fields2: "grid gap-3 sm:grid-cols-2",
  fields3: "grid gap-3 sm:grid-cols-3",
  setupGrid: "grid gap-3 lg:grid-cols-2",
  voiceRail: "grid gap-2 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-3",
  voiceRailReady: "border-[var(--color-success-border)]",
  voiceRailMissing: "border-[var(--studio-border)]",
  voiceRailHead: "flex flex-wrap items-center justify-between gap-2",
  versions: "grid gap-2",
  versionList: "m-0 grid list-none gap-1.5 p-0",
  recipeBox: "rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-3 text-sm text-[var(--studio-fg-muted)]",
  recipeList: "m-0 grid list-none gap-1 p-0",
  exportSoft: "grid gap-2",
  exportVariants: "flex flex-wrap gap-2",

  /** Concept creative panel */
  conceptView: "mx-auto grid w-full max-w-6xl gap-4",
  conceptActions: "mb-1 flex flex-wrap gap-2",
  toolBar: "mb-1 flex flex-wrap items-center gap-2",
  propList: tw.propList,
  propRow: tw.propRow,
  propDt: tw.propDt,
  propDd: tw.propDd,
  propDdEmphasis: tw.propDdEmphasis,
  propEmphasis: "", // marker class for rows that use propDdEmphasis
  sourceDetails:
    "rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] px-3.5 py-2.5 text-sm text-[var(--studio-fg-muted)] open:pb-3",
  sourceSummary: "cursor-pointer list-none font-semibold text-[var(--studio-fg)] [&::-webkit-details-marker]:hidden",
  storyboard: "m-0 grid list-decimal gap-1 pl-5 text-sm leading-relaxed text-[var(--studio-fg-muted)]",
  voiceCard:
    "grid gap-2 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-soft)] p-3",
  voiceCardHead: "flex flex-wrap items-center justify-between gap-2",
  voiceMeta: "m-0 text-sm text-[var(--studio-fg-muted)]",
  selectInline: "w-auto min-w-[8rem] max-w-[14rem] flex-[1_1_7rem]",
} as const;

export function useStudioStyles() {
  return styles;
}
