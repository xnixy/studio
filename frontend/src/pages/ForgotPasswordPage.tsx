import { FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { usePageMeta } from "../components/marketing/usePageMeta";
import { emailFeedback } from "../lib/formValidation";
import { Button, Field, Input, MessageBar } from "../ui";
import { useMarketingStyles } from "../ui/marketingStyles";

export function ForgotPasswordPage() {
  const styles = useMarketingStyles();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  usePageMeta("Forgot password · Studio", "Reset your Studio password.");

  const emailFb = useMemo(() => emailFeedback(email), [email]);
  const formReady = emailFb.state === "success";

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!formReady) {
      setError("Enter a valid email first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.forgotPassword(email);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.authCard}>
      <div className={styles.authCardInner}>
        <header>
          <h1 className={styles.authTitle}>Forgot password</h1>
          <p className={styles.authLede}>We’ll email a reset link if the account exists</p>
        </header>

        {error ? <MessageBar intent="error">{error}</MessageBar> : null}
        {done ? (
          <MessageBar intent="success">
            If an account exists for that email, we sent password reset instructions. Check your inbox.
          </MessageBar>
        ) : (
          <form className={styles.authForm} onSubmit={submit} noValidate>
            <Field
              label="Email"
              required
              validationState={emailFb.state}
              validationMessage={emailFb.message}
            >
              <Input
                id="forgot-email"
                type="email"
                value={email}
                onChange={(_, data) => setEmail(data.value)}
                required
                autoComplete="email"
                aria-invalid={emailFb.state === "error"}
              />
            </Field>
            <div className={styles.authActions}>
              <Button disabled={busy || !formReady} type="submit">
                {busy ? "Sending…" : "Send reset link"}
              </Button>
            </div>
          </form>
        )}

        <p className={styles.authMuted}>
          <Link to="/login">Back to sign in</Link>
        </p>
      </div>
    </div>
  );
}
