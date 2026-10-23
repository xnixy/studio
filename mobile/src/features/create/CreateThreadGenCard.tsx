import { ActivityIndicator, Pressable, StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { Image } from "expo-image";
import { router } from "expo-router";
import type { PlayGeneration } from "@/src/api/types";
import { ClipPlayer } from "@/src/components/ClipPlayer";
import {
  generationKindLabel,
  isSquarePlatform,
  threadClipCardWidth,
} from "@/src/features/create/createConstants";
import { hapticLight } from "@/src/lib/haptics";
import {
  isVideoGeneration,
  mediaImageSource,
  mediaStableKey,
  playGenerationPosterUrl,
  resolveMediaUrl,
} from "@/src/lib/media";
import type { AppColors } from "@/src/ui/theme";

type Props = {
  colors: AppColors;
  generation: PlayGeneration;
  note?: string | null;
  playing: boolean;
  onPlay: () => void;
  onStop: () => void;
  onExtend?: (genId: string, gen: PlayGeneration) => void;
  onRetry?: (gen: PlayGeneration) => void;
  onRefreshStatus?: (genId: string) => void;
};

function Chip({
  label,
  colors,
  onPress,
}: {
  label: string;
  colors: AppColors;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={(e) => {
        e.stopPropagation?.();
        onPress();
      }}
      hitSlop={6}
      style={[styles.chip, { backgroundColor: colors.chipOff, borderColor: colors.border }]}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <Text style={{ color: colors.fg, fontWeight: "600", fontSize: 12 }}>{label}</Text>
    </Pressable>
  );
}

export function CreateThreadGenCard({
  colors,
  generation: g,
  note,
  playing,
  onPlay,
  onStop,
  onExtend,
  onRetry,
  onRefreshStatus,
}: Props) {
  const { width: screenWidth } = useWindowDimensions();
  const status = (g.status || "").toLowerCase();
  const pending = !["ready", "failed", "error", "cancelled", "expired"].includes(status);
  const failed = status === "failed" || status === "error" || status === "expired";
  const url = resolveMediaUrl(g.url);
  const video = isVideoGeneration(g);
  const stillSource = mediaImageSource(g.url);
  const posterSource = mediaImageSource(playGenerationPosterUrl(g));
  const square = isSquarePlatform(g.platform);
  const cardWidth = threadClipCardWidth(screenWidth, g.platform);
  const aspect = square ? 1 : 9 / 16;
  const mediaHeight = cardWidth / aspect;

  const openClip = () => router.push(`/(app)/clip/${g.id}` as const);

  return (
    <View style={[styles.root, { width: cardWidth }]}>
      <View style={[styles.media, { width: cardWidth, height: mediaHeight }]}>
        {pending ? (
          <>
            {posterSource ? (
              <Image
                source={posterSource}
                style={StyleSheet.absoluteFill}
                contentFit="cover"
                transition={0}
                cachePolicy="memory-disk"
                recyclingKey={mediaStableKey(playGenerationPosterUrl(g)) ?? undefined}
              />
            ) : null}
            <View style={styles.overlay}>
              <ActivityIndicator color={colors.brand} />
              <Text style={{ color: "#fff", marginTop: 8, fontWeight: "600" }}>Generating…</Text>
            </View>
          </>
        ) : null}

        {!pending && stillSource && !video ? (
          <Pressable
            onPress={openClip}
            accessibilityRole="button"
            accessibilityLabel="Open still"
            style={StyleSheet.absoluteFill}
          >
            <Image
              source={stillSource}
              style={StyleSheet.absoluteFill}
              contentFit="cover"
              transition={0}
              cachePolicy="memory-disk"
              recyclingKey={mediaStableKey(g.url) ?? undefined}
            />
          </Pressable>
        ) : null}

        {!pending && url && video ? (
          playing ? (
            <ClipPlayer
              uri={url}
              embedded
              nativeControls={false}
              contentFit="cover"
              onTap={onStop}
            />
          ) : (
            <Pressable
              onPress={onPlay}
              style={StyleSheet.absoluteFill}
              accessibilityRole="button"
              accessibilityLabel="Play clip"
            >
              {posterSource ? (
                <Image
                  source={posterSource}
                  style={StyleSheet.absoluteFill}
                  contentFit="cover"
                  transition={0}
                  cachePolicy="memory-disk"
                  recyclingKey={
                    mediaStableKey(playGenerationPosterUrl(g)) ?? mediaStableKey(g.url) ?? undefined
                  }
                />
              ) : null}
              <View style={styles.overlay}>
                <View style={styles.playPill}>
                  <Text style={styles.playIcon}>▶</Text>
                </View>
              </View>
            </Pressable>
          )
        ) : null}

        {!pending && !url ? (
          <View style={styles.overlay}>
            <Text style={{ color: colors.danger, fontWeight: "700", fontSize: 16 }}>
              {failed ? "Failed" : "No media yet"}
            </Text>
            {g.error_message ? (
              <Text style={styles.err} numberOfLines={4}>
                {g.error_message}
              </Text>
            ) : null}
          </View>
        ) : null}
      </View>

      <View style={styles.meta}>
        <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "600" }}>
          {generationKindLabel(g)}
          {failed ? " · Failed" : pending ? " · Working" : ""}
        </Text>
        {note && !failed ? (
          <Text style={{ color: colors.muted, fontSize: 13 }}>{note}</Text>
        ) : null}
        {failed ? (
          <Text style={{ color: colors.muted, fontSize: 13 }}>Credits for this run were returned.</Text>
        ) : null}
        <View style={styles.row}>
          {status === "ready" ? (
            <Chip
              label="Open"
              colors={colors}
              onPress={() => {
                void hapticLight();
                openClip();
              }}
            />
          ) : null}
          {pending && onRefreshStatus ? (
            <Chip label="Refresh" colors={colors} onPress={() => onRefreshStatus(g.id)} />
          ) : null}
          {failed && onRefreshStatus ? (
            <Chip label="Check again" colors={colors} onPress={() => onRefreshStatus(g.id)} />
          ) : null}
          {failed && onRetry ? (
            <Chip label="Retry" colors={colors} onPress={() => onRetry(g)} />
          ) : null}
          {!pending && status === "ready" && video && onExtend ? (
            <Chip label="Extend" colors={colors} onPress={() => onExtend(g.id, g)} />
          ) : null}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { alignSelf: "flex-start", gap: 8 },
  media: {
    overflow: "hidden",
    borderRadius: 22,
    backgroundColor: "#0a0a0a",
  },
  overlay: {
    ...StyleSheet.absoluteFill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(0,0,0,0.28)",
    paddingHorizontal: 12,
  },
  playPill: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "rgba(0,0,0,0.55)",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: "rgba(255,255,255,0.55)",
    alignItems: "center",
    justifyContent: "center",
  },
  playIcon: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 20,
    marginLeft: 3,
  },
  err: {
    color: "#fff",
    fontSize: 13,
    textAlign: "center",
    marginTop: 8,
    opacity: 0.85,
  },
  meta: { gap: 6, paddingHorizontal: 2 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  chip: {
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
});
