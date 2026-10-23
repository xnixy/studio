import { useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useAuth } from "../auth";
import { useWorkspace } from "../workspace";
import {
  WorkspaceSocket,
  type PresenceMember,
  type RealtimeStatus,
  type WorkspaceEvent,
  type WorkspaceSocketMessage,
} from "./workspaceSocket";

type ToastItem = {
  id: string;
  title: string;
  body?: string | null;
  href?: string | null;
  entityId?: string | null;
  assetId?: string | null;
};

type RealtimeContextValue = {
  status: RealtimeStatus;
  presence: PresenceMember[];
  toasts: ToastItem[];
  dismissToast: (id: string) => void;
};

const RealtimeContext = createContext<RealtimeContextValue>({
  status: "offline",
  presence: [],
  toasts: [],
  dismissToast: () => undefined,
});

export function useWorkspaceRealtime() {
  return useContext(RealtimeContext);
}

function shouldToast(event: WorkspaceEvent, userId: string | undefined) {
  if (event.delivery?.toast === false) return false;
  const recipients = event.delivery?.recipient_user_ids;
  if (recipients && recipients.length && userId && !recipients.includes(userId)) {
    // Persist events may list only users who got rows; still allow toast if empty list meaning broadcast
    if (event.delivery?.persist) return false;
  }
  return Boolean(event.payload?.title) || Boolean(event.delivery?.persist);
}

export function WorkspaceRealtimeProvider({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const workspace = useWorkspace();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<RealtimeStatus>("offline");
  const [presence, setPresence] = useState<PresenceMember[]>([]);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const socketRef = useRef<WorkspaceSocket | null>(null);

  const workspaceId = workspace.activeWorkspaceId;
  const token = auth.accessToken;
  const userId = auth.user?.id;

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.body.dataset.studioRealtime = status;
    }
  }, [status]);

  useEffect(() => {
    if (!workspaceId || !token || !auth.isAuthenticated) {
      socketRef.current?.stop();
      socketRef.current = null;
      setStatus("offline");
      setPresence([]);
      return;
    }

    const sock = new WorkspaceSocket(workspaceId, token);
    socketRef.current = sock;

    const offStatus = sock.onStatus(setStatus);
    const offMessage = sock.onMessage((message: WorkspaceSocketMessage) => {
      const mtype = String((message as { type?: string }).type || "");

      if (mtype === "presence.snapshot") {
        const members = (message as { members?: PresenceMember[] }).members || [];
        setPresence(members);
        return;
      }
      if (mtype === "presence.join") {
        const join = message as { user_id: string; display_name?: string };
        setPresence((prev) => {
          if (prev.some((p) => p.user_id === join.user_id)) return prev;
          return [...prev, { user_id: join.user_id, display_name: join.display_name }];
        });
        return;
      }
      if (mtype === "presence.leave") {
        const leave = message as { user_id: string };
        setPresence((prev) => prev.filter((p) => p.user_id !== leave.user_id));
        return;
      }

      if (mtype === "render_status" || mtype === "render_queue") {
        void queryClient.invalidateQueries({ queryKey: ["video", "projects"] });
        return;
      }

      if (mtype === "event") {
        const event = (message as { event: WorkspaceEvent }).event;
        if (!event?.type) return;

        if (event.delivery?.persist || event.type.includes("completed") || event.type.includes("failed") || event.type.startsWith("render.")) {
          void queryClient.invalidateQueries({ queryKey: ["notifications"] });
        }

        if (event.type.startsWith("job.")) {
          void queryClient.invalidateQueries({ queryKey: ["jobs"] });
        }
        if (event.type.startsWith("video.") || event.type.startsWith("render.")) {
          void queryClient.invalidateQueries({ queryKey: ["video", "projects"] });
          void queryClient.invalidateQueries({ queryKey: ["play", "generations"] });
          if (event.entity?.id) {
            void queryClient.invalidateQueries({ queryKey: ["play", "generation", event.entity.id] });
          }
        }
        if (shouldToast(event, userId)) {
          const id = event.id || `${event.type}-${Date.now()}`;
          setToasts((prev) => {
            const next = [
              {
                id,
                title: event.payload?.title || event.type,
                body: event.payload?.body,
                href: event.payload?.href,
                entityId: event.entity?.id || null,
                assetId:
                  typeof event.payload?.extra?.asset_id === "string"
                    ? event.payload.extra.asset_id
                    : null,
              },
              ...prev.filter((t) => t.id !== id),
            ].slice(0, 4);
            return next;
          });
          window.setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
          }, 8000);
        }
      }
    });

    sock.start();
    return () => {
      offStatus();
      offMessage();
      sock.stop();
      if (socketRef.current === sock) socketRef.current = null;
    };
  }, [workspaceId, token, auth.isAuthenticated, queryClient, userId]);

  const value = useMemo<RealtimeContextValue>(
    () => ({
      status,
      presence,
      toasts,
      dismissToast: (id: string) => setToasts((prev) => prev.filter((t) => t.id !== id)),
    }),
    [status, presence, toasts],
  );

  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>;
}
