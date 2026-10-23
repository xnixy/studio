import { Platform } from "react-native";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import Constants from "expo-constants";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { api } from "../api/client";

const DEVICE_ID_KEY = "studio.device.id";

let heldToken: string | null = null;
let registeredUserId: string | null = null;

async function getDeviceId(): Promise<string> {
  const saved = await AsyncStorage.getItem(DEVICE_ID_KEY);
  if (saved) return saved;
  const minted = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
  await AsyncStorage.setItem(DEVICE_ID_KEY, minted);
  return minted;
}

async function getExpoPushToken(requestIfNeeded: boolean): Promise<string | null> {
  if (!Device.isDevice) return null;
  const { status: existing } = await Notifications.getPermissionsAsync();
  let final = existing;
  if (existing !== "granted") {
    if (!requestIfNeeded) return null;
    const req = await Notifications.requestPermissionsAsync();
    final = req.status;
  }
  if (final !== "granted") return null;

  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("generations", {
      name: "Generations",
      importance: Notifications.AndroidImportance.DEFAULT,
    });
  }

  const projectId =
    Constants.easConfig?.projectId ??
    (Constants.expoConfig?.extra as { eas?: { projectId?: string } } | undefined)?.eas?.projectId;

  const token = await Notifications.getExpoPushTokenAsync(
    projectId ? { projectId } : undefined,
  );
  return token.data;
}

export function peekRegisteredPushUserId(): string | null {
  return registeredUserId;
}

export function setRegisteredPushUserId(userId: string | null) {
  registeredUserId = userId;
}

export function hasHeldPushTokenFor(userId: string): boolean {
  return Boolean(heldToken && registeredUserId === userId);
}

export async function registerPushTokenForUser(userId: string, requestIfNeeded: boolean) {
  const token = await getExpoPushToken(requestIfNeeded);
  if (!token) return;
  await api.registerPushToken({
    token,
    platform: Platform.OS === "ios" ? "ios" : "android",
    device_id: await getDeviceId(),
  });
  heldToken = token;
  registeredUserId = userId;
}

/** Ask for permission after the first successful generate, not at login. */
export async function ensurePushRegistration() {
  if (Platform.OS === "web") return;
  try {
    const { status } = await Notifications.getPermissionsAsync();
    if (status !== "granted") {
      const req = await Notifications.requestPermissionsAsync();
      if (req.status !== "granted") return;
    }
    if (!registeredUserId) return;
    await registerPushTokenForUser(registeredUserId, false);
  } catch {
    /* best-effort */
  }
}

/** Call before clearing the session so the server still has a Bearer. */
export async function unregisterPushBeforeLogout() {
  if (Platform.OS === "web" || !heldToken) return;
  try {
    await api.unregisterPushToken({
      token: heldToken,
      platform: Platform.OS === "ios" ? "ios" : "android",
    });
  } catch {
    /* session may already be gone */
  }
  heldToken = null;
  registeredUserId = null;
}
