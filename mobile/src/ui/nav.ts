import type { TextStyle } from "react-native";
import type { AppColors } from "./theme";

/** Pushed stack screens (clip detail, etc.). Solid bar matching canvas. */
export function liquidStackHeaderOptions(colors: AppColors) {
  return {
    headerShown: true,
    headerLargeTitle: false,
    headerTransparent: false,
    headerShadowVisible: false,
    headerStyle: { backgroundColor: colors.bg },
    headerTintColor: colors.brand,
    headerTitleStyle: { color: colors.fg, fontWeight: "600" } as TextStyle,
    headerBackTitle: "Back",
    headerBackVisible: true,
    statusBarTranslucent: true,
    contentStyle: { backgroundColor: colors.bg },
  };
}

/**
 * Pushed stack screens that should match the header-less tab pages
 * (clip detail, Billing, Voices). The bar is transparent so the ambient
 * canvas shows through; on iOS 26 the back button + title render as liquid
 * glass. contentStyle still has to be the canvas: the native screen view
 * defaults to white, which flashes on pop if this is omitted.
 */
export function liquidGlassStackHeaderOptions(colors: AppColors) {
  return {
    headerShown: true,
    headerLargeTitle: false,
    headerTransparent: true,
    headerShadowVisible: false,
    headerStyle: { backgroundColor: "transparent" },
    headerTintColor: colors.brand,
    headerTitleStyle: { color: colors.fg, fontWeight: "600" } as TextStyle,
    headerBackTitle: "Back",
    headerBackVisible: true,
    statusBarTranslucent: true,
    contentStyle: { backgroundColor: colors.bg },
  };
}
