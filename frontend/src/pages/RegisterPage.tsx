import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth";
import { TurnstileField, useTurnstileToken } from "../components/TurnstileField";
import { usePageMeta } from "../components/marketing/usePageMeta";
import {
  confirmPasswordFeedback,
  emailFeedback,
  nameFeedback,
  PASSWORD_HINT,
  passwordFeedback,
} from "../lib/formValidation";
import { Button, Field, Input, MessageBar } from "../ui";
import { useMarketingStyles } from "../ui/marketingStyles";

function paramOnce(params: URLSearchParams, ...keys: string[]): string {
  for (const key of keys) {
    const raw = params.get(key);
    if (raw && raw.trim()) return raw.trim();
  }
  return "";
}

export function RegisterPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const styles = useMarketingStyles();
  const initialEmail = paramOnce(params, "email").toLowerCase();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const turnstile = useTurnstileToken();
  usePageMeta("Create account · Studio", "Create your Studio account.");

  useEffect(() => {
    const nextEmail = paramOnce(params, "email").toLowerCase();
    if (nextEmail) setEmail(nextEmail);
  }, [params]);

  const nameFb = useMemo(() => nameFeedback(fullName), [fullName]);
  const emailFb = useMemo(() => emailFeedback(email), [email]);
  const passwordFb = useMemo(() => passwordFeedback(password), [password]);
  const confirmFb = useMemo(() => confirmPasswordFeedback(password, confirmPassword), [password, confirmPassword]);

  const formReady =
    nameFb.state === "success" &&
    emailFb.state === "success" &&
    passwordFb.state === "success" &&
    confirmFb.state === "success";

  if (auth.initialized && auth.isAuthenticated) {
    return (
      <Navigate to={auth.user?.email_verified ? "/play" : "/verify-email"} replace />
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!formReady) {
      setError("Fix the highlighted fields, then try again.");
      return;
    }
    const captchaHost = document.querySelector("[data-turnstile-slot]");
    if (captchaHost && !turnstile.token) {
      setError("Complete the security check first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await auth.register(email, password, {
        fullName: fullName.trim(),
        turnstileToken: turnstile.token,
      });
      navigate("/verify-email", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
      turnstile.reset();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.authCard}>
      <div className={styles.authCardInner}>
        <header>
          <h1 className={styles.authTitle}>Create account</h1>
          <p className={styles.authLede}>Pick a face. Write a line. Make a clip.</p>
        </header>

        {error ? <MessageBar intent="error">{error}</MessageBar> : null}

        <form className={styles.authForm} onSubmit={submit} noValidate>
          <Field
            label="Full name"
            required
            validationState={nameFb.state}
            validationMessage={nameFb.message}
          >
            <Input
              id="register-name"
              value={fullName}
              maxLength={100}
              onChange={(_, data) => setFullName(data.value)}
              required
              autoComplete="name"
              placeholder="How should we greet you?"
              aria-invalid={nameFb.state === "error"}
            />
          </Field>
          <Field
            label="Email"
            required
            validationState={emailFb.state}
            validationMessage={emailFb.message}
          >
            <Input
              id="register-email"
              type="email"
              value={email}
              onChange={(_, data) => setEmail(data.value)}
              required
              autoComplete="email"
              aria-invalid={emailFb.state === "error"}
            />
          </Field>
          <Field
            label="Password"
            required
            hint={!password ? PASSWORD_HINT : undefined}
            validationState={passwordFb.state}
            validationMessage={passwordFb.message}
          >
            <Input
              id="register-password"
              type="password"
              value={password}
              minLength={8}
              maxLength={128}
              onChange={(_, data) => setPassword(data.value)}
              required
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
              id="register-password-confirm"
              type="password"
              value={confirmPassword}
              minLength={8}
              maxLength={128}
              onChange={(_, data) => setConfirmPassword(data.value)}
              required
              autoComplete="new-password"
              aria-invalid={confirmFb.state === "error"}
            />
          </Field>
          <TurnstileField
            value={turnstile.token}
            onChange={turnstile.setToken}
            disabled={busy}
            resetKey={turnstile.resetKey}
          />
          <div className={styles.authActions}>
            <Button disabled={busy || !formReady} type="submit">
              {busy ? "Creating…" : "Create account"}
            </Button>
          </div>
        </form>

        <p className={styles.authMuted}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
