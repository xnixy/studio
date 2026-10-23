import type {
  AdminContact,
  AdminOverview,
  AdminWorkspaceRow,
  AdminJobRow,
  AdminJobStats,
  AdminUsageRow,
  AdminAuditPage,
  AdminUser,
  AuthResponse,
  ContactTopic,
  MaintenanceStatus,
  Role,
  User,
  BillingSession,
  BillingStatus,
  CreditPack,
  CreditPackName,
  PlanName,
  Workspace,
  UsageEvent,
  VideoAsset,
  AddOnType,
  EffectiveLimits,
  ShareLinkPublic,
} from "./types";

const configuredBase = import.meta.env.VITE_API_BASE_URL as string | undefined;

/** Used when a deployed build shipped without VITE_API_BASE_URL set. */
const PRODUCTION_API_BASE_URL = "https://api.example.com/api";

/**
 * Absolute config wins. A relative base is correct only when something proxies
 * /api to the backend (dev server, same-origin deploy), so an unconfigured
 * build served from a real host falls back to the production API instead of
 * resolving requests and signed media against the SPA origin.
 */
function resolveApiBase(): string {
  const configured = configuredBase?.trim().replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const isLocal =
      host === "localhost" || host === "127.0.0.1" || host === "[::1]" || host.endsWith(".local");
    if (!isLocal) return PRODUCTION_API_BASE_URL;
  }
  return "/api";
}

export const API_BASE_URL = resolveApiBase();

/** Default request budget so a wedged API/proxy cannot leave the app on the boot spinner forever. */
const DEFAULT_REQUEST_TIMEOUT_MS = 12_000;
/** LLM / media generation can take well over the default (backend xAI chat timeout is 60s per call). */
const AI_REQUEST_TIMEOUT_MS = 150_000;
/** FFmpeg export can take several minutes (clips + VO mix + captions). */
const RENDER_REQUEST_TIMEOUT_MS = 600_000;
/** Multi-size image packs: several sequential xAI gens + persist. */
const IMAGE_PACK_REQUEST_TIMEOUT_MS = 600_000;

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string | null;
  constructor(message: string, status: number, code?: string | null) {
    super(message);
    this.status = status;
    this.code = code ?? null;
  }
}

interface RequestOptions extends RequestInit {
  token?: string | null;
  /** Internal: skip 401→refresh retry (used for refresh itself). */
  skipAuthRetry?: boolean;
  /** Abort after this many ms (default 12s). Pass 0 to disable. */
  timeoutMs?: number;
}

type AuthSessionHandlers = {
  getAccessToken: () => string | null;
  applySession: (session: AuthResponse) => void;
  clearSession: () => void;
};

let authHandlers: AuthSessionHandlers | null = null;
let refreshInFlight: Promise<string | null> | null = null;

/** Bind access-token refresh from AuthProvider so expired JWTs recover mid-session. */
export function bindAuthSessionHandlers(handlers: AuthSessionHandlers | null) {
  authHandlers = handlers;
}

/** Server says we lost a rotation race; the jar already holds the new cookie. */
const REFRESH_RACE_CODE = "refresh_race";

async function postRefresh(): Promise<AuthResponse | undefined> {
  return request<AuthResponse | undefined>("/auth/refresh", {
    method: "POST",
    skipAuthRetry: true,
  });
}

