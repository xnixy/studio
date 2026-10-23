import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * SPA route changes keep the previous scroll position by default.
 * Jump to top on path change (instant; hash targets still win when present).
 * Uses window + documentElement + body for iOS Safari.
 */
export function ScrollToTop() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    // Allow the new route to paint, then scroll.
    const id = window.requestAnimationFrame(() => {
      if (hash) {
        const el = document.getElementById(hash.slice(1));
        if (el) {
          el.scrollIntoView({ behavior: "auto", block: "start" });
          return;
        }
      }
      window.scrollTo(0, 0);
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
    });
    return () => window.cancelAnimationFrame(id);
  }, [pathname, hash]);

  return null;
}
