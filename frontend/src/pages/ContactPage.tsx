
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Card } from "../ui";
import { Body1 } from "../ui/Text";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { MarketingPageLayout } from "../components/marketing/MarketingPageLayout";
import { TurnstileField, useTurnstileToken } from "../components/TurnstileField";
import { usePageMeta } from "../components/marketing/usePageMeta";
import type { ContactTopic } from "../types";
import { useAuth } from "../auth";
import {
  CONTACT_MESSAGE_HINT,
  contactMessageFeedback,
  emailFeedback,
  nameFeedback,
} from "../lib/formValidation";
import { Button, Field, Input, LinkButton, MessageBar, Select, Textarea } from "../ui";
import { useMarketingStyles } from "../ui/marketingStyles";

const TOPIC_LABELS: Record<ContactTopic, string> = {
  general: "General",
  account: "Account",
};

function topicFromIntent(intent: string | null): ContactTopic {
  if (intent === "access") return "account";
  if (intent === "pricing") return "general";
  return "general";
}

function helperFromIntent(intent: string | null): string | null {
  if (intent === "access") {
    return "Account questions, sign-in trouble, or help getting started with Create.";
  }
  if (intent === "pricing") {
    return "Ask about Free, Starter, Creator, or Studio, monthly credits, and packs.";
  }
  return null;
}

function messagePlaceholder(intent: string | null): string {
  if (intent === "access") {
    return "Who you are, what you make (Reels, TikTok, stills), and whether you want Talking, Scene, or stills first.";
  }
  if (intent === "pricing") {
    return "Which plan looks closest, rough monthly volume…";
  }
  return "How can we help?";
}

