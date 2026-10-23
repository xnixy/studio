import { useCallback, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Platform, StyleSheet, Text, View } from "react-native";
import { WebView, type WebViewMessageEvent } from "react-native-webview";
import { MARKETING_BASE_URL } from "@/src/lib/config";
import { useAppColors } from "@/src/ui/theme";

type Props = {
  /** Called when Turnstile issues a fresh token. */
  onToken: (token: string | null) => void;
  /** Bump to force a full WebView reload (e.g. after failed register). */
  resetKey?: number;
  height?: number;
};

type BridgeMessage =
  | { type: "ready" }
  | { type: "turnstile"; token: string }
  | { type: "error"; message?: string };

/**
 * Cloudflare Turnstile for native apps via WebView.
 * Loads the hosted bridge on example.com (sitekey hostname must match CF dashboard).
 */
export function TurnstileChallenge({ onToken, resetKey = 0, height = 96 }: Props) {
  const colors = useAppColors();
  const [status, setStatus] = useState<"loading" | "ready" | "ok" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const onTokenRef = useRef(onToken);
  onTokenRef.current = onToken;

  const uri = useMemo(() => {
    const base = MARKETING_BASE_URL.replace(/\/$/, "");
    // Cache-bust when reset so a new challenge is requested.
    return `${base}/captcha-bridge?rn=1&k=${resetKey}`;
  }, [resetKey]);

  const onMessage = useCallback((event: WebViewMessageEvent) => {
    try {
      const data = JSON.parse(event.nativeEvent.data) as BridgeMessage;
      if (data.type === "ready") {
        setStatus((s) => (s === "ok" ? s : "ready"));
        return;
      }
      if (data.type === "turnstile" && typeof data.token === "string" && data.token) {
        setStatus("ok");
        setError(null);
        onTokenRef.current(data.token);
        return;
      }
      if (data.type === "error") {
        setStatus("error");
        setError(data.message || "Captcha failed to load");
        onTokenRef.current(null);
      }
    } catch {
      // Ignore non-JSON noise from the page.
    }
  }, []);

  return (
    <View style={[styles.wrap, { borderColor: colors.border, backgroundColor: colors.card }]}>
      <Text style={[styles.label, { color: colors.muted }]}>Security check</Text>
      {status === "loading" ? (
        <View style={styles.loadingRow}>
          <ActivityIndicator color={colors.brand} />
          <Text style={{ color: colors.muted, fontSize: 13 }}>Loading captcha…</Text>
        </View>
      ) : null}
      {status === "ok" ? (
        <Text style={{ color: colors.success ?? "#4ade80", fontSize: 13, marginBottom: 6 }}>
          Check complete
        </Text>
      ) : null}
      {error ? <Text style={{ color: colors.danger, fontSize: 13, marginBottom: 6 }}>{error}</Text> : null}
      <WebView
        key={`turnstile-${resetKey}`}
        source={{ uri }}
        style={{ height, width: "100%", backgroundColor: "transparent", opacity: status === "ok" ? 0.35 : 1 }}
        javaScriptEnabled
        domStorageEnabled
        originWhitelist={["*"]}
        // Required for Turnstile network / frames (Cloudflare mobile docs).
        setSupportMultipleWindows={false}
        allowsInlineMediaPlayback
        mediaPlaybackRequiresUserAction={false}
        // Keep default UA (do not override mid-session).
        onMessage={onMessage}
        onLoadStart={() => {
          if (status !== "ok") setStatus("loading");
        }}
        onLoadEnd={() => {
          setStatus((s) => (s === "loading" ? "ready" : s));
        }}
        onError={() => {
          setStatus("error");
          setError("Could not load captcha. Check your connection.");
          onTokenRef.current(null);
        }}
        onHttpError={() => {
          setStatus("error");
          setError("Captcha page failed to load. Update the app or try again later.");
          onTokenRef.current(null);
        }}
        // iOS: third-party cookies / storage for challenge state
        {...(Platform.OS === "ios"
          ? { sharedCookiesEnabled: true, thirdPartyCookiesEnabled: true }
          : { thirdPartyCookiesEnabled: true })}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 14,
    padding: 12,
    overflow: "hidden",
    gap: 4,
  },
  label: {
    fontSize: 12,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.4,
    marginBottom: 4,
  },
  loadingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 6,
  },
});
