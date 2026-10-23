import { Link, Stack } from "expo-router";
import { Pressable, StyleSheet, Text, View, useColorScheme } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

export default function NotFoundScreen() {
  const dark = useColorScheme() === "dark";
  const insets = useSafeAreaInsets();
  const colors = {
    bg: dark ? "#050508" : "#E8ECF4",
    fg: dark ? "#F5F5F7" : "#0B0B0F",
    muted: dark ? "#8E8E93" : "#636366",
    brand: dark ? "#0A84FF" : "#007AFF",
    card: dark ? "rgba(28,28,30,0.92)" : "rgba(255,255,255,0.92)",
  };

  return (
    <>
      <Stack.Screen options={{ title: "Not found", headerShown: true }} />
      <View
        style={[
          styles.root,
          {
            backgroundColor: colors.bg,
            paddingTop: insets.top + 48,
            paddingBottom: insets.bottom + 24,
          },
        ]}
      >
        <View style={[styles.card, { backgroundColor: colors.card }]}>
          <Text style={[styles.kicker, { color: colors.muted }]}>404</Text>
          <Text style={[styles.title, { color: colors.fg }]}>This screen does not exist.</Text>
          <Text style={[styles.body, { color: colors.muted }]}>
            The link may be old, or the page moved. Go back home and keep creating.
          </Text>
          <Link href="/" asChild>
            <Pressable
              style={[styles.btn, { backgroundColor: colors.brand }]}
              accessibilityRole="button"
              accessibilityLabel="Go home"
            >
              <Text style={styles.btnText}>Go home</Text>
            </Pressable>
          </Link>
        </View>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: "center",
  },
  card: {
    borderRadius: 20,
    padding: 22,
    gap: 10,
  },
  kicker: {
    fontSize: 13,
    fontWeight: "700",
    letterSpacing: 0.6,
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    letterSpacing: -0.3,
  },
  body: {
    fontSize: 15,
    lineHeight: 21,
    marginBottom: 8,
  },
  btn: {
    alignSelf: "flex-start",
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderRadius: 14,
    minHeight: 44,
    justifyContent: "center",
  },
  btnText: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 16,
  },
});
