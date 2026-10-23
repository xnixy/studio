/** Last-used workspace may seed Home fetches, but only for the same account. */
export function resolveActiveWorkspaceId(
  fetchedId: string | null | undefined,
  stored: { userId: string; workspaceId: string } | null,
  currentUserId: string | null | undefined,
): string | null {
  if (fetchedId) return fetchedId;
  if (!stored || !currentUserId) return null;
  return stored.userId === currentUserId ? stored.workspaceId : null;
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
): readonly ["workspaces", string | null, "verified" | "pending"] {
  return ["workspaces", userId ?? null, emailVerified ? "verified" : "pending"];
}

/** Create / Faces / Voices when the personal space is not ready yet. */
export function workspaceActionBlockedMessage(opts: {
  isLoading: boolean;
  error?: string | null;
}): string {
  if (opts.error && !opts.isLoading) return "Could not load your space. Try again.";
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
