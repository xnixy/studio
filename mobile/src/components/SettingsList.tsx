import { type ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SymbolView } from "expo-symbols";
import { GlassCard } from "./GlassSurface";
import { useAppColors } from "../ui/theme";

export function SettingsGroup({
  header,
  footer,
  children,
}: {
  header?: string;
  footer?: string;
  children: ReactNode;
}) {
  const colors = useAppColors();
  return (
    <View style={styles.group}>
      {header ? (
        <Text style={[styles.header, { color: colors.muted }]}>{header}</Text>
      ) : null}
      <GlassCard padded={false} contentStyle={styles.card}>{children}</GlassCard>
      {footer ? (
        <Text style={[styles.footer, { color: colors.muted }]}>{footer}</Text>
      ) : null}
    </View>
  );
}

export function SettingsRow({
  label,
  detail,
  symbol,
  onPress,
  destructive,
  last,
}: {
  label: string;
  detail?: string;
  symbol: { ios: string; android: string; web: string };
  onPress: () => void;
  destructive?: boolean;
  last?: boolean;
}) {
  const colors = useAppColors();
  const tint = destructive ? colors.danger : colors.brand;
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={detail ? `${label}, ${detail}` : label}
      style={({ pressed }) => [
        styles.row,
        !last ? { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.separator } : null,
        { opacity: pressed ? 0.55 : 1 },
      ]}
    >
      <View style={[styles.iconWell, { backgroundColor: tint }]}>
        <SymbolView name={symbol as never} size={15} tintColor="#fff" weight="semibold" />
      </View>
      <Text style={[styles.label, { color: destructive ? colors.danger : colors.fg }]}>{label}</Text>
      {detail ? (
        <Text style={[styles.detail, { color: colors.muted }]} numberOfLines={1}>
          {detail}
        </Text>
      ) : null}
      <SymbolView
        name={{ ios: "chevron.right", android: "chevron_right", web: "chevron_right" }}
        size={13}
        tintColor={colors.muted}
        weight="semibold"
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  group: { gap: 7 },
  header: {
    fontSize: 13,
    fontWeight: "400",
    letterSpacing: -0.08,
    textTransform: "uppercase",
    paddingHorizontal: 16,
  },
  footer: {
    fontSize: 13,
    lineHeight: 18,
    paddingHorizontal: 16,
  },
  card: { paddingVertical: 0, paddingHorizontal: 0 },
  row: {
    minHeight: 44,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  iconWell: {
    width: 29,
    height: 29,
    borderRadius: 7,
    alignItems: "center",
    justifyContent: "center",
  },
  label: { flex: 1, fontSize: 17, fontWeight: "400" },
  detail: { fontSize: 16, maxWidth: "42%", textAlign: "right" },
});
