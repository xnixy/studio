import { Redirect, Stack, useSegments } from "expo-router";
import { useColorScheme } from "react-native";
import { useAuth } from "@/src/auth/AuthContext";
import { canvasColor, colorsFor } from "@/src/ui/theme";
import { liquidGlassStackHeaderOptions, liquidStackHeaderOptions } from "@/src/ui/nav";

/**
 * Public stack: native transparent headers on the ambient canvas.
 */
export default function PublicLayout() {
  const auth = useAuth();
  const segments = useSegments();
  const dark = useColorScheme() === "dark";
  const colors = colorsFor(dark);
  const onVerify = (segments as string[]).includes("verify-email");

  if (auth.initialized && auth.isAuthenticated) {
    if (!auth.user?.email_verified) {
      if (!onVerify) {
        return <Redirect href={"/(public)/verify-email" as never} />;
      }
    } else {
      return <Redirect href="/(app)" />;
    }
  }

  return (
    <Stack
      screenOptions={{
        ...liquidStackHeaderOptions(colors),
        animation: "default",
        presentation: "card",
        contentStyle: { backgroundColor: canvasColor(dark) },
      }}
    >
      <Stack.Screen name="welcome" options={{ headerShown: false }} />
      {/* Glass pages: transparent header so the ambient canvas shows through the
          status-bar area (matches Welcome/tabs). Hero carries the title, so the
          bar shows only Back. */}
      <Stack.Screen
        name="login"
        options={{ ...liquidGlassStackHeaderOptions(colors), title: "" }}
      />
      <Stack.Screen
        name="register"
        options={{ ...liquidGlassStackHeaderOptions(colors), title: "" }}
      />
      <Stack.Screen
        name="forgot-password"
        options={{ ...liquidGlassStackHeaderOptions(colors), title: "" }}
      />
      <Stack.Screen
        name="reset-password"
        options={{ ...liquidGlassStackHeaderOptions(colors), title: "" }}
      />
      {/* Native-form page keeps the solid bar (transparent breaks its bg). */}
      <Stack.Screen name="verify-email" options={{ title: "Verify Email" }} />
    </Stack>
  );
}
