import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { SymbolView } from "expo-symbols";
import type { PlayVoiceOption } from "@/src/api/types";
import type { AppColors } from "@/src/ui/theme";

type Props = {
  colors: AppColors;
  voices: PlayVoiceOption[];
  voiceId: string;
  hint?: string | null;
  showAdd: boolean;
  showMore?: boolean;
  bindFaceId?: string | null;
  onSelect: (id: string) => void;
};

function voicesHref(bindFaceId?: string | null) {
  return {
    pathname: "/(app)/voices" as const,
    params: bindFaceId ? { bind_face_id: bindFaceId } : {},
  };
}

/** Featured names for the Create bar. Full catalog lives on Voices. */
export function ComposerVoiceStrip({
  colors,
  voices,
  voiceId,
  hint,
  showAdd,
  showMore = true,
  bindFaceId,
  onSelect,
}: Props) {
  return (
    <View style={styles.root}>
      {hint ? (
        <Text style={{ color: colors.muted, fontSize: 12, lineHeight: 16 }}>{hint}</Text>
      ) : null}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.row}
      >
        {voices.length === 0 ? (
          <Text style={{ color: colors.muted, fontSize: 14, paddingVertical: 4 }}>
            Loading voices…
          </Text>
        ) : null}
        {voices.map((v) => {
          const on = v.id === voiceId;
          return (
            <Pressable
              key={v.id}
              onPress={() => onSelect(v.id)}
              accessibilityRole="button"
              accessibilityLabel={v.name}
              accessibilityState={{ selected: on }}
              hitSlop={6}
              style={({ pressed }) => [{ opacity: pressed ? 0.6 : 1 }]}
            >
              <Text
                style={{
                  color: on ? colors.brand : colors.fg,
                  fontWeight: on ? "700" : "500",
                  fontSize: 15,
                }}
              >
                {v.name}
              </Text>
            </Pressable>
          );
        })}
        {showAdd ? (
          <Pressable
            onPress={() => router.push(voicesHref(bindFaceId))}
            accessibilityRole="button"
            accessibilityLabel="Add your voice"
            hitSlop={6}
            style={({ pressed }) => [{ opacity: pressed ? 0.6 : 1 }]}
          >
            <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 15 }}>Add yours</Text>
          </Pressable>
        ) : null}
        {showMore ? (
          <Pressable
            onPress={() => router.push(voicesHref(bindFaceId))}
            accessibilityRole="button"
            accessibilityLabel="More voices"
            hitSlop={6}
            style={({ pressed }) => [styles.more, { opacity: pressed ? 0.6 : 1 }]}
          >
            <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 15 }}>More</Text>
            <SymbolView
              name={{ ios: "chevron.right", android: "chevron_right", web: "chevron_right" }}
              size={12}
              tintColor={colors.brand}
              weight="semibold"
            />
          </Pressable>
        ) : null}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: 8,
    paddingBottom: 8,
  },
  row: {
    gap: 16,
    alignItems: "center",
    paddingHorizontal: 2,
    minHeight: 28,
  },
  more: {
    flexDirection: "row",
    alignItems: "center",
    gap: 2,
  },
});
