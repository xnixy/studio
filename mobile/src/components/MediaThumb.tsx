import { useMemo } from "react";
import { View, StyleSheet, Text } from "react-native";
import { Image } from "expo-image";
import { isVideoGeneration, mediaImageSource, mediaStableKey } from "../lib/media";

type Props = {
  url?: string | null;
  /** Optional still frame URL (face / poster). Prefer over raw video for lists. */
  posterUrl?: string | null;
  assetType?: string;
  size?: number;
  /** When set with height, draws a non-square poster (grid cells). */
  width?: number;
  height?: number;
  borderRadius?: number;
  /** Face portraits crop from the top so the head stays in frame. */
  contentPosition?: "center" | "top";
};

/**
 * List / grid thumbnail. Still image only.
 * Never mounts a video player in scroll lists (scroll jank + battery).
 * Cache key ignores re-signed ?exp=&sig= so list polls do not flash posters.
 */
export function MediaThumb({
  url,
  posterUrl,
  assetType,
  size = 56,
  width,
  height,
  borderRadius = 10,
  contentPosition = "center",
}: Props) {
  const video = isVideoGeneration({ asset_type: assetType, url });
  const w = width ?? size;
  const h = height ?? size;

  const imageSource = useMemo(() => {
    return mediaImageSource(posterUrl) || (!video ? mediaImageSource(url) : null);
  }, [posterUrl, url, video]);

  // Path only — never include query (exp/sig change every list refetch).
  const recyclingKey = mediaStableKey(posterUrl) || mediaStableKey(url) || undefined;

  return (
    <View style={[styles.box, { width: w, height: h, borderRadius, backgroundColor: "#1C1C1E" }]}>
      {imageSource ? (
        <Image
          source={imageSource}
          style={StyleSheet.absoluteFill}
          contentFit="cover"
          contentPosition={contentPosition}
          // Avoid fade flash on every list poll / re-sign.
          transition={0}
          cachePolicy="memory-disk"
          recyclingKey={recyclingKey}
        />
      ) : (
        <View style={[StyleSheet.absoluteFill, styles.placeholder]} />
      )}
      {video ? (
        <View accessible={false} importantForAccessibility="no-hide-descendants">
          <PlayDot />
        </View>
      ) : null}
    </View>
  );
}

function PlayDot() {
  return (
    <View style={styles.playBadge}>
      <Text style={styles.playText}>▶</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    overflow: "hidden",
    backgroundColor: "#2C2C2E",
  },
  placeholder: {
    backgroundColor: "#3A3A3C",
  },
  playBadge: {
    position: "absolute",
    right: 5,
    bottom: 5,
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: "rgba(0,0,0,0.55)",
    alignItems: "center",
    justifyContent: "center",
  },
  playText: {
    color: "#fff",
    fontSize: 8,
    marginLeft: 1,
  },
});
