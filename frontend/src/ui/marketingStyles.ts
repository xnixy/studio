import { tw } from "./tw";

/** Marketing shell + landing — Tailwind only. */
export const styles = {
  shell: tw.mktShell,
  shellLanding:
    "",
  chrome: tw.mktChrome,
  chromeInner: tw.mktChromeInner,
  chromeSpacer: tw.mktChromeSpacer,
  rail: tw.mktRail,
  wordmark: "inline-flex min-w-0 shrink-0 items-center leading-none text-[var(--studio-brand)] no-underline hover:opacity-90 hover:no-underline",
  railNav: tw.mktRailNav,
  railLink: tw.mktRailLink,
  railActions: "flex min-w-0 shrink-0 flex-nowrap items-center justify-end gap-1.5",
  /** Fixed min width so guest CTAs do not reflow the sticky rail between routes. */
  railDesktopCtas:
    "hidden min-w-[13.5rem] flex-nowrap items-center justify-end gap-1.5 md:flex",
  menuButton:
    "inline-grid h-[38px] w-[38px] shrink-0 cursor-pointer place-items-center rounded-[11px] border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-0 leading-none text-[var(--studio-fg)] hover:border-[var(--studio-border)] hover:bg-[var(--studio-fill-soft)] md:hidden",
  /** Full-width sheet under the rail; solid enough to read over page content. */
  mobileNav:
    "relative z-[1] flex max-h-[min(72vh,32rem)] w-full shrink-0 flex-col gap-1 overflow-x-hidden overflow-y-auto overscroll-contain rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass-strong,var(--studio-panel))] p-2 shadow-[var(--studio-shadow-lg)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 md:hidden",
  mobileNavScrim: "fixed inset-0 z-[55] m-0 cursor-pointer border-0 bg-black/45 p-0 md:hidden",
  mobileNavDivider: "my-1.5 mx-1 h-px shrink-0 bg-[var(--studio-border)]",
  /** Stacked nav rows (not desktop rail chips). */
  mobileNavLink:
    "flex w-full items-center rounded-xl border border-transparent px-3.5 py-3 text-[0.95rem] font-medium text-[var(--studio-fg)] no-underline hover:border-[var(--studio-border-soft)] hover:bg-[var(--studio-fill-soft)] hover:no-underline active:bg-[var(--studio-fill)]",
  mobileNavCta:
    "mt-0.5 flex w-full items-center justify-center rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill)] px-3.5 py-3.5 text-[0.95rem] font-semibold text-[var(--studio-fg)] no-underline hover:bg-[var(--studio-fill)] hover:no-underline active:bg-[var(--studio-fill)]",
  main: tw.mktMain,
  /** Full-bleed landing: no main max-width; sections/hero set their own gutters. */
  mainLanding: "max-w-none items-stretch px-0 py-0 pb-0",
  /** Center auth cards in the shell (overrides main max-width + stretch). */
  mainAuth:
    "flex w-full max-w-none flex-1 flex-col items-center justify-center px-[clamp(16px,4vw,32px)] py-[clamp(32px,8vh,64px)] min-h-[calc(100vh-6rem)]",
  /** Docs owns its own rail (same 90rem) so avoid double gutters on main. */
  mainWide: "max-w-none px-0 py-4 pb-10",
  footer: "mt-auto border-t border-[var(--studio-border-soft)] px-[clamp(16px,4vw,32px)] py-8",
  footerInner: "mx-auto flex w-full max-w-[90rem] flex-col gap-4 md:flex-row md:items-start md:justify-between",
  footerBrand: "grid max-w-md gap-2 text-sm font-semibold text-[var(--studio-fg)]",
  footerLinks: "flex flex-wrap gap-x-4 gap-y-2 text-sm text-[var(--studio-fg-muted)]",
  footerMeta: "text-[0.8rem] text-[var(--studio-fg-subtle)]",
  /** Auth form card: readable width, not a skinny column. */
  authCard:
    "mx-auto w-full max-w-lg rounded-[22px] border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-0 shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  authCardInner: "grid w-full gap-4 p-6 sm:p-8",
  authTitle: "m-0 text-xl font-bold text-[var(--studio-fg)]",
  authLede: "m-0 text-sm text-[var(--studio-fg-muted)]",
  authForm: "grid gap-3",
  authActions: "flex flex-wrap items-center gap-2",
  authMuted: "m-0 text-sm text-[var(--studio-fg-muted)]",
  page: "flex w-full flex-col",
  /** Centered playground hero: title + compose, not two-column studio pitch. */
  hero: "relative mx-auto grid w-full max-w-5xl justify-items-center gap-6 px-[clamp(16px,4vw,32px)] py-[clamp(2.25rem,6vw,4rem)] text-center",
  heroAura:
    "pointer-events-none absolute left-1/2 top-0 -z-0 h-[22rem] w-[min(100%,42rem)] -translate-x-1/2 rounded-full opacity-80 studio-hero-shimmer",
  heroCopy: "relative z-[1] grid w-full max-w-2xl justify-items-center gap-4",
  kicker:
    "m-0 inline-flex items-center gap-1.5 rounded-full border border-[var(--studio-border)] bg-[var(--studio-fill)] px-3 py-1 text-[0.75rem] font-bold uppercase tracking-wider text-[var(--studio-brand)]",
  heroTitle:
    "m-0 text-[clamp(2.4rem,5.8vw,3.75rem)] font-bold leading-[1.04] tracking-[-0.035em] text-[var(--studio-fg)]",
  /** Second line of the H1 (must be block so words do not glue together). */
  heroTitleMuted:
    "mt-[0.12em] block bg-gradient-to-r from-[var(--studio-brand)] via-[color-mix(in_srgb,var(--studio-brand)_70%,white)] to-[var(--studio-fg-muted)] bg-clip-text font-semibold text-transparent",
  lede: "m-0 max-w-xl text-[1.08rem] leading-relaxed text-[var(--studio-fg-muted)]",
  ctaRow: "relative z-[1] flex flex-wrap items-center justify-center gap-2.5",
  proof: "grid w-full max-w-2xl grid-cols-2 gap-3 sm:grid-cols-4",
  proofItem: "rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] px-3 py-2.5 text-left",
  proofLabel: "m-0 text-[0.7rem] font-semibold uppercase tracking-wide text-[var(--studio-fg-subtle)]",
  proofValue: "m-0 text-sm font-semibold text-[var(--studio-fg)]",
  /** Landing Create mirror: same shell language as app Create (header + thread + bottom composer). */
  playShell:
    "relative z-[1] flex w-full min-w-0 max-w-5xl flex-col overflow-hidden rounded-[28px] border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] text-left shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  playTop:
    "flex min-w-0 flex-wrap items-center justify-between gap-2 border-b border-[var(--studio-border-soft)] px-3 py-2.5 sm:px-4 sm:py-3",
  playTopTitle: "m-0 flex items-center gap-2 text-base font-bold text-[var(--studio-fg)]",
  playTopMeta: "flex flex-wrap items-center gap-2 text-[0.75rem] text-[var(--studio-fg-muted)]",
  playThread:
    "grid min-h-[5.5rem] max-h-[11rem] gap-2.5 overflow-y-auto border-b border-[var(--studio-border-soft)] bg-[var(--studio-bg)]/30 px-3 py-3 sm:min-h-[7.5rem] sm:max-h-none sm:px-4 sm:py-4",
  playUserBubble:
    "ml-auto max-w-[min(36rem,92%)] break-words rounded-[20px] rounded-br-md bg-[var(--studio-bubble-user,var(--studio-brand))] px-3 py-2 text-[0.9rem] leading-snug text-[var(--studio-bubble-user-fg,#fff)] sm:px-3.5 sm:py-2.5 sm:text-sm sm:leading-normal",
  playSystemBubble:
    "max-w-[min(36rem,92%)] break-words rounded-[20px] rounded-bl-md bg-[var(--studio-bubble-system,var(--studio-fill-quiet))] px-3 py-2 text-[0.9rem] leading-snug text-[var(--studio-bubble-system-fg,var(--studio-fg))] sm:px-3.5 sm:py-2.5 sm:text-sm sm:leading-normal",
  playComposer: "grid min-w-0 gap-2.5 bg-[var(--studio-glass,var(--studio-fill-quiet))] p-2.5 backdrop-blur-md sm:p-4",
  playFieldLabel: "m-0 text-[0.72rem] font-bold uppercase tracking-wide text-[var(--studio-fg-subtle)]",
  playFieldBlurb: "m-0 text-[0.75rem] text-[var(--studio-fg-muted)]",
  playControls: "flex min-w-0 flex-wrap items-center gap-2",
  playSelect:
    "max-w-full rounded-lg border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 px-2 py-1 text-[0.8rem] text-[var(--studio-fg)] outline-none",
  playFaceStrip:
    "flex min-w-0 flex-col gap-2 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 px-2.5 py-2.5 sm:px-3 sm:py-3",
  playFaceLabel: "m-0 text-[0.72rem] font-bold uppercase tracking-wide text-[var(--studio-fg-subtle)]",
  playFaceRow:
    "flex min-w-0 gap-2 overflow-x-auto overscroll-x-contain pb-0.5 [-webkit-overflow-scrolling:touch] [-ms-overflow-style:none] [scrollbar-width:none] sm:gap-2.5 [&::-webkit-scrollbar]:hidden",
  playFaceChip:
    "flex w-[4.25rem] shrink-0 cursor-pointer flex-col items-center gap-1 rounded-xl border border-[var(--studio-border-soft)] bg-[var(--studio-fill-quiet)] p-1.5 transition-colors hover:border-[var(--studio-border)] sm:w-[4.75rem] sm:gap-1.5",
  playFaceChipOn: "border-[var(--studio-brand)] bg-[var(--studio-chip-on,var(--studio-fill))] shadow-[0_0_0_1px_var(--studio-brand)]",
  playFaceImg: "h-12 w-12 rounded-full object-cover object-center ring-1 ring-[var(--studio-border)] sm:h-14 sm:w-14",
  playFaceName: "m-0 max-w-full truncate text-center text-[0.68rem] font-semibold text-[var(--studio-fg)] sm:text-[0.7rem]",
  playFaceHint: "m-0 text-[0.72rem] leading-snug text-[var(--studio-fg-muted)]",
  playFaceDot: "h-8 w-8 shrink-0 rounded-full border border-[var(--studio-border)] bg-[var(--studio-fill)]",
  chipRow:
    "flex min-w-0 flex-nowrap gap-1.5 overflow-x-auto overscroll-x-contain pb-0.5 [-webkit-overflow-scrolling:touch] [-ms-overflow-style:none] [scrollbar-width:none] sm:flex-wrap sm:overflow-visible [&::-webkit-scrollbar]:hidden",
  chip: "inline-flex shrink-0 cursor-pointer items-center gap-1.5 rounded-full border border-transparent bg-[var(--studio-chip-off,var(--studio-fill-quiet))] px-3 py-1.5 text-[0.8rem] font-semibold text-[var(--studio-fg-muted)] transition-colors hover:text-[var(--studio-fg)]",
  chipActive:
    "border-[var(--studio-brand)] bg-[var(--studio-chip-on,var(--studio-fill))] text-[var(--studio-brand)]",
  /** Container for PromptFields on the landing preview. Min-heights live in the component. */
  promptShell:
    "grid w-full min-w-0 rounded-[22px] border border-[var(--studio-border)] bg-[var(--input-bg,var(--studio-fill-quiet))] focus-within:border-[var(--studio-brand)] focus-within:ring-2 focus-within:ring-[var(--focus-ring)]",
  promptField:
    "w-full min-w-0 resize-y border-0 bg-transparent px-3 py-2.5 text-[0.95rem] leading-relaxed text-[var(--studio-fg)] outline-none placeholder:text-[var(--studio-fg-subtle)]",
  playActions: "flex min-w-0 flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between",
  playHint: "m-0 text-[0.78rem] leading-snug text-[var(--studio-fg-subtle)]",
  /** @deprecated kept for any leftover callers */
  playBody: "grid gap-0",
  playMain: "grid gap-3 p-3 sm:p-4",
  playSide: "hidden",
  playSideLabel: "m-0 text-[0.68rem] font-bold uppercase tracking-wider text-[var(--studio-fg-subtle)]",
  playSideValue: "m-0 text-sm font-semibold text-[var(--studio-fg)]",
  playSideHint: "m-0 text-[0.78rem] leading-snug text-[var(--studio-fg-muted)]",
  playDot: "h-2 w-2 rounded-full bg-[var(--studio-fill)]",
  exampleRow: "flex flex-wrap items-center justify-center gap-2",
  exampleChip:
    "inline-flex max-w-full cursor-pointer items-center rounded-full border border-[var(--studio-border-soft)] bg-transparent px-3 py-1.5 text-left text-[0.8rem] text-[var(--studio-fg-muted)] transition-colors hover:border-[var(--studio-border)] hover:bg-[var(--studio-fill-soft)] hover:text-[var(--studio-fg)]",
  previewShell: "overflow-hidden rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-fill-soft))] shadow-[var(--studio-shadow-lg)] backdrop-blur-md",
  previewTop: "flex items-center gap-1.5 border-b border-[var(--studio-border-soft)] px-3 py-2",
  previewDot: "h-2 w-2 rounded-full bg-[var(--studio-fill)]",
  previewGrid: "grid gap-2 p-3 sm:grid-cols-2",
  previewItem: "rounded-xl border border-[var(--studio-border-soft)] bg-[var(--studio-fill-quiet)] p-3 text-sm text-[var(--studio-fg-muted)]",
  caption: "m-0 mt-2 text-[0.8rem] text-[var(--studio-fg-subtle)]",
  band: "border-y border-[var(--studio-border-soft)] bg-[var(--studio-fill-quiet)] px-[clamp(16px,4vw,32px)] py-4",
  bandText: "mx-auto m-0 max-w-[90rem] text-center text-sm font-medium text-[var(--studio-fg-muted)]",
  section: "w-full py-[clamp(2.75rem,7vw,4.5rem)] pb-4",
  sectionInner: "mx-auto grid w-full max-w-[90rem] gap-7 px-[clamp(16px,4vw,32px)]",
  sectionHead: "grid max-w-[40rem] gap-3",
  sectionTitle: "m-0 text-[clamp(1.55rem,3vw,2.1rem)] font-bold leading-[1.15] tracking-[-0.02em] text-[var(--studio-fg)]",
  sectionLede: "m-0 text-[1.02rem] leading-relaxed text-[var(--studio-fg-muted)]",
  grid2: "grid gap-4 md:grid-cols-2",
  grid3: "grid gap-4 md:grid-cols-3",
  grid4: "grid gap-4 sm:grid-cols-2 lg:grid-cols-4",
  /** Same solid panel family as play shell / showcase cards (no mixed fill-quiet vs fill-soft). */
  featureCard:
    "grid gap-3 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-5 shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 transition-[border-color,transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-[var(--studio-border)] hover:shadow-[var(--studio-shadow-lg)]",
  featureCardHot: "border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  iconWell:
    "inline-grid h-10 w-10 place-items-center rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] text-[var(--studio-brand)]",
  featureTitle: "m-0 text-base font-bold text-[var(--studio-fg)]",
  featureBody: "m-0 text-sm leading-relaxed text-[var(--studio-fg-muted)]",
  list: "m-0 grid list-none gap-1.5 p-0 text-sm text-[var(--studio-fg-muted)]",
  /** Higgsfield-style example gallery */
  showcase: "mx-auto grid w-full max-w-[90rem] gap-6 px-[clamp(16px,4vw,32px)] py-[clamp(2rem,5vw,3rem)]",
  showcaseHead: "flex flex-col gap-4 md:flex-row md:items-end md:justify-between",
  showcaseHeadCopy: "grid max-w-xl gap-2 text-left",
  showcaseKicker:
    "m-0 inline-flex items-center gap-1.5 text-[0.75rem] font-bold uppercase tracking-wider text-[var(--studio-brand)]",
  showcaseTitle: "m-0 text-[clamp(1.6rem,3.2vw,2.2rem)] font-bold tracking-[-0.02em] text-[var(--studio-fg)]",
  showcaseLede: "m-0 text-[0.98rem] leading-relaxed text-[var(--studio-fg-muted)]",
  showcaseFilters: "flex flex-wrap gap-1.5",
  showcaseGrid:
    "grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 auto-rows-fr",
  showcaseCard:
    "studio-fade-up group relative flex cursor-pointer flex-col overflow-hidden rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-0 text-left shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 transition-[transform,border-color,box-shadow] duration-200 hover:-translate-y-1 hover:border-[var(--studio-border)] hover:shadow-[var(--studio-shadow-lg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--studio-brand)]",
  showcaseCardTall: "row-span-2 min-h-[20rem] sm:min-h-[24rem]",
  showcaseCardWide: "sm:col-span-2",
  showcaseCardSelected:
    "border-[var(--studio-brand)] shadow-[var(--studio-shadow-lg)]",
  showcaseScene: "relative min-h-[10.5rem] flex-1 overflow-hidden bg-[var(--studio-bg)] sm:min-h-[12rem]",
  showcaseSceneGlow:
    "pointer-events-none absolute -right-6 -top-8 h-28 w-28 rounded-full opacity-40 [filter:blur(24px)]",
  showcaseSceneNoise:
    "pointer-events-none absolute inset-0 opacity-[0.12] [background-image:radial-gradient(circle_at_20%_20%,white_0,transparent_45%),radial-gradient(circle_at_80%_70%,white_0,transparent_40%)]",
  showcaseMockLabel:
    "absolute inset-x-3 bottom-12 z-[1] m-0 text-left text-[0.82rem] font-bold leading-snug tracking-tight drop-shadow-[0_2px_8px_rgba(0,0,0,0.55)] sm:text-[0.9rem]",
  showcasePlay:
    "absolute left-1/2 top-1/2 z-[2] grid h-11 w-11 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-white/30 bg-black/45 text-white opacity-90 shadow-[0_8px_24px_rgba(0,0,0,0.35)] transition-[transform,opacity,background-color] duration-200 group-hover:scale-110 group-hover:bg-black/55",
  showcaseBadges: "absolute left-2 top-2 z-[2] flex flex-wrap gap-1",
  showcaseBadge:
    "rounded-full border border-white/15 bg-black/45 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-white/95",
  showcaseMeta: "grid gap-0.5 border-t border-[var(--studio-border-soft)] px-3 py-2.5",
  showcaseCardTitle: "m-0 text-[0.88rem] font-bold leading-snug text-[var(--studio-fg)]",
  showcaseCardCaption: "m-0 text-[0.75rem] text-[var(--studio-fg-muted)]",
  marquee:
    "relative overflow-hidden border-y border-[var(--studio-border-soft)] bg-[var(--studio-fill-quiet)] py-3",
  marqueeTrack: "studio-marquee-track flex w-max items-center gap-3",
  marqueeItem:
    "inline-flex shrink-0 items-center rounded-full border border-[var(--studio-border)] bg-[var(--studio-fill-soft)] px-3.5 py-1.5 text-[0.8rem] font-semibold text-[var(--studio-fg-muted)]",
  modeStrip: "grid gap-3 sm:grid-cols-2 lg:grid-cols-4",
  modeTile:
    "group relative grid gap-3 overflow-hidden rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 p-5 text-left transition-[transform,border-color] duration-200 hover:-translate-y-0.5 hover:border-[var(--studio-border)]",
  originalityCol: "grid gap-3",
  samplePanel: "rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 p-4",
  samplePanelHead: "mb-2 flex items-center justify-between gap-2",
  samplePanelKicker: "m-0 text-[0.7rem] font-bold uppercase tracking-wider text-[var(--studio-brand)]",
  sampleStack: "grid gap-2",
  sampleRow: "grid gap-0.5 border-b border-[var(--studio-border-soft)] py-2 last:border-0",
  sampleKey: "text-[0.72rem] font-semibold uppercase tracking-wide text-[var(--studio-fg-subtle)]",
  sampleVal: "text-sm text-[var(--studio-fg)]",
  planGrid: "grid gap-4 sm:grid-cols-2 xl:grid-cols-4",
  planCard:
    "grid gap-3 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-5 shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  price: "flex items-baseline gap-1",
  priceValue: "text-3xl font-bold tracking-tight text-[var(--studio-fg)]",
  footnote: "m-0 text-[0.8rem] text-[var(--studio-fg-subtle)]",
  faq: "grid gap-2",
  faqItem: "rounded-xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  faqItemOpen: "border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  faqHeader: "w-full",
  faqHeaderButton: "flex w-full cursor-pointer list-none items-center justify-between gap-3 px-4 py-3.5 text-left font-semibold text-[var(--studio-fg)] [&::-webkit-details-marker]:hidden",
  faqQuestion: "text-[0.95rem]",
  faqPanel: "px-4 pb-4",
  faqAnswer: "m-0 text-sm leading-relaxed text-[var(--studio-fg-muted)]",
  ctaPanel: "px-[clamp(16px,4vw,32px)] py-10 pb-12",
  ctaPanelInner:
    "mx-auto grid max-w-[90rem] gap-4 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-6 shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 md:grid-cols-[1fr_auto] md:items-center md:p-8",
  trust: "mx-auto m-0 flex max-w-[90rem] items-center gap-1.5 px-[clamp(16px,4vw,32px)] pb-8 text-[0.8rem] text-[var(--studio-fg-subtle)]",
  propList: "m-0 grid gap-3 p-0",
  propItem: "grid gap-1 border-b border-[var(--studio-border-soft)] pb-3 last:border-0",
  propTerm: "text-sm font-semibold text-[var(--studio-fg)]",
  propDesc: "m-0 text-sm text-[var(--studio-fg-muted)]",
  legalBody: "prose-like grid gap-4 text-[var(--studio-fg-muted)]",
} as const;

export function useMarketingStyles() {
  return styles;
}
