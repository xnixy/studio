import { useEffect } from "react";
import { TurnstileField, useTurnstileToken } from "../components/TurnstileField";
import { usePageMeta } from "../components/marketing/usePageMeta";

declare global {
  interface Window {
    ReactNativeWebView?: { postMessage: (message: string) => void };
  }
}

/**
 * Minimal page loaded inside the iOS/Android app WebView for Cloudflare Turnstile.
 * Posts the token to React Native via window.ReactNativeWebView.postMessage.
 * Hosted on example.com so the Turnstile sitekey hostname allowlist matches.
 */
export function CaptchaBridgePage() {
  const turnstile = useTurnstileToken();
  usePageMeta("Security check · Studio", "Complete the security check to continue in the app.");

  useEffect(() => {
    const rn = window.ReactNativeWebView;
    if (!rn) return;
    if (turnstile.token) {
      rn.postMessage(JSON.stringify({ type: "turnstile", token: turnstile.token }));
    }
  }, [turnstile.token]);

  useEffect(() => {
    // Let the native shell know the page loaded (useful for loading UI).
    window.ReactNativeWebView?.postMessage(JSON.stringify({ type: "ready" }));
  }, []);

  return (
    <main
      style={{
        minHeight: "100vh",
        margin: 0,
        padding: "20px 16px",
        boxSizing: "border-box",
        background: "#0b0b0c",
        color: "#f5f5f5",
        fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif",
      }}
    >
      <p style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 600 }}>Security check</p>
      <p style={{ margin: "0 0 16px", fontSize: 13, opacity: 0.75, lineHeight: 1.4 }}>
        Confirm you are human, then return to Create Account.
      </p>
      <TurnstileField
        value={turnstile.token}
        onChange={turnstile.setToken}
        resetKey={turnstile.resetKey}
      />
      {turnstile.token ? (
        <p style={{ margin: "16px 0 0", fontSize: 13, color: "#4ade80" }}>
          Check complete. You can go back to the app.
        </p>
      ) : null}
    </main>
  );
}
