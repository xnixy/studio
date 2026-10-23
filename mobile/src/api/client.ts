import { API_BASE_URL, CLIENT_HEADER } from "../lib/config";
import { markNetworkOffline, markNetworkOnline } from "../lib/network";
import type {
  AuthResponse,
  BillingStatus,
  MaintenanceStatus,
  PlayAssistDraft,
  PlayAssistMessage,
  PlayAssistResponse,
  PlayAssistSource,
  PlayFace,
  PlayGenerateResponse,
  PlayGeneration,
  PlayQuote,
  PlayMode,
  PlayModelOption,
  PlayPlatform,
  User,
  Workspace,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string | null;
  constructor(message: string, status: number, code?: string | null) {
    super(message);
    this.status = status;
    this.code = code ?? null;
  }
}

type TokenHandlers = {
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
  applySession: (session: AuthResponse) => void | Promise<void>;
  clearSession: () => void | Promise<void>;
};

let handlers: TokenHandlers | null = null;
let refreshInFlight: Promise<string | null> | null = null;

export function bindAuthHandlers(next: TokenHandlers | null) {
  handlers = next;
}

/** Current access token for media Image/Video loads (no network). */
export function peekAccessToken(): string | null {
  return handlers?.getAccessToken() ?? null;
}

const DEFAULT_TIMEOUT_MS = 15_000;
const AI_TIMEOUT_MS = 150_000;

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
    if (Array.isArray(error.detail) && error.detail.length > 0) {
      const first = error.detail[0] as { msg?: string; message?: string } | string;
      if (typeof first === "string" && first.trim()) return { message: first };
      if (first && typeof first === "object") {
        const msg = first.msg || first.message;
        if (typeof msg === "string" && msg.trim()) return { message: msg };
      }
      return {
        message: response.status === 422 ? "Check the form fields and try again." : "Request failed",
      };
    }
  } catch {
    if (text.trim()) return { message: text };
  }
  return { message: "Request failed" };
}

async function parseError(response: Response): Promise<string> {
  return (await parseErrorPayload(response)).message;
}

/** RN / Expo uploads need file:// (or content://), not a bare filesystem path. */
function normalizeFormFileUri(uri: string): string {
  const u = (uri || "").trim();
  if (!u) return u;
  if (
    u.startsWith("file://") ||
    u.startsWith("content://") ||
    u.startsWith("http://") ||
    u.startsWith("https://") ||
    u.startsWith("ph://") ||
    u.startsWith("assets-library://")
  ) {
    return u;
  }
  if (u.startsWith("/")) return `file://${u}`;
  return u;
}

function parseErrorBody(text: string, status: number): string {
  try {
    const error = JSON.parse(text) as { error?: string; detail?: unknown };
    if (typeof error.error === "string" && error.error.trim()) return error.error;
    if (typeof error.detail === "string" && error.detail.trim()) return error.detail;
    if (Array.isArray(error.detail) && error.detail.length > 0) {
      const first = error.detail[0] as { msg?: string; message?: string } | string;
      if (typeof first === "string" && first.trim()) return first;
      if (first && typeof first === "object") {
        const msg = first.msg || first.message;
        if (typeof msg === "string" && msg.trim()) return msg;
      }
      return status === 422 ? "Check the form fields and try again." : "Request failed";
    }
  } catch {
    if (text.trim()) return text.slice(0, 280);
  }
  return "Request failed";
}

type RequestOptions = RequestInit & {
  token?: string | null;
  skipAuthRetry?: boolean;
  timeoutMs?: number;
};

/** Server says we lost a rotation race; a newer token is already stored. */
const REFRESH_RACE_CODE = "refresh_race";

