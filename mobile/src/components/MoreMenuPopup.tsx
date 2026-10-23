import {
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  useColorScheme,
  useWindowDimensions,
  View,
} from "react-native";
import { BlurView } from "expo-blur";
import { SymbolView } from "expo-symbols";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import type { AppColors } from "@/src/ui/theme";

export type MoreMenuItem = {
  id: string;
  label: string;
  blurb: string;
  /** SF Symbol name */
  sf: string;
  href: string;
};

type Props = {
  visible: boolean;
  colors: AppColors;
  items: readonly MoreMenuItem[];
  onSelect: (item: MoreMenuItem) => void;
  onClose: () => void;
};

/**
 * Overflow menu for secondary destinations (Voices, Account, Billing).
 *
 * Uses RN Modal so it layers above the native UITabBarController on iPhone and
 * iPad (where the tab bar can sit at the top / side). An absolute View sibling
 * paints under native chrome on iPad.
 */
export function MoreMenuPopup({ visible, colors, items, onSelect, onClose }: Props) {
  const dark = useColorScheme() === "dark";
  const insets = useSafeAreaInsets();
  const { width: winW, height: winH } = useWindowDimensions();
  const isPad = Platform.OS === "ios" && Platform.isPad;

  // iPad native tabs often sit at the top; phone bar is at the bottom.
  const tabBarContent = 49;
  const floatGap = 12;
  const cardW = Math.min(winW - 32, isPad ? 360 : 400);

  const cardStyle = isPad
    ? {
        // Float under the top tab/nav region on iPad.
        top: Math.max(insets.top, 12) + tabBarContent + floatGap,
        alignSelf: "center" as const,
        width: cardW,
      }
    : {
        bottom: tabBarContent + Math.max(insets.bottom, 0) + floatGap,
        left: (winW - cardW) / 2,
        width: cardW,
      };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      // Over full screen so we sit above native tab chrome on iPad.
      presentationStyle="overFullScreen"

      onRequestClose={onClose}
    >
      <View style={[styles.portal, { minHeight: winH }]} pointerEvents="box-none">
        <Pressable
          style={styles.scrim}
          onPress={onClose}
          accessibilityRole="button"
          accessibilityLabel="Dismiss menu"
        />

        <View pointerEvents="box-none" style={[styles.anchor, cardStyle]}>
          <View
            style={[
              styles.card,
              {
                borderColor: dark ? "rgba(255,255,255,0.18)" : "rgba(255,255,255,0.65)",
                backgroundColor:
                  Platform.OS === "ios"
                    ? dark
                      ? "rgba(28,28,30,0.92)"
                      : "rgba(255,255,255,0.94)"
                    : dark
                      ? "rgba(44,44,46,0.96)"
                      : "rgba(255,255,255,0.96)",
                shadowColor: "#000",
                shadowOpacity: dark ? 0.45 : 0.18,
                shadowRadius: 24,
                shadowOffset: { width: 0, height: 10 },
                elevation: 24,
              },
            ]}
          >
            {Platform.OS === "ios" ? (
              <BlurView
                intensity={90}
                tint={dark ? "systemChromeMaterialDark" : "systemChromeMaterialLight"}
                style={StyleSheet.absoluteFill}
              />
            ) : null}

            <View style={styles.headerRow}>
              <Text style={[styles.title, { color: colors.fg }]}>More</Text>
              <Pressable onPress={onClose} hitSlop={12} accessibilityLabel="Close">
                <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 16 }}>Close</Text>
              </Pressable>
            </View>

            <View style={styles.list}>
              {items.map((item, index) => (
                <Pressable
                  key={item.id}
                  onPress={() => onSelect(item)}
                  style={[
                    styles.row,
                    {
                      borderBottomColor: dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)",
                      borderBottomWidth: index === items.length - 1 ? 0 : StyleSheet.hairlineWidth,
                    },
                  ]}
                  accessibilityRole="button"
                  accessibilityLabel={item.label}
                >
                  <View
                    style={[
                      styles.iconPlate,
                      {
                        backgroundColor: dark ? "rgba(10,132,255,0.22)" : "rgba(0,122,255,0.12)",
                      },
                    ]}
                  >
                    <SymbolView
                      name={item.sf as never}
                      size={18}
                      tintColor={colors.brand}
                      weight="semibold"
                      fallback={
                        <Text style={{ color: colors.brand, fontWeight: "800", fontSize: 13 }}>
                          {item.label.slice(0, 1)}
                        </Text>
                      }
                    />
                  </View>
                  <View style={{ flex: 1, minWidth: 0 }}>
                    <Text style={{ color: colors.fg, fontSize: 16, fontWeight: "700" }}>
                      {item.label}
                    </Text>
                    <Text
                      style={{ color: colors.muted, fontSize: 12.5, marginTop: 2 }}
                      numberOfLines={1}
                    >
                      {item.blurb}
                    </Text>
                  </View>
                  <Text style={{ color: colors.muted, fontSize: 18, fontWeight: "300" }}>›</Text>
                </Pressable>
              ))}
            </View>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  portal: {
    flex: 1,
  },
  scrim: {
    ...StyleSheet.absoluteFill,
    backgroundColor: "rgba(0,0,0,0.28)",
  },
  anchor: {
    position: "absolute",
    zIndex: 2,
  },
  card: {
    borderRadius: 28,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: "hidden",
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 6,
  },
  title: {
    fontSize: 17,
    fontWeight: "700",
    letterSpacing: -0.2,
  },
  list: {
    paddingHorizontal: 8,
    paddingBottom: 10,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 12,
    paddingHorizontal: 10,
  },
  iconPlate: {
    width: 36,
    height: 36,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
});
