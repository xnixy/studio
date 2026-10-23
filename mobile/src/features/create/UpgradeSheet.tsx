import {
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  useColorScheme,
  View,
} from "react-native";
import { BlurView } from "expo-blur";
import { router } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import type { AppColors } from "@/src/ui/theme";

type Props = {
  visible: boolean;
  onClose: () => void;
  colors: AppColors;
  /** Suggested plan label, e.g. Starter */
  planLabel?: string;
  title?: string;
  body?: string;
};

/**
 * Paywall for Advanced models (Seedance, Veo, Kling, Nano Banana).
 * Free users stay on Grok Fast until they upgrade.
 */
export function UpgradeSheet({
  visible,
  onClose,
  colors,
  planLabel = "Starter",
  title = "Advanced models need Starter",
  body = "Free includes Grok for drafts. Starter adds Seedance, Veo, Kling, Nano Banana, and more engines.",
}: Props) {
  const insets = useSafeAreaInsets();
  const dark = useColorScheme() === "dark";

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"

      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <Pressable
          style={styles.backdrop}
          onPress={onClose}
          accessibilityRole="button"
          accessibilityLabel="Dismiss"
        />
        <View
          style={[
            styles.card,
            {
              marginBottom: Math.max(insets.bottom, 16),
              borderColor: colors.border,
              overflow: "hidden",
            },
          ]}
        >
          {Platform.OS === "ios" ? (
            <BlurView
              intensity={dark ? 48 : 36}
              tint={dark ? "systemChromeMaterialDark" : "systemChromeMaterialLight"}
              style={StyleSheet.absoluteFill}
            />
          ) : (
            <View
              style={[
                StyleSheet.absoluteFill,
                { backgroundColor: dark ? "rgba(28,28,30,0.96)" : "rgba(255,255,255,0.98)" },
              ]}
            />
          )}
          <View style={styles.inner}>
            <Text style={[styles.title, { color: colors.fg }]}>{title}</Text>
            <Text style={[styles.body, { color: colors.muted }]}>{body}</Text>
            <Pressable
              onPress={() => {
                onClose();
                router.push("/(app)/billing" as never);
              }}
              style={[styles.primary, { backgroundColor: colors.brand }]}
              accessibilityRole="button"
              accessibilityLabel={`Upgrade to ${planLabel}`}
            >
              <Text style={styles.primaryText}>Upgrade to {planLabel}</Text>
            </Pressable>
            <Pressable
              onPress={onClose}
              style={styles.secondary}
              accessibilityRole="button"
              accessibilityLabel="Stay on Fast"
            >
              <Text style={{ color: colors.muted, fontWeight: "600", fontSize: 15 }}>
                Stay on Fast (Grok)
              </Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(0,0,0,0.35)",
    paddingHorizontal: 14,
  },
  backdrop: {
    ...StyleSheet.absoluteFill,
  },
  card: {
    borderRadius: 20,
    borderWidth: StyleSheet.hairlineWidth,
  },
  inner: {
    paddingHorizontal: 20,
    paddingTop: 22,
    paddingBottom: 16,
    gap: 12,
  },
  title: {
    fontSize: 20,
    fontWeight: "700",
    letterSpacing: -0.3,
  },
  body: {
    fontSize: 15,
    lineHeight: 22,
  },
  primary: {
    marginTop: 6,
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: "center",
  },
  primaryText: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 16,
  },
  secondary: {
    paddingVertical: 10,
    alignItems: "center",
  },
});
