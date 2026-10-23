import { lazy, type ComponentType, type LazyExoticComponent } from "react";

/**
 * Like React.lazy, but retries failed dynamic imports (common with Vite HMR /
 * tunnel blips). On hard chunk-load failures, reloads the page once so the
 * browser picks up a fresh module graph instead of a blank route.
 *
 * Guard stays set until dismissHtmlBoot / clearChunkReloadGuards so a permanently
 * bad chunk cannot reload-loop (pair with SPA rules that never rewrite /static/*).
 */
export function lazyRetry<T extends ComponentType<any>>(
  factory: () => Promise<{ default: T }>,
  retries = 2,
): LazyExoticComponent<T> {
  return lazy(async () => {
    let lastError: unknown;
    for (let attempt = 0; attempt <= retries; attempt += 1) {
      try {
        const mod = await factory();
        try {
          sessionStorage.removeItem("studio.lazy-reload");
        } catch {
          /* ignore */
        }
        return mod;
      } catch (error) {
        lastError = error;
        const message = error instanceof Error ? error.message : String(error);
        // MIME/text-html errors happen when SPA fallback serves index.html for a
        // missing hashed chunk (often after a deploy, sometimes edge-cached).
        const isChunkError =
          /Failed to fetch dynamically imported module|Importing a module script failed|Loading chunk [\d]+ failed|error loading dynamically imported module|ChunkLoadError|disallowed MIME type|Expected a JavaScript|is not a valid JavaScript MIME type/i.test(
            message,
          );

        if (attempt < retries) {
          await new Promise((r) => setTimeout(r, 300 * (attempt + 1)));
          continue;
        }

        if (isChunkError && typeof window !== "undefined") {
          try {
            if (sessionStorage.getItem("studio.lazy-reload") !== "1") {
              sessionStorage.setItem("studio.lazy-reload", "1");
              // Bypass sticky document caches; module URL hashes change per deploy.
              const url = new URL(window.location.href);
              url.searchParams.set("_studio_reload", String(Date.now()));
              window.location.replace(url.toString());
              return new Promise(() => undefined) as Promise<{ default: T }>;
            }
          } catch {
            // Storage blocked: still only one reload via in-memory is not possible
            // across documents — rethrow so the error boundary can show "Reload app".
            throw lastError;
          }
        }
      }
    }
    throw lastError;
  }) as LazyExoticComponent<T>;
}

/** Lazy-load a named export as if it were default. */
export function namedLazy<T extends ComponentType<any>>(
  loader: () => Promise<Record<string, unknown>>,
  exportName: string,
  retries = 2,
): LazyExoticComponent<T> {
  return lazyRetry(async () => {
    const mod = await loader();
    const Comp = mod[exportName] as T | undefined;
    if (!Comp) {
      throw new Error(`Export "${exportName}" not found in lazy module`);
    }
    return { default: Comp };
  }, retries);
}
