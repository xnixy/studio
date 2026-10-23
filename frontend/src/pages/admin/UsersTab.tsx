import type { AdminUser, Role } from "../../types";
import type { WithBusy } from "./types";
import { Button, Field, Input, Select } from "../../ui";
import { adminTable as t } from "./tableClasses";

export function UsersTab({
  users,
  filter,
  onFilter,
  busy,
  selfId,
  withBusy,
  onRole,
  onToggleDisabled,
  onRevoke,
}: {
  users: AdminUser[];
  filter: string;
  onFilter: (value: string) => void;
  busy: boolean;
  selfId: string | undefined;
  withBusy: WithBusy;
  onRole: (userId: string, role: Role) => Promise<void>;
  onToggleDisabled: (userId: string, disabled: boolean) => Promise<void>;
  onRevoke: (userId: string) => Promise<void>;
}) {
  return (
    <div className={t.stack}>
      <p className={t.lead}>People who make avatars and clips. Change role, disable, or revoke sessions.</p>
      <Field label="Search">
        <Input value={filter} placeholder="Email, name, or role" onChange={(_, data) => onFilter(data.value)} />
      </Field>
      <div className={t.wrap}>
        <table className={t.table}>
          <thead>
            <tr>
              <th className={t.th}>User</th>
              <th className={t.th}>Role</th>
              <th className={t.th}>Status</th>
              <th className={t.th}>Spaces</th>
              <th className={t.th}>Last login</th>
              <th className={t.th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-[var(--studio-fill-quiet)]">
                <td className={t.td}>
                  <strong>{user.full_name || "—"}</strong>
                  <div className={t.subtle}>{user.email}</div>
                </td>
                <td className={t.td}>
                  <Select
                    value={user.role}
                    fullWidth={false}
                    disabled={busy || user.id === selfId}
                    onChange={(event) => void onRole(user.id, event.target.value as Role)}
                    aria-label={`Role for ${user.email}`}
                  >
                    <option value="user">user</option>
                    <option value="admin">admin</option>
                  </Select>
                </td>
                <td className={t.td}>{user.is_disabled ? "Disabled" : "Active"}</td>
                <td className={t.td}>{user.workspace_count ?? "—"}</td>
                <td className={t.td}>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "—"}</td>
                <td className={`${t.td} whitespace-nowrap text-right`}>
                  <div className="flex flex-wrap justify-end gap-1.5">
                    <Button
                      variant="secondary"
                      size="small"
                      type="button"
                      disabled={busy || user.id === selfId}
                      onClick={() =>
                        void withBusy(
                          () => onToggleDisabled(user.id, !user.is_disabled),
                          user.is_disabled ? "User re-enabled" : "User disabled",
                        )
                      }
                    >
                      {user.is_disabled ? "Enable" : "Disable"}
                    </Button>
                    <Button
                      variant="secondary"
                      size="small"
                      type="button"
                      disabled={busy}
                      onClick={() => void withBusy(() => onRevoke(user.id), "Sessions revoked")}
                    >
                      Revoke sessions
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!users.length ? <div className={t.empty}>No users match that search.</div> : null}
    </div>
  );
}
