import { peekAccessToken } from "../api/client";
import type { PlayGeneration } from "../api/types";
import { API_BASE_URL } from "./config";

function apiOrigin(): string {
  return API_BASE_URL.replace(/\/api\/?$/, "");
}

/** Hosts the phone can never use as "this machine" (dev API mistakes). */
function isLoopbackHost(hostname: string): boolean {
  const h = hostname.toLowerCase();
  return h === "localhost" || h === "127.0.0.1" || h === "0.0.0.0" || h === "::1";
}

/**
 * Turn relative `/api/media/...` into an absolute URL for Image/Video on device.
 * Rewrites localhost absolute media URLs onto API_BASE_URL so Expo Go on a
 * physical phone does not try to stream from the phone itself.
 */
export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  const u = url.trim();
  if (!u) return null;
  if (u.startsWith("blob:") || u.startsWith("data:")) {
    return u;
  }
  if (u.startsWith("http://") || u.startsWith("https://")) {
    try {
      const parsed = new URL(u);
      if (isLoopbackHost(parsed.hostname) && parsed.pathname.includes("/api/media/")) {
        return `${apiOrigin()}${parsed.pathname}${parsed.search}${parsed.hash}`;
      }
    } catch {
      /* keep original */
    }
    return u;
  }
  if (u.startsWith("/")) {
    return `${apiOrigin()}${u}`;
  }
  return u;
}

/**
 * Stable identity for a media URL across API re-signs.
 * Backend re-issues fresh ?exp=&sig= on every list; if Image recyclingKey uses
 * the full URI, posters reload every poll (looks like a refresh loop).
 */
export function mediaStableKey(url: string | null | undefined): string | null {
  const uri = resolveMediaUrl(url);
  if (!uri) return null;
  const hash = uri.indexOf("#");
  const noHash = hash >= 0 ? uri.slice(0, hash) : uri;
  const q = noHash.indexOf("?");
  return q >= 0 ? noHash.slice(0, q) : noHash;
}

/**
 * True when a signed media URL's ``exp`` has passed (or is about to).
 * Pinned URLs outlive their signature on a screen left open, and the retry then
 * replays a URL the API answers with 401. AVPlayer reports that as
 * "Failed to load the player item".
 */
export function isSignedMediaUrlExpired(
  url: string | null | undefined,
  { skewSeconds = 60 }: { skewSeconds?: number } = {},
): boolean {
  if (!url) return false;
  const match = /[?&]exp=(\d+)/.exec(url);
  if (!match) return false;
  const exp = Number(match[1]);
  if (!Number.isFinite(exp) || exp <= 0) return false;
  return exp * 1000 <= Date.now() + skewSeconds * 1000;
}

/** Refetch a generation when its signed URL is past exp, so Share/Save/play still work. */
export async function freshPlayMediaUrl(
  gen: { id: string; url?: string | null },
  refetch: (id: string) => Promise<{ url?: string | null }>,
): Promise<string | null> {
  if (gen.url && !isSignedMediaUrlExpired(gen.url)) return gen.url;
  try {
    const next = await refetch(gen.id);
    return next.url ?? gen.url ?? null;
  } catch {
    return gen.url ?? null;
  }
}

/**
 * Keep previously signed media URLs when only exp/sig changed.
 * Stops expo-image thrashing on Clips list refetch.
 */
export function preserveSignedMediaUrls(
  prev: PlayGeneration[] | undefined,
  next: PlayGeneration[],
): PlayGeneration[] {
  if (!prev?.length) return next;
  const byId = new Map(prev.map((g) => [g.id, g]));
  return next.map((g) => {
    const old = byId.get(g.id);
    if (!old) return g;
    if ((old.status || "") !== (g.status || "")) return g;

    let url = g.url;
    let poster_url = g.poster_url;
    // Keeping the old URL stops expo-image thrashing, but never past its own
    // signature window: the server 401s an expired one and Retry would replay it.
    if (
      mediaStableKey(old.url) &&
      mediaStableKey(old.url) === mediaStableKey(g.url) &&
      old.url &&
      !isSignedMediaUrlExpired(old.url)
    ) {
      url = old.url;
    }
    if (
      mediaStableKey(old.poster_url) &&
      mediaStableKey(old.poster_url) === mediaStableKey(g.poster_url) &&
      old.poster_url &&
      !isSignedMediaUrlExpired(old.poster_url)
    ) {
      poster_url = old.poster_url;
    }

    let metadata = g.metadata;
    if (old.metadata && g.metadata && metadata) {
      const nextMeta = { ...g.metadata };
      for (const key of [
        "poster_url",
        "clip_poster_url",
        "face_image_url",
        "last_frame_url",
        "image_url",
        "thumb_url",
        "thumbnail_url",
        "download_url",
        "media_url",
      ] as const) {
        const a = old.metadata[key];
        const b = g.metadata[key];
        if (
          typeof a === "string" &&
          typeof b === "string" &&
          mediaStableKey(a) === mediaStableKey(b)
        ) {
          nextMeta[key] = a;
        }
      }
      metadata = nextMeta;
    }

    if (url === g.url && poster_url === g.poster_url && metadata === g.metadata) return g;
    return { ...g, url, poster_url, metadata };
  });
}

