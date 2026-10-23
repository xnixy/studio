import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "../ui/theme";
import { GlassCard } from "./GlassSurface";

export function LoadingBlock({ colors, label = "Loading…" }: { colors: AppColors; label?: string }) {
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.brand} />
      <Text style={[styles.muted, { color: colors.muted }]}>{label}</Text>
    </View>
  );
}

export function EmptyState({
  colors,
  title,
  body,
  actionLabel,
  onAction,
}: {
  colors: AppColors;
  title: string;
  body: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <GlassCard style={styles.wrap}>
      <Text style={[styles.title, { color: colors.fg }]}>{title}</Text>
      <Text style={[styles.body, { color: colors.muted }]}>{body}</Text>
      {actionLabel && onAction ? (
        <Pressable
          onPress={onAction}
          accessibilityRole="button"
          accessibilityLabel={actionLabel}
          style={{ marginTop: 14 }}
        >
          <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 16 }}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </GlassCard>
  );
}

export function ErrorState({
  colors,
  message,
  onRetry,
}: {
  colors: AppColors;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <GlassCard style={styles.wrap}>
      <Text style={[styles.title, { color: colors.danger }]}>Something went wrong</Text>
      <Text style={[styles.body, { color: colors.muted }]}>{message}</Text>
      {onRetry ? (
        <Pressable
          onPress={onRetry}
          accessibilityRole="button"
          accessibilityLabel="Try again"
          style={{ marginTop: 14 }}
        >
          <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 16 }}>Try again</Text>
        </Pressable>
      ) : null}
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  center: { padding: 40, alignItems: "center", gap: 10 },
  muted: { fontSize: 14 },
  wrap: { marginHorizontal: 0 },
  title: { fontSize: 17, fontWeight: "700", letterSpacing: -0.2 },
  body: { fontSize: 15, lineHeight: 21, marginTop: 6 },
});
