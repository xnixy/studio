import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useAuth } from "../../auth";
import { api } from "../../api";
import { useWorkspace } from "../../workspace";
import { Button, Card, Checkbox, MessageBar } from "../../ui";

/** Workspace notification prefs (bell + toast). */
export function NotificationPreferencesCard() {
  const auth = useAuth();
  const workspace = useWorkspace();
  const queryClient = useQueryClient();
  const workspaceId = workspace.activeWorkspaceId;
  const token = auth.accessToken;
  const [inApp, setInApp] = useState(true);
  const [toast, setToast] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  const prefs = useQuery({
    queryKey: ["notification-preferences", workspaceId],
    queryFn: () => api.listNotificationPreferences(token!, workspaceId || undefined),
    enabled: Boolean(token),
  });

  useEffect(() => {
    const star = (prefs.data || []).find(
      (p) => p.event_type === "*" && (p.workspace_id === workspaceId || p.workspace_id == null),
    );
    if (star) {
      setInApp(star.in_app);
      setToast(star.toast);
    }
  }, [prefs.data, workspaceId]);

  const save = useMutation({
    mutationFn: () =>
      api.upsertNotificationPreference(token!, {
        workspace_id: workspaceId || null,
        event_type: "*",
        in_app: inApp,
        email: false,
        toast,
      }),
    onSuccess: async () => {
      setMessage("Preferences saved.");
      await queryClient.invalidateQueries({ queryKey: ["notification-preferences"] });
    },
    onError: (err: Error) => setMessage(err.message || "Save failed"),
  });

  return (
    <Card className="grid gap-3 p-4">
      <div className="grid gap-1">
        <h3 className="m-0 text-base font-semibold tracking-tight text-[var(--studio-fg)]">
          Notifications
        </h3>
        <p className="m-0 text-sm leading-snug text-[var(--studio-fg-muted)]">
          Choose how this workspace pings you. Live jobs still update the page when you are connected.
        </p>
      </div>
      {message ? (
        <MessageBar intent={message.includes("saved") ? "success" : "error"}>{message}</MessageBar>
      ) : null}
      <div className="grid gap-2.5">
        <Checkbox
          checked={inApp}
          onChange={(_, data) => setInApp(Boolean(data.checked))}
          label="Show in the notification bell"
        />
        <Checkbox
          checked={toast}
          onChange={(_, data) => setToast(Boolean(data.checked))}
          label="Show toast popups"
        />
        <Button
          type="button"
          variant="primary"
          disabled={save.isPending || !token}
          onClick={() => save.mutate()}
        >
          Save preferences
        </Button>
      </div>
    </Card>
  );
}
