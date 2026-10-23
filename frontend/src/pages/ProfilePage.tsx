import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { useAuth } from "../auth";
import { useWorkspace } from "../workspace";
import { AppearanceSettings } from "../components/AppearanceSettings";
import {
  confirmPasswordFeedback,
  nameFeedback,
  PASSWORD_HINT,
  passwordError,
  passwordFeedback,
  requiredTextFeedback,
} from "../lib/formValidation";
import {
  Button,
  Field,
  Input,
  LinkButton,
  MessageBar,
  Page,
  PageBoard,
  PageForm,
  PageFormActions,
  PageGrid2,
  PageHeader,
  PageLabel,
  PageMuted,
  PageSection,
  PageStack,
} from "../ui";

const styles = {
  identity: "flex min-w-0 items-center gap-3.5",
  avatar:
    "grid h-[52px] w-[52px] shrink-0 place-items-center rounded-full border border-[var(--studio-border)] bg-[var(--studio-brand)] text-lg font-bold text-[var(--studio-brand-fg)] shadow-[0_0_0_3px_rgb(var(--studio-brand-rgb)_/_0.12)]",
  identityCopy: "grid min-w-0 gap-0.5",
  name: "m-0 truncate text-base font-semibold text-[var(--studio-fg)]",
  email: "m-0 truncate text-sm text-[var(--studio-fg-muted)]",
  facts: "m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(8.5rem,1fr))] gap-2.5 p-0",
  fact: "m-0 grid min-w-0 gap-1 rounded-xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] px-3 py-2.5",
  factTerm: "m-0 text-[0.7rem] font-bold uppercase tracking-wide text-[var(--studio-fg-subtle)]",
  factDesc: "m-0 truncate text-sm font-semibold text-[var(--studio-fg)]",
  form: "grid min-w-0 gap-3",
  fieldFull: "w-full min-w-0",
} as const;
function useStyles() {
  return styles;
}

