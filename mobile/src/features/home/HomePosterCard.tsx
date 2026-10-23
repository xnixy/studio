import { Pressable, StyleSheet, Text, View } from "react-native";
import { GlassSurface } from "@/src/components/GlassSurface";
import { MediaThumb } from "@/src/components/MediaThumb";
import { useAppColors } from "@/src/ui/theme";

type PosterCardProps = {
  width: number;
  mediaHeight: number;
  title: string;
  caption: string;
  accessibilityLabel: string;
  onPress: () => void;
  url?: string | null;
  posterUrl?: string | null;
  assetType?: string;
  contentPosition?: "center" | "top";
};

/** Shared Home grid card. Full-bleed glass poster plus title and caption. */
export function HomePosterCard({
  width,
  mediaHeight,
  title,
  caption,
  accessibilityLabel,
  onPress,
  url,
  posterUrl,
  assetType = "image",
  contentPosition = "center",
}: PosterCardProps) {
  const colors = useAppColors();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      style={({ pressed }) => [{ width, opacity: pressed ? 0.92 : 1 }]}
    >
      <GlassSurface
        intensity={42}
        radius={18}
        style={styles.shadow}
        contentStyle={styles.cell}
      >
        <MediaThumb
          url={url}
          posterUrl={posterUrl}
          assetType={assetType}
          width={width}
          height={mediaHeight}
          borderRadius={0}
          contentPosition={contentPosition}
        />
        <View style={styles.meta}>
          <Text numberOfLines={2} style={[styles.title, { color: colors.fg }]}>
            {title}
          </Text>
          <Text numberOfLines={1} style={[styles.caption, { color: colors.muted }]}>
            {caption}
          </Text>
        </View>
      </GlassSurface>
    </Pressable>
  );
}

export function HomePosterSkeleton({
  width,
  mediaHeight,
}: {
  width: number;
  mediaHeight: number;
}) {
  const colors = useAppColors();
  return (
    <GlassSurface intensity={32} radius={18} style={styles.shadow} contentStyle={styles.cell}>
      <View style={{ width, height: mediaHeight, backgroundColor: colors.chipOff }} />
      <View style={styles.meta}>
        <View style={[styles.bar, { width: "78%", backgroundColor: colors.chipOff }]} />
        <View style={[styles.barSm, { width: "46%", backgroundColor: colors.chipOff }]} />
      </View>
    </GlassSurface>
  );
}

const styles = StyleSheet.create({
  shadow: {
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  cell: { overflow: "hidden" },
  meta: {
    paddingHorizontal: 10,
    paddingVertical: 8,
    minHeight: 52,
    gap: 4,
  },
  title: { fontSize: 13, fontWeight: "600" },
  caption: { fontSize: 12 },
  bar: { height: 12, borderRadius: 4 },
  barSm: { height: 10, borderRadius: 4 },
});
