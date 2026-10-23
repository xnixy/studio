import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const ACCESS_KEY = "studio_access_token";
const REFRESH_KEY = "studio_refresh_token";
const WORKSPACE_KEY = "studio_workspace_id";
const WORKSPACE_USER_KEY = "studio_workspace_user";
const FACE_KEY = "studio_active_face";
const VOICE_KEY = "studio_active_voice";
const PLAY_IDEM_KEY = "studio.play.idempotency";

/**
 * iOS Keychain default (WHEN_UNLOCKED) can throw:
 * "getValueWithKeyAsync ... User interaction is not allowed"
 * during login / cold start when the UI isn't considered interactive yet.
 *
 * AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY: readable after first unlock without
 * prompting the user, and not restored to other devices from backups.
 */
const SECURE_OPTS: SecureStore.SecureStoreOptions =
  Platform.OS === "ios"
    ? {
        keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
      }
    : {};

/** Store / TestFlight builds must not fall back to plain AsyncStorage for tokens. */
function isStoreBuild(): boolean {
  return !__DEV__;
}

async function secureGet(key: string): Promise<string | null> {
  try {
    const value = await SecureStore.getItemAsync(key);
    if (value != null) return value;
  } catch (error) {
    console.warn("[sessionStorage] SecureStore get failed", key, error);
    if (isStoreBuild()) return null;
  }
  if (isStoreBuild()) {
    // Read legacy AsyncStorage only to migrate/clear, not as ongoing storage.
    try {
      const legacy = await AsyncStorage.getItem(key);
      if (legacy != null) {
        try {
          await SecureStore.setItemAsync(key, legacy, SECURE_OPTS);
          await AsyncStorage.removeItem(key);
          return legacy;
        } catch {
          await AsyncStorage.removeItem(key);
          return null;
        }
      }
    } catch {
      /* ignore */
    }
    return null;
  }
  try {
    return await AsyncStorage.getItem(key);
  } catch {
    return null;
  }
}

async function secureSet(key: string, value: string): Promise<void> {
  try {
    await SecureStore.setItemAsync(key, value, SECURE_OPTS);
    // Drop any legacy AsyncStorage copy once Keychain write succeeds.
    try {
      await AsyncStorage.removeItem(key);
    } catch {
      /* ignore */
    }
    return;
  } catch (error) {
    console.warn("[sessionStorage] SecureStore set failed", key, error);
    if (isStoreBuild()) {
      throw error instanceof Error ? error : new Error("Could not store session securely");
    }
  }
  await AsyncStorage.setItem(key, value);
}

async function secureDelete(key: string): Promise<void> {
  try {
    await SecureStore.deleteItemAsync(key);
  } catch (error) {
    console.warn("[sessionStorage] SecureStore delete failed", key, error);
  }
  try {
    await AsyncStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

async function prefGet(key: string): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(key);
  } catch {
    // Migrate any older SecureStore prefs once.
    try {
      const legacy = await SecureStore.getItemAsync(key);
      if (legacy != null) {
        await AsyncStorage.setItem(key, legacy);
        try {
          await SecureStore.deleteItemAsync(key);
        } catch {
          /* ignore */
        }
        return legacy;
      }
    } catch {
      /* ignore */
    }
    return null;
  }
}

async function prefSet(key: string, value: string): Promise<void> {
  await AsyncStorage.setItem(key, value);
}

async function prefDelete(key: string): Promise<void> {
  try {
    await AsyncStorage.removeItem(key);
  } catch {
    /* ignore */
  }
  try {
    await SecureStore.deleteItemAsync(key);
  } catch {
    /* ignore */
  }
}

export const sessionStorage = {
  getAccessToken: () => secureGet(ACCESS_KEY),
  getRefreshToken: () => secureGet(REFRESH_KEY),

  setTokens: async (access: string, refresh: string | null | undefined) => {
    // Write independently so a Keychain hiccup on one key still persists the other via fallback.
    await secureSet(ACCESS_KEY, access);
    if (refresh) {
      await secureSet(REFRESH_KEY, refresh);
    }
  },

  clearAccountPrefs: () =>
    Promise.all([
      prefDelete(WORKSPACE_KEY),
      prefDelete(WORKSPACE_USER_KEY),
      prefDelete(FACE_KEY),
      prefDelete(VOICE_KEY),
      prefDelete(PLAY_IDEM_KEY),
    ]).then(() => undefined),

  clearTokens: async () => {
    await Promise.all([
      secureDelete(ACCESS_KEY),
      secureDelete(REFRESH_KEY),
      prefDelete(WORKSPACE_KEY),
      prefDelete(WORKSPACE_USER_KEY),
      prefDelete(FACE_KEY),
      prefDelete(VOICE_KEY),
      prefDelete(PLAY_IDEM_KEY),
    ]);
  },

  getWorkspaceBinding: async (): Promise<{ userId: string; workspaceId: string } | null> => {
    const [workspaceId, userId] = await Promise.all([
      prefGet(WORKSPACE_KEY),
      prefGet(WORKSPACE_USER_KEY),
    ]);
    if (!workspaceId || !userId) return null;
    return { userId, workspaceId };
  },
  getWorkspaceId: () => prefGet(WORKSPACE_KEY),
  setWorkspaceId: async (id: string, userId?: string | null) => {
    await prefSet(WORKSPACE_KEY, id);
    if (userId) await prefSet(WORKSPACE_USER_KEY, userId);
    else await prefDelete(WORKSPACE_USER_KEY);
  },
  clearWorkspaceId: async () => {
    await Promise.all([prefDelete(WORKSPACE_KEY), prefDelete(WORKSPACE_USER_KEY)]);
  },

  getActiveFaceId: () => prefGet(FACE_KEY),
  setActiveFaceId: (id: string) => prefSet(FACE_KEY, id),
  clearActiveFaceId: () => prefDelete(FACE_KEY),

  getActiveVoiceId: () => prefGet(VOICE_KEY),
  setActiveVoiceId: (id: string) => prefSet(VOICE_KEY, id),
  clearActiveVoiceId: () => prefDelete(VOICE_KEY),
};
