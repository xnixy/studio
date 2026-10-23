import { useState } from "react";
import { StyleSheet, Text, TextInput } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { api, ApiError } from "@/src/api/client";
import {
  AuthFormShell,
  NativeFormField,
  NativeFormGroup,
  NativePrimaryButton,
} from "@/src/components/AuthFormShell";
import { alertInfo } from "@/src/lib/alerts";
import { PASSWORD_HINT, validatePasswordStrength } from "@/src/lib/password";
import { useAppColors } from "@/src/ui/theme";

function firstParam(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return (value[0] || "").trim();
  return (value || "").trim();
}

export default function ResetPasswordScreen() {
  const params = useLocalSearchParams<{ token?: string | string[] }>();
  const token = firstParam(params.token);
  const colors = useAppColors();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (value: string) => {
    setError(null);
    if (!token) {
      setError("Missing reset token. Open the link from your email.");
      return;
    }
    const passwordIssue = validatePasswordStrength(value);
    if (passwordIssue) {
      setError(passwordIssue);
      return;
    }
    setBusy(true);
    try {
      const res = await api.resetPassword(token, value);
      alertInfo("Password updated", res.message);
      router.replace("/(public)/login");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Reset failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthFormShell title="New password" subtitle="Choose a new password for your Studio account.">
      {!token ? (
        <Text style={{ color: colors.danger, paddingHorizontal: 4 }}>
          This reset link is missing a token. Open it from the email we sent.
        </Text>
      ) : null}
      <NativeFormGroup footer={PASSWORD_HINT}>
        <NativeFormField label="New password" isLast>
          <TextInput
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            textContentType="newPassword"
            autoComplete="new-password"
            placeholder="New password"
            placeholderTextColor={colors.muted}
            style={[styles.input, { color: colors.fg }]}
            onSubmitEditing={() => void onSubmit(password)}
            editable={Boolean(token)}
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
        label={busy ? "Updating…" : "Update Password"}
        onPress={() => void onSubmit(password)}
        busy={busy}
        disabled={busy || !token}
      />
    </AuthFormShell>
  );
}

const styles = StyleSheet.create({
  input: { fontSize: 17, paddingVertical: 4, minHeight: 28 },
});
