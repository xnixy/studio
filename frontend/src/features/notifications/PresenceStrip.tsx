import { useWorkspaceRealtime } from "../../realtime/WorkspaceRealtimeProvider";
import { useDashboardStyles } from "../../ui/dashboardStyles";
import { useAuth } from "../../auth";

export function PresenceStrip() {
  const { presence, status } = useWorkspaceRealtime();
  const auth = useAuth();
  const styles = useDashboardStyles();

  if (status !== "live" || presence.length <= 1) return null;

  const others = presence.filter((m) => m.user_id !== auth.user?.id).slice(0, 6);
  if (!others.length) return null;

  return (
    <div className={styles.presenceStrip} title="Online in this workspace">
      {others.map((m) => {
        const label = (m.display_name || m.user_id).slice(0, 1).toUpperCase();
        return (
          <span key={m.user_id} className={styles.presenceDot} title={m.display_name || m.user_id}>
            {label}
          </span>
        );
      })}
    </div>
  );
}
