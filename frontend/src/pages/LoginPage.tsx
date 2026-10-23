import { FormEvent, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { usePageMeta } from "../components/marketing/usePageMeta";
import { emailFeedback, requiredTextFeedback } from "../lib/formValidation";
import { Button, Field, Input, MessageBar } from "../ui";
import { useMarketingStyles } from "../ui/marketingStyles";

/** Safe in-app path after login (relative only, no protocol-relative //). */
function safeNextPath(raw: string | null): string {
  if (!raw) return "/play";
  let value = raw.trim();
  try {
    value = decodeURIComponent(value);
  } catch {
    return "/play";
  }
  if (!value.startsWith("/") || value.startsWith("//")) return "/play";
  if (value.startsWith("/login") || value.startsWith("/register")) return "/play";
  return value;
}

export function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const nextPath = safeNextPath(searchParams.get("next"));
  const styles = useMarketingStyles();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  usePageMeta("Sign in · Studio", "Sign in to your Studio workspace.");

  const emailFb = useMemo(() => emailFeedback(email), [email]);
  const passwordFb = useMemo(() => requiredTextFeedback(password, "Password is required"), [password]);
  const formReady = emailFb.state === "success" && passwordFb.state === "success";

  if (auth.initialized && auth.isAuthenticated) {
    return (
      <Navigate
        to={auth.user?.email_verified ? nextPath : "/verify-email"}
        replace
      />
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!formReady) {
      setError("Enter a valid email and password.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await auth.login(email, password);
      navigate(nextPath, { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.code === "email_not_verified") {
        setError(err.message);
        try {
          await api.resendVerification(null, email.trim());
        } catch {
          // Message already explains verify; resend is best-effort.
        }
        navigate(`/verify-email?email=${encodeURIComponent(email.trim())}`, { replace: false });
        return;
      }
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.authCard}>
      <div className={styles.authCardInner}>
        <header>
          <h1 className={styles.authTitle}>Sign in</h1>
          <p className={styles.authLede}>Open your workspace</p>
        </header>

        {error ? <MessageBar intent="error">{error}</MessageBar> : null}

        <form className={styles.authForm} onSubmit={submit} noValidate>
          <Field
            label="Email"
            required
            validationState={emailFb.state}
            validationMessage={emailFb.message}
          >
            <Input
              id="login-email"
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
            validationState={passwordFb.state}
            validationMessage={passwordFb.message}
          >
            <Input
              id="login-password"
              type="password"
              value={password}
              onChange={(_, data) => setPassword(data.value)}
              required
              autoComplete="current-password"
              aria-invalid={passwordFb.state === "error"}
            />
          </Field>
          <p className={styles.authMuted} style={{ marginTop: 0 }}>
            <Link to="/forgot-password">Forgot password?</Link>
          </p>
          <div className={styles.authActions}>
            <Button disabled={busy || !formReady} type="submit">
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </div>
        </form>

        <p className={styles.authMuted}>
          Need an account? <Link to="/register">Create account</Link>
        </p>
      </div>
    </div>
  );
}
