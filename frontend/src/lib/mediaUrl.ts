/** Resolve API media paths so open/download work from the SPA (Vite proxy or absolute API). */

import { API_BASE_URL } from "../api";

/**
 * Turn relative `/api/media/...` (signed or not) into a browser-loadable URL.
 *
 * Production SPA is on example.com while the API is on api.example.com. Always prefer
 * the configured API origin for `/api/*` paths so posters/clips do not request
 * `https://example.com/api/media/...` (missing host / no media ACL).
 */

/** SPA hosts that must never serve private `/api/media` (API is on api.example.com). */
const SPA_ONLY_MEDIA_HOSTS = new Set(["example.com", "www.example.com"]);

function apiOriginFromBase(): string | null {
  if (!API_BASE_URL.startsWith("http")) return null;
  try {
    return new URL(API_BASE_URL).origin;
  } catch {
    return API_BASE_URL.replace(/\/api\/?$/, "") || null;
  }
}

/**
 * True when a signed media URL's window has passed.
 * Signatures carry ?exp=<unix seconds> and the server 401s afterwards, so a
 * long-lived view holding a pinned URL has to refetch rather than replay it.
 */
export function isSignedMediaUrlExpired(url: string | null | undefined, skewSeconds = 30): boolean {
  if (!url) return false;
  const match = /[?&]exp=(\d+)/.exec(url);
  if (!match) return false;
  const exp = Number(match[1]);
  if (!Number.isFinite(exp)) return false;
  return exp * 1000 <= Date.now() + skewSeconds * 1000;
}

export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  const u = url.trim();
  if (!u) return null;
  if (u.startsWith("blob:") || u.startsWith("data:")) {
    return u;
  }
  if (u.startsWith("http://") || u.startsWith("https://")) {
    // Absolute media on the SPA host is always wrong in production split-domain.
    // HTTP media on an HTTPS page is mixed content (Tailscale PUBLIC_API_BASE_URL).
    // Rewrite onto the API origin, or this page when /api is proxied.
    if (u.includes("/api/media/")) {
      try {
        const parsed = new URL(u);
        const apiOrigin = apiOriginFromBase();
        const pageOrigin =
          typeof window !== "undefined" && window.location?.origin ? window.location.origin : null;
        const targetOrigin = apiOrigin || pageOrigin;
        if (targetOrigin) {
          const target = new URL(targetOrigin);
          const host = parsed.hostname.toLowerCase();
          const onSpaHost =
            SPA_ONLY_MEDIA_HOSTS.has(host) ||
            (pageOrigin &&
              host === new URL(pageOrigin).hostname.toLowerCase() &&
              host !== target.hostname.toLowerCase());
          const mixed =
            typeof window !== "undefined" &&
            window.location.protocol === "https:" &&
            parsed.protocol === "http:";
          if ((onSpaHost || mixed) && parsed.origin !== target.origin) {
            return `${target.origin}${parsed.pathname}${parsed.search}${parsed.hash}`;
          }
        }
      } catch {
        /* keep original */
      }
    }
    return u;
  }
  if (u.startsWith("/")) {
    // Cross-origin API (prod): VITE_API_BASE_URL=https://api.example.com/api
    const apiOrigin = apiOriginFromBase();
    if (apiOrigin) {
      return `${apiOrigin}${u}`;
    }
    // Relative base means something proxies /api on this origin (dev server or
    // same-origin deploy), so the SPA host is the right target here. api.ts
    // guarantees an absolute base on any non-local host, so this no longer
    // silently points production media at the SPA.
    if (typeof window !== "undefined" && window.location?.origin) {
      return `${window.location.origin}${u}`;
    }
    return u;
  }
  return u;
}

/** Still frame for list thumbs (clip poster when ready; face only while processing). */
export function playGenerationPosterUrl(gen: {
  asset_type?: string;
  status?: string | null;
  url?: string | null;
  poster_url?: string | null;
  metadata?: Record<string, unknown> | null;
}): string | null {
  const meta = gen.metadata || {};
  const status = (gen.status || "").toLowerCase();
  const readyVideo = gen.asset_type === "video" && status === "ready";
  const face =
    typeof meta.face_image_url === "string" && meta.face_image_url ? meta.face_image_url : null;

  // Prefer top-level poster_url (API signs it). Do not prefer raw metadata paths.
  if (gen.poster_url) {
    if (readyVideo && face && gen.poster_url === face && !meta.clip_poster) {
      // fall through — still the identity plate
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
  return null;
}

/** Force a file download (new-tab "open" is separate). */
export async function downloadMediaFile(url: string, filename: string): Promise<void> {
  const resolved = resolveMediaUrl(url);
  if (!resolved) throw new Error("No media URL");
  const response = await fetch(resolved, { credentials: "include" });
  if (!response.ok) {
    throw new Error(`Download failed (${response.status})`);
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  try {
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = filename || "clip.mp4";
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

export function openMediaInNewTab(url: string): void {
  const resolved = resolveMediaUrl(url);
  if (!resolved) return;
  window.open(resolved, "_blank", "noopener,noreferrer");
}
