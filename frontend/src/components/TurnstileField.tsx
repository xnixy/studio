import { useEffect, useId, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { Field } from "../ui";

declare global {
  interface Window {
    turnstile?: {
      render: (
        element: HTMLElement,
        options: {
          sitekey: string;
          callback?: (token: string) => void;
          "expired-callback"?: () => void;
          "error-callback"?: () => void;
          theme?: "light" | "dark" | "auto";
          appearance?: "always" | "execute" | "interaction-only";
        },
      ) => string;
      reset: (widgetId?: string) => void;
      remove: (widgetId?: string) => void;
    };
    onloadTurnstileCallback?: () => void;
  }
}

const SCRIPT_ID = "cf-turnstile-script";
const SCRIPT_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=onloadTurnstileCallback";

let scriptPromise: Promise<void> | null = null;

function loadTurnstileScript(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.resolve();
  }
  if (window.turnstile) {
    return Promise.resolve();
  }
  if (scriptPromise) {
    return scriptPromise;
  }
  scriptPromise = new Promise((resolve, reject) => {
    const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    if (existing) {
      window.onloadTurnstileCallback = () => resolve();
      if (window.turnstile) {
        resolve();
      }
      existing.addEventListener("error", () => reject(new Error("Captcha script failed to load")));
      return;
    }
    window.onloadTurnstileCallback = () => resolve();
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.src = SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onerror = () => reject(new Error("Captcha script failed to load"));
    document.head.appendChild(script);
  });
  return scriptPromise;
}

function resolveTheme(): "light" | "dark" {
  try {
    return document.documentElement.dataset.theme === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

export function TurnstileField({
  value,
  onChange,
  disabled = false,
  resetKey = 0,
}: {
  value: string | null;
  onChange: (token: string | null) => void;
  disabled?: boolean;
  /** Change to force widget reset (e.g. after failed submit). */
  resetKey?: number;
}) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const widgetIdRef = useRef<string | null>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const reactId = useId();
  const [scriptError, setScriptError] = useState<string | null>(null);

  const envKey = (import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined)?.trim() || "";
  const publicConfig = useQuery({
    queryKey: ["public-config"],
    queryFn: () => api.publicConfig(),
    staleTime: 5 * 60_000,
    enabled: !envKey,
  });

  const siteKey = envKey || publicConfig.data?.turnstile_site_key || "";
  const enabled = Boolean(siteKey);

  useEffect(() => {
    if (!enabled || disabled || !hostRef.current) {
      return;
    }
    let cancelled = false;

    void (async () => {
      try {
        await loadTurnstileScript();
        if (cancelled || !hostRef.current || !window.turnstile) {
          return;
        }
        if (widgetIdRef.current) {
          try {
            window.turnstile.remove(widgetIdRef.current);
          } catch {
            /* ignore */
          }
          widgetIdRef.current = null;
        }
        hostRef.current.innerHTML = "";
        const id = window.turnstile.render(hostRef.current, {
          sitekey: siteKey,
          theme: resolveTheme(),
          callback: (token) => onChangeRef.current(token),
          "expired-callback": () => onChangeRef.current(null),
          "error-callback": () => onChangeRef.current(null),
        });
        widgetIdRef.current = id;
        setScriptError(null);
      } catch (err) {
        setScriptError(err instanceof Error ? err.message : "Captcha failed to load");
      }
    })();

    return () => {
      cancelled = true;
      if (widgetIdRef.current && window.turnstile) {
        try {
          window.turnstile.remove(widgetIdRef.current);
        } catch {
          /* ignore */
        }
        widgetIdRef.current = null;
      }
    };
  }, [enabled, siteKey, disabled, resetKey]);

  if (!enabled) {
    if (publicConfig.isLoading && !envKey) {
      return (
        <Field label="Security check">
          <p style={{ margin: 0, opacity: 0.7, fontSize: "0.875rem" }}>Loading captcha…</p>
        </Field>
      );
    }
    // Local/dev without keys: no widget (backend skips when secret unset in development).
    return null;
  }

  return (
    <Field
      label="Security check"
      required
      hint={scriptError || (!value ? "Complete the check before submitting." : undefined)}
    >
      <div
        ref={hostRef}
        data-turnstile-slot={reactId}
        style={{ minHeight: 65 }}
        aria-busy={!value}
      />
    </Field>
  );
}

export function useTurnstileToken() {
  const [token, setToken] = useState<string | null>(null);
  const [resetKey, setResetKey] = useState(0);
  function reset() {
    setToken(null);
    setResetKey((n) => n + 1);
  }
  return { token, setToken, resetKey, reset };
}
