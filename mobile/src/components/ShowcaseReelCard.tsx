import { useEffect } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useIsFocused } from "expo-router";
import { Image } from "expo-image";
import { useVideoPlayer, VideoView } from "expo-video";
import type { ShowcaseExample } from "@/src/lib/examples";
import { useAppColors } from "@/src/ui/theme";

type Props = {
  example: ShowcaseExample;
  /** Play muted loop when this card is the focused page. */
  active: boolean;
  /** Shared card width (every cell same size). */
  width: number;
  /** Shared media height (every cell same size). Prefer portrait. */
  height: number;
};

/**
 * Landing / Home example card.
 * All cards share the same outer size so stills and videos line up in a reel.
 * Media is always cover-cropped into that frame (faces use top bias).
 * Title sits under the media frame.
 */
export function ShowcaseReelCard({ example, active, width, height }: Props) {
  const colors = useAppColors();
  const screenFocused = useIsFocused();
  const isFace = Boolean(example.isFace) || (!example.videoUrl && example.aspect === "1:1");
  const hasVideo = Boolean(example.videoUrl) && !isFace;
  const shouldPlay = hasVideo && active && screenFocused;

  const player = useVideoPlayer(hasVideo ? example.videoUrl ?? null : null, (p) => {
    p.loop = true;
    p.muted = true;
  });

  useEffect(() => {
    if (!hasVideo || !player) return;
    try {
      if (shouldPlay) {
        player.play();
      } else {
        player.pause();
      }
    } catch {
      /* player may not be ready */
    }
  }, [shouldPlay, hasVideo, player]);

  return (
    <View style={[styles.card, { width }]}>
      <View
        style={[
          styles.media,
          {
            width,
            height,
            backgroundColor: colors.chipOff,
          },
        ]}
      >
        {hasVideo && shouldPlay ? (
          <VideoView
            style={StyleSheet.absoluteFill}
            player={player}
            contentFit="cover"
            nativeControls={false}
          />
        ) : (
          <Image
            source={{ uri: example.posterUrl }}
            style={StyleSheet.absoluteFill}
            contentFit="cover"
            contentPosition={isFace ? "top" : "center"}
            transition={180}
            recyclingKey={example.id}
          />
        )}

        <View style={styles.badgeRow} pointerEvents="none">
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{modeLabel(example.mode, isFace)}</Text>
          </View>
          {!isFace && example.duration ? (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{example.duration}</Text>
            </View>
          ) : null}
        </View>

        {hasVideo && !shouldPlay ? (
          <View style={styles.playDot} pointerEvents="none">
            <Text style={styles.playText}>▶</Text>
          </View>
        ) : null}
      </View>

      <View style={styles.meta}>
        <Text style={[styles.title, { color: colors.fg }]} numberOfLines={2}>
          {example.title}
        </Text>
        <Text style={[styles.caption, { color: colors.muted }]} numberOfLines={1}>
          {example.caption}
        </Text>
      </View>
    </View>
  );
}

function modeLabel(mode: string, isFace: boolean) {
  if (isFace) return "Face";
  switch (mode) {
    case "avatar":
      return "Talking";
    case "lipsync":
      return "Talking";
    case "video":
      return "Scene";
    case "image":
      return "Still";
    default:
      return mode;
  }
}

const styles = StyleSheet.create({
  card: {
    gap: 8,
  },
  media: {
    borderRadius: 22,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOpacity: 0.22,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 10 },
    elevation: 6,
  },
  badgeRow: {
    position: "absolute",
    top: 10,
    left: 10,
    right: 10,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
  },
  badge: {
    backgroundColor: "rgba(0,0,0,0.45)",
    borderRadius: 999,
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: "rgba(255,255,255,0.2)",
  },
  badgeText: {
    color: "#fff",
    fontSize: 11,
    fontWeight: "600",
  },
  playDot: {
    position: "absolute",
    right: 10,
    bottom: 10,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: "rgba(0,0,0,0.5)",
    alignItems: "center",
    justifyContent: "center",
  },
  playText: {
    color: "#fff",
    fontSize: 11,
    marginLeft: 2,
  },
  meta: {
    paddingHorizontal: 4,
    gap: 2,
    minHeight: 40,
  },
  title: {
    fontSize: 15,
    fontWeight: "700",
    letterSpacing: -0.2,
  },
  caption: {
    fontSize: 12,
    lineHeight: 16,
  },
});
