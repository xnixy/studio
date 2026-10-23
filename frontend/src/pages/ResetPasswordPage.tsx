import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { usePageMeta } from "../components/marketing/usePageMeta";
import { confirmPasswordFeedback, PASSWORD_HINT, passwordFeedback } from "../lib/formValidation";
import { Button, Field, Input, MessageBar } from "../ui";
import { useMarketingStyles } from "../ui/marketingStyles";

export function ResetPasswordPage() {
  const styles = useMarketingStyles();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = useMemo(() => params.get("token") || "", [params]);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  usePageMeta("Reset password · Studio", "Choose a new Studio password.");

  const passwordFb = useMemo(() => passwordFeedback(password), [password]);
  const confirmFb = useMemo(() => confirmPasswordFeedback(password, confirm), [password, confirm]);
  const formReady = Boolean(token) && passwordFb.state === "success" && confirmFb.state === "success";

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token) {
      setError("Missing reset token. Open the link from your email.");
      return;
    }
    if (!formReady) {
      setError("Fix the highlighted fields, then try again.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.resetPassword(token, password);
      navigate("/login", { replace: true, state: { message: "Password reset. Sign in with your new password." } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.authCard}>
      <div className={styles.authCardInner}>
        <header>
          <h1 className={styles.authTitle}>Reset password</h1>
          <p className={styles.authLede}>Choose a new password for your account</p>
        </header>

        {error ? <MessageBar intent="error">{error}</MessageBar> : null}
        {!token ? <MessageBar intent="warning">This page needs a valid reset link from your email.</MessageBar> : null}

        <form className={styles.authForm} onSubmit={submit} noValidate>
          <Field
            label="New password"
            required
            hint={!password ? PASSWORD_HINT : undefined}
            validationState={passwordFb.state}
            validationMessage={passwordFb.message}
          >
            <Input
              id="reset-password"
              type="password"
              value={password}
              onChange={(_, data) => setPassword(data.value)}
              required
              minLength={8}
              maxLength={128}
              autoComplete="new-password"
              aria-invalid={passwordFb.state === "error"}
            />
          </Field>
          <Field
            label="Confirm password"
            required
            validationState={confirmFb.state}
            validationMessage={confirmFb.message}
          >
            <Input
              id="reset-password-confirm"
              type="password"
              value={confirm}
              onChange={(_, data) => setConfirm(data.value)}
              required
              minLength={8}
              maxLength={128}
              autoComplete="new-password"
              aria-invalid={confirmFb.state === "error"}
            />
          </Field>
          <div className={styles.authActions}>
            <Button disabled={busy || !formReady} type="submit">
              {busy ? "Saving…" : "Update password"}
            </Button>
          </div>
        </form>

        <p className={styles.authMuted}>
          <Link to="/login">Back to sign in</Link>
        </p>
      </div>
    </div>
  );
}
