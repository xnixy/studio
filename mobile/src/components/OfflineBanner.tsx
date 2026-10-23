import { StatusBanner } from "./StatusBanner";
import { useOnlineStatus } from "../hooks/useOnlineStatus";

/** Sits under the status bar when the API cannot be reached. */
export function OfflineBanner() {
  const online = useOnlineStatus();
  if (online) return null;
  return (
    <StatusBanner
      tone="error"
      message="You're offline. Connect to send, save, or refresh."
    />
  );
}
