/** Mirror backend validate_password_strength (common.py). */

export function validatePasswordStrength(value: string): string | null {
  if (value.length < 8 || value.length > 128) {
    return "Password must be between 8 and 128 characters.";
  }
  if (value.toLowerCase() === value) {
    return "Password must include an uppercase letter.";
  }
  if (value.toUpperCase() === value) {
    return "Password must include a lowercase letter.";
  }
  const hasDigit = /[0-9]/.test(value);
  const hasSymbol = /[^A-Za-z0-9]/.test(value);
  if (!hasDigit && !hasSymbol) {
    return "Password must include a number or symbol.";
  }
  const common = new Set([
    "password1",
    "password123",
    "admin123!",
    "qwerty123",
    "welcome1",
    "letmein1",
    "changeme1",
  ]);
  if (common.has(value.toLowerCase())) {
    return "Choose a less common password.";
  }
  return null;
}

export const PASSWORD_HINT =
  "At least 8 characters, with upper and lower case, plus a number or symbol.";
