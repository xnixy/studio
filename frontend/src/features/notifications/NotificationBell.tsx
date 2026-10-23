import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cn } from "../../lib/cn";
import { Bell } from "lucide-react";
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../auth";
import { api } from "../../api";
import type { AppNotification } from "../../types";
import { useWorkspace } from "../../workspace";
import { Button, IconButton } from "../../ui";
import { useDashboardStyles } from "../../ui/dashboardStyles";
import { useWorkspaceRealtime } from "../../realtime/WorkspaceRealtimeProvider";

/** Page size for inbox list (API supports cursor via `before`). */
const PAGE_SIZE = 12;

function relativeTime(iso: string) {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const sec = Math.round((Date.now() - t) / 1000);
  if (sec < 60) return "just now";
  if (sec < 3600) return `${Math.floor(sec / 60)}m`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h`;
  return `${Math.floor(sec / 86400)}d`;
}

function typeLabel(type: string) {
  const t = (type || "").replace(/_/g, " ").trim();
  if (!t) return "update";
  return t.length > 22 ? `${t.slice(0, 20)}…` : t;
}

type PanelPos = { top: number; left: number; maxHeight: number; origin: "top" | "bottom" };

function getPortalHost(): HTMLElement {
  return (
    document.getElementById("studio-portal-root") ||
    document.querySelector<HTMLElement>(".studio-app-root") ||
    document.getElementById("root") ||
    document.body
  );
}

export function NotificationBell() {
  const styles = useDashboardStyles();
  const auth = useAuth();
  const workspace = useWorkspace();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const realtime = useWorkspaceRealtime();
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<PanelPos | null>(null);
  const [items, setItems] = useState<AppNotification[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const panelId = useId();

  const workspaceId = workspace.activeWorkspaceId;
  const token = auth.accessToken;

  const listQuery = useQuery({
    queryKey: ["notifications", "list", workspaceId, PAGE_SIZE],
    queryFn: () =>
      api.listNotifications(workspaceId!, token!, { limit: PAGE_SIZE }),
    enabled: Boolean(workspaceId && token && open),
    refetchInterval: open ? (realtime.status === "live" ? 60_000 : 30_000) : false,
  });

  // Reset when closed. When open, merge first-page data without wiping "Load older" rows.
  useEffect(() => {
    if (!open) {
      setItems([]);
      setHasMore(false);
      setLoadingMore(false);
    }
  }, [open]);

  useEffect(() => {
    if (!open || !listQuery.data) return;
    const page = listQuery.data;
    setItems((prev) => {
      if (prev.length === 0 || prev.length <= PAGE_SIZE) {
        setHasMore(page.length >= PAGE_SIZE);
        return page;
      }
      // Keep older rows loaded via "Load older"; refresh the newest page in place.
      const pageIds = new Set(page.map((n) => n.id));
      const older = prev.filter((n) => !pageIds.has(n.id));
      return [...page, ...older];
    });
  }, [listQuery.data, open]);

  const countQuery = useQuery({
    queryKey: ["notifications", "unread-count", workspaceId],
    queryFn: () => api.notificationUnreadCount(workspaceId!, token!),
    enabled: Boolean(workspaceId && token),
    refetchInterval: realtime.status === "live" ? 60_000 : 20_000,
  });

  const markRead = useMutation({
    mutationFn: (id: string) => api.markNotificationRead(id, token!),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const markAll = useMutation({
    mutationFn: () => api.markAllNotificationsRead(workspaceId!, token!),
    onSuccess: async () => {
      setItems((prev) =>
        prev.map((n) => (n.read_at ? n : { ...n, read_at: new Date().toISOString() })),
      );
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const clearAll = useMutation({
    mutationFn: () => api.clearNotifications(workspaceId!, token!),
    onSuccess: async () => {
      setItems([]);
      setHasMore(false);
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const loadMore = useCallback(async () => {
    if (!workspaceId || !token || loadingMore || !hasMore || !items.length) return;
    const oldest = items[items.length - 1];
    if (!oldest?.created_at) return;
    setLoadingMore(true);
    try {
      const next = await api.listNotifications(workspaceId, token, {
        limit: PAGE_SIZE,
        before: oldest.created_at,
      });
      setItems((prev) => {
        const seen = new Set(prev.map((p) => p.id));
        const merged = [...prev];
        for (const n of next) {
          if (!seen.has(n.id)) merged.push(n);
        }
        return merged;
      });
      setHasMore(next.length >= PAGE_SIZE);
    } catch {
      setHasMore(false);
    } finally {
      setLoadingMore(false);
    }
  }, [workspaceId, token, loadingMore, hasMore, items]);

  const updatePosition = useCallback(() => {
    const el = wrapRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    // Keep panel ~sidebar width, never wider than viewport - 16.
    const panelWidth = Math.min(264, window.innerWidth - 16);
    const gap = 6;
    const spaceBelow = window.innerHeight - rect.bottom - gap;
    const spaceAbove = rect.top - gap;
    const preferBelow = spaceBelow >= 160 || spaceBelow >= spaceAbove;
    // Compact: cap height so it doesn't dominate the screen.
    const maxHeight = Math.max(160, Math.min(320, preferBelow ? spaceBelow : spaceAbove));

    let left = rect.right - panelWidth;
    left = Math.max(8, Math.min(left, window.innerWidth - panelWidth - 8));

    if (preferBelow) {
      setPos({ top: rect.bottom + gap, left, maxHeight, origin: "top" });
    } else {
      setPos({ top: rect.top - gap, left, maxHeight, origin: "bottom" });
    }
  }, []);

  useLayoutEffect(() => {
    if (!open) {
      setPos(null);
      return;
    }
    updatePosition();
    const onWin = () => updatePosition();
    window.addEventListener("resize", onWin);
    window.addEventListener("scroll", onWin, true);
    return () => {
      window.removeEventListener("resize", onWin);
      window.removeEventListener("scroll", onWin, true);
    };
  }, [open, updatePosition]);

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      const target = e.target as Node;
      if (wrapRef.current?.contains(target)) return;
      if (panelRef.current?.contains(target)) return;
      setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const unread = countQuery.data?.count ?? 0;
  const loading = listQuery.isLoading;
  const error = listQuery.isError
    ? (listQuery.error as Error)?.message || "Failed to load"
    : null;

  async function onItemClick(item: AppNotification) {
    if (!item.read_at) {
      markRead.mutate(item.id);
    }
    setOpen(false);
    let href = item.href || "";
    const payloadAsset =
      typeof item.payload?.asset_id === "string" ? item.payload.asset_id : null;
    const entityIsAsset = item.entity_kind === "video_asset" && item.entity_id;
    if (entityIsAsset) {
      const id = payloadAsset || item.entity_id;
      href = id ? `/clips/${id}` : "/clips";
    } else if (href.startsWith("/studio/")) {
      href = "/clips";
    }
    if (href) navigate(href);
  }

  const liveLabel =
    realtime.status === "live"
      ? "Live"
      : realtime.status === "connecting"
        ? "…"
        : "Poll";

  const panel =
    open && pos
      ? createPortal(
          <div
            ref={panelRef}
            id={panelId}
            className={styles.notifPanel}
            role="dialog"
            aria-label="Notifications"
            style={{
              top: pos.origin === "top" ? pos.top : undefined,
              bottom: pos.origin === "bottom" ? window.innerHeight - pos.top : undefined,
              left: pos.left,
              maxHeight: pos.maxHeight,
            }}
          >
            <div className={styles.notifPanelHead}>
              <div className={styles.notifPanelTitleRow}>
                <h2 className={styles.notifPanelTitle}>Notifications</h2>
                <span
                  className={cn(styles.notifLive, realtime.status === "live" && styles.notifLiveOn)}
                >
                  <span className={styles.notifLiveDot} aria-hidden />
                  {liveLabel}
                </span>
              </div>
              <div className={styles.notifActions}>
                <Button
                  variant="subtle"
                  size="small"
                  type="button"
                  disabled={!unread || markAll.isPending || !workspaceId}
                  onClick={() => markAll.mutate()}
                >
                  Mark read
                </Button>
                <Button
                  variant="subtle"
                  size="small"
                  type="button"
                  disabled={!items.length || clearAll.isPending || !workspaceId}
                  onClick={() => {
                    if (
                      window.confirm(
                        "Clear all notifications in this workspace? This cannot be undone.",
                      )
                    ) {
                      clearAll.mutate();
                    }
                  }}
                >
                  Clear
                </Button>
              </div>
            </div>
            <ul className={styles.notifList}>
              {error ? <li className={styles.notifEmpty}>{error}</li> : null}
              {!error && loading && !items.length ? (
                <li className={styles.notifEmpty}>Loading…</li>
              ) : null}
              {items.map((item) => {
                const unreadItem = !item.read_at;
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={cn(styles.notifItem, unreadItem && styles.notifItemUnread)}
                      onClick={() => void onItemClick(item)}
                    >
                      <span
                        className={unreadItem ? styles.notifItemDot : styles.notifItemDotRead}
                        aria-hidden
                      />
                      <span className={styles.notifItemCopy}>
                        <span className={styles.notifItemTitle}>{item.title}</span>
                        {item.body ? (
                          <span className={styles.notifItemBody}>{item.body}</span>
                        ) : null}
                        <span className={styles.notifItemMeta}>
                          {typeLabel(item.type)} · {relativeTime(item.created_at)}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
              {!error && !loading && !items.length ? (
                <li className={styles.notifEmpty}>No notifications yet.</li>
              ) : null}
            </ul>
            {hasMore ? (
              <div className={styles.notifFoot}>
                <Button
                  variant="subtle"
                  size="small"
                  type="button"
                  disabled={loadingMore}
                  onClick={() => void loadMore()}
                >
                  {loadingMore ? "Loading…" : "Load older"}
                </Button>
              </div>
            ) : null}
          </div>,
          getPortalHost(),
        )
      : null;

  return (
    <div className={styles.notifWrap} ref={wrapRef}>
      <IconButton
        aria-label={unread ? `${unread} unread notifications` : "Notifications"}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-controls={open ? panelId : undefined}
        title="Notifications"
        onClick={() => setOpen((v) => !v)}
      >
        <span className={styles.notifBellInner}>
          <Bell size={18} aria-hidden />
          {unread > 0 ? (
            <span className={styles.notifBadge} aria-hidden>
              {unread > 99 ? "99+" : unread}
            </span>
          ) : null}
        </span>
      </IconButton>
      {panel}
    </div>
  );
}
