import { useColorScheme, type ColorSchemeName } from "react-native";
import { DarkTheme, DefaultTheme, type Theme } from "expo-router";

/**
 * Single ambient canvas + liquid-glass tokens (public + logged-in).
 * No dual system-grouped vs ambient product skins.
 */
export type AppColors = {
  bg: string;
  card: string;
  fg: string;
  muted: string;
  brand: string;
  brandSoft: string;
  border: string;
  danger: string;
  success: string;
  input: string;
  chipOn: string;
  chipOff: string;
  userBubble: string;
  userText: string;
  systemBubble: string;
  systemText: string;
  field: string;
  divider: string;
  ring: string;
  composer: string;
  /** @deprecated Alias of bg — kept so old call sites typecheck during migration */
  systemGroupedBg: string;
  /** Translucent cell / glass underlay (not solid Settings white) */
  systemGroupedCell: string;
  separator: string;
};

export function colorsFor(dark: boolean): AppColors {
  const bg = dark ? "#050508" : "#E8ECF4";
  return {
    bg,
    card: dark ? "rgba(28,28,30,0.55)" : "rgba(255,255,255,0.55)",
    fg: dark ? "#F5F5F7" : "#0B0B0F",
    muted: dark ? "#8E8E93" : "#636366",
    brand: dark ? "#0A84FF" : "#007AFF",
    brandSoft: dark ? "rgba(10,132,255,0.22)" : "rgba(0,122,255,0.14)",
    border: dark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.08)",
    danger: "#FF453A",
    success: "#34C759",
    input: dark ? "rgba(118,118,128,0.28)" : "rgba(120,120,128,0.12)",
    chipOn: dark ? "rgba(10,132,255,0.28)" : "rgba(0,122,255,0.14)",
    chipOff: dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.05)",
    userBubble: dark ? "#0A84FF" : "#007AFF",
    userText: "#FFFFFF",
    systemBubble: dark ? "rgba(118,118,128,0.28)" : "rgba(120,120,128,0.16)",
    systemText: dark ? "#F5F5F7" : "#111111",
    field: dark ? "rgba(118,118,128,0.24)" : "rgba(120,120,128,0.12)",
    divider: dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)",
    ring: dark ? "rgba(10,132,255,0.9)" : "rgba(0,122,255,0.85)",
    composer: dark ? "rgba(20,20,22,0.78)" : "rgba(255,255,255,0.55)",
    systemGroupedBg: bg,
    systemGroupedCell: dark ? "rgba(28,28,30,0.72)" : "rgba(255,255,255,0.72)",
    separator: dark ? "rgba(84,84,88,0.65)" : "rgba(60,60,67,0.29)",
  };
}

/** Canvas under glass / stack contentStyle. */
export function canvasColor(dark: boolean): string {
  return colorsFor(dark).bg;
}

export function useAppColors(): AppColors {
  return colorsFor(useColorScheme() === "dark");
}

/**
 * Expo Router ThemeProvider value.
 * Card and background must both be the canvas. DefaultTheme uses white, and a
 * mismatched card is what you see as a white splash when popping a stack screen.
 */
export function studioNavigationTheme(scheme: ColorSchemeName | null | undefined): Theme {
  const dark = scheme === "dark";
  const c = colorsFor(dark);
  const base = dark ? DarkTheme : DefaultTheme;
  return {
    ...base,
    dark,
    colors: {
      ...base.colors,
      primary: c.brand,
      background: c.bg,
      card: c.bg,
      text: c.fg,
      border: dark ? "#38383A" : "#C6C6C8",
      notification: c.brand,
    },
  };
}

export const type = {
  title: { fontSize: 34, fontWeight: "700" as const, letterSpacing: -0.8 },
  headline: { fontSize: 22, fontWeight: "700" as const, letterSpacing: -0.3 },
  body: { fontSize: 16, fontWeight: "400" as const, lineHeight: 22 },
  callout: { fontSize: 15, fontWeight: "400" as const, lineHeight: 20 },
  caption: { fontSize: 13, fontWeight: "400" as const },
  section: {
    fontSize: 13,
    fontWeight: "600" as const,
    letterSpacing: -0.1,
  },
};

export const radii = {
  card: 22,
  cardLg: 28,
  chip: 999,
  field: 22,
  button: 16,
  bubble: 20,
};
