import { Platform } from "react-native";

/** Safe haptics wrapper — never static-imports expo-haptics (breaks web SSR). */
type HapticsModule = typeof import("expo-haptics");

async function run(fire: (h: HapticsModule) => Promise<void>) {
  if (Platform.OS === "web") return;
  try {
    await fire(await import("expo-haptics"));
  } catch {
    /* ignore */
  }
}

/** Finished and worked: clip ready, face saved, purchase complete. */
export function hapticSuccess() {
  return run((h) => h.notificationAsync(h.NotificationFeedbackType.Success));
}

/** Failed and needs attention. Fires centrally from `alertError`. */
export function hapticError() {
  return run((h) => h.notificationAsync(h.NotificationFeedbackType.Error));
}

/** About to do something destructive or irreversible. */
export function hapticWarning() {
  return run((h) => h.notificationAsync(h.NotificationFeedbackType.Warning));
}

/** Ordinary tap: buttons, chips, opening a sheet. */
export function hapticLight() {
  return run((h) => h.impactAsync(h.ImpactFeedbackStyle.Light));
}

/** Heavier tap for a committing action, e.g. starting a generation. */
export function hapticMedium() {
  return run((h) => h.impactAsync(h.ImpactFeedbackStyle.Medium));
}

/**
 * Value changed in a picker, segmented control, or filter row.
 * Quieter than an impact, so it does not get tiring while scrubbing options.
 */
export function hapticSelection() {
  return run((h) => h.selectionAsync());
}
