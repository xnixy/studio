import { useState } from "react";
import { StyleSheet, View, type GestureResponderEvent } from "react-native";
import { Image, type ImageSource } from "expo-image";
import type { AppColors } from "@/src/ui/theme";

/** Cap so iPad does not turn the plate into a full-screen square. */
const PREVIEW_MAX = 320;

type Props = {
  colors: AppColors;
  after: ImageSource | null;
  before?: ImageSource | null;
  compare?: number;
  onCompare?: (value: number) => void;
};

function clampCompare(x: number, width: number): number {
  if (width <= 0) return 50;
  return Math.max(0, Math.min(100, (x / width) * 100));
}

/**
 * Face-edit preview. After Apply, drag to wipe between old and new.
 * No range slider under the photo. The divider is the control.
 */
export function BeforeAfterCompare({
  colors,
  after,
  before = null,
  compare = 50,
  onCompare,
}: Props) {
  const [width, setWidth] = useState(0);
  const canCompare = Boolean(before && onCompare);
  const split = canCompare ? (width * compare) / 100 : 0;

  const setFromEvent = (e: GestureResponderEvent) => {
    if (!onCompare) return;
    onCompare(clampCompare(e.nativeEvent.locationX, width));
  };

  return (
    <View style={styles.wrap}>
      <View
        onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
        onStartShouldSetResponder={() => canCompare}
        onMoveShouldSetResponder={() => canCompare}
        onResponderGrant={canCompare ? setFromEvent : undefined}
        onResponderMove={canCompare ? setFromEvent : undefined}
        accessibilityRole={canCompare ? "adjustable" : undefined}
        accessibilityLabel={canCompare ? "Compare before and after" : undefined}
        accessibilityValue={canCompare ? { min: 0, max: 100, now: Math.round(compare) } : undefined}
        style={[styles.frame, { backgroundColor: colors.field }]}
      >
        {after ? (
          <Image source={after} style={StyleSheet.absoluteFill} contentFit="cover" />
        ) : null}
        {canCompare && before && width > 0 ? (
          <View style={[styles.clip, { width: split }]}>
            <Image source={before} style={{ width, height: width }} contentFit="cover" />
          </View>
        ) : null}
        {canCompare && width > 0 ? (
          <View pointerEvents="none" style={[styles.rule, { left: split - 1 }]}>
            <View style={[styles.thumb, { borderColor: colors.bg, backgroundColor: colors.fg }]} />
          </View>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: "center",
  },
  frame: {
    width: "100%",
    maxWidth: PREVIEW_MAX,
    aspectRatio: 1,
    borderRadius: 18,
    overflow: "hidden",
  },
  clip: {
    position: "absolute",
    top: 0,
    bottom: 0,
    left: 0,
    overflow: "hidden",
  },
  rule: {
    position: "absolute",
    top: 0,
    bottom: 0,
    width: 2,
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  thumb: {
    width: 28,
    height: 28,
    marginLeft: -13,
    borderRadius: 14,
    borderWidth: 2,
  },
});