async function refreshAccessTokenSingleFlight(): Promise<string | null> {
  if (!authHandlers) return null;
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    try {
      let session: AuthResponse | undefined;
      try {
        session = await postRefresh();
      } catch (error) {
        // A sibling tab rotated the cookie a moment ago. Retry once with what
        // is in the jar now instead of signing the user out of the tab that
        // merely lost the race.
        if (error instanceof ApiError && error.code === REFRESH_RACE_CODE) {
          session = await postRefresh();
        } else {
          throw error;
        }
      }
      // 204 no cookie → undefined; treat as signed out without raising.
      if (!session?.access_token || !session.user) {
        authHandlers?.clearSession();
        return null;
      }
      authHandlers?.applySession(session);
      return session.access_token;
    } catch (error) {
      // Only a definitive rejection ends the session. A timeout, an offline
      // moment, or a 5xx says nothing about whether the cookie is still good,
      // and clearing on those is why a flaky connection signed people out.
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        authHandlers?.clearSession();
      }
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

function mergeAbortSignals(signals: Array<AbortSignal | null | undefined>): AbortSignal | undefined {
  const active = signals.filter((s): s is AbortSignal => Boolean(s));
  if (active.length === 0) return undefined;
  if (active.length === 1) return active[0];
  if (typeof AbortSignal.any === "function") {
    return AbortSignal.any(active);
  }
  // Fallback for older browsers: abort when any input aborts.
  const controller = new AbortController();
  for (const signal of active) {
    if (signal.aborted) {
      controller.abort(signal.reason);
      break;
    }
    signal.addEventListener("abort", () => controller.abort(signal.reason), { once: true });
  }
  return controller.signal;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { token: tokenOpt, skipAuthRetry, timeoutMs, signal: userSignal, ...fetchInit } = options;
  const headers = new Headers(fetchInit.headers);
  if (fetchInit.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = tokenOpt ?? (path.startsWith("/auth/") ? null : authHandlers?.getAccessToken() ?? null);
  if (tokenOpt) {
    headers.set("Authorization", `Bearer ${tokenOpt}`);
  } else if (token && !path.startsWith("/auth/login") && !path.startsWith("/auth/register") && !path.startsWith("/auth/refresh")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const budget = timeoutMs === undefined ? DEFAULT_REQUEST_TIMEOUT_MS : timeoutMs;
  const timeoutSignal =
    budget > 0 && typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function"
      ? AbortSignal.timeout(budget)
      : undefined;
  const signal = mergeAbortSignals([userSignal ?? null, timeoutSignal ?? null]);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...fetchInit,
      headers,
      credentials: "include",
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && (err.name === "TimeoutError" || err.name === "AbortError")) {
      throw new ApiError(
        "This is taking longer than usual. Wait a bit, refresh the page, and check whether it finished. If nothing appears, try again.",
        0,
      );
    }
    if (err instanceof TypeError) {
      throw new ApiError("Network error. Check your connection or API.", 0);
    }
    throw err;
  }

  if (response.status === 401 && !skipAuthRetry && !path.startsWith("/auth/")) {
    const next = await refreshAccessTokenSingleFlight();
    if (next) {
      return request<T>(path, { ...options, token: next, skipAuthRetry: true });
    }
  }

  if (!response.ok) {
    const payload = await parseErrorPayload(response);
    throw new ApiError(payload.message, response.status, payload.code);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function parseErrorPayload(
  response: Response,
): Promise<{ message: string; code?: string | null }> {
  const text = await response.text();
  try {
    const error = JSON.parse(text) as {
      error?: string;
      code?: string;
      message?: string;
      detail?: unknown;
    };
    if (typeof error.error === "string" && error.error.trim()) {
      return { message: error.error, code: error.code ?? null };
    }
    if (typeof error.message === "string" && error.message.trim()) {
      return { message: error.message, code: error.code ?? null };
    }
    if (typeof error.detail === "string" && error.detail.trim()) {
      return { message: error.detail, code: error.code ?? null };
    }
    if (Array.isArray(error.detail)) {
      return {
        message: response.status === 422 ? "Check the form fields and try again." : "Request failed",
      };
    }
  } catch {
    if (text.trim()) return { message: text };
  }
  return { message: "Request failed" };
}

async function parseErrorMessage(response: Response): Promise<string> {
  return (await parseErrorPayload(response)).message;
}

async function upload<T>(path: string, formData: FormData, token: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
    headers: {
      Authorization: `Bearer ${token}`,
    },
    credentials: "include",
  });

  if (!response.ok) {
    throw new ApiError(await parseErrorMessage(response), response.status);
  }

  return (await response.json()) as T;
}

export const api = {
  maintenance: () => request<MaintenanceStatus>("/maintenance"),
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  publicConfig: () =>
    request<{ turnstile_site_key: string | null; turnstile_enabled: boolean; turnstile_required: boolean }>(
      "/public-config",
    ),
  register: (
    email: string,
    password: string,
    options?: { fullName?: string; turnstileToken?: string | null },
  ) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        full_name: options?.fullName ?? "",
        turnstile_token: options?.turnstileToken ?? null,
      }),
    }),
  forgotPassword: (email: string) =>
    request<{ message: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  resetPassword: (token: string, password: string) =>
    request<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),
  verifyEmail: (token: string) =>
    request<{ message: string }>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
      skipAuthRetry: true,
    }),
  /**
   * Signed-in resend: pass Bearer token.
   * Signed-out resend: pass email only (anti-enumeration response).
   */
  resendVerification: (tokenOrEmail?: string | null, emailWhenToken?: string | null) => {
    // Back-compat: resendVerification(accessToken) or resendVerification(null, email)
    const looksLikeEmail = Boolean(tokenOrEmail && tokenOrEmail.includes("@") && !emailWhenToken);
    const token = looksLikeEmail ? undefined : tokenOrEmail || undefined;
    const email = looksLikeEmail ? tokenOrEmail : emailWhenToken;
    return request<{ message: string }>("/auth/resend-verification", {
      method: "POST",
      token: token || undefined,
      body: email ? JSON.stringify({ email }) : JSON.stringify({}),
      skipAuthRetry: true,
    });
  },
  refresh: () =>
    request<AuthResponse | undefined>("/auth/refresh", { method: "POST", skipAuthRetry: true }),
  logout: () => request<{ message: string }>("/auth/logout", { method: "POST", skipAuthRetry: true }),
  deleteAccount: (password: string, token: string) =>
    request<{ message: string }>("/auth/delete-account", {
      method: "POST",
      token,
      body: JSON.stringify({ password, confirm: "DELETE" }),
    }),
  wsTicket: (workspaceId: string, token: string) =>
    request<{ ticket: string; expires_in: number }>("/ws/ticket", {
      method: "POST",
      token,
      body: JSON.stringify({ workspace_id: workspaceId }),
    }),
  listNotifications: (
    workspaceId: string,
    token: string,
    opts?: { unreadOnly?: boolean; limit?: number; before?: string },
  ) => {
    const params = new URLSearchParams({ workspace_id: workspaceId });
    if (opts?.unreadOnly) params.set("unread_only", "true");
    if (opts?.limit) params.set("limit", String(opts.limit));
    if (opts?.before) params.set("before", opts.before);
    return request<import("./types").AppNotification[]>(`/notifications?${params}`, { token });
  },
  notificationUnreadCount: (workspaceId: string, token: string) =>
    request<{ count: number }>(
      `/notifications/unread-count?workspace_id=${encodeURIComponent(workspaceId)}`,
      { token },
    ),
  markNotificationRead: (notificationId: string, token: string) =>
    request<import("./types").AppNotification>(`/notifications/${encodeURIComponent(notificationId)}/read`, {
      method: "POST",
      token,
    }),
  markAllNotificationsRead: (workspaceId: string, token: string) =>
    request<{ count: number }>(
      `/notifications/read-all?workspace_id=${encodeURIComponent(workspaceId)}`,
      { method: "POST", token },
    ),
  clearNotifications: (workspaceId: string, token: string) =>
    request<{ count: number }>(
      `/notifications?workspace_id=${encodeURIComponent(workspaceId)}`,
      { method: "DELETE", token },
    ),
  listNotificationPreferences: (token: string, workspaceId?: string) => {
    const params = new URLSearchParams();
    if (workspaceId) params.set("workspace_id", workspaceId);
    const q = params.toString();
    return request<import("./types").NotificationPreference[]>(
      `/notification-preferences${q ? `?${q}` : ""}`,
      { token },
    );
  },
  upsertNotificationPreference: (
    token: string,
    body: {
      workspace_id?: string | null;
      event_type?: string;
      in_app?: boolean;
      email?: boolean;
      toast?: boolean;
    },
  ) =>
    request<import("./types").NotificationPreference>("/notification-preferences", {
      method: "PUT",
      token,
      body: JSON.stringify(body),
    }),
  me: (token: string) => request<{ user: User }>("/auth/me", { token }),
  updateProfile: (fullName: string | null, token: string) =>
    request<{ user: User }>("/auth/profile", {
      method: "PATCH",
      token,
      body: JSON.stringify({ full_name: fullName }),
    }),
  updatePassword: (currentPassword: string, password: string, token: string) =>
    request<{ message: string }>("/auth/password", {
      method: "POST",
      token,
      body: JSON.stringify({ current_password: currentPassword, password }),
    }),
  submitContact: (
    name: string,
    email: string,
    topic: ContactTopic,
    message: string,
    options?: { turnstileToken?: string | null },
  ) =>
    request<{ id: string; message: string }>("/contact", {
      method: "POST",
      body: JSON.stringify({
        name,
        email,
        topic,
        message,
        turnstile_token: options?.turnstileToken ?? null,
      }),
    }),
  listUsers: (token: string, q?: string) =>
    request<AdminUser[]>(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`, { token }),
  updateAdminUser: (userId: string, payload: { role?: Role; is_disabled?: boolean; full_name?: string | null }, token: string) =>
    request<AdminUser>(`/admin/users/${userId}`, {
      method: "PATCH",
      token,
      body: JSON.stringify(payload),
    }),
  revokeUserSessions: (userId: string, token: string) =>
    request<{ message: string }>(`/admin/users/${userId}/revoke-sessions`, { method: "POST", token }),
  listContacts: (token: string) => request<AdminContact[]>("/admin/contacts", { token }),
  resolveContact: (contactId: string, token: string) =>
    request<AdminContact>(`/admin/contacts/${contactId}/resolve`, { method: "POST", token }),
  adminMaintenance: (token: string) => request<MaintenanceStatus>("/admin/maintenance", { token }),
  setMaintenance: (enabled: boolean, message: string | null, token: string) =>
    request<MaintenanceStatus>("/admin/maintenance", {
      method: "POST",
      token,
      body: JSON.stringify({ enabled, message }),
    }),
  adminOverview: (token: string) => request<AdminOverview>("/admin/overview", { token }),
  adminWorkspaces: (token: string) => request<AdminWorkspaceRow[]>("/admin/workspaces", { token }),
  updateAdminWorkspace: (
    workspaceId: string,
    payload: { plan?: string; subscription_status?: string; limit_overrides?: Record<string, number> },
    token: string,
  ) =>
    request<AdminWorkspaceRow>(`/admin/workspaces/${workspaceId}`, {
      method: "PATCH", token, body: JSON.stringify(payload),
    }),
  adminGrantBoost: (
    payload: {
      workspace_id: string;
      addon_type: string;
      quantity: number;
      notes?: string | null;
    },
    token: string,
  ) =>
    request<{
      id: string;
      workspace_id: string;
      addon_type: string;
      quantity: number;
      unit_price_cents: number;
      status: string;
      notes: string | null;
      monthly_total_cents: number;
    }>("/admin/billing/addons", {
      method: "PUT",
      token,
      body: JSON.stringify(payload),
    }),
  adminCancelBoost: (workspaceId: string, addonType: string, token: string) =>
    request<{ message: string }>(
      `/admin/billing/addons/${encodeURIComponent(addonType)}?workspace_id=${encodeURIComponent(workspaceId)}`,
      { method: "DELETE", token },
    ),
  adminJobs: (token: string, status?: string) =>
    request<AdminJobRow[]>(`/admin/jobs${status ? `?status=${encodeURIComponent(status)}` : ""}`, { token }),
  adminJobStats: (token: string) => request<AdminJobStats>("/admin/jobs/stats", { token }),
  adminCancelJob: (jobId: string, token: string) =>
    request<AdminJobRow>(`/admin/jobs/${jobId}/cancel`, { method: "POST", token }),
  adminUsage: (token: string) => request<AdminUsageRow[]>("/admin/usage", { token }),
  adminAudit: (
    token: string,
    opts?: {
      limit?: number;
      offset?: number;
      action?: string;
      q?: string;
      workspace_id?: string;
      since?: string;
      until?: string;
    },
  ) => {
    const params = new URLSearchParams();
    if (opts?.limit != null) params.set("limit", String(opts.limit));
    if (opts?.offset != null) params.set("offset", String(opts.offset));
    if (opts?.action?.trim()) params.set("action", opts.action.trim());
    if (opts?.q?.trim()) params.set("q", opts.q.trim());
    if (opts?.workspace_id) params.set("workspace_id", opts.workspace_id);
    if (opts?.since?.trim()) params.set("since", opts.since.trim());
    if (opts?.until?.trim()) params.set("until", opts.until.trim());
    const qs = params.toString();
    return request<AdminAuditPage>(`/admin/audit${qs ? `?${qs}` : ""}`, { token });
  },
  adminRevokeApiKey: (keyId: string, token: string) =>
    request<{ message: string }>(`/admin/api-keys/${keyId}`, { method: "DELETE", token }),
  /** Personal space only (one per user). */
  listWorkspaces: (token: string) => request<Workspace[]>("/workspaces", { token }),
  billingStatus: (token: string, workspaceId: string) => request<BillingStatus>(`/billing?workspace_id=${encodeURIComponent(workspaceId)}`, { token }),
  createCheckout: (token: string, workspaceId: string, plan: PlanName) =>
    request<BillingSession>("/billing/checkout", {
      method: "POST",
      token,
      body: JSON.stringify({ workspace_id: workspaceId, plan }),
    }),
  billingUsage: (token: string, workspaceId: string) => request<UsageEvent[]>(`/billing/usage?workspace_id=${workspaceId}`, { token }),
  listCreditPacks: (token: string) => request<CreditPack[]>("/billing/packs", { token }),
  createPackCheckout: (token: string, workspaceId: string, pack: CreditPackName) =>
    request<BillingSession>("/billing/packs/checkout", {
      method: "POST",
      token,
      body: JSON.stringify({ workspace_id: workspaceId, pack }),
    }),
  createBillingPortal: (token: string, workspaceId: string) =>
    request<BillingSession>(`/billing/portal?workspace_id=${workspaceId}`, { method: "POST", token }),
  pollVideoAsset: (token: string, assetId: string, opts?: { timeoutMs?: number }) =>
    request<VideoAsset>(`/video/assets/${encodeURIComponent(assetId)}/poll`, {
      method: "POST",
      token,
      timeoutMs: opts?.timeoutMs ?? 90_000,
    }),
  getPublicShare: (token: string) => request<ShareLinkPublic>(`/public/shares/${encodeURIComponent(token)}`),
  unlockPublicShare: (token: string, password: string) =>
    request<ShareLinkPublic>(`/public/shares/${encodeURIComponent(token)}/unlock`, {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  getEffectiveLimits: (token: string, workspaceId: string) =>
    request<EffectiveLimits>(`/billing/addons?workspace_id=${encodeURIComponent(workspaceId)}`, { token }),
  cancelAddon: (token: string, workspaceId: string, addonType: AddOnType) =>
    request<{ message: string }>(`/billing/addons/${encodeURIComponent(addonType)}?workspace_id=${encodeURIComponent(workspaceId)}`, {
      method: "DELETE",
      token,
    }),

  listPlayModels: (token?: string | null, workspaceId?: string | null) =>
    request<import("./types").PlayModelOption[]>(
      workspaceId
        ? `/play/models?workspace_id=${encodeURIComponent(workspaceId)}`
        : "/play/models",
      { token: token ?? undefined },
    ),
  playQuote: (
    token: string | null | undefined,
    payload: {
      mode: import("./types").PlayMode;
      model?: string | null;
      duration_seconds?: number | null;
      prompt?: string | null;
      resolution?: string | null;
      count?: number;
      generate_audio?: boolean | null;
      return_last_frame?: boolean | null;
      has_face?: boolean;
      ref_image_count?: number;
      ref_video_count?: number;
      ref_audio_count?: number;
      continue_from?: boolean;
      cloned_voice?: boolean;
      has_scene?: boolean;
    },
  ) =>
    request<import("./types").PlayQuote>("/play/quote", {
      method: "POST",
      token: token ?? undefined,
      body: JSON.stringify(payload),
    }),
  playGenerate: (
    token: string,
    payload: {
      workspace_id: string;
      mode: import("./types").PlayMode;
      platform: import("./types").PlayPlatform;
      prompt: string;
      model?: string | null;
      face_asset_id?: string | null;
      voice?: string | null;
      duration_seconds?: number | null;
      resolution?: string | null;
      generate_audio?: boolean | null;
      return_last_frame?: boolean | null;
      reference_asset_ids?: string[];
      reference_roles?: string[];
      count?: number;
      continue_from_asset_id?: string | null;
      revoice_of_asset_id?: string | null;
      /** Lip-sync place. Empty cover-crops the Face; set builds a one-off plate. */
      scene?: string | null;
    },
    /**
     * Stable per-submission id. A resubmit after the client-side timeout would
     * otherwise reserve credits and start a second provider job.
     */
    idempotencyKey?: string,
  ) =>
    request<import("./types").PlayGenerateResponse>("/play/generate", {
      method: "POST",
      token,
      body: JSON.stringify(
        idempotencyKey ? { ...payload, client_request_id: idempotencyKey } : payload,
      ),
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
      timeoutMs: AI_REQUEST_TIMEOUT_MS,
    }),
  /** Rewrite a draft prompt for the selected mode. Free, rate limited server-side. */
  /** Talk a draft into shape before generating. Free, rate limited server-side. */
  playAssist: (
    token: string,
    payload: {
      workspace_id: string;
      mode: import("./types").PlayMode;
      draft: Partial<import("./types").PlayAssistDraft>;
      messages: import("./types").PlayAssistMessage[];
      source?: import("./types").PlayAssistSource | null;
    },
  ) =>
    request<import("./types").PlayAssistResponse>("/play/assist", {
      method: "POST",
      token,
      body: JSON.stringify(payload),
      timeoutMs: AI_REQUEST_TIMEOUT_MS,
    }),
  uploadPlayRef: (
    token: string,
    workspaceId: string,
    file: File,
    kind?: "image" | "video" | "audio",
    label?: string,
  ) => {
    const formData = new FormData();
    formData.set("workspace_id", workspaceId);
    formData.set("file", file);
    if (kind) formData.set("kind", kind);
    if (label?.trim()) formData.set("label", label.trim());
    return upload<import("./types").PlayRef>("/play/refs", formData, token);
  },
  listPlayRefs: (token: string, workspaceId: string, limit = 40) =>
    request<import("./types").PlayRef[]>(
      `/play/refs?workspace_id=${encodeURIComponent(workspaceId)}&limit=${limit}`,
      { token },
    ),
  playUploadAvatar: (
    token: string,
    workspaceId: string,
    file: File,
    consentName: string,
    label?: string,
  ) => {
    const formData = new FormData();
    formData.set("workspace_id", workspaceId);
    formData.set("file", file);
    formData.set("consent_confirmed", "true");
    formData.set("consent_name", consentName);
    if (label?.trim()) formData.set("label", label.trim());
    return upload<import("./types").PlayGeneration>("/play/avatar-image", formData, token);
  },
  listPlayFaces: (token: string, workspaceId: string, limit = 40) =>
    request<import("./types").PlayFace[]>(
      `/play/faces?workspace_id=${encodeURIComponent(workspaceId)}&limit=${limit}`,
      { token },
    ),
  generatePlayFace: (
    token: string,
    payload: {
      workspace_id: string;
      prompt: string;
      label?: string | null;
      consent_name: string;
      consent_confirmed: boolean;
      model?: string | null;
    },
  ) =>
    request<import("./types").PlayFace>("/play/faces/generate", {
      method: "POST",
      token,
      body: JSON.stringify(payload),
      timeoutMs: AI_REQUEST_TIMEOUT_MS,
    }),
  deletePlayFace: (token: string, faceId: string) =>
    request<void>(`/play/faces/${encodeURIComponent(faceId)}`, {
      method: "DELETE",
      token,
    }),
  editPlayFace: (
    token: string,
    faceId: string,
    payload: {
      workspace_id: string;
      instruction: string;
      kind: "touchup" | "look";
      save?: "replace" | "new";
      model?: string | null;
    },
  ) =>
    request<import("./types").PlayFace>(`/play/faces/${encodeURIComponent(faceId)}/edit`, {
      method: "POST",
      token,
      body: JSON.stringify(payload),
      timeoutMs: AI_REQUEST_TIMEOUT_MS,
    }),
  bindPlayFaceVoice: (
    token: string,
    faceId: string,
    workspaceId: string,
    boundVoiceId: string | null,
  ) =>
    request<import("./types").PlayFace>(`/play/faces/${encodeURIComponent(faceId)}/voice`, {
      method: "PATCH",
      token,
      body: JSON.stringify({ workspace_id: workspaceId, bound_voice_id: boundVoiceId }),
    }),
  restorePlayFace: (token: string, faceId: string, workspaceId: string) =>
    request<import("./types").PlayFace>(`/play/faces/${encodeURIComponent(faceId)}/restore`, {
      method: "POST",
      token,
      body: JSON.stringify({ workspace_id: workspaceId }),
    }),
  listPlayGenerations: (token: string, workspaceId: string, limit = 40) =>
    request<import("./types").PlayGeneration[]>(
      `/play/generations?workspace_id=${encodeURIComponent(workspaceId)}&limit=${limit}`,
      { token },
    ),
  getPlayGeneration: (token: string, assetId: string) =>
    request<import("./types").PlayGeneration>(`/play/generations/${encodeURIComponent(assetId)}`, { token }),
  deletePlayGeneration: (token: string, assetId: string) =>
    request<void>(`/play/generations/${encodeURIComponent(assetId)}`, {
      method: "DELETE",
      token,
    }),

  /** Built-in voices + cloned voices + custom-voice access for the workspace. */
  listPlayVoices: (token: string, workspaceId: string) =>
    request<import("./types").PlayVoicesResponse>(
      `/play/voices?workspace_id=${encodeURIComponent(workspaceId)}`,
      { token },
    ),
  clonePlayVoice: (
    token: string,
    workspaceId: string,
    options: {
      label: string;
      consentName: string;
      gender: "female" | "male" | "neutral";
      file: File;
      language?: string;
      bindFaceId?: string | null;
    },
  ) => {
    const formData = new FormData();
    formData.set("workspace_id", workspaceId);
    formData.set("label", options.label.trim());
    formData.set("consent_name", options.consentName.trim());
    formData.set("consent_confirmed", "true");
    formData.set("gender", options.gender);
    formData.set("language", options.language || "en");
    if (options.bindFaceId) formData.set("bind_face_id", options.bindFaceId);
    formData.set("file", options.file);
    return upload<import("./types").PlayVoiceOption>("/play/voices/clone", formData, token);
  },
  deletePlayVoice: (token: string, workspaceId: string, voiceId: string) =>
    request<void>(
      `/play/voices/${encodeURIComponent(voiceId)}?workspace_id=${encodeURIComponent(workspaceId)}`,
      {
        method: "DELETE",
        token,
      },
    ),
  /** Short MP3 sample for a voice id. Returns a blob URL (caller should revoke). */
  previewPlayVoice: async (token: string, workspaceId: string, voice: string, text?: string | null) => {
    const headers = new Headers({ "Content-Type": "application/json" });
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(`${API_BASE_URL}/play/voices/preview`, {
      method: "POST",
      headers,
      credentials: "include",
      body: JSON.stringify({
        workspace_id: workspaceId,
        voice,
        text: text?.trim() || null,
      }),
      signal: typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function"
        ? AbortSignal.timeout(45_000)
        : undefined,
    });
    if (!response.ok) {
      throw new ApiError(await parseErrorMessage(response), response.status);
    }
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  },

};
