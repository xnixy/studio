/** Instant client-side field checks for auth / contact forms. */

export type FieldState = "error" | "warning" | "success" | "none";

export type FieldFeedback = {
  state: FieldState;
  /** Shown under the field when non-empty. */
  message?: string;
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const COMMON_PASSWORDS = new Set([
  "password1",
  "password123",
  "admin123!",
  "qwerty123",
  "welcome1",
  "letmein1",
  "changeme1",
]);

/** Neutral until the user types; then error or success. */
export function liveFeedback(value: string, error: string | null, okMessage?: string): FieldFeedback {
  if (!value) {
    return { state: "none" };
  }
  if (error) {
    return { state: "error", message: error };
  }
  return { state: "success", message: okMessage };
}

export function nameError(value: string): string | null {
  const cleaned = value.trim().replace(/\s+/g, " ");
  if (!cleaned) return "Name is required";
  if (cleaned.length > 100) return "Keep name under 100 characters";
  return null;
}

export function emailError(value: string): string | null {
  const cleaned = value.trim();
  if (!cleaned) return "Email is required";
  if (!EMAIL_RE.test(cleaned) || cleaned.includes("..")) return "Enter a valid email";
  return null;
}

export type PasswordRule = { id: string; label: string; ok: boolean };

export function passwordRules(password: string): PasswordRule[] {
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasDigitOrSymbol = /[0-9]/.test(password) || /[^A-Za-z0-9]/.test(password);
  const notCommon = !COMMON_PASSWORDS.has(password.toLowerCase());
  return [
    { id: "len", label: "At least 8 characters", ok: password.length >= 8 },
    { id: "upper", label: "One uppercase letter", ok: hasUpper },
    { id: "lower", label: "One lowercase letter", ok: hasLower },
    { id: "symbol", label: "One number or symbol", ok: hasDigitOrSymbol },
    { id: "common", label: "Not a common password", ok: password.length === 0 || notCommon },
  ];
}

export function passwordError(password: string): string | null {
  if (!password) return "Password is required";
  if (password.length > 128) return "Password must be 128 characters or fewer";
  const failed = passwordRules(password).filter((r) => !r.ok);
  if (failed.length) {
    return failed.map((r) => r.label).join(" · ");
  }
  return null;
}

export function passwordFeedback(password: string): FieldFeedback {
  if (!password) {
    return { state: "none" };
  }
  const err = passwordError(password);
  if (err) {
    return { state: "error", message: err };
  }
  return { state: "success", message: "Password looks good" };
}

export const PASSWORD_HINT = "At least 8 characters with upper, lower, and a number or symbol.";

export function confirmPasswordError(password: string, confirm: string): string | null {
  if (!confirm) return "Confirm your password";
  if (password !== confirm) return "Passwords do not match";
  return null;
}

export function confirmPasswordFeedback(password: string, confirm: string): FieldFeedback {
  if (!confirm) {
    return { state: "none" };
  }
  const err = confirmPasswordError(password, confirm);
  if (err) {
    return { state: "error", message: err };
  }
  return { state: "success", message: "Passwords match" };
}

export function contactMessageError(value: string): string | null {
  const cleaned = value.trim();
  if (!cleaned) return "Message is required";
  if (cleaned.length < 10) return `A bit more detail helps (${cleaned.length}/10 min)`;
  if (cleaned.length > 5000) return "Keep messages under 5000 characters";
  return null;
}

export function contactMessageFeedback(value: string): FieldFeedback {
  if (!value) {
    return { state: "none" };
  }
  const err = contactMessageError(value);
  if (err) {
    return { state: "error", message: err };
  }
  return { state: "success", message: `${value.trim().length} characters` };
}

export const CONTACT_MESSAGE_HINT = "10–5000 characters";

export function nameFeedback(value: string): FieldFeedback {
  return liveFeedback(value, nameError(value), "Looks good");
}

export function emailFeedback(value: string): FieldFeedback {
  return liveFeedback(value, emailError(value), "Looks good");
}

/** Required non-empty field that only needs “something typed”. */
export function requiredTextFeedback(value: string, emptyLabel = "Required"): FieldFeedback {
  if (!value) return { state: "none" };
  if (!value.trim()) return { state: "error", message: emptyLabel };
  return { state: "success", message: "Looks good" };
}

/** Required label/title with min length (workspace, client, brand profile, etc.). */
export function minLabelError(
  value: string,
  opts?: { min?: number; max?: number; label?: string },
): string | null {
  const min = opts?.min ?? 2;
  const max = opts?.max ?? 120;
  const label = opts?.label ?? "Name";
  const cleaned = value.trim().replace(/\s+/g, " ");
  if (!cleaned) return `${label} is required`;
  if (cleaned.length < min) return `At least ${min} characters (${cleaned.length}/${min})`;
  if (cleaned.length > max) return `Keep under ${max} characters`;
  return null;
}

export function minLabelFeedback(
  value: string,
  opts?: { min?: number; max?: number; label?: string },
): FieldFeedback {
  return liveFeedback(value, minLabelError(value, opts), "Looks good");
}

/** Optional http(s) URL. */
export function optionalUrlFeedback(value: string): FieldFeedback {
  const cleaned = value.trim();
  if (!cleaned) return { state: "none" };
  try {
    const url = new URL(cleaned);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return { state: "error", message: "Use an http or https link" };
    }
    return { state: "success", message: "Looks good" };
  } catch {
    return { state: "error", message: "Enter a valid URL" };
  }
}

/** Product brief / longer required text. */
export function briefFeedback(value: string, min = 8): FieldFeedback {
  if (!value) return { state: "none" };
  const cleaned = value.trim();
  if (!cleaned) return { state: "error", message: "Describe the product or offer" };
  if (cleaned.length < min) {
    return { state: "error", message: `Add a bit more (${cleaned.length}/${min} min)` };
  }
  if (cleaned.length > 8000) return { state: "error", message: "Keep under 8000 characters" };
  return { state: "success", message: `${cleaned.length} characters` };
}

/** Optional free text with max length only. */
export function optionalTextFeedback(value: string, max = 5000): FieldFeedback {
  if (!value) return { state: "none" };
  if (value.trim().length > max) return { state: "error", message: `Keep under ${max} characters` };
  return { state: "success", message: "Looks good" };
}
