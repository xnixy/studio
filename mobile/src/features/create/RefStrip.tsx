import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Image } from "expo-image";
import type { PlayRef } from "@/src/api/types";
import { mediaImageSource } from "@/src/lib/media";

export type LocalRefChip =
  | { localId: string; status: "uploading"; kind: "image" | "video" | "audio"; previewUri?: string }
  | {
      localId: string;
      status: "ready";
      kind: "image" | "video" | "audio";
      ref: PlayRef;
      previewUri?: string;
      /** What this image shows ("her friend"). Named refs are the only ones
       *  the model can act on; unnamed ones arrive as pixels with no role. */
      role?: string;
    }
  | { localId: string; status: "error"; kind: "image" | "video" | "audio"; message: string };

type Props = {
  items: LocalRefChip[];
  colors: {
    card: string;
    border: string;
    fg: string;
    muted: string;
    brand: string;
    danger: string;
    chipOff: string;
    field?: string;
  };
  onRemove: (localId: string) => void;
  onRoleChange?: (localId: string, role: string) => void;
};

export function RefStrip({ items, colors, onRemove, onRoleChange }: Props) {
  if (!items.length) return null;
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{ gap: 8, paddingBottom: 8 }}
    >
      {items.map((item) => {
        const remote =
          item.status === "ready" ? mediaImageSource(item.ref.url) : null;
        const localPreview =
          item.status === "uploading"
            ? item.previewUri
            : item.status === "ready"
              ? item.previewUri
              : undefined;
        const thumbSource = remote || (localPreview ? { uri: localPreview } : null);
        return (
          <View
            key={item.localId}
            style={[
              styles.chip,
              {
                backgroundColor: colors.field || colors.chipOff,
                borderColor: colors.border,
              },
            ]}
          >
            {item.kind === "image" && thumbSource ? (
              <Image source={thumbSource} style={styles.thumb} contentFit="cover" />
            ) : (
              <View style={[styles.thumb, { backgroundColor: colors.chipOff, alignItems: "center", justifyContent: "center" }]}>
                <Text style={{ color: colors.muted, fontSize: 10, fontWeight: "800" }}>
                  {item.kind === "video" ? "Clip" : item.kind === "audio" ? "Audio" : "Photo"}
                </Text>
              </View>
            )}
            <Text style={{ color: colors.muted, fontSize: 10, fontWeight: "700", marginTop: 2 }}>
              {item.kind}
            </Text>
            {item.status === "uploading" ? (
              <ActivityIndicator size="small" color={colors.brand} style={{ marginTop: 4 }} />
            ) : null}
            {item.status === "error" ? (
              <Text style={{ color: colors.danger, fontSize: 9, marginTop: 2 }} numberOfLines={1}>
                Fail
              </Text>
            ) : null}
            {item.status === "ready" && item.kind === "image" && onRoleChange ? (
              <TextInput
                value={item.role ?? ""}
                onChangeText={(next) => onRoleChange(item.localId, next)}
                placeholder="name it"
                placeholderTextColor={colors.muted}
                maxLength={80}
                accessibilityLabel="Name this reference"
                style={[styles.role, { color: colors.fg, borderColor: colors.border }]}
              />
            ) : null}
            <Pressable
              onPress={() => onRemove(item.localId)}
              hitSlop={8}
              accessibilityRole="button"
              accessibilityLabel="Remove reference"
              style={[styles.x, { backgroundColor: colors.chipOff }]}
            >
              <Text style={{ color: colors.fg, fontWeight: "800", fontSize: 11 }}>×</Text>
            </Pressable>
          </View>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  chip: {
    width: 64,
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    padding: 6,
    alignItems: "center",
  },
  thumb: { width: 48, height: 48, borderRadius: 12 },
  role: {
    marginTop: 3,
    width: 52,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 8,
    paddingHorizontal: 4,
    paddingVertical: 2,
    fontSize: 9,
    textAlign: "center",
  },
  x: {
    position: "absolute",
    top: 2,
    right: 2,
    width: 18,
    height: 18,
    borderRadius: 9,
    alignItems: "center",
    justifyContent: "center",
  },
});
