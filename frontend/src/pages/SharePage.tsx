
import { Lock } from "lucide-react";
import { Card, Spinner } from "../ui";
import { Body1, Caption1 } from "../ui/Text";
import { useMemo, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { ApiError, api } from "../api";
import type { ShareLinkPublic } from "../types";
import { requiredTextFeedback } from "../lib/formValidation";
import { Button, Field, Input, MessageBar } from "../ui";
import { useMarketingStyles } from "../ui/marketingStyles";

function errorMessage(error: unknown) {
  return error instanceof ApiError || error instanceof Error ? error.message : "Request failed";
}

function ShareShell({ children }: { children: React.ReactNode }) {
  const styles = useMarketingStyles();
  return (
    <div className="grid min-h-[calc(100vh-5rem)] place-items-center p-4">
      <Card className={styles.authCard}>
        <div className={styles.authCardInner}>{children}</div>
      </Card>
    </div>
  );
}

export function SharePage() {
  const { token = "" } = useParams();
  const styles = useMarketingStyles();
  const [password, setPassword] = useState("");
  const [unlocked, setUnlocked] = useState<ShareLinkPublic | null>(null);
  const [unlockError, setUnlockError] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState(false);
  const passwordFb = useMemo(() => requiredTextFeedback(password, "Password is required"), [password]);

  const share = useQuery({
    queryKey: ["public-share", token],
    queryFn: () => api.getPublicShare(token),
    enabled: Boolean(token),
    retry: false,
  });

  const view = unlocked || share.data;

  async function unlock(event: FormEvent) {
    event.preventDefault();
    if (passwordFb.state !== "success") {
      setUnlockError("Enter the share password.");
      return;
    }
    setUnlocking(true);
    setUnlockError(null);
    try {
      const result = await api.unlockPublicShare(token, password);
      setUnlocked(result);
    } catch (error) {
      setUnlockError(errorMessage(error));
    } finally {
      setUnlocking(false);
    }
  }

  if (share.isLoading) {
    return (
      <ShareShell>
        <div style={{ placeItems: "center", textAlign: "center", display: "grid", gap: 12 }}>
          <Spinner label="Loading share…" />
        </div>
      </ShareShell>
    );
  }

  if (share.isError && !unlocked) {
    return (
      <ShareShell>
        <header>
          <h1 className={styles.authTitle}>Share unavailable</h1>
          <p className={styles.authLede}>{errorMessage(share.error)}</p>
        </header>
      </ShareShell>
    );
  }

  if (view?.requires_password && !unlocked) {
    return (
      <ShareShell>
        <header>
          <Lock size={22} aria-hidden="true" />
          <h1 className={styles.authTitle}>{view.title}</h1>
          <p className={styles.authLede}>This client share is password protected.</p>
        </header>
        {unlockError ? <MessageBar intent="error">{unlockError}</MessageBar> : null}
        <form className={styles.authForm} onSubmit={(event) => void unlock(event)} noValidate>
          <Field
            label="Password"
            required
            validationState={passwordFb.state}
            validationMessage={passwordFb.message}
          >
            <Input
              type="password"
              value={password}
              onChange={(_, data) => setPassword(data.value)}
              required
              autoComplete="current-password"
              aria-invalid={passwordFb.state === "error"}
            />
          </Field>
          <div className={styles.authActions}>
            <Button type="submit" disabled={unlocking || passwordFb.state !== "success"}>
              {unlocking ? "Unlocking…" : "Unlock"}
            </Button>
          </div>
        </form>
      </ShareShell>
    );
  }

  const body = view?.snapshot?.body;
  const client = view?.snapshot?.client;

  return (
    <ShareShell>
      <Caption1>Client share</Caption1>
      <h1 className={styles.authTitle}>{view?.title}</h1>
      {client ? <p className={styles.authMuted}>Prepared for {String(client)}</p> : null}
      <div className={styles.legalBody}>
        {typeof body === "string" && body.trim() ? (
          body.split("\n").map((line, index) => <Body1 key={index}>{line || "\u00A0"}</Body1>)
        ) : (
          <pre style={{ whiteSpace: "pre-wrap", margin: 0, fontSize: "0.85rem" }}>
            {JSON.stringify(view?.snapshot || {}, null, 2)}
          </pre>
        )}
      </div>
      <Caption1>Shared securely via Studio</Caption1>
    </ShareShell>
  );
}
