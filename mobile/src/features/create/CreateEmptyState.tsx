import { StyleSheet, Text, View } from "react-native";
import type { PlayMode } from "@/src/api/types";
import { composerTabForMode } from "@/src/features/create/createConstants";
import type { AppColors } from "@/src/ui/theme";

type Props = {
  colors: AppColors;
  mode: PlayMode;
};

/**
 * Empty Create thread. Clip vs Still only. Kind is confirmed on the draft card.
 */
export function CreateEmptyState({ colors, mode }: Props) {
  const tab = composerTabForMode(mode);

  return (
    <View style={styles.root}>
      <Text style={[styles.title, { color: colors.fg }]}>
        {tab === "still" ? "Make a still" : "Make a clip"}
      </Text>
      <Text style={[styles.sub, { color: colors.muted }]}>
        {tab === "still"
          ? "Describe the still. Send when you are ready."
          : "Write what it is about. We confirm Talking or Scene before you spend credits."}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    paddingBottom: 60,
    paddingHorizontal: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    letterSpacing: -0.4,
    textAlign: "center",
  },
  sub: {
    fontSize: 15,
    lineHeight: 21,
    textAlign: "center",
  },
});
