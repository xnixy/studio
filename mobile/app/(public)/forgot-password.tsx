import { useState } from "react";
import { StyleSheet, Text, TextInput } from "react-native";
import { router } from "expo-router";
import { api, ApiError } from "@/src/api/client";
import {
  AuthFormShell,
  NativeFormField,
  NativeFormGroup,
  NativePrimaryButton,
  NativeTextLink,
} from "@/src/components/AuthFormShell";
import { alertInfo } from "@/src/lib/alerts";
import { useAppColors } from "@/src/ui/theme";

export default function ForgotPasswordScreen() {
  const colors = useAppColors();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");

  const onSubmit = async (value: string) => {
    setError(null);
    if (!value.trim()) {
      setError("Enter your email.");
      return;
    }
    setBusy(true);
    try {
      const res = await api.forgotPassword(value.trim());
      alertInfo("Check your email", res.message);
      router.back();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Request failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthFormShell
      title="Reset password"
      subtitle="We'll email a reset link if an account exists for that address."
    >
      <NativeFormGroup>
        <NativeFormField label="Email" isLast>
          <TextInput
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            textContentType="username"
            autoComplete="email"
            placeholder="name@example.com"
            placeholderTextColor={colors.muted}
            style={[styles.input, { color: colors.fg }]}
            onSubmitEditing={() => void onSubmit(email)}
          />
        </NativeFormField>
      </NativeFormGroup>

      {error ? (
        <Text
          accessibilityRole="alert"
          style={{ color: colors.danger, paddingHorizontal: 4 }}
        >
          {error}
        </Text>
      ) : null}

      <NativePrimaryButton
        label={busy ? "Sending…" : "Send Reset Link"}
        onPress={() => void onSubmit(email)}
        busy={busy}
        disabled={busy}
      />

      <NativeTextLink label="Back to Sign In" onPress={() => router.back()} />
    </AuthFormShell>
  );
}

const styles = StyleSheet.create({
  input: { fontSize: 17, paddingVertical: 4, minHeight: 28 },
});
