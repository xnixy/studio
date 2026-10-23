import { tw } from "./tw";

export const pageStyles = {
  page: tw.page,
  pageWide: tw.pageWide,
  header: tw.pageHeader,
  headerTitle: "grid min-w-0 flex-[1_1_12rem] gap-0.5",
  headerRow: "flex min-w-0 flex-wrap items-center gap-2",
  subtitle: tw.pageMuted,
  path: "text-[0.8rem] text-[var(--studio-fg-subtle)]",
  sep: "hidden",
  actions: "flex min-w-0 flex-wrap items-center justify-end gap-2 text-[0.78rem] text-[var(--studio-fg-muted)]",
  board: tw.pageBoard,
  boardPlain: "",
  boardNarrow: "mx-auto w-full max-w-lg",
  section: tw.pageSection,
  form: "grid gap-3",
  formActions: "flex flex-wrap items-center gap-2",
  muted: tw.pageMuted,
  label: tw.pageLabel,
  empty:
    "rounded-xl border border-dashed border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-6 text-center text-sm text-[var(--studio-fg-muted)]",
  grid2: "grid gap-3 md:grid-cols-[minmax(0,1.1fr)_minmax(16rem,0.9fr)] md:items-start",
  stack: "grid gap-3",
  opsGrid: "grid items-start gap-3 [grid-template-columns:repeat(auto-fit,minmax(18rem,1fr))]",
  opsPanel:
    "ops-panel grid min-w-0 content-start gap-2.5 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] px-4 py-3.5",
  opsList: "ops-list m-0 grid list-none gap-2 p-0",
  opsListItem:
    "grid gap-1.5 rounded-lg border border-[var(--studio-border-soft)] bg-[var(--studio-fill-quiet)] px-3 py-2.5",
  notice: "",
} as const;

export function usePageStyles() {
  return pageStyles;
}
