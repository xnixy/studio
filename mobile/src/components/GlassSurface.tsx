import { type ReactNode, useMemo } from "react";
import {
  Platform,
  StyleSheet,
  View,
  type StyleProp,
  type ViewStyle,
} from "react-native";
import { BlurView } from "expo-blur";
import { useColorScheme } from "react-native";
import { radii } from "../ui/theme";

type BlurTint =
  | "default"
  | "light"
  | "dark"
  | "systemChromeMaterial"
  | "systemMaterial"
  | "systemUltraThinMaterial"
  | "systemThinMaterial"
  | "systemThickMaterial";

type GlassStyle = "clear" | "regular" | "none";

type LiquidProps = {
  children?: ReactNode;
  style?: StyleProp<ViewStyle>;
  contentStyle?: StyleProp<ViewStyle>;
  /** Corner radius */
  radius?: number;
  /** Skip specular edge layer */
  flat?: boolean;
  /** Prefer interactive glass (iOS 26+) */
  interactive?: boolean;
  /** GlassView style when liquid glass API is available */
  glassStyle?: GlassStyle;
  /** Legacy BlurView intensity (fallback only) */
  intensity?: number;
  tint?: BlurTint;
};

function canUseLiquidGlass(): boolean {
  if (Platform.OS !== "ios") return false;
  try {
    // Lazy require so Android/web never load the module path hard.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const glass = require("expo-glass-effect") as {
      isGlassEffectAPIAvailable?: () => boolean;
      isLiquidGlassAvailable?: () => boolean;
    };
    const api = glass.isGlassEffectAPIAvailable?.() ?? false;
    const liq = glass.isLiquidGlassAvailable?.() ?? false;
    return Boolean(api && liq);
  } catch {
    return false;
  }
}

/**
 * Liquid glass plate (SDK 57).
 * - iOS 26+: `GlassView` from expo-glass-effect
 * - Else: expo-blur system material / solid Android fill
 */
export function GlassSurface({
  children,
  style,
  contentStyle,
  intensity = 55,
  tint,
  radius = radii.cardLg,
  flat = false,
  interactive = false,
  glassStyle = "regular",
}: LiquidProps) {
  const dark = useColorScheme() === "dark";
  const useLiquid = useMemo(() => canUseLiquidGlass(), []);

  const resolvedTint: BlurTint =
    tint ??
    (Platform.OS === "ios"
      ? dark
        ? "systemChromeMaterial"
        : "systemUltraThinMaterial"
      : dark
        ? "dark"
        : "light");

  if (useLiquid) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { GlassView } = require("expo-glass-effect") as {
      GlassView: React.ComponentType<{
        style?: StyleProp<ViewStyle>;
        glassEffectStyle?: GlassStyle;
        isInteractive?: boolean;
        colorScheme?: "auto" | "light" | "dark";
        children?: ReactNode;
      }>;
    };
    return (
      <GlassView
        style={[{ overflow: "hidden", borderRadius: radius }, style]}
        glassEffectStyle={glassStyle}
        isInteractive={interactive}
        colorScheme="auto"
      >
        {!flat ? (
          <View
            pointerEvents="none"
            style={[
              StyleSheet.absoluteFill,
              {
                borderWidth: StyleSheet.hairlineWidth,
                borderColor: dark ? "rgba(255,255,255,0.14)" : "rgba(255,255,255,0.55)",
                borderRadius: radius,
              },
            ]}
          />
        ) : null}
        <View style={[{ position: "relative", borderRadius: radius }, contentStyle]}>
          {children}
        </View>
      </GlassView>
    );
  }

  return (
    <View style={[{ overflow: "hidden", borderRadius: radius }, style]}>
      {Platform.OS === "ios" ? (
        <BlurView intensity={intensity} tint={resolvedTint} style={StyleSheet.absoluteFill} />
      ) : (
        <View
          style={[
            StyleSheet.absoluteFill,
            {
              backgroundColor: dark ? "rgba(28,28,30,0.92)" : "rgba(255,255,255,0.92)",
            },
          ]}
        />
      )}
      {!flat ? (
        <View
          pointerEvents="none"
          style={[
            StyleSheet.absoluteFill,
            {
              backgroundColor: dark ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.35)",
              borderWidth: StyleSheet.hairlineWidth,
              borderColor: dark ? "rgba(255,255,255,0.14)" : "rgba(255,255,255,0.65)",
              borderRadius: radius,
            },
          ]}
        />
      ) : null}
      <View style={[{ position: "relative", borderRadius: radius }, contentStyle]}>{children}</View>
    </View>
  );
}

/** Compact glass card / list cell */
export function GlassCard({
  children,
  style,
  contentStyle,
  padded = true,
}: {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  contentStyle?: StyleProp<ViewStyle>;
  padded?: boolean;
}) {
  return (
    <GlassSurface
      intensity={48}
      radius={radii.card}
      style={[
        {
          shadowColor: "#000",
          shadowOpacity: 0.08,
          shadowRadius: 16,
          shadowOffset: { width: 0, height: 6 },
          elevation: 3,
        },
        style,
      ]}
      contentStyle={[{ padding: padded ? 16 : 0 }, contentStyle]}
    >
      {children}
    </GlassSurface>
  );
}
