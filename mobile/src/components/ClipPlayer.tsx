import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, AppState, Pressable, StyleSheet, Text, View } from "react-native";
import { useFocusEffect } from "expo-router";
import { useVideoPlayer, VideoView } from "expo-video";
import { isSignedMediaUrlExpired, mediaStableKey, mediaVideoSource } from "../lib/media";

type Props = {
  uri: string;
  aspectRatio?: number;
  maxWidth?: number;
  maxHeight?: number;
  /** Fill the parent (no outer padding, no own radius) for embedding in a card. */
  embedded?: boolean;
  /** Clip detail keeps native chrome. Create thread uses a poster + tap instead. */
  nativeControls?: boolean;
  contentFit?: "contain" | "cover" | "fill";
  /** When native controls are off, a tap on the video (Create thread: stop). */
  onTap?: () => void;
  /** Home hero loops silent. Create / clip detail keep audio. */
  muted?: boolean;
};

/**
 * Progressive stream only (no full download).
 *
 * Uses the documented direct-source pattern (`useVideoPlayer(source, …)`) so the
 * player binds to the item at creation and autoplays, instead of the
 * `useVideoPlayer(null)` + `replaceAsync` dance that could hang on "loading".
 * The source URL is pinned per clip so token re-signs never rebuild the player.
 */
