import Constants from "expo-constants";
import { Platform } from "react-native";

/** Public marketing site (privacy / terms). */
export const MARKETING_BASE_URL = "https://example.com";

/** Production API used by store / TestFlight builds when no env override is set. */
export const PRODUCTION_API_BASE_URL = "https://api.example.com/api";

/**
 * Resolve a host the phone can actually reach.
 * - Expo Go: use the same machine IP Metro uses (not localhost).
 * - Explicit EXPO_PUBLIC_API_BASE_URL always wins.
 */
function expoLanHost(): string | null {
  const hostUri =
    Constants.expoConfig?.hostUri ||
    // Expo Go / legacy manifests
    (Constants as { manifest2?: { extra?: { expoGo?: { debuggerHost?: string } } } }).manifest2
      ?.extra?.expoGo?.debuggerHost ||
    (Constants as { manifest?: { debuggerHost?: string } }).manifest?.debuggerHost ||
    null;

  if (!hostUri) return null;
  // hostUri looks like "10.0.0.131:8081" or "10.0.0.131:8081/path"
  const host = hostUri.split(":")[0]?.trim();
  if (!host || host === "localhost" || host === "127.0.0.1") return null;
  return host;
}

function isLocalUrl(url: string): boolean {
  return (
    url.includes("localhost") ||
    url.includes("127.0.0.1") ||
    url.includes("10.0.2.2") ||
    /^https?:\/\/(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(url)
  );
}

function isStoreBuild(): boolean {
  // Expo Go / dev client keep __DEV__ true. Release and TestFlight builds do not.
  return !__DEV__;
}

function defaultApiBase(): string {
  if (isStoreBuild()) {
    return PRODUCTION_API_BASE_URL;
  }
  const lan = expoLanHost();
  if (lan) {
    // Docker compose API is typically 3001; local uvicorn often 3001 too.
    return `http://${lan}:3001/api`;
  }
  // Simulator / web on the same machine
  if (Platform.OS === "android") {
    // Android emulator loopback to host
    return "http://10.0.2.2:3001/api";
  }
  return "http://localhost:3001/api";
}

const fromEnv = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
const fromExtra = (Constants.expoConfig?.extra as { apiBaseUrl?: string } | undefined)?.apiBaseUrl;

/** Prefer env, then app.json extra only if it is not a bare localhost default on device. */
function resolveApiBase(): string {
  if (fromEnv) {
    const env = fromEnv.replace(/\/$/, "");
    // Never ship a private LAN URL inside a store binary, even if someone baked .env into EAS.
    if (isStoreBuild() && isLocalUrl(env)) {
      return PRODUCTION_API_BASE_URL;
    }
    return env;
  }

  const extra = fromExtra?.trim().replace(/\/$/, "");
  const lan = expoLanHost();
  if (extra) {
    if (isStoreBuild() && isLocalUrl(extra)) {
      return PRODUCTION_API_BASE_URL;
    }
    const isLocalhost = extra.includes("localhost") || extra.includes("127.0.0.1");
    if (isLocalhost && lan && !isStoreBuild()) {
      return `http://${lan}:3001/api`;
    }
    return extra;
  }

  return defaultApiBase().replace(/\/$/, "");
}

export const API_BASE_URL = resolveApiBase();

/** True when talking to a production-like host (hide debug chrome). */
export const IS_PRODUCTION_API =
  isStoreBuild() ||
  API_BASE_URL.includes("api.example.com") ||
  API_BASE_URL.startsWith("https://");

/** Sent on every request so the API returns refresh tokens in JSON. */
export const CLIENT_HEADER = "mobile" as const;