export function ContactPage() {
  const auth = useAuth();
  const styles = useMarketingStyles();
  const [searchParams] = useSearchParams();
  const intent = searchParams.get("intent");
  const initialTopic = topicFromIntent(intent);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [topic, setTopic] = useState<ContactTopic>(initialTopic);
  const [body, setBody] = useState("");
  const [serverMessage, setServerMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [submittedName, setSubmittedName] = useState("");
  const [submittedTopic, setSubmittedTopic] = useState<ContactTopic>("general");
  const turnstile = useTurnstileToken();

  usePageMeta(
    "Contact Studio · Account help or ask about plans",
    "Ask about your Studio account, Free, Starter, Creator, or Studio plans, or email contact@example.com.",
  );

  useEffect(() => {
    setTopic(topicFromIntent(intent));
  }, [intent]);

  useEffect(() => {
    if (!auth.user) return;
    if (!name.trim() && auth.user.full_name) {
      setName(auth.user.full_name);
    }
    if (!email.trim() && auth.user.email) {
      setEmail(auth.user.email);
    }
    // Prefill once when a signed-in user opens contact.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only when identity becomes available
  }, [auth.user?.id]);

  const helper = useMemo(() => helperFromIntent(intent), [intent]);
  const nameFb = useMemo(() => nameFeedback(name), [name]);
  const emailFb = useMemo(() => emailFeedback(email), [email]);
  const messageFb = useMemo(() => contactMessageFeedback(body), [body]);
  const formReady =
    nameFb.state === "success" && emailFb.state === "success" && messageFb.state === "success";
  const pageTitle =
    intent === "access" ? "Account help" : intent === "pricing" ? "Plans" : "Contact";
  const pageLede =
    intent === "access"
      ? "Sign-in, billing, or getting started. We read every message."
      : intent === "pricing"
        ? "Tell us what you need and we will follow up."
        : "Account help or product questions. We read every message.";

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
      const result = await api.submitContact(name, email, topic, body, {
        turnstileToken: turnstile.token,
      });
      setServerMessage(result.message || "Message received. We will get back to you soon.");
      setSubmittedName(name.trim());
      setSubmittedTopic(topic);
      setBody("");
      turnstile.reset();
    } catch (err) {
      turnstile.reset();
      if (err instanceof ApiError) {
        if (err.status === 429) {
          setError(err.message || "Too many contact submissions. Please try again later.");
        } else if (err.status === 400) {
          setError(err.message || "Captcha failed. Please try again.");
        } else if (err.status === 422) {
          setError("Check name, email, and message length (10 to 5000 characters).");
        } else {
          setError(err.message || "Contact submission failed");
        }
      } else {
        setError(err instanceof Error ? err.message : "Contact submission failed");
      }
    } finally {
      setBusy(false);
    }
  }

  if (serverMessage) {
    return (
      <MarketingPageLayout
        eyebrow="Contact"
        title="Message sent"
        lede={serverMessage}
        width="narrow"
      >
        <Card>
          <div className={styles.authCardInner}>
            <Body1>
              Thanks{submittedName ? `, ${submittedName}` : ""}. Topic:{" "}
              <strong>{TOPIC_LABELS[submittedTopic]}</strong>.
            </Body1>
            <Body1>We read every message and reply as soon as we can.</Body1>
            <div className={styles.ctaRow}>
              <Button
                variant="secondary"
                type="button"
                onClick={() => {
                  setServerMessage(null);
                  setError(null);
                }}
              >
                Send another
              </Button>
              <LinkButton variant="secondary" to="/">
                Home
              </LinkButton>
              {!auth.isAuthenticated ? (
                <LinkButton variant="secondary" to="/register">
                  Create account
                </LinkButton>
              ) : (
                <LinkButton to="/play">Open play</LinkButton>
              )}
            </div>
          </div>
        </Card>
      </MarketingPageLayout>
    );
  }

  return (
    <MarketingPageLayout eyebrow="Contact" title={pageTitle} lede={pageLede} width="narrow">
      {error ? <MessageBar intent="error">{error}</MessageBar> : null}

      {helper ? <Body1>{helper}</Body1> : null}

      <p className={styles.authMuted}>
        Prefer email? <a href="mailto:contact@example.com">contact@example.com</a>
        {auth.isAuthenticated ? (
          <>
            {" "}
            · Already signed in? <Link to="/play">Open play</Link>
          </>
        ) : (
          <>
            {" "}
            · Need an account? <Link to="/register">Create your account</Link>
          </>
        )}
      </p>

      <form className={styles.authForm} onSubmit={submit} noValidate>
        <Field
          label="Name"
          required
          validationState={nameFb.state}
          validationMessage={nameFb.message}
        >
          <Input
            id="contact-name"
            value={name}
            maxLength={100}
            onChange={(_, data) => setName(data.value)}
            required
            autoComplete="name"
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
            id="contact-email"
            type="email"
            value={email}
            onChange={(_, data) => setEmail(data.value)}
            required
            autoComplete="email"
            aria-invalid={emailFb.state === "error"}
          />
        </Field>
        <Field label="Topic">
          <Select
            id="contact-topic"
            value={topic}
            onChange={(event) => setTopic(event.target.value as ContactTopic)}
            aria-label="Contact topic"
          >
            <option value="account">Account</option>
            <option value="general">General</option>
          </Select>
        </Field>
        <Field
          label="Message"
          required
          hint={!body ? CONTACT_MESSAGE_HINT : undefined}
          validationState={messageFb.state}
          validationMessage={messageFb.message}
        >
          <Textarea
            id="contact-message"
            rows={6}
            value={body}
            minLength={10}
            maxLength={5000}
            placeholder={messagePlaceholder(intent)}
            onChange={(_, data) => setBody(data.value)}
            required
            aria-invalid={messageFb.state === "error"}
          />
        </Field>
        <TurnstileField
          value={turnstile.token}
          onChange={turnstile.setToken}
          disabled={busy}
          resetKey={turnstile.resetKey}
        />
        <p className={styles.authMuted}>
          We read every message and reply as soon as we can. Do not send passwords or payment card numbers.
        </p>
        <div className={styles.authActions}>
          <Button disabled={busy || !formReady} type="submit">
            {busy ? "Sending…" : "Send message"}
          </Button>
        </div>
      </form>
    </MarketingPageLayout>
  );
}
