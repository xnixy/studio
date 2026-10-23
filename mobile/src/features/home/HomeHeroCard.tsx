import { ActivityIndicator, Pressable, StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Image } from "expo-image";
import type { PlayGeneration } from "@/src/api/types";
import { ClipPlayer } from "@/src/components/ClipPlayer";
import {
  generationKindLabel,
  isSquarePlatform,
  promptForDisplay,
} from "@/src/features/create/createConstants";
import { homeHeroCardWidth, homeInnerWidth, homePagePad } from "@/src/features/home/homeLayout";
import { hapticLight } from "@/src/lib/haptics";
import {
  isVideoGeneration,
  mediaImageSource,
  mediaStableKey,
  playGenerationPosterUrl,
  resolveMediaUrl,
} from "@/src/lib/media";
import { supportsPlayExtend } from "@/src/lib/qualityTier";
import type { AppColors } from "@/src/ui/theme";

type Props = {
  colors: AppColors;
  generation: PlayGeneration | null;
  loading: boolean;
  onOpen: (id: string) => void;
  onEmptyClip: () => void;
  onRetry: (gen: PlayGeneration) => void;
  onExtend: (gen: PlayGeneration) => void;
};

export function HomeHeroCard({
  colors,
  generation: g,
  loading,
  onOpen,
  onEmptyClip,
  onRetry,
  onExtend,
}: Props) {
  const { width: screenWidth } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const innerWidth = homeInnerWidth(screenWidth, insets.left, insets.right);
  const square = isSquarePlatform(g?.platform);
  const cardWidth = homeHeroCardWidth(innerWidth, g?.platform ?? "tiktok");
  const aspect = square ? 1 : 9 / 16;
  const mediaHeight = cardWidth / aspect;
  const pagePad = homePagePad(innerWidth);

  if (loading) {
    return (
      <View style={[styles.wrap, { paddingHorizontal: pagePad }]}>
        <View style={[styles.phone, { width: cardWidth, height: mediaHeight, backgroundColor: colors.chipOff }]} />
      </View>
    );
  }

  if (!g) {
    return (
      <View style={[styles.wrap, { paddingHorizontal: pagePad }]}>
        <Pressable
          onPress={() => {
            void hapticLight();
            onEmptyClip();
          }}
          accessibilityRole="button"
          accessibilityLabel="Make your first clip"
          style={[
            styles.phone,
            styles.empty,
            { width: cardWidth, height: mediaHeight, borderColor: colors.border },
          ]}
        >
          <Text style={{ color: colors.muted, fontSize: 15, textAlign: "center", paddingHorizontal: 16 }}>
            Make your first clip
          </Text>
        </Pressable>
      </View>
    );
  }

  const status = (g.status || "").toLowerCase();
  const pending = !["ready", "failed", "error", "cancelled", "expired"].includes(status);
  const failed = status === "failed" || status === "error" || status === "expired";
  const ready = status === "ready";
  const video = isVideoGeneration(g);
  const url = resolveMediaUrl(g.url);
  const posterSource = mediaImageSource(playGenerationPosterUrl(g));
  const stillSource = mediaImageSource(g.url);
  const caption = [generationKindLabel(g), promptForDisplay(g.prompt, g.mode)].filter(Boolean).join(" · ");
  const provider =
    g.provider || (typeof g.metadata?.provider === "string" ? g.metadata.provider : null);
  const canExtend = ready && video && g.mode !== "image" && supportsPlayExtend(provider);

  return (
    <View style={[styles.wrap, { paddingHorizontal: pagePad }]}>
      <Pressable
        onPress={() => onOpen(g.id)}
        accessibilityRole="button"
        accessibilityLabel={caption || "Open clip"}
        style={[styles.phone, { width: cardWidth, height: mediaHeight, backgroundColor: colors.chipOff }]}
      >
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
              <ActivityIndicator color="#fff" />
              <Text style={styles.overlayText}>Working on it</Text>
            </View>
          </>
        ) : null}

        {!pending && stillSource && !video ? (
          <Image
            source={stillSource}
            style={StyleSheet.absoluteFill}
            contentFit="cover"
            transition={0}
            cachePolicy="memory-disk"
            recyclingKey={mediaStableKey(g.url) ?? undefined}
          />
        ) : null}

        {!pending && video && url && ready ? (
          <ClipPlayer
            uri={url}
            embedded
            nativeControls={false}
            contentFit="cover"
            muted
            onTap={() => onOpen(g.id)}
          />
        ) : null}

        {!pending && video && !url && posterSource ? (
          <Image
            source={posterSource}
            style={StyleSheet.absoluteFill}
            contentFit="cover"
            transition={0}
            cachePolicy="memory-disk"
            recyclingKey={mediaStableKey(playGenerationPosterUrl(g)) ?? undefined}
          />
        ) : null}

        {failed ? (
          <View style={styles.overlay} pointerEvents="none">
            <Text style={styles.overlayText}>Failed</Text>
          </View>
        ) : null}
      </Pressable>

      {caption ? (
        <Text style={[styles.caption, { color: colors.muted }]} numberOfLines={2}>
          {caption}
        </Text>
      ) : null}

      {failed || canExtend ? (
        <View style={styles.actions}>
          {failed ? (
            <Pressable
              onPress={() => {
                void hapticLight();
                onRetry(g);
              }}
              accessibilityRole="button"
              accessibilityLabel="Retry"
              style={[styles.chip, { backgroundColor: colors.chipOff }]}
            >
              <Text style={{ color: colors.brand, fontWeight: "700", fontSize: 13 }}>Retry</Text>
            </Pressable>
          ) : null}
          {canExtend ? (
            <Pressable
              onPress={() => {
                void hapticLight();
                onExtend(g);
              }}
              accessibilityRole="button"
              accessibilityLabel="Extend"
              style={[styles.chip, { backgroundColor: colors.chipOff }]}
            >
              <Text style={{ color: colors.brand, fontWeight: "700", fontSize: 13 }}>Extend</Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: "center",
    gap: 10,
  },
  phone: {
    borderRadius: 22,
    overflow: "hidden",
  },
  empty: {
    borderWidth: 1.5,
    borderStyle: "dashed",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "transparent",
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.35)",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  overlayText: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 14,
  },
  caption: {
    fontSize: 14,
    lineHeight: 20,
    textAlign: "center",
    paddingHorizontal: 12,
    maxWidth: 280,
  },
  actions: {
    flexDirection: "row",
    gap: 8,
  },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
  },
});
