import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import Constants from "expo-constants";
import { useQuery } from "@tanstack/react-query";
import { hapticSuccess } from "@/src/lib/haptics";
import { router } from "expo-router";
import { api, ApiError } from "@/src/api/client";
import { useAuth } from "@/src/auth/AuthContext";
import { Screen } from "@/src/components/Screen";
import { SettingsGroup, SettingsRow } from "@/src/components/SettingsList";
import { alertConfirm, alertError, alertInfo } from "@/src/lib/alerts";
import {
  openContact,
  openManageSubscriptions,
  openPrivacyPolicy,
  openTermsOfUse,
} from "@/src/lib/legal";
import { useAppColors } from "@/src/ui/theme";
import { useWorkspace } from "@/src/workspace/WorkspaceContext";

export default function ProfileScreen() {
  const auth = useAuth();
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const colors = useAppColors();
  const [fullName, setFullName] = useState(auth.user?.full_name || "");
  const [busy, setBusy] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");

  const appVersion =
    Constants.expoConfig?.version || Constants.nativeAppVersion || "1.0.0";
  const buildNumber =
    Constants.expoConfig?.ios?.buildNumber || Constants.nativeBuildVersion || null;

  useEffect(() => {
    setFullName(auth.user?.full_name || "");
  }, [auth.user?.full_name]);

  const billingQuery = useQuery({
    queryKey: ["billing", workspaceId],
    queryFn: () => api.billingStatus(workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
  });
  const billing = billingQuery.data;
  const planLabel =
    billing &&
    ((billing.plans || []).find((p) => p.name === billing.plan)?.label || billing.plan);

  const saveProfile = async () => {
    const name = fullName.trim() || null;
    setBusy(true);
    try {
      const res = await api.updateProfile(name);
      auth.updateUser(res.user);
      void hapticSuccess();
      alertInfo("Saved", "Your name was updated.");
    } catch (e) {
      alertError("Could not save", e instanceof ApiError ? e.message : "Try again.");
    } finally {
      setBusy(false);
    }
  };

  const onLogout = () => {
    alertConfirm("Sign out", "You can sign back in anytime.", () => {
      void auth.logout();
    }, "Sign out");
  };

  const onDeleteAccount = () => {
    const pw = deletePassword.trim();
    if (!pw) {
      alertError("Password required", "Enter your password, then try again.");
      return;
    }
    alertConfirm(
      "Delete account",
      "This permanently closes your account. App Store subscriptions stay in Apple Settings until you cancel them.",
      () => {
        void (async () => {
          setBusy(true);
          try {
            await api.deleteAccount(pw);
            await auth.logout();
            router.replace("/(public)/login" as never);
          } catch (e) {
            alertError(
              "Could not delete",
              e instanceof ApiError ? e.message : "Check your password and try again.",
            );
          } finally {
            setBusy(false);
          }
        })();
      },
      "Delete",
    );
  };

  const displayName = auth.user?.full_name?.trim() || "You";

  return (
    <Screen contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 8, gap: 22 }} bottomPad={32}>
      <View style={styles.hero}>
        <Text style={{ color: colors.muted, fontSize: 15 }} numberOfLines={1}>
          {displayName}
        </Text>
      </View>

      <SettingsGroup header="Account">
        <View
          style={[styles.field, { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.separator }]}
        >
          <Text style={[styles.fieldLabel, { color: colors.muted }]}>Email</Text>
          <Text style={{ color: colors.fg, fontSize: 17 }}>{auth.user?.email}</Text>
        </View>
        <View style={styles.field}>
          <Text style={[styles.fieldLabel, { color: colors.muted }]}>Name</Text>
          <TextInput
            value={fullName}
            onChangeText={setFullName}
            onEndEditing={() => void saveProfile()}
            placeholder="Your name"
            placeholderTextColor={colors.muted}
            textContentType="name"
            autoComplete="name"
            returnKeyType="done"
            style={{ color: colors.fg, fontSize: 17, paddingVertical: 2 }}
          />
        </View>
      </SettingsGroup>

      <SettingsGroup header="Plan">
        <SettingsRow
          label="Billing"
          detail={planLabel || undefined}
          symbol={{ ios: "creditcard", android: "credit_card", web: "credit_card" }}
          onPress={() => router.push("/(app)/billing" as never)}
          last
        />
      </SettingsGroup>

      <SettingsGroup header="Legal">
        <SettingsRow
          label="Privacy Policy"
          symbol={{ ios: "hand.raised", android: "privacy_tip", web: "privacy_tip" }}
          onPress={() => void openPrivacyPolicy()}
        />
        <SettingsRow
          label="Terms of Use"
          symbol={{ ios: "doc.text", android: "description", web: "description" }}
          onPress={() => void openTermsOfUse()}
        />
        <SettingsRow
          label="Contact"
          symbol={{ ios: "envelope", android: "mail", web: "mail" }}
          onPress={() => void openContact()}
        />
        <SettingsRow
          label="Apple subscriptions"
          symbol={{ ios: "gear", android: "settings", web: "settings" }}
          onPress={() => void openManageSubscriptions()}
          last
        />
      </SettingsGroup>

      <SettingsGroup>
        <SettingsRow
          label="Sign out"
          symbol={{ ios: "rectangle.portrait.and.arrow.right", android: "logout", web: "logout" }}
          onPress={onLogout}
          destructive
          last
        />
      </SettingsGroup>

      <SettingsGroup
        header="Delete account"
        footer={`Version ${appVersion}${buildNumber ? ` (${buildNumber})` : ""}. Cancel App Store plans in Apple Settings if you still pay there.`}
      >
        <View style={styles.field}>
          <TextInput
            value={deletePassword}
            onChangeText={setDeletePassword}
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="Password"
            placeholderTextColor={colors.muted}
            style={{ color: colors.fg, fontSize: 17, paddingVertical: 6 }}
          />
        </View>
        <Pressable
          onPress={onDeleteAccount}
          disabled={busy}
          accessibilityRole="button"
          accessibilityLabel="Delete account"
          style={({ pressed }) => [styles.deleteBtn, { opacity: pressed ? 0.55 : 1 }]}
        >
          {busy ? (
            <ActivityIndicator color={colors.danger} />
          ) : (
            <Text style={{ color: colors.danger, fontSize: 17 }}>Delete account</Text>
          )}
        </Pressable>
      </SettingsGroup>
    </Screen>
  );
}

const styles = StyleSheet.create({
  hero: { gap: 2, paddingHorizontal: 4, paddingBottom: 2 },
  field: { paddingHorizontal: 16, paddingVertical: 10, gap: 3 },
  fieldLabel: { fontSize: 13 },
  deleteBtn: {
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
  },
});
