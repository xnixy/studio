import assert from "node:assert/strict";
import {
  accountIdentityChanged,
  canFetchWorkspaces,
  resolveActiveWorkspaceId,
  workspaceActionBlockedMessage,
  workspacesQueryKey,
} from "./resolveWorkspaceId";

assert.equal(resolveActiveWorkspaceId("ws-new", { userId: "a", workspaceId: "ws-old" }, "a"), "ws-new");
assert.equal(
  resolveActiveWorkspaceId(null, { userId: "a", workspaceId: "ws-old" }, "a"),
  "ws-old",
);
assert.equal(
  resolveActiveWorkspaceId(null, { userId: "a", workspaceId: "ws-old" }, "b"),
  null,
);
assert.equal(resolveActiveWorkspaceId(null, { userId: "a", workspaceId: "ws-old" }, null), null);
assert.equal(resolveActiveWorkspaceId(null, null, "b"), null);

assert.equal(accountIdentityChanged("a", "b"), true);
assert.equal(accountIdentityChanged("a", null), true);
assert.equal(accountIdentityChanged(null, "b"), false);
assert.equal(accountIdentityChanged("a", "a"), false);

assert.equal(canFetchWorkspaces({ accessToken: "t", userId: "u", emailVerified: true }), true);
assert.equal(canFetchWorkspaces({ accessToken: "t", userId: "u", emailVerified: false }), false);
assert.equal(canFetchWorkspaces({ accessToken: "t", userId: "u", emailVerified: null }), false);
assert.equal(canFetchWorkspaces({ accessToken: null, userId: "u", emailVerified: true }), false);

assert.deepEqual(workspacesQueryKey("u1", true), ["workspaces", "u1", "verified"]);
assert.deepEqual(workspacesQueryKey("u1", false), ["workspaces", "u1", "pending"]);

assert.equal(workspaceActionBlockedMessage({ isLoading: true, error: null }), "Account is still loading");
assert.equal(
  workspaceActionBlockedMessage({ isLoading: false, error: "Request failed" }),
  "Could not load your space. Try again.",
);

console.log("resolveWorkspaceId ok");
