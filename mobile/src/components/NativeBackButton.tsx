import { Pressable, Text, Platform, View, type TextStyle } from "react-native";
import { router } from "expo-router";

type Props = {
  tint: string;
  label?: string;
};

/** Minimal stack options bag (avoids hard dep on @react-navigation/native-stack types). */
export type ClearStackHeaderExtras = {
  title?: string;
  presentation?: "card" | "modal" | "transparentModal" | "fullScreenModal" | "formSheet";
  headerShown?: boolean;
  headerBackTitle?: string;
  [key: string]: unknown;
};

/**
 * Custom back control with fully transparent chrome.
 * System UIBarButtonItem glass often renders a white plate on iOS.
 */
export function NativeBackButton({ tint, label = "Back" }: Props) {
  return (
    <View style={{ backgroundColor: "transparent" }}>
      <Pressable
        onPress={() => {
          if (router.canGoBack()) router.back();
          else router.replace("/(public)/welcome");
        }}
        hitSlop={12}
        style={{
          flexDirection: "row",
          alignItems: "center",
          paddingVertical: 4,
          paddingRight: 8,
          marginLeft: Platform.OS === "ios" ? -6 : 0,
          backgroundColor: "transparent",
        }}
        accessibilityRole="button"
        accessibilityLabel="Go back"
      >
        <Text
          style={{
            color: tint,
            fontSize: 28,
            fontWeight: "300",
            lineHeight: 30,
            marginTop: -2,
            backgroundColor: "transparent",
          }}
        >
          ‹
        </Text>
        <Text
          style={{
            color: tint,
            fontSize: 17,
            fontWeight: "400",
            marginLeft: 2,
            backgroundColor: "transparent",
          }}
        >
          {label}
        </Text>
      </Pressable>
    </View>
  );
}

export function navTint(dark: boolean) {
  return dark ? "#0A84FF" : "#007AFF";
}

export function navTitleColor(dark: boolean) {
  return dark ? "#FFFFFF" : "#000000";
}

export function navBackground(dark: boolean) {
  // Same ambient canvas as the rest of the app (liquid glass underlay).
  return dark ? "#050508" : "#E8ECF4";
}

/** Fully clear nav bar background (no blur material, no solid fill). */
export function ClearHeaderBackground() {
  return <View style={{ flex: 1, backgroundColor: "transparent" }} pointerEvents="none" />;
}

/** Solid header fill when you explicitly want a painted bar. */
export function HeaderBackground({ color }: { color: string }) {
  return <View style={{ flex: 1, backgroundColor: color }} />;
}

/**
 * Stack header with no plate (no blur / no solid fill) and the **system** back button.
 * Prefer solidStackHeaderOptions for auth screens; transparent is easy to flash white on iOS.
 */
export function clearStackHeaderOptions(dark: boolean, extras?: ClearStackHeaderExtras) {
  const tint = navTint(dark);
  const titleColor = navTitleColor(dark);
  const titleStyle: TextStyle = { fontWeight: "600", color: titleColor };
  return {
    headerShown: true,
    headerLargeTitle: false,
    headerTransparent: true,
    headerShadowVisible: false,
    headerStyle: { backgroundColor: "transparent" },
    headerBackground: () => <ClearHeaderBackground />,
    headerTintColor: tint,
    headerTitleStyle: titleStyle,
    headerBackTitle: "Back",
    headerBackVisible: true,
    ...extras,
  };
}

/**
 * Solid stack header matching the app canvas (login/register/etc.).
 * Avoids transparent + blur plates that read as white in dark mode.
 */
export function solidStackHeaderOptions(dark: boolean, extras?: ClearStackHeaderExtras) {
  const tint = navTint(dark);
  const titleColor = navTitleColor(dark);
  const bg = navBackground(dark);
  const titleStyle: TextStyle = { fontWeight: "600", color: titleColor };
  return {
    headerShown: true,
    headerLargeTitle: false,
    headerTransparent: false,
    headerShadowVisible: false,
    headerStyle: { backgroundColor: bg },
    headerBackground: () => <HeaderBackground color={bg} />,
    headerTintColor: tint,
    headerTitleStyle: titleStyle,
    headerBackTitle: "Back",
    headerBackVisible: true,
    contentStyle: { backgroundColor: bg },
    ...extras,
  };
}
