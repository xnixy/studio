import { useEffect, useMemo, useState } from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";
import { Redirect, router, useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { hapticError, hapticSuccess } from "@/src/lib/haptics";
import { api, ApiError } from "@/src/api/client";
import { useAuth } from "@/src/auth/AuthContext";
import {
  AuthFormShell,
  NativeFormField,
  NativeFormGroup,
  NativePrimaryButton,
  NativeTextLink,
} from "@/src/components/AuthFormShell";
import { TurnstileChallenge } from "@/src/components/TurnstileChallenge";
import { PASSWORD_HINT, validatePasswordStrength } from "@/src/lib/password";
import { useAppColors } from "@/src/ui/theme";

function firstParam(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return (value[0] || "").trim();
  return (value || "").trim();
}

export default function RegisterScreen() {
  const auth = useAuth();
  const colors = useAppColors();
  const params = useLocalSearchParams<{
    email?: string | string[];
  }>();

  const prefillEmail = useMemo(() => firstParam(params.email).toLowerCase(), [params.email]);

  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [captchaReset, setCaptchaReset] = useState(0);

  const publicConfig = useQuery({
    queryKey: ["public-config"],
    queryFn: () => api.publicConfig(),
    staleTime: 60_000,
    retry: 1,
  });
  const captchaRequired = publicConfig.data?.turnstile_required ?? true;

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState(prefillEmail);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  useEffect(() => {
    if (prefillEmail) setEmail(prefillEmail);
  }, [prefillEmail]);

  if (auth.isAuthenticated) {
    if (!auth.user?.email_verified) {
      return <Redirect href={"/(public)/verify-email" as never} />;
    }
    return <Redirect href="/(app)" />;
  }

  const submit = async () => {
    setError(null);
    if (!fullName.trim() || !email.trim() || !password || !confirmPassword) {
      setError("Fill in name, email, password, and confirm password.");
      return;
    }
    const passwordIssue = validatePasswordStrength(password);
    if (passwordIssue) {
      setError(passwordIssue);
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (captchaRequired && !turnstileToken) {
      setError(
        publicConfig.isError
          ? "Security check failed to load. Retry, or try again in a moment."
          : "Complete the security check first.",
      );
      return;
    }
    setBusy(true);
    try {
      await auth.register({
        fullName: fullName.trim(),
        email: email.trim(),
        password,
        turnstileToken,
      });
      void hapticSuccess();
    } catch (e) {
      void hapticError();
      setError(e instanceof ApiError ? e.message : "Could not create account.");
      // Token is single-use; force a new challenge after any API failure.
      setTurnstileToken(null);
      setCaptchaReset((n) => n + 1);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthFormShell title="Create account" subtitle="Pick a face. Write a line. Make a clip.">
      <NativeFormGroup footer={PASSWORD_HINT}>
        <NativeFormField label="Name">
          <TextInput
            value={fullName}
            onChangeText={setFullName}
            autoCapitalize="words"
            textContentType="name"
            autoComplete="name"
            style={[styles.input, { color: colors.fg }]}
            placeholderTextColor={colors.muted}
            placeholder="Your name"
          />
        </NativeFormField>
        <NativeFormField label="Email">
          <TextInput
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            textContentType="username"
            autoComplete="email"
            style={[styles.input, { color: colors.fg }]}
            placeholderTextColor={colors.muted}
            placeholder="name@example.com"
          />
        </NativeFormField>
        <NativeFormField label="Password">
          <TextInput
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            textContentType="newPassword"
            autoComplete="new-password"
            style={[styles.input, { color: colors.fg }]}
            placeholderTextColor={colors.muted}
            placeholder="Create a password"
          />
        </NativeFormField>
        <NativeFormField label="Confirm password" isLast>
          <TextInput
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            secureTextEntry
            textContentType="newPassword"
            autoComplete="new-password"
            style={[styles.input, { color: colors.fg }]}
            placeholderTextColor={colors.muted}
            placeholder="Confirm password"
          />
        </NativeFormField>
      </NativeFormGroup>

      {captchaRequired ? (
        <View style={styles.captchaBlock}>
          <Text style={[styles.captchaLabel, { color: colors.muted }]}>Quick security check</Text>
          {publicConfig.isError ? (
            <Text style={{ color: colors.danger, fontSize: 13, marginBottom: 8 }}>
              Could not load the security check.{" "}
              <Text
                style={{ color: colors.brand, fontWeight: "700" }}
                onPress={() => void publicConfig.refetch()}
                accessibilityRole="button"
              >
                Retry
              </Text>
            </Text>
          ) : null}
          <TurnstileChallenge onToken={setTurnstileToken} resetKey={captchaReset} height={110} />
        </View>
      ) : null}

      {error ? (
        <Text
          accessibilityRole="alert"
          style={{ color: colors.danger, paddingHorizontal: 4 }}
        >
          {error}
        </Text>
      ) : null}

      <NativePrimaryButton
        label={busy ? "Creating…" : "Create Account"}
        onPress={() => void submit()}
        busy={busy}
        disabled={busy}
      />

      <View style={styles.links}>
        <NativeTextLink
          label="Already have an account? Sign In"
          onPress={() => router.push("/(public)/login")}
        />
      </View>
    </AuthFormShell>
  );
}

const styles = StyleSheet.create({
  input: { fontSize: 17, paddingVertical: 4, minHeight: 28 },
  captchaBlock: { gap: 6 },
  captchaLabel: {
    fontSize: 13,
    fontWeight: "600",
    paddingHorizontal: 4,
  },
  links: {
    gap: 14,
    alignItems: "center",
    marginTop: 4,
  },
});
