import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./auth";
import { App } from "./App";
import { WorkspaceProvider } from "./workspace";
import { WorkspaceRealtimeProvider } from "./realtime/WorkspaceRealtimeProvider";
import { StudioThemeProvider } from "./ui";

// Surface unexpected client errors in the console (Sentry DSN can be added later).
window.addEventListener("error", (event) => {
  console.error("[Studio]", event.error || event.message);
});
window.addEventListener("unhandledrejection", (event) => {
  console.error("[Studio] unhandledrejection", event.reason);
});

/**
 * After a deploy, cached index.html can reference hashed chunks that no longer exist.
 * Vite emits vite:preloadError; reload once (cache-busted) so the client picks up a
 * fresh entry shell. Do NOT clear the guard here — that caused infinite reloads when
 * the same chunk kept failing (e.g. HTML cached as JS for a /static/* hash).
 * Guards clear in dismissHtmlBoot after a route actually paints.
 */
const RELOAD_KEY = "studio.chunk-reload";
window.addEventListener("vite:preloadError", (event) => {
  try {
    if (sessionStorage.getItem(RELOAD_KEY) === "1") {
      // Already tried one recovery reload this session; let the error propagate to
      // React.lazy / RouteErrorBoundary instead of looping forever.
      return;
    }
    // Only cancel the throw when we are about to hard-navigate away.
    event.preventDefault();
    sessionStorage.setItem(RELOAD_KEY, "1");
    const url = new URL(window.location.href);
    url.searchParams.set("_studio_reload", String(Date.now()));
    window.location.replace(url.toString());
  } catch {
    event.preventDefault();
    window.location.reload();
  }
});

// Drop stale deploy cache-bust param once the new document is running.
try {
  const url = new URL(window.location.href);
  if (url.searchParams.has("_studio_reload")) {
    url.searchParams.delete("_studio_reload");
    window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  }
} catch {
  /* ignore */
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // One extra retry helps brief tunnel / API blips that otherwise leave a blank pane
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 4000),
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <StudioThemeProvider>
          <AuthProvider>
            <WorkspaceProvider>
              <WorkspaceRealtimeProvider>
                <App />
              </WorkspaceRealtimeProvider>
            </WorkspaceProvider>
          </AuthProvider>
        </StudioThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