export function ProfilePage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const workspace = useWorkspace();
  const styles = useStyles();
  const token = auth.accessToken ?? "";
  const [fullName, setFullName] = useState(auth.user?.full_name || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [profileBusy, setProfileBusy] = useState(false);
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

  const billing = useQuery({
    queryKey: ["workspaces", "billing", workspace.activeWorkspaceId],
    queryFn: () => api.billingStatus(token, workspace.activeWorkspaceId!),
    enabled: Boolean(token && workspace.activeWorkspaceId),
  });

  useEffect(() => setFullName(auth.user?.full_name || ""), [auth.user?.full_name]);

  const nameFb = useMemo(() => nameFeedback(fullName), [fullName]);
  const currentPwFb = useMemo(() => requiredTextFeedback(currentPassword, "Current password is required"), [currentPassword]);
  const newPwFb = useMemo(() => passwordFeedback(password), [password]);
  const confirmPwFb = useMemo(() => confirmPasswordFeedback(password, confirmPassword), [password, confirmPassword]);
  const passwordFormReady =
    currentPwFb.state === "success" && newPwFb.state === "success" && confirmPwFb.state === "success";

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    if (nameFb.state !== "success") {
      setError("Add a name so the team knows who you are.");
      return;
    }
    if (!token) {
      setError("Sign in to save your profile.");
      return;
    }
    setProfileBusy(true);
    setMessage(null);
    setError(null);
    try {
      const result = await api.updateProfile(fullName.trim(), token);
      auth.updateUser(result.user);
      setMessage("Name saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Profile update failed");
    } finally {
      setProfileBusy(false);
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    if (!passwordFormReady || passwordError(password)) {
      setError("Fix the password fields, then try again.");
      return;
    }
    if (!token) {
      setError("Sign in to change your password.");
      return;
    }
    setPasswordBusy(true);
    setMessage(null);
    setError(null);
    try {
      await api.updatePassword(currentPassword, password, token);
      setCurrentPassword("");
      setPassword("");
      setConfirmPassword("");
      setMessage("Password updated. Signing you out so every session picks up the change…");
      await auth.logout();
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password update failed");
    } finally {
      setPasswordBusy(false);
    }
  }

  const planLabel = billing.data?.plans.find((plan) => plan.name === billing.data?.plan)?.label || "Free";

  const anyBusy = profileBusy || passwordBusy || busy || deleteBusy;

  async function deleteAccount(event: FormEvent) {
    event.preventDefault();
    if (!token) {
      setError("Sign in to delete your account.");
      return;
    }
    if (!deletePassword.trim()) {
      setError("Enter your password to delete the account.");
      return;
    }
    if (!deleteConfirmOpen) {
      setDeleteConfirmOpen(true);
      setMessage(null);
      setError("Type your password and click Delete account again to confirm. This cannot be undone.");
      return;
    }
    setDeleteBusy(true);
    setMessage(null);
    setError(null);
    try {
      await api.deleteAccount(deletePassword, token);
      await auth.logout();
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete account");
      setDeleteConfirmOpen(false);
    } finally {
      setDeleteBusy(false);
    }
  }
  const displayName = auth.user?.full_name?.trim() || "Add your name";
  const nameDirty = fullName.trim() !== (auth.user?.full_name || "").trim();

  return (
    <Page>
      <PageBoard>
      <PageHeader
        title="Your account"
        subtitle="Name, password, look and feel, and your credit plan."
      />
      <PageSection>
      {message ? <MessageBar intent="success">{message}</MessageBar> : null}
      {error ? <MessageBar intent="error">{error}</MessageBar> : null}

      <PageGrid2>
        <PageStack>
          <div className="grid gap-3 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-md shadow-[var(--studio-card-shadow)] p-4">
              <PageLabel>You</PageLabel>
              <div className={styles.identity}>
                <div className={styles.avatar} aria-hidden="true">
                  {(auth.user?.full_name || auth.user?.email || "U").slice(0, 1).toUpperCase()}
                </div>
                <div className={styles.identityCopy}>
                  <p className={styles.name}>{displayName}</p>
                  <p className={styles.email}>{auth.user?.email}</p>
                  <PageMuted>
                    {auth.isAdmin ? "Admin" : "Member"}
                    {" · "}
                    {auth.user?.email_verified ? "Email verified" : "Email not verified yet"}
                  </PageMuted>
                  {!auth.user?.email_verified ? (
                    <div style={{ marginTop: 8 }}>
                      <Button
                        size="small"
                        variant="secondary"
                        type="button"
                        disabled={anyBusy}
                        onClick={() => {
                          void (async () => {
                            if (!token) {
                              setError("Sign in to resend verification.");
                              return;
                            }
                            setBusy(true);
                            setMessage(null);
                            setError(null);
                            try {
                              const result = await api.resendVerification(token);
                              setMessage(result.message);
                            } catch (err) {
                              setError(err instanceof Error ? err.message : "Could not resend verification");
                            } finally {
                              setBusy(false);
                            }
                          })();
                        }}
                      >
                        Resend verification email
                      </Button>
                    </div>
                  ) : null}
                </div>
              </div>

              <dl className={styles.facts}>
                <div className={styles.fact}>
                  <dt className={styles.factTerm}>Plan</dt>
                  <dd className={styles.factDesc}>{planLabel}</dd>
                </div>
                <div className={styles.fact}>
                  <dt className={styles.factTerm}>Clip credits</dt>
                  <dd className={styles.factDesc}>
                    {billing.data
                      ? (billing.data.play_clip_remaining ??
                        billing.data.play_avatar_remaining ??
                        billing.data.video_generations_remaining)
                      : "…"}
                  </dd>
                </div>
                <div className={styles.fact}>
                  <dt className={styles.factTerm}>Still credits</dt>
                  <dd className={styles.factDesc}>
                    {billing.data
                      ? (billing.data.play_still_remaining ?? billing.data.image_generations_remaining)
                      : "…"}
                  </dd>
                </div>
              </dl>

              <PageFormActions>
                <LinkButton variant="secondary" size="small" to="/play">
                  Create
                </LinkButton>
                <LinkButton variant="secondary" size="small" to="/avatars">
                  Faces
                </LinkButton>
                <LinkButton variant="secondary" size="small" to="/billing">
                  Billing
                </LinkButton>
                {auth.isAdmin ? (
                  <LinkButton variant="secondary" size="small" to="/admin">
                    Admin
                  </LinkButton>
                ) : null}
                <Button
                  size="small"
                  variant="secondary"
                  type="button"
                  disabled={anyBusy}
                  onClick={() => {
                    void (async () => {
                      setBusy(true);
                      try {
                        await auth.logout();
                        navigate("/login", { replace: true });
                      } finally {
                        setBusy(false);
                      }
                    })();
                  }}
                >
                  Sign out
                </Button>
              </PageFormActions>
          </div>

          <div className="grid gap-3 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-md shadow-[var(--studio-card-shadow)] p-4">
              <PageLabel>Look and feel</PageLabel>
              <PageMuted>Light or dark mode on this device only.</PageMuted>
              <AppearanceSettings />
          </div>
        </PageStack>

        <PageStack>
          <div className="grid gap-3 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-md shadow-[var(--studio-card-shadow)] p-4">
              <PageLabel>Display name</PageLabel>
              <PageMuted>Shown in the app. Email stays the same for sign-in.</PageMuted>
              <PageForm className={styles.form} onSubmit={saveProfile} noValidate>
                <Field
                  label="Full name"
                  required
                  className={styles.fieldFull}
                  validationState={nameFb.state}
                  validationMessage={nameFb.message}
                >
                  <Input
                    id="profile-name"
                    value={fullName}
                    maxLength={100}
                    onChange={(_, data) => setFullName(data.value)}
                    required
                    autoComplete="name"
                    placeholder="Your name"
                    aria-invalid={nameFb.state === "error"}
                  />
                </Field>
                <Field label="Email" hint="Contact support if you need to change sign-in email." className={styles.fieldFull}>
                  <Input id="profile-email" value={auth.user?.email || ""} readOnly autoComplete="email" />
                </Field>
                <PageFormActions>
                  <Button
                    size="small"
                    disabled={profileBusy || !nameDirty || nameFb.state !== "success"}
                    type="submit"
                  >
                    {profileBusy ? "Saving…" : "Save name"}
                  </Button>
                </PageFormActions>
              </PageForm>
          </div>

          <div className="grid gap-3 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-md shadow-[var(--studio-card-shadow)] p-4">
              <PageLabel>Password</PageLabel>
              <PageMuted>Changing password signs you out on every device. Use a unique password.</PageMuted>
              <PageForm className={styles.form} onSubmit={savePassword} noValidate>
                <Field
                  label="Current password"
                  required
                  className={styles.fieldFull}
                  validationState={currentPwFb.state}
                  validationMessage={currentPwFb.message}
                >
                  <Input
                    id="profile-current-password"
                    type="password"
                    autoComplete="current-password"
                    value={currentPassword}
                    onChange={(_, data) => setCurrentPassword(data.value)}
                    required
                    aria-invalid={currentPwFb.state === "error"}
                  />
                </Field>
                <Field
                  label="New password"
                  required
                  className={styles.fieldFull}
                  hint={!password ? PASSWORD_HINT : undefined}
                  validationState={newPwFb.state}
                  validationMessage={newPwFb.message}
                >
                  <Input
                    id="profile-new-password"
                    type="password"
                    autoComplete="new-password"
                    value={password}
                    minLength={8}
                    maxLength={128}
                    onChange={(_, data) => setPassword(data.value)}
                    required
                    aria-invalid={newPwFb.state === "error"}
                  />
                </Field>
                <Field
                  label="Confirm new password"
                  required
                  className={styles.fieldFull}
                  validationState={confirmPwFb.state}
                  validationMessage={confirmPwFb.message}
                >
                  <Input
                    id="profile-confirm-password"
                    type="password"
                    autoComplete="new-password"
                    value={confirmPassword}
                    minLength={8}
                    maxLength={128}
                    onChange={(_, data) => setConfirmPassword(data.value)}
                    required
                    aria-invalid={confirmPwFb.state === "error"}
                  />
                </Field>
                <PageFormActions>
                  <Button variant="secondary" size="small" disabled={passwordBusy || !passwordFormReady} type="submit">
                    {passwordBusy ? "Updating…" : "Update password"}
                  </Button>
                </PageFormActions>
              </PageForm>
          </div>

          <div className="grid gap-3 rounded-2xl border border-[var(--studio-danger,var(--studio-border))] bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-md shadow-[var(--studio-card-shadow)] p-4">
              <PageLabel>Delete account</PageLabel>
              <PageMuted>
                Permanently closes your account and signs you out. Active App Store subscriptions are managed in
                Settings → Apple ID → Subscriptions.
              </PageMuted>
              <PageForm className={styles.form} onSubmit={deleteAccount} noValidate>
                <Field label="Password" required className={styles.fieldFull}>
                  <Input
                    id="profile-delete-password"
                    type="password"
                    autoComplete="current-password"
                    value={deletePassword}
                    onChange={(_, data) => {
                      setDeletePassword(data.value);
                      setDeleteConfirmOpen(false);
                    }}
                    required
                  />
                </Field>
                <PageFormActions>
                  <Button
                    variant="secondary"
                    size="small"
                    disabled={deleteBusy || !deletePassword.trim()}
                    type="submit"
                  >
                    {deleteBusy ? "Deleting…" : deleteConfirmOpen ? "Confirm delete account" : "Delete account"}
                  </Button>
                </PageFormActions>
              </PageForm>
          </div>
        </PageStack>
      </PageGrid2>
      </PageSection>
      </PageBoard>
    </Page>
  );
}
