/** Pre-React HTML boot overlay (#studio-boot). One loading UI until the first route paints. */

export function isHtmlBootActive(): boolean {
  if (typeof document === "undefined") return false;
  const el = document.getElementById("studio-boot");
  return Boolean(el && !el.hasAttribute("data-done"));
}

/**
 * Clear one-shot chunk recovery flags only after a route actually painted.
 * Cleared too early (e.g. at main.tsx parse time) the next failed import reloads forever.
 */
export function clearChunkReloadGuards(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem("studio.chunk-reload");
    sessionStorage.removeItem("studio.lazy-reload");
  } catch {
    /* ignore */
  }
}

/** Hide the static boot shell once real app content is ready. */
export function dismissHtmlBoot(): void {
  if (typeof document === "undefined") return;
  // First successful route paint ⇒ recovery reload is no longer needed.
  clearChunkReloadGuards();
  const el = document.getElementById("studio-boot");
  if (!el || el.hasAttribute("data-done")) return;
  el.setAttribute("data-done", "1");
  el.setAttribute("aria-busy", "false");
  el.setAttribute("hidden", "");
  // Remove after fade so we don't leave a focus trap / extra node around forever
  window.setTimeout(() => {
    el.remove();
  }, 180);
}
