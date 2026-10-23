/** Docs layout — Tailwind class map (all keys used by docs pages/components). */
export const styles = {
  shell:
    "mx-auto grid min-h-[calc(100vh-5rem)] w-full max-w-[90rem] gap-6 px-[clamp(16px,4vw,32px)] py-6 md:grid-cols-[minmax(15rem,17rem)_minmax(0,1fr)] md:gap-8",
  sidebar:
    "flex min-w-0 flex-col gap-3 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-3.5 shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 md:sticky md:top-20 md:max-h-[calc(100vh-6rem)] md:overflow-y-auto",
  brand: "text-sm font-bold tracking-wide text-[var(--studio-brand)] no-underline hover:opacity-90",
  search: "w-full",
  nav: "grid gap-4",
  sectionLabel: "m-0 mb-1 px-1 text-[0.7rem] font-bold uppercase tracking-wider text-[var(--studio-fg-subtle)]",
  navList: "m-0 grid list-none gap-0.5 p-0",
  link: "block rounded-lg px-2.5 py-1.5 text-sm text-[var(--studio-fg-muted)] no-underline transition-colors hover:bg-[var(--studio-fill-soft)] hover:text-[var(--studio-fg)]",
  linkActive:
    "bg-[var(--studio-fill)] font-semibold text-[var(--studio-fg)] shadow-[inset_2px_0_0_var(--studio-brand)]",
  empty: "px-1 py-2 text-sm text-[var(--studio-fg-muted)]",
  foot: "mt-auto border-t border-[var(--studio-border-soft)] pt-3 text-[0.75rem] text-[var(--studio-fg-subtle)]",
  footer: "mt-10 border-t border-[var(--studio-border-soft)] pt-5 text-sm text-[var(--studio-fg-subtle)]",
  main: "min-w-0",
  article:
    "grid gap-5 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-5 shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 sm:p-7",
  articleHeader: "grid gap-2 border-b border-[var(--studio-border-soft)] pb-4",
  articleTitle: "m-0 text-[clamp(1.55rem,3vw,2.1rem)] font-bold tracking-tight text-[var(--studio-fg)]",
  articleDesc: "m-0 max-w-[42rem] text-base leading-relaxed text-[var(--studio-fg-muted)]",
  articleMeta: "m-0 text-[0.75rem] text-[var(--studio-fg-subtle)]",
  crumb: "m-0 flex flex-wrap items-center gap-1 text-sm text-[var(--studio-fg-subtle)] [&_a]:text-[var(--studio-brand)] [&_a]:no-underline hover:[&_a]:underline",
  prose:
    "grid max-w-[42rem] gap-3.5 text-[0.98rem] leading-[1.65] text-[var(--studio-fg-muted)] [&_a]:font-medium [&_a]:text-[var(--studio-brand)] [&_a]:underline-offset-2 hover:[&_a]:underline [&_code]:rounded [&_code]:bg-[var(--studio-fill-soft)] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-[0.9em] [&_code]:text-[var(--studio-fg)]",
  proseList: "my-1 list-disc space-y-1.5 pl-5 text-[var(--studio-fg-muted)]",
  h2: "m-0 mt-8 scroll-mt-24 border-t border-[var(--studio-border-soft)] pt-6 text-lg font-bold tracking-tight text-[var(--studio-fg)] first:mt-0 first:border-t-0 first:pt-0",
  h3: "m-0 mt-5 text-base font-semibold text-[var(--studio-fg)]",
  p: "m-0 text-[0.98rem] leading-[1.65] text-[var(--studio-fg-muted)]",
  callout:
    "grid gap-1.5 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-soft)] p-3.5 text-sm text-[var(--studio-fg-muted)] [&_strong]:text-[var(--studio-fg)]",
  calloutTip:
    "grid gap-1.5 rounded-xl border border-[var(--color-success-border,rgb(16_185_129/0.35))] bg-[var(--color-success-bg,rgb(16_185_129/0.12))] p-3.5 text-sm [&_strong]:text-[var(--studio-fg)]",
  calloutNote:
    "grid gap-1.5 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-soft)] p-3.5 text-sm text-[var(--studio-fg-muted)] [&_strong]:text-[var(--studio-fg)]",
  calloutWarning:
    "grid gap-1.5 rounded-xl border border-[var(--color-warning-border,rgb(251_191_36/0.35))] bg-[var(--color-warning-bg,rgb(251_191_36/0.12))] p-3.5 text-sm [&_strong]:text-[var(--studio-fg)]",
  linkList: "m-0 grid list-none gap-2 p-0",
  steps: "my-2 grid list-none gap-2.5 p-0",
  step: "grid grid-cols-[auto_1fr] items-start gap-3 rounded-xl border border-[var(--studio-border-soft)] bg-[var(--studio-fill-quiet)] p-3.5",
  stepNum:
    "grid h-7 w-7 place-items-center rounded-full bg-[var(--studio-fill)] text-xs font-bold text-[var(--studio-brand)]",
  pager: "mt-2 flex flex-wrap justify-between gap-3",
  pagerLink:
    "inline-flex max-w-[16rem] items-start gap-2 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] px-3.5 py-3 text-sm font-semibold text-[var(--studio-fg)] no-underline transition-colors hover:border-[var(--studio-border)] hover:bg-[var(--studio-fill-soft)] hover:no-underline [&_small]:block [&_small]:text-[0.72rem] [&_small]:font-normal [&_small]:text-[var(--studio-fg-subtle)]",
  pagerNext: "ml-auto text-right",
  missing: "grid gap-3 place-items-start rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-8",
  helpLine: "m-0 mt-4 text-sm text-[var(--studio-fg-muted)] [&_a]:text-[var(--studio-brand)]",
  toc: "grid gap-1.5 rounded-xl border border-[var(--studio-border-soft)] bg-[var(--studio-fill-quiet)] p-3.5 text-sm",
  tocLabel: "m-0 text-[0.7rem] font-bold uppercase tracking-wider text-[var(--studio-fg-subtle)]",
  tocList: "m-0 grid list-none gap-1 p-0",
  tocLink: "text-[var(--studio-fg-muted)] no-underline hover:text-[var(--studio-fg)]",
  hero: "grid gap-3 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-5 shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 sm:p-7",
  heroTitle: "m-0 text-[clamp(1.55rem,3vw,2.1rem)] font-bold tracking-tight text-[var(--studio-fg)]",
  heroLede: "m-0 max-w-[40rem] text-base leading-relaxed text-[var(--studio-fg-muted)]",
  kicker: "m-0 text-[0.7rem] font-bold uppercase tracking-wider text-[var(--studio-brand)]",
  ctaRow: "flex flex-wrap items-center gap-2.5",
  pathGrid: "mt-6 grid gap-3 sm:grid-cols-2",
  pathCard:
    "grid gap-2 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-4 no-underline shadow-[var(--studio-card-shadow)] backdrop-blur-md transition-colors hover:border-[var(--studio-border)] hover:bg-[var(--studio-fill-soft)] hover:no-underline",
  pathTitle: "m-0 text-base font-bold text-[var(--studio-fg)]",
  pathBody: "m-0 text-sm leading-relaxed text-[var(--studio-fg-muted)]",
  pathGo: "inline-flex items-center gap-1 text-sm font-semibold text-[var(--studio-brand)]",
  allSection: "mt-8 grid gap-3",
  allTitle: "m-0 text-lg font-bold text-[var(--studio-fg)]",
  allList: "m-0 grid list-none gap-1 p-0",
  allLink:
    "grid gap-0.5 rounded-xl border border-transparent px-3 py-2.5 no-underline transition-colors hover:border-[var(--studio-border)] hover:bg-[var(--studio-fill-soft)] hover:no-underline",
  allLinkStrong: "text-sm font-semibold text-[var(--studio-fg)]",
  allLinkDesc: "text-[0.8rem] leading-snug text-[var(--studio-fg-muted)]",
} as const;

export function useDocsStyles() {
  return styles;
}
