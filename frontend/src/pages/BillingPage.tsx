import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "../api";
import { useAuth } from "../auth";
import { BillingSection } from "../features/billing/BillingSection";
import { useWorkspace } from "../workspace";
import type { AddOnType, CreditPackName, PlanName } from "../types";
import {
  MessageBar,
  Page,
  PageBoard,
  PageHeader,
  PageSection,
  bannerIntent,
} from "../ui";

function errorMessage(error: unknown) {
  return error instanceof ApiError || error instanceof Error ? error.message : "Request failed";
}

/** Plan, credit packs, monthly boosts, and period usage. */
export function BillingPage() {
  const auth = useAuth();
  const token = auth.accessToken ?? "";
  const workspace = useWorkspace();
  const queryClient = useQueryClient();
  const active = workspace.activeWorkspace;
  const [notice, setNotice] = useState<{ kind: "success" | "error" | "info"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const billing = useQuery({
    queryKey: ["workspaces", "billing", active?.id],
    queryFn: () => api.billingStatus(token, active!.id),
    enabled: Boolean(token && active),
    staleTime: 30_000,
  });
  const usage = useQuery({
    queryKey: ["workspaces", "billing-usage", active?.id],
    queryFn: () => api.billingUsage(token, active!.id),
    enabled: Boolean(token && active),
  });
  const packs = useQuery({
    queryKey: ["billing", "packs"],
    queryFn: () => api.listCreditPacks(token),
    enabled: Boolean(token && active),
    staleTime: 60_000,
  });
  const addons = useQuery({
    queryKey: ["billing", "addons", active?.id],
    queryFn: () => api.getEffectiveLimits(token, active!.id),
    enabled: Boolean(token && active),
  });

  useEffect(() => {
    if (!notice) return;
    const t = window.setTimeout(() => setNotice(null), 4000);
    return () => window.clearTimeout(t);
  }, [notice]);

  // Solo product: owner of personal space (or platform admin).
  const canManage = useMemo(() => {
    const role = active?.role;
    return role === "owner" || role === "admin" || auth.isAdmin;
  }, [active?.role, auth.isAdmin]);

  async function runBusy(fn: () => Promise<void>) {
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page wide>
      <PageBoard>
        <PageHeader
          title="Billing"
          subtitle="Plan, credit pools, packs, and support boosts. Length and quality change the run cost."
        />
        <PageSection>
          {notice ? (
            <MessageBar intent={bannerIntent(notice.kind)} onDismiss={() => setNotice(null)}>
              {notice.text}
            </MessageBar>
          ) : null}

          {!active ? (
            <p className="m-0 text-sm text-[var(--studio-fg-muted)]">Loading your account…</p>
          ) : (
            <BillingSection
              billing={billing.data || null}
              billingLoading={billing.isLoading}
              billingError={billing.error ? errorMessage(billing.error) : null}
              onRetryBilling={() => void billing.refetch()}
              usage={usage.data || []}
              packs={packs.data || []}
              grants={addons.data?.credit_grants || []}
              addons={(addons.data?.addons || []).map((a) => ({
                id: a.id,
                addon_type: a.addon_type as AddOnType,
                quantity: a.quantity,
                monthly_total_cents: a.monthly_total_cents,
                status: a.status,
              }))}
              canManage={canManage}
              busy={busy}
              onCheckout={(planName: PlanName) =>
                void runBusy(async () => {
                  if (!token) throw new Error("Sign in to check out");
                  const session = await api.createCheckout(token, active.id, planName);
                  if (session.url) window.location.href = session.url;
                })
              }
              onPortal={() =>
                void runBusy(async () => {
                  if (!token) throw new Error("Sign in to open billing");
                  const session = await api.createBillingPortal(token, active.id);
                  if (session.url) window.location.href = session.url;
                })
              }
              onBuyPack={(pack) =>
                void runBusy(async () => {
                  if (!token) throw new Error("Sign in to buy a pack");
                  const session = await api.createPackCheckout(token, active.id, pack as CreditPackName);
                  if (session.url) window.location.href = session.url;
                })
              }
              onCancelAddon={(type) =>
                void runBusy(async () => {
                  if (!token) throw new Error("Sign in to cancel add-on");
                  await api.cancelAddon(token, active.id, type);
                  await queryClient.invalidateQueries({ queryKey: ["billing", "addons", active.id] });
                  await queryClient.invalidateQueries({ queryKey: ["workspaces", "billing", active.id] });
                  setNotice({ kind: "success", text: "Boost cancelled" });
                })
              }
            />
          )}
        </PageSection>
      </PageBoard>
    </Page>
  );
}
