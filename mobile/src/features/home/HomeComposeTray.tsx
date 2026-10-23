import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Image } from "expo-image";
import type { PlayFace, PlayVoiceOption } from "@/src/api/types";
import { HOME_TRAY_MAX, HOME_TRAY_GUTTER, homeInnerWidth } from "@/src/features/home/homeLayout";
import { hapticLight } from "@/src/lib/haptics";
import { mediaImageSource } from "@/src/lib/media";
import { faceVoiceCaption } from "@/src/lib/stockVoices";
import type { AppColors } from "@/src/ui/theme";

type Props = {
  colors: AppColors;
  faces: PlayFace[];
  voices: PlayVoiceOption[];
  onNewFace: () => void;
  onSelectFace: (id: string) => void;
  onEditFace: (id: string) => void;
  onClip: () => void;
  onStill: () => void;
};

export function HomeComposeTray({
  colors,
  faces,
  voices,
  onNewFace,
  onSelectFace,
  onEditFace,
  onClip,
  onStill,
}: Props) {
  const { width } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const inner = homeInnerWidth(width, insets.left, insets.right);
  const trayW = Math.min(HOME_TRAY_MAX, Math.max(0, inner - HOME_TRAY_GUTTER * 2));

  return (
    <View
      style={[
        styles.shadow,
        {
          width: trayW,
          marginBottom: Math.max(insets.bottom, 10),
        },
      ]}
    >
      <View
        style={[
          styles.tray,
          {
            backgroundColor: colors.composer,
          },
        ]}
      >
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.rail}
        >
          <Pressable
            onPress={onNewFace}
            accessibilityRole="button"
            accessibilityLabel="Add a new face"
            style={[styles.circle, styles.circleDash, { borderColor: colors.brand }]}
          >
            <Text style={{ color: colors.brand, fontWeight: "700", fontSize: 18 }}>+</Text>
          </Pressable>
          {faces.slice(0, 16).map((f) => {
            const src = mediaImageSource(f.url);
            const caption = faceVoiceCaption(f, voices);
            return (
              <View key={f.id} style={styles.faceCol}>
                <Pressable
                  onPress={() => onSelectFace(f.id)}
                  onLongPress={() => {
                    void hapticLight();
                    onEditFace(f.id);
                  }}
                  delayLongPress={350}
                  accessibilityRole="button"
                  accessibilityLabel={
                    caption
                      ? `${f.label || "Face"}, ${caption}. Long-press to edit look and voice.`
                      : `${f.label || "Face"}. Long-press to edit look and voice.`
                  }
                  style={[styles.circle, { borderColor: colors.border }]}
                >
                  {src ? (
                    <Image
                      source={src}
                      style={styles.circleImg}
                      contentFit="cover"
                      contentPosition="top"
                      recyclingKey={f.id}
                    />
                  ) : (
                    <View style={[styles.circleImg, { backgroundColor: colors.chipOff }]} />
                  )}
                </Pressable>
                {caption ? (
                  <Text
                    numberOfLines={1}
                    style={{ color: colors.muted, fontSize: 10, fontWeight: "600", maxWidth: 56 }}
                  >
                    {caption}
                  </Text>
                ) : null}
              </View>
            );
          })}
        </ScrollView>
        {faces.length === 0 ? (
          <Text style={{ color: colors.muted, fontSize: 12, lineHeight: 16 }}>
            Add a Face. That is who talks.
          </Text>
        ) : null}

        <View style={styles.btns}>
          <Pressable
            onPress={onClip}
            accessibilityRole="button"
            accessibilityLabel="Clip"
            style={({ pressed }) => [
              styles.btn,
              { backgroundColor: colors.brand, opacity: pressed ? 0.85 : 1 },
            ]}
          >
            <Text style={styles.btnPrimary}>Clip</Text>
          </Pressable>
          <Pressable
            onPress={onStill}
            accessibilityRole="button"
            accessibilityLabel="Still"
            style={({ pressed }) => [
              styles.btn,
              { backgroundColor: colors.chipOff, opacity: pressed ? 0.85 : 1 },
            ]}
          >
            <Text style={[styles.btnSecondary, { color: colors.fg }]}>Still</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  shadow: {
    alignSelf: "center",
    shadowColor: "#000",
    shadowOpacity: 0.22,
    shadowRadius: 22,
    shadowOffset: { width: 0, height: 10 },
    elevation: 16,
  },
  tray: {
    paddingTop: 10,
    paddingHorizontal: 14,
    paddingBottom: 12,
    gap: 10,
    borderRadius: 22,
    overflow: "hidden",
  },
  rail: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    paddingBottom: 2,
  },
  faceCol: {
    alignItems: "center",
    gap: 4,
    width: 56,
  },
  circle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 1.5,
    overflow: "hidden",
    alignItems: "center",
    justifyContent: "center",
  },
  circleDash: {
    borderStyle: "dashed",
  },
  circleImg: {
    width: 44,
    height: 44,
    borderRadius: 22,
  },
  btns: {
    flexDirection: "row",
    gap: 8,
  },
  btn: {
    flex: 1,
    minHeight: 44,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  btnPrimary: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 16,
  },
  btnSecondary: {
    fontWeight: "700",
    fontSize: 16,
  },
});