async function refreshAccessToken(): Promise<string | null> {
  if (!handlers) return null;
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    const post = (token: string) =>
      request<AuthResponse | undefined>("/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: token }),
        skipAuthRetry: true,
      });
    try {
      const refreshToken = handlers?.getRefreshToken() ?? null;
      if (!refreshToken) {
        await handlers?.clearSession();
        return null;
      }
      let session: AuthResponse | undefined;
      try {
        session = await post(refreshToken);
      } catch (error) {
        // Another call rotated a moment ago. Retry once with whatever is stored
        // now rather than ending a session that is actually fine.
        if (error instanceof ApiError && error.code === REFRESH_RACE_CODE) {
          const current = handlers?.getRefreshToken() ?? null;
          if (!current) throw error;
          session = await post(current);
        } else {
          throw error;
        }
      }
      if (!session?.access_token || !session.user) {
        await handlers?.clearSession();
        return null;
      }
      await handlers?.applySession(session);
      return session.access_token;
    } catch (error) {
      // Only a definitive rejection ends the session. Phones lose signal
      // constantly, and treating a timeout as "signed out" is why the app
      // dropped sessions on a bad connection.
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        await handlers?.clearSession();
      }
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { token: tokenOpt, skipAuthRetry, timeoutMs, ...init } = options;
  const headers = new Headers(init.headers);
  headers.set("X-Studio-Client", CLIENT_HEADER);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token =
    tokenOpt ??
    (path.startsWith("/auth/login") ||
    path.startsWith("/auth/register") ||
    path.startsWith("/auth/refresh")
      ? null
      : handlers?.getAccessToken() ?? null);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const budget = timeoutMs === undefined ? DEFAULT_TIMEOUT_MS : timeoutMs;
  const controller = new AbortController();
  const timer =
    budget > 0
      ? setTimeout(() => controller.abort(), budget)
      : undefined;

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new ApiError("This is taking longer than usual. Try again in a moment.", 0);
    }
    markNetworkOffline();
    if (__DEV__) {
      throw new ApiError(
        `Network error. Cannot reach ${API_BASE_URL}. Same Wi-Fi as your PC, API on :3001, or set EXPO_PUBLIC_API_BASE_URL.`,
        0,
      );
    }
    throw new ApiError("Could not reach the server. Check your connection and try again.", 0);
  } finally {
    if (timer) clearTimeout(timer);
  }

  markNetworkOnline();

  if (response.status === 401 && !skipAuthRetry && !path.startsWith("/auth/")) {
    const next = await refreshAccessToken();
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

/**
 * Multipart file upload via expo-file-system (native URLSession on iOS).
 *
 * Avoid React Native `fetch` + FormData + AbortSignal — that combo often throws
 * "Network request failed" on iOS even when JSON API calls work fine.
 */
async function uploadMultipart<T>(
  path: string,
  file: { uri: string; name: string; type: string },
  fields: Record<string, string>,
  token: string,
  opts?: { skipAuthRetry?: boolean },
): Promise<T> {
  const FileSystem = await import("expo-file-system/legacy");
  const fileUri = normalizeFormFileUri(file.uri);
  if (!fileUri) {
    throw new ApiError("Photo file is missing. Pick the image again.", 400);
  }

  try {
    const info = await FileSystem.getInfoAsync(fileUri);
    if (!info.exists || info.isDirectory) {
      throw new ApiError("Photo file is missing. Pick the image again.", 400);
    }
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError("Could not read the photo file. Try another image.", 400);
  }

  const url = `${API_BASE_URL}${path}`;
  let result: { status: number; body: string };
  try {
    result = await FileSystem.uploadAsync(url, fileUri, {
      httpMethod: "POST",
      uploadType: FileSystem.FileSystemUploadType.MULTIPART,
      fieldName: "file",
      mimeType: file.type || "application/octet-stream",
      parameters: fields,
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Studio-Client": CLIENT_HEADER,
        Accept: "application/json",
      },
      // Foreground so a backgrounded app does not leave the JS promise hanging forever.
      sessionType: FileSystem.FileSystemSessionType.FOREGROUND,
    });
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    if (__DEV__) {
      throw new ApiError(`Upload failed: ${detail} (${API_BASE_URL})`, 0);
    }
    throw new ApiError("Could not reach the server to upload. Check your connection.", 0);
  }

  if (result.status === 401 && !opts?.skipAuthRetry && !path.startsWith("/auth/")) {
    const next = await refreshAccessToken();
    if (next) {
      return uploadMultipart<T>(path, file, fields, next, { skipAuthRetry: true });
    }
  }

  if (result.status < 200 || result.status >= 300) {
    throw new ApiError(parseErrorBody(result.body || "", result.status), result.status);
  }

  if (!result.body?.trim()) {
    return undefined as T;
  }
  try {
    return JSON.parse(result.body) as T;
  } catch {
    throw new ApiError("Upload succeeded but the response was invalid.", result.status);
  }
}

