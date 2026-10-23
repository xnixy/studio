import { Redirect, Stack } from "expo-router";
import { useColorScheme } from "react-native";
import { useAuth } from "@/src/auth/AuthContext";
import { canvasColor, colorsFor } from "@/src/ui/theme";
import { liquidGlassStackHeaderOptions } from "@/src/ui/nav";

/**
 * Authenticated shell: Home is the root. Everything else is a stack screen.
 */
export default function AppLayout() {
  const auth = useAuth();
  const dark = useColorScheme() === "dark";
  const colors = colorsFor(dark);
  const bg = canvasColor(dark);

  if (!auth.initialized) {
    return null;
  }
  if (!auth.isAuthenticated) {
    return <Redirect href="/(public)/welcome" />;
  }
  if (!auth.user?.email_verified) {
    return <Redirect href={"/(public)/verify-email" as never} />;
  }

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        headerShadowVisible: false,
        headerTransparent: false,
        statusBarTranslucent: true,
        contentStyle: { backgroundColor: bg },
      }}
    >
      <Stack.Screen
        name="index"
        options={{
          headerShown: false,
          // iOS 26 paints a liquid-glass fade on the first ScrollView. Hide it
          // so Home stays a transparent status bar with clips sliding under.
          scrollEdgeEffects: {
            top: "hidden",
            bottom: "hidden",
            left: "hidden",
            right: "hidden",
          },
        }}
      />
      <Stack.Screen
        name="profile"
        options={{
          ...liquidGlassStackHeaderOptions(colors),
          title: "Account",
          presentation: "card",
        }}
      />
      <Stack.Screen
        name="play"
        options={{
          ...liquidGlassStackHeaderOptions(colors),
          title: "Create",
          presentation: "card",
          // Composer is position:absolute. Native avoidance does not move it,
          // and enabling both with a manual lift double-counts on some iPads.
          keyboardHandlingEnabled: false,
        }}
      />
      <Stack.Screen
        name="library"
        options={{
          ...liquidGlassStackHeaderOptions(colors),
          title: "Library",
          presentation: "card",
        }}
      />
      <Stack.Screen
        name="faces"
        options={{
          ...liquidGlassStackHeaderOptions(colors),
          title: "Faces",
          presentation: "card",
        }}
      />
      <Stack.Screen
        name="face-edit"
        options={{
          ...liquidGlassStackHeaderOptions(colors),
          title: "Edit face",
          presentation: "card",
        }}
      />
      <Stack.Screen
        name="clip/[id]"
        options={{
          ...liquidGlassStackHeaderOptions(colors),
          title: "Clip",
          presentation: "card",
        }}
      />
      <Stack.Screen
        name="voices"
        options={{
          ...liquidGlassStackHeaderOptions(colors),
          title: "Voices",
          presentation: "card",
        }}
      />
      <Stack.Screen
        name="face-voice"
        options={{
          ...liquidGlassStackHeaderOptions(colors),
          title: "Voice",
          presentation: "card",
        }}
      />
      <Stack.Screen
        name="billing"
        options={{
          ...liquidGlassStackHeaderOptions(colors),
          title: "Billing",
          presentation: "card",
        }}
      />
    </Stack>
  );
}
