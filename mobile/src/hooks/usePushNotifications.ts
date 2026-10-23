import { useEffect } from "react";
import { Platform } from "react-native";
import * as Notifications from "expo-notifications";
import { router } from "expo-router";
import { useAuth } from "../auth/AuthContext";
import {
  ensurePushRegistration,
  hasHeldPushTokenFor,
  registerPushTokenForUser,
  setRegisteredPushUserId,
  unregisterPushBeforeLogout,
} from "../lib/pushToken";

export { ensurePushRegistration, unregisterPushBeforeLogout };

// Push is native-only; avoid native module setup on web.
if (Platform.OS !== "web") {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}

const UUID_RE =
  /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
/** Last-response is sticky across launches. Ignore taps older than this. */
const COLD_START_WINDOW_SEC = 45;

let lastOpenedIdent: string | null = null;
let lastOpenedAt = 0;
let listenerOpenedThisSession = false;

function asRecord(value: unknown): Record<string, unknown> | undefined {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  if (typeof value === "string" && value.startsWith("{")) {
    try {
      const parsed = JSON.parse(value) as unknown;
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
    } catch {
      /* ignore */
    }
  }
  return undefined;
}

function uuidFrom(value: unknown): string | null {
  if (typeof value !== "string" || !value) return null;
  const hit = UUID_RE.exec(value);
  return hit ? hit[0].toLowerCase() : null;
}

export function clipIdFromPushData(data: Record<string, unknown> | undefined): string | null {
  const root = asRecord(data) ?? {};
  const extra = asRecord(root.extra);
  return (
    uuidFrom(root.asset_id) ||
    uuidFrom(extra?.asset_id) ||
    uuidFrom(root.entity_id) ||
    uuidFrom(root.href) ||
    null
  );
}

function notificationTimeSec(n: Notifications.Notification): number {
  const raw = n.date;
  if (typeof raw !== "number" || !Number.isFinite(raw)) return Date.now() / 1000;
  return raw > 1e12 ? raw / 1000 : raw;
}

function openClipFromResponse(response: Notifications.NotificationResponse) {
  const ident = response.notification.request.identifier;
  const at = notificationTimeSec(response.notification);
  if (ident && ident === lastOpenedIdent) return;
  if (at && lastOpenedAt && at < lastOpenedAt) return;
  const data = asRecord(response.notification.request.content.data);
  const id = clipIdFromPushData(data);
  if (!id) return;
  lastOpenedIdent = ident || id;
  lastOpenedAt = at || Date.now() / 1000;
  router.push(`/(app)/clip/${id}`);
}

/** Register device for remote push + open the clip when a banner is tapped. */
export function usePushNotifications() {
  const auth = useAuth();

  useEffect(() => {
    if (Platform.OS === "web") return;
    let cancelled = false;

    (async () => {
      if (!auth.isAuthenticated || !auth.user?.id) {
        setRegisteredPushUserId(null);
        return;
      }

      setRegisteredPushUserId(auth.user.id);
      if (hasHeldPushTokenFor(auth.user.id)) return;

      try {
        // Do not prompt here. Login is the wrong moment. Register if already granted.
        await registerPushTokenForUser(auth.user.id, false);
        if (cancelled) return;
      } catch {
        // Push is best-effort (Expo Go / simulators may not support it).
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [auth.isAuthenticated, auth.user?.id]);

  useEffect(() => {
    if (Platform.OS === "web") return;

    const sub = Notifications.addNotificationResponseReceivedListener((response) => {
      listenerOpenedThisSession = true;
      openClipFromResponse(response);
    });

    void Notifications.getLastNotificationResponseAsync().then((response) => {
      if (!response) return;
      // A live tap already won. The last-response API is sticky and can replay
      // yesterday's clip after today's banner.
      if (listenerOpenedThisSession) return;
      const at = notificationTimeSec(response.notification);
      if (Date.now() / 1000 - at > COLD_START_WINDOW_SEC) return;
      openClipFromResponse(response);
    });

    return () => {
      sub.remove();
    };
  }, []);
}
