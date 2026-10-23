import { Pressable, StyleSheet, Text, View } from "react-native";
import { hapticLight } from "@/src/lib/haptics";
import type { QualityTier } from "@/src/lib/qualityTier";
import type { AppColors } from "@/src/ui/theme";

type QualityProps = {
  colors: AppColors;
  qualityTier: QualityTier;
  onQualityTierChange: (tier: QualityTier) => void;
};

/** Still Fast / Quality. Lives in headerRight. Clip vs Still is chosen on Home. */
export function CreateQualityHeader({ colors, qualityTier, onQualityTierChange }: QualityProps) {
  return (
    <View style={styles.qualityRow} accessibilityRole="tablist">
      {(["fast", "advanced"] as const).map((tier) => {
        const on = qualityTier === tier;
        const label = tier === "fast" ? "Fast" : "Quality";
        return (
          <Pressable
            key={tier}
            onPress={() => {
              void hapticLight();
              onQualityTierChange(tier);
            }}
            accessibilityRole="tab"
            accessibilityLabel={label}
            accessibilityState={{ selected: on }}
            style={[styles.qualityChip, { backgroundColor: on ? colors.chipOn : "transparent" }]}
          >
            <Text style={{ color: on ? colors.brand : colors.muted, fontWeight: "600", fontSize: 13 }}>
              {label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  qualityRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 2,
    paddingRight: 4,
  },
  qualityChip: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
  },
});
