import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { SymbolView } from "expo-symbols";
import { hapticLight } from "@/src/lib/haptics";
import type { AppColors } from "@/src/ui/theme";

export function HomeShortcuts({ colors }: { colors: AppColors }) {
  return (
    <View style={styles.row}>
      <Shortcut
        colors={colors}
        label="Faces"
        accessibilityLabel="Faces"
        symbol={{ ios: "person.crop.rectangle", android: "person", web: "person" }}
        onPress={() => {
          void hapticLight();
          router.push("/(app)/faces");
        }}
      />
      <Shortcut
        colors={colors}
        label="Voices"
        accessibilityLabel="Voices"
        symbol={{ ios: "waveform", android: "graphic_eq", web: "graphic_eq" }}
        onPress={() => {
          void hapticLight();
          router.push("/(app)/voices");
        }}
      />
    </View>
  );
}

function Shortcut({
  colors,
  label,
  accessibilityLabel,
  symbol,
  onPress,
}: {
  colors: AppColors;
  label: string;
  accessibilityLabel: string;
  symbol: { ios: string; android: string; web: string };
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      style={({ pressed }) => [
        styles.btn,
        { backgroundColor: colors.chipOff, opacity: pressed ? 0.7 : 1 },
      ]}
    >
      <SymbolView
        name={symbol as never}
        size={18}
        tintColor={colors.brand}
        weight="semibold"
        fallback={<Text style={{ color: colors.brand, fontWeight: "700", fontSize: 15 }}>{label}</Text>}
      />
      <Text style={{ color: colors.fg, fontWeight: "700", fontSize: 15 }}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: 8 },
  btn: {
    flex: 1,
    minHeight: 44,
    borderRadius: 14,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 12,
  },
});