export const api = {
  maintenance: () => request<MaintenanceStatus>("/maintenance"),

  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      skipAuthRetry: true,
    }),

  publicConfig: () =>
    request<{
      turnstile_site_key: string | null;
      turnstile_enabled: boolean;
      turnstile_required: boolean;
    }>("/public-config", { skipAuthRetry: true }),

  register: (payload: {
    email: string;
    password: string;
    fullName: string;
    turnstileToken?: string | null;
  }) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: payload.email,
        password: payload.password,
        full_name: payload.fullName,
        turnstile_token: payload.turnstileToken ?? null,
      }),
      skipAuthRetry: true,
    }),

  refresh: (refreshToken: string) =>
    request<AuthResponse | undefined>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
      skipAuthRetry: true,
    }),

  logout: (refreshToken: string | null) =>
    request<{ message: string }>("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
      skipAuthRetry: true,
    }),

  forgotPassword: (email: string) =>
    request<{ message: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
      skipAuthRetry: true,
    }),

  resetPassword: (token: string, password: string) =>
    request<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
      skipAuthRetry: true,
    }),

  verifyEmail: (token: string) =>
    request<{ message: string }>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
      skipAuthRetry: true,
    }),

  /**
   * Resend verification. When signed in, uses Bearer only.
   * When signed out, pass the account email.
   */
  resendVerification: (email?: string | null) =>
    request<{ message: string }>("/auth/resend-verification", {
      method: "POST",
      body: email?.trim() ? JSON.stringify({ email: email.trim() }) : JSON.stringify({}),
      skipAuthRetry: true,
    }),

  me: (token?: string) => request<{ user: User }>("/auth/me", { token }),

  updateProfile: (fullName: string | null) =>
    request<{ user: User }>("/auth/profile", {
      method: "PATCH",
      body: JSON.stringify({ full_name: fullName }),
    }),

  registerPushToken: (payload: { token: string; platform: string; device_id?: string }) =>
    request<{ message: string }>("/devices/push-token", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  unregisterPushToken: (payload: { token: string; platform: string }) =>
    request<{ message: string }>("/devices/push-token", {
      method: "DELETE",
      body: JSON.stringify(payload),
    }),

  deleteAccount: (password: string) =>
    request<{ message: string }>("/auth/delete-account", {
      method: "POST",
      body: JSON.stringify({ password, confirm: "DELETE" }),
    }),

  listIapProducts: () =>
    request<
      {
        apple_product_id: string;
        kind: "plan" | "pack";
        sku: string;
        title: string;
        description: string;
        store_type: "subscription" | "consumable";
        price_cents: number;
      }[]
    >("/billing/iap/products"),

  confirmIapPurchase: (payload: {
    workspace_id: string;
    apple_product_id: string;
    transaction_id: string;
    signed_transaction?: string | null;
  }) =>
    request<{
      ok: boolean;
      kind: string;
      sku: string;
      message: string;
      already_processed: boolean;
    }>("/billing/iap/confirm", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  /** Personal space only (one per user). */
  listWorkspaces: () => request<Workspace[]>("/workspaces"),

  billingStatus: (workspaceId: string) =>
    request<BillingStatus>(`/billing?workspace_id=${encodeURIComponent(workspaceId)}`),

  listPlayModels: (workspaceId?: string | null) =>
    request<PlayModelOption[]>(
      workspaceId
        ? `/play/models?workspace_id=${encodeURIComponent(workspaceId)}`
        : "/play/models",
    ),

  listPlayVoices: (workspaceId: string) =>
    request<import("./types").PlayVoicesResponse>(
      `/play/voices?workspace_id=${encodeURIComponent(workspaceId)}`,
    ),

  clonePlayVoice: async (
    workspaceId: string,
    options: {
      label: string;
      consentName: string;
      gender: "female" | "male" | "neutral";
      file: { uri: string; name: string; type: string };
      language?: string;
      bindFaceId?: string | null;
    },
  ) => {
    const token = handlers?.getAccessToken();
    if (!token) throw new ApiError("Not authenticated", 401);
    const fields: Record<string, string> = {
      workspace_id: workspaceId,
      label: options.label.trim(),
      consent_name: options.consentName.trim(),
      consent_confirmed: "true",
      gender: options.gender,
      language: options.language || "en",
    };
    if (options.bindFaceId) fields.bind_face_id = options.bindFaceId;
    return uploadMultipart<import("./types").PlayVoiceOption>(
      "/play/voices/clone",
      options.file,
      fields,
      token,
    );
  },

  deletePlayVoice: (workspaceId: string, voiceId: string) =>
    request<void>(
      `/play/voices/${encodeURIComponent(voiceId)}?workspace_id=${encodeURIComponent(workspaceId)}`,
      { method: "DELETE" },
    ),

  /**
   * Short MP3 sample for a voice id.
   * Returns a local file path (native) playable with expo-audio.
   */
  previewPlayVoice: async (
    workspaceId: string,
    voice: string,
    text?: string | null,
  ): Promise<string> => {
    const token = handlers?.getAccessToken();
    if (!token) throw new ApiError("Not authenticated", 401);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 45_000);
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/play/voices/preview`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          Accept: "audio/mpeg, application/octet-stream, */*",
          "X-Studio-Client": CLIENT_HEADER,
        },
        body: JSON.stringify({
          workspace_id: workspaceId,
          voice,
          text: text?.trim() || null,
        }),
        signal: controller.signal,
      });
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        throw new ApiError("Preview timed out. Try again.", 0);
      }
      throw new ApiError("Could not load preview.", 0);
    } finally {
      clearTimeout(timer);
    }
    if (!response.ok) {
      throw new ApiError(await parseError(response), response.status);
    }
    // Write temp file so expo-audio can play it (blob URLs are flaky on native).
    const buf = await response.arrayBuffer();
    if (!buf.byteLength) {
      throw new ApiError("Preview audio was empty.", 0);
    }
    try {
      const FileSystem = await import("expo-file-system/legacy");
      const cacheDir = FileSystem.cacheDirectory;
      if (!cacheDir) {
        throw new Error("No cache directory");
      }
      // Ensure a real file:// URI — some Expo runtimes return bare paths.
      const path = `${cacheDir}voice-preview-${Date.now()}.mp3`;
      const bytes = new Uint8Array(buf);
      // Chunked base64 encode (avoid spreading huge arrays into fromCharCode).
      let binary = "";
      const chunk = 0x2000;
      for (let i = 0; i < bytes.length; i += chunk) {
        const slice = bytes.subarray(i, i + chunk);
        binary += String.fromCharCode.apply(null, slice as unknown as number[]);
      }
      const b64 = globalThis.btoa(binary);
      await FileSystem.writeAsStringAsync(path, b64, {
        encoding: FileSystem.EncodingType.Base64,
      });
      const info = await FileSystem.getInfoAsync(path);
      if (!info.exists || !("size" in info) || !info.size) {
        throw new Error("Preview file missing after write");
      }
      // Always return a file:// URI for AVPlayer.
      return path.startsWith("file://") ? path : `file://${path}`;
    } catch {
      throw new ApiError("Could not save preview audio.", 0);
    }
  },

  playQuote: (payload: {
    mode: PlayMode;
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
  }) =>
    request<PlayQuote>("/play/quote", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  playGenerate: (payload: {
    workspace_id: string;
    mode: PlayMode;
    platform: PlayPlatform;
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
    /** Client UUID so retries do not double-charge. */
    client_request_id?: string | null;
  }) => {
    const clientRequestId =
      (payload.client_request_id || "").trim() ||
      `mob-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
    const { client_request_id: _omit, ...rest } = payload;
    return request<PlayGenerateResponse>("/play/generate", {
      method: "POST",
      headers: { "Idempotency-Key": clientRequestId },
      body: JSON.stringify({ ...rest, client_request_id: clientRequestId }),
      timeoutMs: AI_TIMEOUT_MS,
    });
  },

  /** Talk a draft into shape before generating. Free, rate limited server-side. */
  playAssist: (payload: {
    workspace_id: string;
    mode: PlayMode;
    draft: Partial<PlayAssistDraft>;
    messages: PlayAssistMessage[];
    source?: PlayAssistSource | null;
  }) =>
    request<PlayAssistResponse>("/play/assist", {
      method: "POST",
      body: JSON.stringify(payload),
      timeoutMs: AI_TIMEOUT_MS,
    }),

  uploadPlayRef: async (
    workspaceId: string,
    file: { uri: string; name: string; type: string },
    kind?: "image" | "video" | "audio",
    label?: string,
  ) => {
    const token = handlers?.getAccessToken();
    if (!token) throw new ApiError("Not authenticated", 401);
    const fields: Record<string, string> = { workspace_id: workspaceId };
    if (kind) fields.kind = kind;
    if (label?.trim()) fields.label = label.trim();
    return uploadMultipart<import("./types").PlayRef>("/play/refs", file, fields, token);
  },

  listPlayRefs: (workspaceId: string, limit = 40) =>
    request<import("./types").PlayRef[]>(
      `/play/refs?workspace_id=${encodeURIComponent(workspaceId)}&limit=${limit}`,
    ),

  listPlayFaces: (workspaceId: string, limit = 40) =>
    request<PlayFace[]>(
      `/play/faces?workspace_id=${encodeURIComponent(workspaceId)}&limit=${limit}`,
    ),

  generatePlayFace: (payload: {
    workspace_id: string;
    prompt: string;
    label?: string | null;
    consent_name: string;
    consent_confirmed: boolean;
    model?: string | null;
  }) =>
    request<PlayFace>("/play/faces/generate", {
      method: "POST",
      body: JSON.stringify(payload),
      timeoutMs: AI_TIMEOUT_MS,
    }),

  deletePlayFace: (faceId: string) =>
    request<void>(`/play/faces/${encodeURIComponent(faceId)}`, { method: "DELETE" }),

  editPlayFace: (payload: {
    faceId: string;
    workspace_id: string;
    instruction: string;
    kind: "touchup" | "look";
    save?: "replace" | "new";
    model?: string | null;
  }) =>
    request<PlayFace>(`/play/faces/${encodeURIComponent(payload.faceId)}/edit`, {
      method: "POST",
      body: JSON.stringify({
        workspace_id: payload.workspace_id,
        instruction: payload.instruction,
        kind: payload.kind,
        save: payload.save ?? "replace",
        model: payload.model ?? null,
      }),
      timeoutMs: AI_TIMEOUT_MS,
    }),

  bindPlayFaceVoice: (faceId: string, workspaceId: string, boundVoiceId: string | null) =>
    request<PlayFace>(`/play/faces/${encodeURIComponent(faceId)}/voice`, {
      method: "PATCH",
      body: JSON.stringify({ workspace_id: workspaceId, bound_voice_id: boundVoiceId }),
    }),

  restorePlayFace: (faceId: string, workspaceId: string) =>
    request<PlayFace>(`/play/faces/${encodeURIComponent(faceId)}/restore`, {
      method: "POST",
      body: JSON.stringify({ workspace_id: workspaceId }),
    }),

  uploadPlayFace: async (
    workspaceId: string,
    file: { uri: string; name: string; type: string },
    consentName: string,
    label?: string,
  ) => {
    const token = handlers?.getAccessToken();
    if (!token) throw new ApiError("Not authenticated", 401);
    // Always send jpeg mime after client-side convert (iOS HEIC fix).
    const name = file.name?.match(/\.(jpe?g|png|webp)$/i)
      ? file.name
      : `face-${Date.now()}.jpg`;
    const type =
      file.type && file.type !== "image/heic" && file.type !== "image/heif"
        ? file.type
        : "image/jpeg";
    const fields: Record<string, string> = {
      workspace_id: workspaceId,
      consent_confirmed: "true",
      consent_name: consentName,
    };
    if (label?.trim()) fields.label = label.trim();
    return uploadMultipart<PlayGeneration>(
      "/play/avatar-image",
      { uri: file.uri, name, type },
      fields,
      token,
    );
  },

  listPlayGenerations: (workspaceId: string, limit = 40) =>
    request<PlayGeneration[]>(
      `/play/generations?workspace_id=${encodeURIComponent(workspaceId)}&limit=${limit}`,
    ),

  getPlayGeneration: (assetId: string) =>
    request<PlayGeneration>(`/play/generations/${encodeURIComponent(assetId)}`),

  deletePlayGeneration: (assetId: string) =>
    request<void>(`/play/generations/${encodeURIComponent(assetId)}`, { method: "DELETE" }),

  pollVideoAsset: (assetId: string) =>
    request<PlayGeneration | { status: string; url?: string | null }>(
      `/video/assets/${encodeURIComponent(assetId)}/poll`,
      { method: "POST", timeoutMs: 60_000 },
    ),
};