/**
 * Private `/api/media` needs either a path signature or a Bearer token.
 * expo-image / expo-video do not send Authorization by default, so store builds
 * fail to load thumbs/clips when the sig is missing or stale. Expo Go often
 * hid this when pointed at a LAN API with looser local media.
 */
export function isPrivateApiMediaUrl(url: string | null | undefined): boolean {
  if (!url) return false;
  const u = url.trim();
  if (!u) return false;
  if (u.includes("/api/media/")) return true;
  try {
    const base = API_BASE_URL.replace(/\/api\/?$/, "");
    if (base && u.startsWith(base) && u.includes("/media/")) return true;
  } catch {
    /* ignore */
  }
  return false;
}

export function mediaAuthHeaders(url: string | null | undefined): Record<string, string> | undefined {
  if (!isPrivateApiMediaUrl(url)) return undefined;
  const token = peekAccessToken();
  if (!token) return undefined;
  return { Authorization: `Bearer ${token}` };
}

/** Source object for expo-image (uri + optional auth headers + stable cache key). */
export function mediaImageSource(
  url: string | null | undefined,
): { uri: string; headers?: Record<string, string>; cacheKey?: string } | null {
  const uri = resolveMediaUrl(url);
  if (!uri) return null;
  const headers = mediaAuthHeaders(uri);
  const cacheKey = mediaStableKey(uri) ?? undefined;
  if (headers) return { uri, headers, cacheKey };
  return cacheKey ? { uri, cacheKey } : { uri };
}

/**
 * Stream source for expo-video (progressive HTTP only, no local download).
 *
 * Two deliberate choices, both needed for clips to actually play on iOS:
 *  1. `contentType: "progressive"`. Play clips are progressive MP4, but the
 *     signed URL buries the `.mp4` before `?exp=&sig=`, so `auto` extension
 *     sniffing is unreliable and AVPlayer can hang on "loading" forever.
 *     Naming the type removes the guesswork.
 *  2. No Authorization header when the URL is already signed. A valid path
 *     signature authorizes on its own (the server verifies it before any
 *     Bearer). Adding a header forces expo-video onto iOS's
 *     `AVURLAssetHTTPHeaderFieldsKey` path, which is flaky for range streaming.
 *     Bearer is only a fallback for unsigned URLs.
 */
export function mediaVideoSource(
  url: string | null | undefined,
): { uri: string; headers?: Record<string, string>; contentType?: "auto" | "progressive" } | null {
  const uri = resolveMediaUrl(url);
  if (!uri) return null;
  // A valid path signature is self-authorizing; skip the flaky header path.
  if (/[?&]sig=/.test(uri)) {
    return { uri, contentType: "progressive" };
  }
  const headers = mediaAuthHeaders(uri);
  if (headers) {
    return { uri, headers, contentType: "progressive" };
  }
  return { uri, contentType: "progressive" };
}

export function isVideoGeneration(gen: { asset_type?: string; url?: string | null }): boolean {
  if (gen.asset_type === "video") return true;
  const u = gen.url || "";
  return /\.(mp4|webm|mov)(\?|$)/i.test(u);
}

/**
 * Still frame for list thumbs.
 * Prefer API poster_url (signed) first, then metadata fallbacks, then face
 * only while processing. Ready talking clips must not show the identity plate.
 *
 * Do not prefer raw metadata.clip_poster_url over gen.poster_url: metadata is
 * often an unsigned `/api/media/...` path that Image cannot load without a sig.
 */
export function playGenerationPosterUrl(gen: {
  asset_type?: string;
  status?: string | null;
  url?: string | null;
  poster_url?: string | null;
  metadata?: Record<string, unknown> | null;
}): string | null {
  const meta = gen.metadata || {};
  const status = (gen.status || "").toLowerCase();
  const readyVideo =
    isVideoGeneration({ asset_type: gen.asset_type, url: gen.url }) && status === "ready";
  const face =
    typeof meta.face_image_url === "string" && meta.face_image_url ? meta.face_image_url : null;

  if (gen.poster_url) {
    // API already prefers clip poster; still skip if it equals face on a ready video.
    if (readyVideo && face && gen.poster_url === face && !meta.clip_poster) {
      // fall through
    } else {
      return gen.poster_url;
    }
  }

  const clipPoster =
    (typeof meta.clip_poster_url === "string" && meta.clip_poster_url) ||
    (meta.clip_poster === true && typeof meta.poster_url === "string" && meta.poster_url) ||
    null;
  if (clipPoster) return clipPoster;

  const metaPoster = typeof meta.poster_url === "string" && meta.poster_url ? meta.poster_url : null;
  if (metaPoster && !(readyVideo && face && metaPoster === face && !meta.clip_poster)) {
    return metaPoster;
  }
  if (!readyVideo && face) return face;
  if (gen.asset_type === "image" && gen.url) return gen.url;
  if (gen.url && !isVideoGeneration({ asset_type: gen.asset_type, url: gen.url })) {
    return gen.url;
  }
  return null;
}
