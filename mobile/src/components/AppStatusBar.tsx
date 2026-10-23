import { useEffect } from "react";
import { Platform, StatusBar, useColorScheme } from "react-native";

/**
 * Translucent status bar. The canvas and scrolled clips show through.
 * Screen `safeTop` pads scroll content so "Hey" starts below the icons.
 */
export function AppStatusBar() {
  const dark = useColorScheme() === "dark";
  const barStyle = dark ? "light-content" : "dark-content";

  useEffect(() => {
    StatusBar.setBarStyle(barStyle, true);
    if (Platform.OS === "android") {
      StatusBar.setBackgroundColor("transparent", true);
      StatusBar.setTranslucent(true);
    }
  }, [barStyle]);

  return (
    <StatusBar
      barStyle={barStyle}
      backgroundColor="transparent"
      translucent
      animated
    />
  );
}
