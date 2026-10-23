import { useEffect } from "react";

const SITE_ORIGIN = "https://example.com";
const DEFAULT_TITLE = "Studio · Talking, Scene, and stills";
const DEFAULT_DESCRIPTION =
  "Make Talking, Scene, and stills for TikTok, Reels, and Shorts. One box, then we confirm the kind. Credits show before you spend.";
const DEFAULT_OG_IMAGE = `${SITE_ORIGIN}/og-default.png`;

function setMeta(name: string, content: string, property = false) {
  const attr = property ? "property" : "name";
  let el = document.querySelector(`meta[${attr}="${name}"]`) as HTMLMetaElement | null;
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, name);
    document.head.appendChild(el);
  }
  el.content = content;
}

function setCanonical(href: string) {
  let el = document.querySelector('link[rel="canonical"]') as HTMLLinkElement | null;
  if (!el) {
    el = document.createElement("link");
    el.rel = "canonical";
    document.head.appendChild(el);
  }
  el.href = href;
}

function absoluteUrl(pathname: string) {
  const path = pathname.startsWith("/") ? pathname : `/${pathname}`;
  if (path === "/") return `${SITE_ORIGIN}/`;
  return `${SITE_ORIGIN}${path}`;
}

/**
 * Sets document title and meta description (and basic OG text) while mounted.
 * Restores defaults on unmount so navigation does not leave stale titles.
 */
export function usePageMeta(title: string, description?: string) {
  useEffect(() => {
    // Avoid "Docs · Studio · Studio" when callers already include the brand suffix
    const alreadyBranded =
      title === DEFAULT_TITLE ||
      title === "Studio" ||
      title.startsWith("Studio ·") ||
      title.endsWith(" · Studio") ||
      // "About Studio" / "Contact Studio" already include the brand name
      /\bstudio\b/i.test(title.trim());
    const fullTitle = alreadyBranded ? title : `${title} · Studio`;
    const desc = description?.trim() || DEFAULT_DESCRIPTION;
    const pageUrl = absoluteUrl(window.location.pathname);
    const previousTitle = document.title;
    document.title = fullTitle;
    setMeta("description", desc);
    setMeta("og:title", fullTitle, true);
    setMeta("og:description", desc, true);
    setMeta("og:url", pageUrl, true);
    setMeta("og:image", DEFAULT_OG_IMAGE, true);
    setMeta("og:type", "website", true);
    setMeta("twitter:card", "summary");
    setMeta("twitter:title", fullTitle);
    setMeta("twitter:description", desc);
    setMeta("twitter:image", DEFAULT_OG_IMAGE);
    setCanonical(pageUrl);

    return () => {
      document.title = previousTitle || DEFAULT_TITLE;
    };
  }, [title, description]);
}
