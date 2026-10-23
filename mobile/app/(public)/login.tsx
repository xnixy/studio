import { useState } from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";
import { Redirect, router } from "expo-router";
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
import { useAppColors } from "@/src/ui/theme";

export default function LoginScreen() {
  const auth = useAuth();
  const colors = useAppColors();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  if (auth.isAuthenticated) {
    if (!auth.user?.email_verified) {
      return <Redirect href={"/(public)/verify-email" as never} />;
    }
    return <Redirect href="/(app)" />;
  }

  const submit = async (emailValue: string, passwordValue: string) => {
    setError(null);
    if (!emailValue.trim() || !passwordValue) {
      setError("Enter your email and password.");
      return;
    }
    setBusy(true);
    try {
      await auth.login(emailValue.trim(), passwordValue);
      void hapticSuccess();
    } catch (e) {
      void hapticError();
      if (e instanceof ApiError && e.code === "email_not_verified") {
        setError(e.message);
        try {
          await api.resendVerification(emailValue.trim());
        } catch {
          // best-effort resend
        }
        router.push({
          pathname: "/(public)/verify-email" as never,
          params: { email: emailValue.trim() },
        });
        return;
      }
      setError(e instanceof ApiError ? e.message : "Sign in failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthFormShell title="Sign in" subtitle="Use your Studio account from the web.">
      <NativeFormGroup>
        <NativeFormField label="Email">
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
          />
        </NativeFormField>
        <NativeFormField label="Password" isLast>
          <TextInput
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            textContentType="password"
            autoComplete="password"
            placeholder="Required"
            placeholderTextColor={colors.muted}
            style={[styles.input, { color: colors.fg }]}
            onSubmitEditing={() => void submit(email, password)}
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
        label={busy ? "Signing in…" : "Sign In"}
        onPress={() => void submit(email, password)}
        busy={busy}
        disabled={busy}
      />

      <View style={styles.links}>
        <NativeTextLink
          label="Forgot password?"
          onPress={() => router.push("/(public)/forgot-password" as never)}
        />
        <NativeTextLink
          label="Create account"
          onPress={() => router.push("/(public)/register")}
        />
      </View>
    </AuthFormShell>
  );
}

const styles = StyleSheet.create({
  input: {
    fontSize: 17,
    paddingVertical: 4,
    minHeight: 28,
  },
  links: {
    gap: 14,
    alignItems: "center",
    marginTop: 4,
  },
});
