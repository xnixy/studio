import { tw } from "./tw";

/** Dashboard shell — Tailwind only. */
export const styles = {
  shell: tw.dashShell,
  sidebar: tw.dashSidebar,
  desktopSidebar: tw.dashSidebarDesktop,
  mobileSidebar: tw.dashSidebarMobile,
  backdrop: "fixed inset-0 z-[80] bg-black/50",
  sidebarTop: "flex items-center justify-between gap-2 border-b border-transparent px-0.5 pb-3 pt-0.5",
  sidebarTopTools: "inline-flex shrink-0 items-center gap-1",
  wordmark: "inline-flex items-center leading-none text-[var(--studio-brand)] no-underline hover:opacity-90 hover:no-underline",
  sidebarNav: tw.dashNav,
  sidebarSection: "mb-3 flex flex-col gap-0.5",
  sidebarLabel: "mx-2.5 mb-1.5 mt-3 text-[0.6875rem] font-bold uppercase tracking-wider text-[var(--studio-fg-subtle)]",
  sidebarGroupToggle:
    "my-0.5 flex w-full items-center justify-between gap-2 rounded-full border-0 bg-transparent px-2.5 py-1.5 text-left text-sm font-semibold text-[var(--studio-fg-muted)] hover:bg-[var(--studio-fill-soft)] hover:text-[var(--studio-fg)]",
  sidebarGroupBody: "flex flex-col gap-0.5",
  sidebarGroupBodyCollapsed: "hidden",
  sidebarSectionCompact: "mb-2 flex flex-col gap-0.5",
  navLink: tw.dashNavLink,
  navLinkActive: tw.dashNavLinkActive,
  sidebarBottom: "mt-auto grid gap-2 border-t border-[var(--studio-border-soft)] pt-2.5",
  userRow: "flex items-center gap-2.5 px-1",
  userAvatar:
    "grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[var(--studio-fill)] text-xs font-bold text-[var(--studio-brand)]",
  userMeta: "grid min-w-0 flex-1 overflow-hidden text-sm",
  sidebarTools: "flex flex-wrap items-center gap-1.5",
  frame: tw.dashFrame,
  topbar: tw.dashTopbar,
  topbarReserve: tw.dashTopbarSpacer,
  topbarBrand: "inline-flex items-center gap-2 font-semibold",
  topbarSpacer: "flex-1",
  main: tw.dashMain,
  mobileOnly: "inline-grid md:hidden",
  desktopOnly: "hidden md:inline-grid",
  notifWrap: "relative inline-flex shrink-0",
  notifBellInner: "relative inline-flex items-center justify-center",
  notifBadge:
    "absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full border border-[var(--studio-bg)] bg-[var(--studio-brand)] px-0.5 text-[0.6rem] font-bold leading-none text-[var(--studio-brand-fg)]",
  /** Match sidebar width (~16.5rem), not a huge popover. */
  notifPanel:
    "fixed z-[100] flex w-[min(var(--studio-sidebar-w,16.5rem),calc(100vw-1rem))] flex-col overflow-hidden rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass-strong,var(--studio-panel))] text-[var(--studio-fg)] shadow-[var(--studio-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  notifPanelHead:
    "flex shrink-0 flex-col gap-1.5 border-b border-[var(--studio-border-soft)] px-2.5 py-2",
  notifPanelTitleRow: "flex items-center justify-between gap-1.5",
  notifPanelTitle: "m-0 text-[0.8125rem] font-semibold tracking-tight text-[var(--studio-fg)]",
  notifLive:
    "inline-flex items-center gap-1 rounded-full bg-[var(--studio-fill-quiet)] px-1.5 py-0.5 text-[0.62rem] font-semibold text-[var(--studio-fg-subtle)]",
  notifLiveOn: "bg-[var(--color-success-bg)] text-[var(--color-success)]",
  notifLiveDot: "h-1 w-1 shrink-0 rounded-full bg-current",
  notifActions: "flex flex-wrap items-center gap-1",
  notifList:
    "m-0 flex min-h-0 flex-1 list-none flex-col gap-0.5 overflow-y-auto overscroll-contain p-1.5 [scrollbar-width:thin]",
  notifItem:
    "flex w-full cursor-pointer gap-2 rounded-xl border-0 bg-transparent px-2 py-1.5 text-left text-[var(--studio-fg)] transition-colors hover:bg-[var(--studio-fill-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-[var(--studio-brand)]",
  notifItemUnread: "bg-[var(--studio-chip-on,var(--studio-fill-soft))]",
  notifItemDot: "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--studio-brand)]",
  notifItemDotRead: "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-transparent",
  notifItemCopy: "grid min-w-0 flex-1 gap-0",
  notifItemTitle: "m-0 text-[0.78rem] font-semibold leading-snug text-[var(--studio-fg)] line-clamp-1",
  notifItemBody: "m-0 text-[0.72rem] leading-snug text-[var(--studio-fg-muted)] line-clamp-1",
  notifItemMeta: "m-0 text-[0.65rem] text-[var(--studio-fg-subtle)]",
  notifEmpty: "m-0 px-2 py-6 text-center text-[0.78rem] text-[var(--studio-fg-muted)]",
  notifFoot:
    "flex shrink-0 items-center justify-center border-t border-[var(--studio-border-soft)] px-2 py-1.5",
  toastStack:
    "pointer-events-none fixed bottom-3 right-3 z-[110] flex w-[min(var(--studio-sidebar-w,16.5rem),calc(100vw-1.5rem))] flex-col gap-2 sm:bottom-4 sm:right-4",
  toastCard:
    "pointer-events-auto rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass-strong,var(--studio-panel))] p-2.5 text-sm text-[var(--studio-fg)] shadow-[var(--studio-shadow)] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150",
  toastTitle: "m-0 text-[0.8rem] font-semibold tracking-tight text-[var(--studio-fg)]",
  toastBody: "m-0 mt-0.5 text-[0.75rem] leading-snug text-[var(--studio-fg-muted)] line-clamp-2",
  toastActions: "mt-2 flex flex-wrap items-center gap-1",
  presenceStrip: "inline-flex items-center gap-1.5 text-[0.7rem] font-medium text-[var(--studio-fg-subtle)]",
  presenceDot: "h-1.5 w-1.5 rounded-full bg-[var(--color-success)]",
} as const;

export function useDashboardStyles() {
  return styles;
}
