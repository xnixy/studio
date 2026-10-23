import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import type { PlayGeneration } from "@/src/api/types";
import { MediaThumb } from "@/src/components/MediaThumb";
import { generationKindLabel } from "@/src/features/create/createConstants";
import { homeInnerWidth, homeRecentsLayout } from "@/src/features/home/homeLayout";
import { playGenerationPosterUrl } from "@/src/lib/media";
import type { AppColors } from "@/src/ui/theme";

type Props = {
  colors: AppColors;
  items: PlayGeneration[];
  onOpen: (id: string) => void;
  onSeeAll: () => void;
};

export function HomeRecentsStrip({ colors, items, onOpen, onSeeAll }: Props) {
  const { width: screenW } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const layout = homeRecentsLayout(homeInnerWidth(screenW, insets.left, insets.right));

  return (
    <View>
      <View style={[styles.header, { paddingHorizontal: layout.pad }]}>
        <Text style={{ color: colors.muted, fontSize: 13, fontWeight: "600" }}>Recent</Text>
        <Pressable
          onPress={onSeeAll}
          accessibilityRole="button"
          accessibilityLabel="See all library items"
          hitSlop={8}
          style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}
        >
          <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 15 }}>See All</Text>
        </Pressable>
      </View>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={[
          styles.row,
          { paddingLeft: layout.pad, paddingRight: layout.pad, gap: layout.gap },
        ]}
      >
        {items.map((g) => (
          <Thumb
            key={g.id}
            g={g}
            width={layout.thumbW}
            height={layout.thumbH}
            onOpen={onOpen}
          />
        ))}
      </ScrollView>
    </View>
  );
}

function Thumb({
  g,
  width,
  height,
  onOpen,
}: {
  g: PlayGeneration;
  width: number;
  height: number;
  onOpen: (id: string) => void;
}) {
  return (
    <Pressable
      onPress={() => onOpen(g.id)}
      accessibilityRole="button"
      accessibilityLabel={generationKindLabel(g)}
    >
      <MediaThumb
        url={g.url}
        posterUrl={playGenerationPosterUrl(g)}
        assetType={g.asset_type}
        width={width}
        height={height}
        borderRadius={14}
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "baseline",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  row: { alignItems: "center" },
});
