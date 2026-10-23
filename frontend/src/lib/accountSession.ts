import type { QueryClient } from "@tanstack/react-query";

const ACCOUNT_LOCAL_KEYS = [
  "studio-active-face",
  "studio-active-voice",
  "studio-workspace",
] as const;

const ACCOUNT_SESSION_KEYS = ["studio.play.idempotency"] as const;

/** Drop account-scoped browser prefs. Theme and chunk-reload guards stay. */
export function clearAccountBrowserStorage(): void {
  try {
    for (const key of ACCOUNT_LOCAL_KEYS) {
      localStorage.removeItem(key);
    }
    const prefixed: string[] = [];
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i);
      if (key?.startsWith("studio-workspace:")) prefixed.push(key);
    }
    for (const key of prefixed) localStorage.removeItem(key);
  } catch {
    /* quota / private mode */
  }
  try {
    for (const key of ACCOUNT_SESSION_KEYS) {
      sessionStorage.removeItem(key);
    }
  } catch {
    /* ignore */
  }
}

/** Wipe Library / Faces / billing cache so the next account cannot see it. */
export function resetAccountClientState(queryClient: QueryClient): void {
  queryClient.clear();
  clearAccountBrowserStorage();
}

/** GET /workspaces 403s until verify. Fetching then caches a dead query. */
export function canFetchWorkspaces(opts: {
  accessToken?: string | null;
  userId?: string | null;
  emailVerified?: boolean | null;
}): boolean {
  return Boolean(opts.accessToken && opts.userId && opts.emailVerified);
}

export function workspacesQueryKey(
  userId: string | null | undefined,
  emailVerified: boolean | null | undefined,
): readonly ["workspaces", "workspaces", string | null, "verified" | "pending"] {
  return ["workspaces", "workspaces", userId ?? null, emailVerified ? "verified" : "pending"];
}

export function workspaceActionBlockedMessage(opts: {
  loading: boolean;
  error?: string | null;
}): string {
  if (opts.error && !opts.loading) return "Could not load your space. Try again.";
  return "Account is still loading";
}

/** True when the signed-in account changed, including logout. */
export function accountIdentityChanged(
  previousUserId: string | null | undefined,
  nextUserId: string | null | undefined,
): boolean {
  const prev = previousUserId ?? null;
  const next = nextUserId ?? null;
  return Boolean(prev && prev !== next);
}