export function ClipPlayer({
  uri,
  aspectRatio = 9 / 16,
  maxWidth = 360,
  maxHeight = 520,
  embedded = false,
  nativeControls = true,
  contentFit = "contain",
  onTap,
  muted = false,
}: Props) {
  const [retryN, setRetryN] = useState(0);
  const ratio = aspectRatio > 0 ? aspectRatio : 9 / 16;

  // Pin the first signed URL we see for a clip. The backend re-issues fresh
  // ?exp=&sig= on every poll; without pinning, the source object would change
  // and rebuild the player mid-playback.
  //
  // Re-pin on a new clip, on Retry, and once the signature expires. Signatures
  // last 2 hours, so a screen left open (or a retry after that) would otherwise
  // replay a URL the API now rejects.
  const stableKey = mediaStableKey(uri) || uri || "";
  const pinnedRef = useRef<{ key: string; uri: string; retry: number } | null>(null);
  if (
    uri &&
    (!pinnedRef.current ||
      pinnedRef.current.key !== stableKey ||
      pinnedRef.current.retry !== retryN ||
      isSignedMediaUrlExpired(pinnedRef.current.uri))
  ) {
    pinnedRef.current = { key: stableKey, uri, retry: retryN };
  }
  const pinnedUri = pinnedRef.current?.uri ?? uri;

  const source = useMemo(() => {
    const base = mediaVideoSource(pinnedUri);
    if (!base) return null;
    // Default is `progressive`. On manual retry, try `auto` as a fallback.
    return retryN % 2 === 1 ? { ...base, contentType: "auto" as const } : base;
  }, [pinnedUri, retryN]);

  const player = useVideoPlayer(source, (p) => {
    p.loop = true;
    p.muted = muted;
    p.play();
  });

  const [phase, setPhase] = useState<"loading" | "ready" | "error">("loading");
  const [errorText, setErrorText] = useState<string | null>(null);
  // A slow cellular load is not a failure. After a while we keep the spinner
  // but expose Retry, so a legit slow start still plays if it arrives.
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    if (!source) {
      setPhase("error");
      setErrorText("No video URL.");
      return;
    }
    setPhase("loading");
    setErrorText(null);
    setSlow(false);

    const sub = player.addListener("statusChange", (payload) => {
      if (payload.status === "error") {
        setPhase("error");
        setErrorText(payload.error?.message || "Playback failed.");
      } else if (payload.status === "readyToPlay") {
        setPhase("ready");
        try {
          player.play();
        } catch {
          /* native controls still work */
        }
      }
    });

    const slowTimer = setTimeout(() => {
      setSlow((prev) => prev || true);
    }, 12_000);

    return () => {
      try {
        sub.remove();
      } catch {
        /* ignore */
      }
      clearTimeout(slowTimer);
    };
  }, [player, source]);

  // Stop playback (audio too) when the screen loses focus. This is the reliable
  // pre-unmount hook: it fires while the player is still alive, before the
  // screen pops. expo-video can otherwise keep the audio session running after
  // you navigate back.
  useEffect(() => {
    try {
      player.muted = muted;
    } catch {
      /* released */
    }
  }, [player, muted]);

  useFocusEffect(
    useCallback(() => {
      if (muted) {
        try {
          player.play();
        } catch {
          /* released */
        }
      }
      return () => {
        try {
          player.pause();
        } catch {
          /* released */
        }
      };
    }, [player, muted]),
  );

  // Also pause when the app backgrounds, and once more on unmount as a backstop.
  useEffect(() => {
    const sub = AppState.addEventListener("change", (state) => {
      if (state !== "active") {
        try {
          player.pause();
        } catch {
          /* released */
        }
      } else if (muted) {
        try {
          player.play();
        } catch {
          /* released */
        }
      }
    });
    return () => {
      sub.remove();
      try {
        player.pause();
      } catch {
        /* released */
      }
    };
  }, [player, muted]);

  return (
    <View style={[styles.outer, embedded ? styles.outerBare : null]}>
      <View
        style={[
          styles.playerWrap,
          embedded
            ? styles.playerWrapBare
            : {
                aspectRatio: ratio,
                maxWidth,
                maxHeight,
              },
        ]}
      >
        <VideoView
          style={styles.player}
          player={player}
          nativeControls={nativeControls}
          contentFit={contentFit}
          allowsPictureInPicture={false}
          startsPictureInPictureAutomatically={false}
        />
        {!nativeControls ? (
          <Pressable
            style={styles.tapCatch}
            onPress={() => {
              if (onTap) {
                onTap();
                return;
              }
              try {
                if (player.playing) player.pause();
                else player.play();
              } catch {
                /* released */
              }
            }}
            accessibilityRole="button"
            accessibilityLabel="Pause clip"
          />
        ) : null}
        {phase === "loading" ? (
          <View style={styles.overlay} pointerEvents={slow ? "auto" : "none"}>
            <ActivityIndicator color="#fff" />
            {slow ? (
              <>
                <Text style={styles.errorText}>Still loading…</Text>
                <Pressable
                  onPress={() => setRetryN((n) => n + 1)}
                  style={styles.retryBtn}
                  accessibilityRole="button"
                  accessibilityLabel="Retry video"
                >
                  <Text style={styles.retryLabel}>Retry</Text>
                </Pressable>
              </>
            ) : null}
          </View>
        ) : null}
        {phase === "error" ? (
          <View style={styles.overlay}>
            <Text style={styles.errorText}>{errorText || "Video failed to stream."}</Text>
            <Pressable
              onPress={() => setRetryN((n) => n + 1)}
              style={styles.retryBtn}
              accessibilityRole="button"
              accessibilityLabel="Retry video"
            >
              <Text style={styles.retryLabel}>Retry</Text>
            </Pressable>
          </View>
        ) : null}
      </View>
      {__DEV__ && !embedded ? (
        <Text style={styles.debug} selectable numberOfLines={3}>
          {`phase=${phase} ct=${source?.contentType ?? "-"} hdr=${
            source && "headers" in source ? "y" : "n"
          }\n${pinnedUri}${errorText ? `\nerr: ${errorText}` : ""}`}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  outer: {
    width: "100%",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 4,
  },
  outerBare: {
    paddingHorizontal: 0,
    paddingTop: 0,
    paddingBottom: 0,
    height: "100%",
    alignItems: "stretch",
  },
  playerWrap: {
    width: "100%",
    borderRadius: 20,
    overflow: "hidden",
    backgroundColor: "#000",
    alignSelf: "center",
  },
  playerWrapBare: {
    borderRadius: 0,
    width: "100%",
    height: "100%",
    maxHeight: "100%",
  },
  player: {
    width: "100%",
    height: "100%",
  },
  tapCatch: {
    ...StyleSheet.absoluteFill,
    zIndex: 2,
  },
  overlay: {
    ...StyleSheet.absoluteFill,
    zIndex: 3,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(0,0,0,0.45)",
    paddingHorizontal: 16,
    gap: 12,
  },
  errorText: {
    color: "#fff",
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
  },
  retryBtn: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: "rgba(255,255,255,0.2)",
  },
  retryLabel: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 15,
  },
  debug: {
    color: "#8E8E93",
    fontSize: 10,
    lineHeight: 13,
    marginTop: 6,
    paddingHorizontal: 16,
    fontFamily: "Courier",
  },
});
