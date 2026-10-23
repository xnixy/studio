import { Alert, Platform } from "react-native";

import { hapticError, hapticWarning } from "./haptics";

export function alertError(title: string, message: string) {
  // Every error alert in the app routes through here, so this is the one place
  // failure needs to be wired up. Do not add hapticError at the call sites too.
  void hapticError();
  Alert.alert(title, message, [{ text: "OK", style: "default" }]);
}

export function alertConfirm(
  title: string,
  message: string,
  onConfirm: () => void,
  confirmLabel = "Delete",
) {
  const destructive =
    /delete|remove|sign out|log out/i.test(confirmLabel) ||
    /delete|remove|sign out|log out/i.test(title);
  // Warn on the way in, so a destructive prompt feels different from a plain one.
  if (destructive) void hapticWarning();
  Alert.alert(title, message, [
    { text: "Cancel", style: "cancel" },
    {
      text: confirmLabel,
      style: destructive ? "destructive" : "default",
      onPress: onConfirm,
    },
  ]);
}

export function alertInfo(title: string, message: string) {
  Alert.alert(title, message);
}

/** iOS action sheet-style options (uses Alert on both platforms). */
export function alertActions(
  title: string,
  message: string | undefined,
  actions: { label: string; style?: "default" | "cancel" | "destructive"; onPress?: () => void }[],
) {
  Alert.alert(
    title,
    message,
    actions.map((a) => ({
      text: a.label,
      style: a.style ?? "default",
      onPress: a.onPress,
    })),
    { cancelable: true },
  );
}

export function isIos() {
  return Platform.OS === "ios";
}
