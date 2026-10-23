import { useEffect, useMemo, useState } from "react";
import { Platform, StyleSheet, Text, TextInput, View } from "react-native";
import { Redirect, router, useLocalSearchParams } from "expo-router";
import {
  Button,
  Form,
  Host,
  Section,
  Text as SwiftText,
  TextField,
  useNativeState,
} from "@expo/ui/swift-ui";
import {
  buttonStyle,
  controlSize,
  foregroundStyle,
  tint,
} from "@expo/ui/swift-ui/modifiers";
import { api, ApiError } from "@/src/api/client";
import { useAuth } from "@/src/auth/AuthContext";
import {
  AuthFormShell,
  NativeFormField,
  NativeFormGroup,
  NativePrimaryButton,
  NativeTextLink,
} from "@/src/components/AuthFormShell";
import { alertInfo } from "@/src/lib/alerts";
import { useAppColors } from "@/src/ui/theme";

function firstParam(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return (value[0] || "").trim();
  return (value || "").trim();
}

export default function VerifyEmailScreen() {
  const auth = useAuth();
  const colors = useAppColors();
  const params = useLocalSearchParams<{
    token?: string | string[];
    email?: string | string[];
  }>();
  const token = firstParam(params.token);
  const emailPrefill = firstParam(params.email).toLowerCase();

  const emailState = useNativeState(emailPrefill);
  const [email, setEmail] = useState(emailPrefill || auth.user?.email || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const waiting = useMemo(
    () => auth.isAuthenticated && !auth.user?.email_verified && !token,
    [auth.isAuthenticated, auth.user?.email_verified, token],
  );

  useEffect(() => {
    if (emailPrefill) {
      emailState.set(emailPrefill);
      setEmail(emailPrefill);
    } else if (auth.user?.email) {
      emailState.set(auth.user.email);
      setEmail(auth.user.email);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [emailPrefill, auth.user?.email]);

  // Consume link token.
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
            if (cancelled) return;
            auth.updateUser(me.user);
            router.replace("/(app)" as never);
            return;
          } catch {
            // fall through
          }
        }
        alertInfo("Email verified", "You can sign in now.");
        router.replace("/(public)/login" as never);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Verification failed.");
        }
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Poll while waiting after register.
  useEffect(() => {
    if (!waiting || !auth.accessToken) return;
    let cancelled = false;
    const id = setInterval(() => {
      void (async () => {
        try {
          const me = await api.me(auth.accessToken!);
          if (cancelled) return;
          auth.updateUser(me.user);
          if (me.user.email_verified) {
            router.replace("/(app)" as never);
          }
        } catch {
          // stay
        }
      })();
    }, 4000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [waiting, auth.accessToken, auth]);

  if (auth.initialized && auth.isAuthenticated && auth.user?.email_verified && !token) {
    return <Redirect href={"/(app)" as never} />;
  }

  const onResend = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      let result: { message: string };
      if (auth.accessToken) {
        result = await api.resendVerification();
      } else {
        const address = (Platform.OS === "ios" ? emailState.get() : email).trim();
        if (!address) {
          setError("Enter the email you registered with.");
          setBusy(false);
          return;
        }
        result = await api.resendVerification(address);
      }
      setMessage(result.message);
      alertInfo("Email sent", result.message);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not resend.");
    } finally {
      setBusy(false);
    }
  };

  const accountEmail = auth.user?.email || emailPrefill || email;
  const subtitle = waiting
    ? "Open the link we sent, or resend a new one below."
    : "Confirm the address on your Studio account.";

  if (Platform.OS === "ios") {
    return (
      <AuthFormShell nativeForm subtitle={subtitle}>
        <Host style={styles.host} useViewportSizeMeasurement seedColor={colors.brand}>
          <Form>
            {waiting ? (
              <Section
                header={<SwiftText>Check your inbox</SwiftText>}
                footer={
                  <SwiftText>
                    Sent to {accountEmail || "your email"}. This screen updates when you are
                    verified.
                  </SwiftText>
                }
              >
                <SwiftText>Waiting for verification…</SwiftText>
              </Section>
            ) : null}
            {!auth.accessToken && !token ? (
              <Section title="Email">
                <TextField text={emailState} placeholder="name@example.com" />
              </Section>
            ) : null}
            {error ? (
              <Section>
                <SwiftText modifiers={[foregroundStyle(colors.danger)]}>{error}</SwiftText>
              </Section>
            ) : null}
            {message ? (
              <Section>
                <SwiftText modifiers={[foregroundStyle(colors.brand)]}>{message}</SwiftText>
              </Section>
            ) : null}
            <Section
              footer={
                <SwiftText>
                  Did not get it? Check spam, then resend. Links expire after a couple of days.
                </SwiftText>
              }
            >
              <Button
                label={busy ? "Sending…" : "Resend verification email"}
                onPress={() => {
                  if (busy) return;
                  void onResend();
                }}
                modifiers={[
                  buttonStyle("glassProminent"),
                  controlSize("large"),
                  tint(colors.brand),
                ]}
              />
              {auth.isAuthenticated ? (
                <Button
                  label="Sign out"
                  onPress={() => void auth.logout()}
                  modifiers={[buttonStyle("borderless"), tint(colors.brand)]}
                />
              ) : (
                <Button
                  label="Sign in"
                  onPress={() => router.push("/(public)/login")}
                  modifiers={[buttonStyle("borderless"), tint(colors.brand)]}
                />
              )}
            </Section>
          </Form>
        </Host>
      </AuthFormShell>
    );
  }

  return (
    <AuthFormShell subtitle={subtitle}>
      {waiting ? (
        <Text style={{ color: colors.muted, marginBottom: 12 }}>
          We sent a link to {auth.user?.email || "your email"}. Open it to continue.
        </Text>
      ) : null}
      {!auth.accessToken && !token ? (
        <NativeFormGroup>
          <NativeFormField label="Email" isLast>
            <TextInput
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              style={[styles.input, { color: colors.fg }]}
              placeholderTextColor={colors.muted}
              placeholder="name@example.com"
            />
          </NativeFormField>
        </NativeFormGroup>
      ) : null}
      {error ? (
        <Text accessibilityRole="alert" style={{ color: colors.danger }}>
          {error}
        </Text>
      ) : null}
      {message ? <Text style={{ color: colors.brand }}>{message}</Text> : null}
      <NativePrimaryButton
        label={busy ? "Sending…" : "Resend verification email"}
        onPress={() => void onResend()}
        busy={busy}
        disabled={busy}
      />
      <View style={{ alignItems: "center" }}>
        {auth.isAuthenticated ? (
          <NativeTextLink label="Sign out" onPress={() => void auth.logout()} />
        ) : (
          <NativeTextLink label="Sign in" onPress={() => router.push("/(public)/login")} />
        )}
      </View>
    </AuthFormShell>
  );
}

const styles = StyleSheet.create({
  host: { flex: 1 },
  input: { fontSize: 17, paddingVertical: 4, minHeight: 28 },
});
