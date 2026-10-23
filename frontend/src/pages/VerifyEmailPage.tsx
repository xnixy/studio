import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { usePageMeta } from "../components/marketing/usePageMeta";
import { Button, Field, Input, MessageBar } from "../ui";
import { useMarketingStyles } from "../ui/marketingStyles";

export function VerifyEmailPage() {
  const styles = useMarketingStyles();
  const auth = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = useMemo(() => params.get("token") || "", [params]);
  const emailFromQuery = useMemo(() => (params.get("email") || "").trim().toLowerCase(), [params]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [resendEmail, setResendEmail] = useState(emailFromQuery);
  usePageMeta("Verify email · Studio", "Confirm your Studio email address.");

  useEffect(() => {
    if (emailFromQuery) setResendEmail(emailFromQuery);
  }, [emailFromQuery]);

  // Consume verification token from the email link.
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      setBusy(true);
      setError(null);
      try {
        const result = await api.verifyEmail(token);
        if (cancelled) return;
        setMessage(result.message);
        if (auth.accessToken) {
          try {
            const me = await api.me(auth.accessToken);
            auth.updateUser(me.user);
            navigate("/play", { replace: true });
            return;
          } catch {
            // Fall through to sign-in CTA
          }
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Verification failed");
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // Only re-run when the token changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Poll while signed in and waiting for email confirmation (user may verify on another device).
  useEffect(() => {
    if (token || !auth.isAuthenticated || auth.user?.email_verified || !auth.accessToken) {
      return;
    }
    let cancelled = false;
    const tick = async () => {
      try {
        const me = await api.me(auth.accessToken!);
        if (cancelled) return;
        auth.updateUser(me.user);
        if (me.user.email_verified) {
          navigate("/play", { replace: true });
        }
      } catch {
        // stay on page
      }
    };
    const id = window.setInterval(() => void tick(), 4000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [token, auth.isAuthenticated, auth.user?.email_verified, auth.accessToken, auth, navigate]);

  if (auth.initialized && auth.isAuthenticated && auth.user?.email_verified && !token) {
    return <Navigate to="/play" replace />;
  }

  async function resend() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      if (auth.accessToken) {
        const result = await api.resendVerification(auth.accessToken);
        setMessage(result.message);
      } else {
        const email = resendEmail.trim();
        if (!email) {
          setError("Enter the email you registered with.");
          return;
        }
        const result = await api.resendVerification(null, email);
        setMessage(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resend");
    } finally {
      setBusy(false);
    }
  }

  const waiting = auth.isAuthenticated && !auth.user?.email_verified && !token;

  return (
    <div className={styles.authCard}>
      <div className={styles.authCardInner}>
        <header>
          <h1 className={styles.authTitle}>Verify email</h1>
          <p className={styles.authLede}>
            {waiting
              ? "Confirm your email to open the studio"
              : "Confirm the address on your Studio account"}
          </p>
        </header>

        {error ? <MessageBar intent="error">{error}</MessageBar> : null}
        {message ? <MessageBar intent="success">{message}</MessageBar> : null}
        {busy && !message && !error ? <MessageBar intent="info">Working…</MessageBar> : null}

        {waiting ? (
          <MessageBar intent="info">
            We sent a confirmation link to{" "}
            <strong>{auth.user?.email || "your inbox"}</strong>. Open it to continue. This page
            updates when your email is verified.
          </MessageBar>
        ) : null}

        {!token && !waiting ? (
          <MessageBar intent="warning">
            Open the verification link from your email, or resend a new one below.
          </MessageBar>
        ) : null}

        {token && message && !auth.isAuthenticated ? (
          <p className={styles.authMuted}>
            Email confirmed. <Link to="/login">Sign in</Link> to open your workspace.
          </p>
        ) : null}

        {token ? (
          <p className={styles.authMuted}>
            <a href={`studio://verify-email?token=${encodeURIComponent(token)}`}>
              Open in the Studio app
            </a>{" "}
            if you already have it installed.
          </p>
        ) : null}

        {!auth.accessToken && !token ? (
          <div className={styles.authForm}>
            <Field label="Email">
              <Input
                id="verify-resend-email"
                type="email"
                value={resendEmail}
                onChange={(_, data) => setResendEmail(data.value)}
                autoComplete="email"
                placeholder="name@example.com"
              />
            </Field>
          </div>
        ) : null}

        <div className={styles.authActions}>
          <Button disabled={busy} type="button" onClick={() => void resend()}>
            Resend verification email
          </Button>
          {auth.isAuthenticated ? (
            <Button
              disabled={busy}
              type="button"
              variant="secondary"
              onClick={() => void auth.logout()}
            >
              Sign out
            </Button>
          ) : null}
        </div>

        <p className={styles.authMuted}>
          <Link to={auth.isAuthenticated && auth.user?.email_verified ? "/play" : "/login"}>
            {auth.isAuthenticated && auth.user?.email_verified ? "Back to studio" : "Sign in"}
          </Link>
        </p>
      </div>
    </div>
  );
}
