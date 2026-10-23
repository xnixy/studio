import { API_BASE_URL, api } from "../api";

export type RealtimeStatus = "connecting" | "live" | "offline";

export type WorkspaceEvent = {
  v?: number;
  id?: string;
  type: string;
  workspace_id?: string;
  occurred_at?: string;
  actor_user_id?: string | null;
  entity?: { kind?: string | null; id?: string | null };
  payload?: {
    title?: string;
    body?: string | null;
    href?: string | null;
    extra?: Record<string, unknown>;
  };
  delivery?: {
    persist?: boolean;
    live?: boolean;
    toast?: boolean;
    recipient_mode?: string;
    recipient_user_ids?: string[];
  };
};

export type WorkspaceSocketMessage =
  | { type: "hello"; workspace_id: string; user_id: string; render_only?: boolean }
  | { type: "error"; detail?: string }
  | { type: "pong" }
  | { type: "render_queue"; workspace_id: string; queued: number; running: number; items: unknown[] }
  | { type: "render_status"; workspace_id?: string; render_id?: string; status?: string; output_url?: string }
  | { type: "presence.snapshot"; members: PresenceMember[] }
  | { type: "presence.join"; user_id: string; display_name?: string }
  | { type: "presence.leave"; user_id: string }
  | { type: "event"; event: WorkspaceEvent }
  | Record<string, unknown>;

export type PresenceMember = {
  user_id: string;
  display_name?: string;
  path?: string;
  last_seen?: string;
};

export type WorkspaceSocketHandler = (message: WorkspaceSocketMessage) => void;

function wsUrl(path: string, workspaceId: string, ticket: string) {
  const base = API_BASE_URL.replace(/\/$/, "");
  if (base.startsWith("http://") || base.startsWith("https://")) {
    const u = new URL(base);
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    u.pathname = `${u.pathname.replace(/\/$/, "")}${path}`;
    u.search = `workspace_id=${encodeURIComponent(workspaceId)}&ticket=${encodeURIComponent(ticket)}`;
    return u.toString();
  }
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.host;
  const prefix = base.startsWith("/") ? base : `/${base}`;
  return `${proto}://${host}${prefix}${path}?workspace_id=${encodeURIComponent(workspaceId)}&ticket=${encodeURIComponent(ticket)}`;
}

export class WorkspaceSocket {
  private socket: WebSocket | null = null;
  private closed = false;
  private retryTimer: number | undefined;
  private heartbeatTimer: number | undefined;
  private handlers = new Set<WorkspaceSocketHandler>();
  private statusHandlers = new Set<(s: RealtimeStatus) => void>();
  status: RealtimeStatus = "offline";

  constructor(
    private workspaceId: string,
    private token: string,
  ) {}

  onMessage(handler: WorkspaceSocketHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  onStatus(handler: (s: RealtimeStatus) => void) {
    this.statusHandlers.add(handler);
    handler(this.status);
    return () => this.statusHandlers.delete(handler);
  }

  private setStatus(s: RealtimeStatus) {
    this.status = s;
    this.statusHandlers.forEach((h) => h(s));
  }

  private emit(message: WorkspaceSocketMessage) {
    this.handlers.forEach((h) => h(message));
  }

  start() {
    this.closed = false;
    void this.connect();
  }

  stop() {
    this.closed = true;
    if (this.retryTimer) window.clearTimeout(this.retryTimer);
    if (this.heartbeatTimer) window.clearInterval(this.heartbeatTimer);
    this.socket?.close();
    this.socket = null;
    this.setStatus("offline");
  }

  send(payload: Record<string, unknown>) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }

  private async connect() {
    if (this.closed) return;
    this.setStatus("connecting");
    try {
      const { ticket } = await api.wsTicket(this.workspaceId, this.token);
      if (this.closed) return;
      this.socket = new WebSocket(wsUrl("/ws/workspace", this.workspaceId, ticket));
    } catch {
      this.setStatus("offline");
      this.scheduleRetry();
      return;
    }

    this.socket.onopen = () => {
      this.setStatus("live");
      if (this.heartbeatTimer) window.clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = window.setInterval(() => {
        this.send({ type: "presence.heartbeat", path: window.location.pathname });
        this.send({ type: "ping" });
      }, 20000);
    };
    this.socket.onclose = () => {
      this.setStatus("offline");
      if (this.heartbeatTimer) window.clearInterval(this.heartbeatTimer);
      if (!this.closed) this.scheduleRetry();
    };
    this.socket.onerror = () => this.setStatus("offline");
    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as WorkspaceSocketMessage;
        this.emit(data);
      } catch {
        /* ignore */
      }
    };
  }

  private scheduleRetry() {
    if (this.retryTimer) window.clearTimeout(this.retryTimer);
    this.retryTimer = window.setTimeout(() => void this.connect(), 4000);
  }
}
