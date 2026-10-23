import { useNavigate } from "react-router-dom";
import { useWorkspaceRealtime } from "../../realtime/WorkspaceRealtimeProvider";
import { useDashboardStyles } from "../../ui/dashboardStyles";
import { Button } from "../../ui";

/** Cap concurrent toasts so the stack stays small. */
const MAX_VISIBLE = 3;

export function RealtimeToasts() {
  const { toasts, dismissToast } = useWorkspaceRealtime();
  const styles = useDashboardStyles();
  const navigate = useNavigate();

  const visible = toasts.slice(0, MAX_VISIBLE);
  if (!visible.length) return null;

  return (
    <div className={styles.toastStack} aria-live="polite">
      {visible.map((toast) => (
        <div key={toast.id} className={styles.toastCard} role="status">
          <p className={styles.toastTitle}>{toast.title}</p>
          {toast.body ? <p className={styles.toastBody}>{toast.body}</p> : null}
          <div className={styles.toastActions}>
            {toast.href ? (
              <Button
                size="small"
                variant="primary"
                type="button"
                onClick={() => {
                  dismissToast(toast.id);
                  let href = toast.href || "";
                  if (href.startsWith("/studio/")) {
                    const assetId = toast.assetId || toast.entityId;
                    href = assetId ? `/clips/${assetId}` : "/clips";
                  }
                  if (href) navigate(href);
                }}
              >
                Open
              </Button>
            ) : null}
            <Button size="small" variant="subtle" type="button" onClick={() => dismissToast(toast.id)}>
              Dismiss
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
