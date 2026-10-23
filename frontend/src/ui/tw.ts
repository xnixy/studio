/** Shared Tailwind class recipes (single styling system). */

export const tw = {
  btn: "inline-flex items-center justify-center gap-1.5 rounded-[14px] border border-transparent font-semibold leading-tight transition-colors select-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--studio-brand)] disabled:opacity-45 disabled:cursor-not-allowed disabled:pointer-events-none",
  /** min 40px so thumbs hit easily on mobile */
  btnSm: "min-h-10 px-3 py-2 text-sm rounded-xl",
  btnMd: "min-h-10 px-3.5 py-2 text-sm",
  btnLg: "min-h-11 px-4 py-2.5 text-base rounded-2xl",
  btnPrimary:
    "bg-[var(--studio-brand)] text-[var(--studio-brand-fg)] border-[var(--studio-brand)] shadow-[0_8px_24px_rgb(var(--studio-brand-rgb)/0.28)] hover:bg-[var(--studio-brand-hover)] hover:border-[var(--studio-brand-hover)]",
  btnSecondary:
    "bg-[var(--studio-fill-soft)] text-[var(--studio-fg)] border-[var(--studio-border)] backdrop-blur-md hover:bg-[var(--studio-fill)]",
  btnOutline:
    "bg-transparent text-[var(--studio-fg)] border-[var(--studio-border)] backdrop-blur-sm hover:bg-[var(--studio-fill-soft)]",
  btnSubtle: "bg-transparent text-[var(--studio-fg)] border-transparent hover:bg-[var(--studio-fill-soft)]",
  btnIcon: "aspect-square min-h-10 min-w-10 px-0",

  field: "flex w-full min-w-0 flex-col gap-1.5",
  fieldLabel: "text-[0.8rem] font-semibold text-[var(--studio-fg)]",
  fieldHint: "m-0 text-[0.78rem] leading-snug text-[var(--studio-fg-muted)]",
  fieldError: "m-0 text-[0.78rem] text-[var(--color-danger-fg,var(--color-danger))]",
  fieldSuccess: "m-0 text-[0.78rem] text-[var(--color-success-fg,var(--color-success))]",
  fieldWarning: "m-0 text-[0.78rem] text-[var(--color-warning-fg,var(--color-warning))]",

  /** text-base (16px) avoids iOS zoom on focus for inputs/selects */
  control:
    "box-border w-full min-w-0 m-0 rounded-[14px] border border-[var(--input-border,var(--studio-border))] bg-[var(--input-bg,var(--studio-elevated))] text-[var(--studio-fg)] text-base leading-snug font-inherit transition-[border-color,background-color,box-shadow]",
  input:
    "min-h-10 px-3 py-2 focus:outline-none focus:border-[var(--studio-brand)] focus:shadow-[0_0_0_3px_var(--focus-ring)]",
  textarea:
    "min-h-20 px-3 py-2 resize-y focus:outline-none focus:border-[var(--studio-brand)] focus:shadow-[0_0_0_3px_var(--focus-ring)]",
  select:
    "min-h-10 cursor-pointer appearance-none bg-[var(--input-bg,var(--studio-elevated))] py-2 pl-3 text-[var(--studio-fg)] focus:outline-none focus:border-[var(--studio-brand)] focus:shadow-[0_0_0_3px_var(--focus-ring)] disabled:cursor-not-allowed",
  selectSm: "min-h-10 rounded-xl py-1.5 pl-2.5 pr-9 text-base",
  selectAuto: "w-auto max-w-[18rem] min-w-[7.5rem] flex-none",

  tabList:
    "mb-3 flex w-full max-w-full flex-nowrap gap-1 overflow-x-auto overflow-y-hidden box-border rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-1 backdrop-blur-md [scrollbar-width:thin]",
  tab: "flex-none whitespace-nowrap rounded-xl border border-transparent min-h-10 px-3.5 py-1.5 text-sm font-semibold text-[var(--studio-fg-muted)] cursor-pointer bg-transparent hover:bg-[var(--studio-fill-soft)] hover:text-[var(--studio-fg)] data-[active=true]:bg-[var(--studio-chip-on,var(--studio-fill))] data-[active=true]:border-[var(--studio-border)] data-[active=true]:text-[var(--studio-brand)] disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--studio-brand)]",

  messageBar:
    "flex items-start gap-2.5 rounded-2xl border px-3.5 py-2.5 text-sm leading-snug text-[var(--studio-fg)] backdrop-blur-md",
  messageInfo:
    "border-[var(--studio-border)] bg-[var(--studio-chip-on,var(--color-info-bg))] text-[var(--studio-fg)]",
  messageError:
    "border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] text-[var(--color-danger-fg,var(--studio-fg))]",
  messageSuccess:
    "border-[var(--color-success-border)] bg-[var(--color-success-bg)] text-[var(--color-success-fg,var(--color-success))]",
  messageWarning:
    "border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] text-[var(--color-warning-fg,var(--color-warning))]",

  badge:
    "inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[0.72rem] font-bold tracking-wide leading-tight",
  badgeBrand:
    "border-[var(--studio-border)] bg-[var(--studio-fill-soft)] text-[var(--studio-brand)]",
  badgeSuccess:
    "border-[var(--color-success-border)] bg-[var(--color-success-bg)] text-[var(--color-success)]",
  badgeDanger:
    "border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] text-[var(--color-danger-fg,var(--color-danger))]",
  badgeWarning:
    "border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]",
  badgeSubtle: "border-[var(--color-border)] bg-[var(--color-muted-surface)] text-[var(--studio-fg-muted)]",

  /** Frosted plate (iOS glass). Prefer over solid panel-solid. */
  glass:
    "studio-surface-glass border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] text-[var(--studio-fg)] shadow-[var(--studio-card-shadow,var(--studio-shadow))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  card:
    "studio-surface-glass rounded-[var(--studio-card-radius,22px)] border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] text-[var(--studio-fg)] shadow-[var(--studio-card-shadow,var(--studio-shadow))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",

  /** Shared dashboard content rail. Create uses max-w-5xl in PlayPage, not this. */
  page: "mx-auto grid w-full max-w-5xl gap-3 box-border",
  /** Card grids and dense ops tables: wider rail, still inside dashMain's 90rem. */
  pageWide: "mx-auto grid w-full max-w-7xl gap-3 box-border",
  pageHeader:
    "flex min-w-0 flex-col gap-3 border-b border-[var(--studio-border-soft,var(--studio-border))] px-3 py-3 text-[var(--studio-fg)] sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-2 sm:px-4",
  pageBoard:
    "studio-surface-glass flex min-w-0 flex-col rounded-[var(--studio-card-radius,22px)] border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] text-[var(--studio-fg)] shadow-[var(--studio-card-shadow,var(--studio-shadow))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 [-webkit-backdrop-filter:var(--studio-backdrop-filter,blur(28px)_saturate(1.35))]",
  pageSection:
    "grid flex-1 content-start gap-3 border-b border-[var(--studio-border-soft,var(--studio-border))] px-4 py-4 last:border-b-0 sm:px-[18px]",
  pageTitle: "m-0 flex items-center gap-2 text-lg font-bold leading-tight tracking-tight text-[var(--studio-fg)]",
  pageMuted: "m-0 text-sm leading-snug text-[var(--studio-fg-muted)]",
  pageLabel: "m-0 text-[0.72rem] font-semibold tracking-wide text-[var(--studio-fg-subtle)]",

  menu: "studio-surface-glass z-[60] min-w-[12rem] rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass-strong,var(--studio-panel))] p-1.5 text-[var(--studio-fg)] shadow-[var(--studio-shadow-lg)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  menuItem:
    "flex w-full cursor-pointer items-center gap-2 rounded-xl border-0 bg-transparent px-2.5 py-2 text-left text-sm text-inherit hover:bg-[var(--studio-fill-soft)] focus:bg-[var(--studio-fill-soft)] focus:outline-none",
  tooltip:
    "z-50 max-w-[16rem] rounded-xl border border-[var(--studio-border)] bg-[var(--studio-glass-strong,var(--studio-panel))] px-2.5 py-1.5 text-[0.78rem] leading-snug text-[var(--studio-fg)] shadow-[var(--studio-shadow)] backdrop-blur-xl",

  spinner:
    "h-7 w-7 animate-spin rounded-full border-2 border-[var(--color-spinner-track,var(--studio-fill-soft))] border-t-[var(--studio-brand)]",

  dashShell:
    "relative box-border grid min-h-dvh grid-cols-1 items-start gap-2 bg-transparent p-2 text-[var(--studio-fg)] sm:gap-3 sm:p-3 md:grid-cols-[var(--studio-sidebar-w,16.5rem)_minmax(0,1fr)]",
  dashSidebar:
    "studio-surface-glass flex w-full max-w-[var(--studio-sidebar-w,16.5rem)] flex-col gap-2.5 rounded-[22px] border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-3 text-[var(--studio-fg)] shadow-[var(--studio-card-shadow,var(--studio-shadow))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  dashSidebarDesktop:
    "sticky top-3 hidden h-[calc(100dvh-1.5rem)] max-h-[calc(100dvh-1.5rem)] w-[var(--studio-sidebar-w,16.5rem)] overflow-hidden md:flex",
  dashSidebarMobile:
    "studio-surface-glass fixed top-2.5 bottom-2.5 left-2.5 z-[90] flex h-auto max-h-[calc(100dvh-20px)] w-[min(18rem,calc(100vw-20px))] max-w-[18rem] flex-col gap-2 rounded-[22px] p-3 shadow-[var(--studio-shadow-lg)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  dashNav: "flex min-h-0 flex-1 flex-col gap-0.5 overflow-x-hidden overflow-y-auto pr-0.5",
  dashNavLink:
    "flex min-h-11 items-center gap-2.5 rounded-[14px] px-2.5 py-2.5 text-sm font-medium text-[var(--studio-fg-muted)] no-underline hover:bg-[var(--studio-fill-soft)] hover:text-[var(--studio-fg)]",
  dashNavLinkActive:
    "bg-[var(--studio-chip-on,var(--studio-fill))] text-[var(--studio-brand)] font-semibold",
  dashFrame: "flex min-h-[calc(100dvh-1rem)] min-w-0 flex-col bg-transparent md:min-h-[calc(100dvh-1.5rem)]",
  dashMain:
    "mx-auto box-border w-full min-w-0 max-w-[90rem] flex-1 px-2 py-2 pb-6 sm:px-[clamp(12px,2.5vw,28px)] sm:py-3.5 sm:pb-10",
  /**
   * Mobile dashboard top bar. fixed (not sticky) so it survives overflow-x ancestors
   * and always stays on screen while the page scrolls.
   */
  dashTopbar:
    "studio-surface-glass fixed top-2 right-2 left-2 z-40 flex min-h-12 items-center gap-1.5 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] px-2.5 py-1.5 shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 sm:top-3 sm:right-3 sm:left-3 sm:gap-2 sm:px-3.5 sm:py-2 md:hidden",
  /** Reserves space under the fixed mobile top bar (top offset + bar height). */
  dashTopbarSpacer: "mb-2 h-12 shrink-0 sm:mb-2.5 md:hidden",

  mktShell:
    "relative box-border flex min-h-screen flex-col bg-transparent text-[var(--studio-fg)]",
  /**
   * Public navbar chrome. fixed so it stays pinned on mobile scroll
   * (sticky breaks when any ancestor sets overflow-x other than visible).
   */
  mktChrome:
    "fixed top-0 right-0 left-0 z-[60] mx-auto box-border flex w-full max-w-none shrink-0 flex-col items-center gap-2 px-3 pt-3 pb-1",
  mktChromeInner: "flex w-full max-w-[90rem] flex-col gap-2",
  /** Closed-rail height + top padding so content does not jump under fixed chrome. */
  mktChromeSpacer: "h-[calc(52px+0.75rem+0.25rem)] shrink-0",
  mktRail:
    "studio-surface-glass relative z-[2] grid min-h-[52px] w-full shrink-0 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-2.5 overflow-visible rounded-[22px] border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] px-[clamp(12px,2vw,18px)] py-2 text-[var(--studio-fg)] shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  mktRailNav: "hidden min-w-0 items-center justify-center gap-0.5 overflow-hidden md:flex",
  mktRailLink:
    "inline-flex items-center whitespace-nowrap rounded-full border border-transparent px-3 py-[7px] text-sm font-medium text-[var(--studio-fg-muted)] no-underline hover:border-[var(--studio-border-soft)] hover:bg-[var(--studio-fill-soft)] hover:text-[var(--studio-fg)]",
  mktMain:
    "relative z-[1] mx-auto box-border flex w-full min-w-0 max-w-[90rem] flex-1 flex-col items-stretch px-[clamp(16px,4vw,32px)] py-7 pb-10",

  body: "m-0 text-[0.9rem] leading-relaxed text-[var(--studio-fg)]",
  caption: "m-0 text-[0.78rem] leading-snug text-[var(--studio-fg-muted)]",
  title1: "m-0 text-[clamp(1.75rem,4vw,2.5rem)] font-bold leading-tight text-[var(--studio-fg)]",
  title2: "m-0 text-xl font-bold leading-tight text-[var(--studio-fg)]",
  subtitle2: "m-0 text-base font-semibold leading-snug text-[var(--studio-fg)]",

  statCard:
    "studio-surface-glass grid min-w-0 grid-cols-[auto_minmax(0,1fr)] grid-rows-[auto_auto] items-center gap-x-3 gap-y-0.5 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] px-3.5 py-3 text-[var(--studio-fg)] shadow-[var(--studio-card-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",

  propList: "m-0 grid gap-0 p-0",
  propRow:
    "grid grid-cols-1 gap-1 border-b border-[var(--studio-border-soft,var(--studio-border))] py-2.5 last:border-b-0 sm:grid-cols-[6.5rem_minmax(0,1fr)] sm:gap-x-4 sm:gap-y-0",
  propDt: "m-0 pt-0.5 text-[0.75rem] font-semibold text-[var(--studio-fg-subtle)]",
  propDd: "m-0 text-[0.92rem] leading-relaxed text-[var(--studio-fg)]",
  propDdEmphasis: "m-0 text-[1.05rem] font-semibold leading-snug tracking-tight text-[var(--studio-fg)]",

  tableWrap:
    "studio-surface-glass w-full overflow-x-auto rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  table: "w-full min-w-[34rem] border-collapse text-[0.88rem]",
  th: "border-b border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] px-3 py-2.5 text-left text-[0.72rem] font-bold uppercase tracking-wide text-[var(--studio-fg-subtle)]",
  td: "border-b border-[var(--studio-border-soft,var(--studio-border))] px-3 py-2.5 align-top text-[var(--studio-fg)]",
  tdMuted:
    "border-b border-[var(--studio-border-soft,var(--studio-border))] px-3 py-2.5 align-top text-[var(--studio-fg-muted)]",
  tableEmpty:
    "rounded-2xl border border-dashed border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-6 text-center text-sm text-[var(--studio-fg-muted)]",

  /** Soft selected chip (matches iOS Create mode pills). */
  chip:
    "inline-flex items-center rounded-full border px-3 py-1.5 text-[0.8rem] font-semibold transition-colors",
  chipOn:
    "border-[var(--studio-brand)] bg-[var(--studio-chip-on,var(--studio-fill))] text-[var(--studio-brand)]",
  chipOff:
    "border-transparent bg-[var(--studio-chip-off,var(--studio-fill-quiet))] text-[var(--studio-fg)]",
} as const;
