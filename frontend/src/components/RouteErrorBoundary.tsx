import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button, PageBoard, PageLabel, PageSection } from "../ui";

type Props = { children: ReactNode };
type State = { error: Error | null; retryKey: number };

/**
 * Catches route/render errors (including failed lazy loads that escape retry)
 * so the dashboard does not stuck on a blank pane until a full manual refresh.
 */
export class RouteErrorBoundary extends Component<Props, State> {
  state: State = { error: null, retryKey: 0 };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Route error", error, info.componentStack);
  }

  private retry = () => {
    // Bump key so children fully remount (clears bad lazy/HMR state).
    this.setState((s) => ({ error: null, retryKey: s.retryKey + 1 }));
  };

  private hardReload = () => {
    try {
      sessionStorage.removeItem("studio.lazy-reload");
      sessionStorage.removeItem("studio.chunk-reload");
    } catch {
      /* ignore */
    }
    window.location.reload();
  };

  render() {
    if (!this.state.error) {
      // Full width so flex parents (e.g. marketing mainAuth items-center) do not
      // shrink-wrap cards to input min-content (~20ch).
      return (
        <div key={this.state.retryKey} className="box-border w-full min-w-0">
          {this.props.children}
        </div>
      );
    }

    const message = this.state.error.message || "Something went wrong loading this page.";
    const looksLikeChunk =
      /Failed to fetch dynamically imported module|Loading chunk|dynamically imported module/i.test(message);
    const looksLikeTheme = /useStudioTheme|StudioThemeProvider/i.test(message);

    return (
      <div
        style={{
          minHeight: "40vh",
          display: "grid",
          placeItems: "center",
          padding: "24px",
        }}
      >
        <PageBoard narrow>
          <PageSection>
            <PageLabel>Couldn’t load page</PageLabel>
            <p style={{ margin: "0.35rem 0 0.85rem", color: "var(--studio-fg-muted)", lineHeight: 1.45 }}>
              {looksLikeChunk
                ? "A script chunk failed to load (common after a hot reload or brief network blip)."
                : looksLikeTheme
                  ? "Theme UI hit a bad hot-reload state. Try again, or reload once if it sticks."
                  : message}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              <Button type="button" onClick={this.retry}>
                Try again
              </Button>
              <Button type="button" variant="secondary" onClick={this.hardReload}>
                Reload app
              </Button>
            </div>
          </PageSection>
        </PageBoard>
      </div>
    );
  }
}
