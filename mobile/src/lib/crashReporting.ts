import * as Sentry from "@sentry/react-native";

import { IS_PRODUCTION_API } from "./config";

/**
 * Crash reporting for store builds.
 *
 * No DSN means no init, so local and Expo Go runs stay quiet and a missing
 * secret can never break startup. Set EXPO_PUBLIC_SENTRY_DSN in the EAS build
 * profile (or an EAS secret) to turn it on.
 */
const DSN = process.env.EXPO_PUBLIC_SENTRY_DSN?.trim();

export const crashReportingEnabled = Boolean(DSN) && !__DEV__;

export function initCrashReporting(): void {
  if (!crashReportingEnabled) return;
  Sentry.init({
    dsn: DSN,
    environment: IS_PRODUCTION_API ? "production" : "staging",
    // Crashes and errors only. No session replay, no profiling, no PII.
    sendDefaultPii: false,
    tracesSampleRate: 0,
    enableAutoSessionTracking: true,
  });
}

/** Attach the signed-in user so a crash can be traced to an account. */
export function setCrashUser(userId: string | null): void {
  if (!crashReportingEnabled) return;
  Sentry.setUser(userId ? { id: userId } : null);
}

/** Report a handled failure worth knowing about (never user content). */
export function reportHandledError(error: unknown, context?: Record<string, string>): void {
  if (!crashReportingEnabled) return;
  Sentry.captureException(error, context ? { tags: context } : undefined);
}
