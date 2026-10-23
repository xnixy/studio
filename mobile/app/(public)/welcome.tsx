import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import {
  AuthFormShell,
  NativePrimaryButton,
  NativeTextLink,
} from "@/src/components/AuthFormShell";
import { openPrivacyPolicy, openTermsOfUse } from "@/src/lib/legal";
import { useAppColors } from "@/src/ui/theme";

/**
 * Signed-out first screen. iOS-native: icon, one line, sign in.
 */
export default function WelcomeScreen() {
  const colors = useAppColors();

  return (
    <AuthFormShell title="Studio" subtitle="A face, a line, a clip.">
      <NativePrimaryButton label="Sign in" onPress={() => router.push("/(public)/login")} />
      <Pressable
        onPress={() => router.push("/(public)/register")}
        accessibilityRole="button"
        accessibilityLabel="Create account"
        style={({ pressed }) => [
          styles.secondary,
          { backgroundColor: colors.chipOff, opacity: pressed ? 0.85 : 1 },
        ]}
      >
        <Text style={[styles.secondaryText, { color: colors.fg }]}>Create account</Text>
      </Pressable>
      <View style={styles.legal}>
        <Pressable
          onPress={() => void openPrivacyPolicy()}
          hitSlop={8}
          accessibilityRole="link"
          accessibilityLabel="Privacy policy"
        >
          <Text style={{ color: colors.muted, fontSize: 13 }}>Privacy</Text>
        </Pressable>
        <Text style={{ color: colors.muted, fontSize: 13 }}>·</Text>
        <Pressable
          onPress={() => void openTermsOfUse()}
          hitSlop={8}
          accessibilityRole="link"
          accessibilityLabel="Terms of use"
        >
          <Text style={{ color: colors.muted, fontSize: 13 }}>Terms</Text>
        </Pressable>
      </View>
    </AuthFormShell>
  );
}

const styles = StyleSheet.create({
  secondary: {
    minHeight: 50,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  secondaryText: {
    fontSize: 17,
    fontWeight: "600",
  },
  legal: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
    paddingTop: 8,
  },
});
