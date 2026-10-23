import { type ReactNode } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Image } from "expo-image";
import { GlassCard } from "./GlassSurface";
import { useAppColors } from "../ui/theme";

type Props = {
  children: ReactNode;
  /** Big title in the glass hero (e.g. "Sign in"). */
  title?: string;
  /** Short line under the title. */
  subtitle?: string;
  contentContainerStyle?: StyleProp<ViewStyle>;
  /**
   * When true, children own the full-screen SwiftUI Form Host.
   * Shell only paints the canvas (no ScrollView).
   */
  nativeForm?: boolean;
};

/**
 * Public auth shell: same canvas + liquid glass as the logged-in app.
 * Prefer nativeForm + SwiftUI Form (iOS). Android/web still use ScrollView children.
 */
export function AuthFormShell({
  children,
  title,
  subtitle,
  contentContainerStyle,
  nativeForm = false,
}: Props) {
  const colors = useAppColors();
  const insets = useSafeAreaInsets();

  const hero =
    title || subtitle ? (
      <View style={styles.hero}>
        {title ? (
          <Image
            source={require("../../assets/images/icon.png")}
            style={styles.heroIcon}
            contentFit="cover"
            accessibilityLabel="Studio"
          />
        ) : null}
        {title ? <Text style={[styles.heroTitle, { color: colors.fg }]}>{title}</Text> : null}
        {subtitle ? (
          <Text style={[styles.heroSub, { color: colors.muted }]}>{subtitle}</Text>
        ) : null}
      </View>
    ) : null;

  if (nativeForm) {
    return (
      <View style={[styles.root, { backgroundColor: colors.bg }]}>
        {subtitle ? (
          <Text
            style={[
              styles.subtitle,
              {
                color: colors.muted,
                paddingTop: 8,
                paddingHorizontal: 20,
              },
            ]}
          >
            {subtitle}
          </Text>
        ) : null}
        <View style={styles.flex}>{children}</View>
      </View>
    );
  }

  return (
    <View style={[styles.root, { backgroundColor: colors.bg }]}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? 8 : 0}
      >
        <ScrollView
          style={styles.flex}
          contentContainerStyle={[
            {
              paddingHorizontal: 16,
              paddingTop: 8,
              paddingBottom: Math.max(insets.bottom, 12) + 28,
              gap: 16,
            },
            contentContainerStyle,
          ]}
          contentInsetAdjustmentBehavior="automatic"
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="interactive"
          showsVerticalScrollIndicator={false}
        >
          {hero}
          {children}
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

/** Glass section for non-SwiftUI form fallbacks (Android / web). */
export function NativeFormGroup({
  children,
  footer,
}: {
  children: ReactNode;
  footer?: string;
}) {
  const colors = useAppColors();
  return (
    <View style={styles.groupWrap}>
      <GlassCard contentStyle={{ padding: 0 }} padded={false}>
        {children}
      </GlassCard>
      {footer ? (
        <Text style={[styles.groupFooter, { color: colors.muted }]}>{footer}</Text>
      ) : null}
    </View>
  );
}

export function NativeFormField({
  label,
  children,
  isLast,
}: {
  label: string;
  children: ReactNode;
  isLast?: boolean;
}) {
  const colors = useAppColors();
  return (
    <View
      style={[
        styles.fieldRow,
        !isLast && {
          borderBottomWidth: StyleSheet.hairlineWidth,
          borderBottomColor: colors.separator,
        },
      ]}
    >
      <Text style={[styles.fieldLabel, { color: colors.muted }]}>{label}</Text>
      {children}
    </View>
  );
}

export function NativePrimaryButton({
  label,
  onPress,
  disabled,
  busy,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  busy?: boolean;
}) {
  const colors = useAppColors();
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || busy}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: Boolean(disabled || busy), busy: Boolean(busy) }}
      style={({ pressed }) => [
        styles.primaryBtn,
        {
          backgroundColor: disabled || busy ? colors.border : colors.brand,
          opacity: pressed && !disabled && !busy ? 0.88 : 1,
        },
      ]}
    >
      <Text style={[styles.primaryBtnText]}>{label}</Text>
    </Pressable>
  );
}

export function NativeTextLink({
  label,
  onPress,
}: {
  label: string;
  onPress: () => void;
}) {
  const colors = useAppColors();
  return (
    <Pressable
      onPress={onPress}
      hitSlop={10}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <Text style={[styles.textLink, { color: colors.brand }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  flex: { flex: 1 },
  hero: {
    alignItems: "center",
    gap: 5,
    paddingTop: 8,
    paddingBottom: 12,
    paddingHorizontal: 16,
  },
  heroIcon: {
    width: 60,
    height: 60,
    borderRadius: 15,
    marginBottom: 4,
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
  },
  heroTitle: {
    fontSize: 26,
    fontWeight: "700",
    letterSpacing: -0.6,
    textAlign: "center",
  },
  heroSub: {
    fontSize: 15,
    lineHeight: 21,
    textAlign: "center",
    maxWidth: 320,
  },
  subtitle: {
    fontSize: 15,
    lineHeight: 21,
    paddingHorizontal: 4,
    marginBottom: 2,
  },
  groupWrap: { gap: 8 },
  groupFooter: {
    fontSize: 13,
    lineHeight: 18,
    paddingHorizontal: 12,
  },
  fieldRow: {
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 10,
    gap: 6,
  },
  fieldLabel: {
    fontSize: 13,
    fontWeight: "400",
  },
  primaryBtn: {
    minHeight: 50,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 4,
  },
  primaryBtnText: {
    color: "#fff",
    fontSize: 17,
    fontWeight: "600",
  },
  textLink: {
    fontSize: 16,
    fontWeight: "400",
    textAlign: "center",
    paddingVertical: 4,
  },
});
