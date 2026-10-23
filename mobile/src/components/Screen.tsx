import { type ReactNode } from "react";
import {
  ScrollView,
  StyleSheet,
  View,
  type RefreshControlProps,
  type StyleProp,
  type ViewStyle,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAppColors } from "../ui/theme";

type Props = {
  children: ReactNode;
  /** Scrollable content (default true for list-style screens) */
  scroll?: boolean;
  contentContainerStyle?: StyleProp<ViewStyle>;
  style?: StyleProp<ViewStyle>;
  refreshControl?: React.ReactElement<RefreshControlProps>;
  keyboardShouldPersistTaps?: "always" | "never" | "handled";
  /** Extra bottom padding under the home indicator */
  bottomPad?: number;
  /**
   * Pad scroll *content* below the status bar (header-less Home). The screen
   * itself stays edge-to-edge so clips slide under a transparent status bar.
   * Do not put paddingTop on the root View: that paints a solid plate the
   * scroller never draws into.
   */
  safeTop?: boolean;
  /**
   * Add the home-indicator inset to scroll padding. Home sets this false when
   * an overlay tray already includes that inset.
   */
  safeBottom?: boolean;
};

/**
 * Authenticated screen shell: canvas + optional scroll.
 * Uses automatic content insets on screens with a native header.
 */
export function Screen({
  children,
  scroll = true,
  contentContainerStyle,
  style,
  refreshControl,
  keyboardShouldPersistTaps = "handled",
  bottomPad = 24,
  safeTop = false,
  safeBottom = true,
}: Props) {
  const colors = useAppColors();
  const insets = useSafeAreaInsets();

  // Horizontal insets matter on iPad when the tab bar becomes a sidebar: native
  // may publish leading safe-area for the content column; apply it in RN too.
  const padL = insets.left > 0 ? insets.left : 0;
  const padR = insets.right > 0 ? insets.right : 0;
  const flatContent = StyleSheet.flatten(contentContainerStyle);
  const extraTop = typeof flatContent?.paddingTop === "number" ? flatContent.paddingTop : 8;

  return (
    <View
      style={[
        styles.root,
        {
          backgroundColor: colors.bg,
          paddingLeft: padL,
          paddingRight: padR,
        },
        style,
      ]}
    >
      {scroll ? (
        <ScrollView
          style={styles.flex}
          contentContainerStyle={[
            {
              paddingBottom: (safeBottom ? Math.max(insets.bottom, 12) : 0) + bottomPad,
            },
            contentContainerStyle,
            safeTop ? { paddingTop: insets.top + extraTop } : null,
          ]}
          contentInsetAdjustmentBehavior={safeTop ? "never" : "automatic"}
          automaticallyAdjustsScrollIndicatorInsets
          keyboardShouldPersistTaps={keyboardShouldPersistTaps}
          keyboardDismissMode="on-drag"
          showsVerticalScrollIndicator={false}
          refreshControl={refreshControl}
          nestedScrollEnabled
        >
          {children}
        </ScrollView>
      ) : (
        children
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  flex: { flex: 1 },
});
