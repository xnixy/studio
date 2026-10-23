import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { useWorkspace } from "../workspace";
import { hasFeature, type PlanFeature, type PlanTrack } from "../planFeatures";
import type { BillingStatus } from "../types";

/**
 * Stable plan/features for the app shell.
 * Caches last-known features so sidebar nav items do not mount/unmount on billing refetch.
 */
export function usePlanFeatures() {
  const auth = useAuth();
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const userId = auth.user?.id ?? null;
  const lastFeaturesRef = useRef<string[]>([]);
  const lastBillingRef = useRef<BillingStatus | null>(null);
  const lastAccountRef = useRef<string | null>(null);

  const billing = useQuery({
    queryKey: ["workspaces", "billing", userId, workspaceId],
    queryFn: () => api.billingStatus(auth.accessToken!, workspaceId!),
    enabled: Boolean(auth.accessToken && workspaceId),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
    refetchOnMount: false,
    refetchOnReconnect: false,
    placeholderData: (previous, query) => {
      const keyUser = query?.queryKey?.[2];
      return keyUser && keyUser === userId ? previous : undefined;
    },
  });

  useEffect(() => {
    const accountKey = userId && workspaceId ? `${userId}:${workspaceId}` : null;
    if (lastAccountRef.current !== accountKey) {
      lastAccountRef.current = accountKey;
      lastFeaturesRef.current = [];
      lastBillingRef.current = null;
    }
    if (billing.data?.features?.length) {
      lastFeaturesRef.current = billing.data.features;
    }
    if (billing.data) {
      lastBillingRef.current = billing.data;
    }
  }, [billing.data, userId, workspaceId]);

  const billingData = billing.data ?? lastBillingRef.current;
  const features =
    billingData?.features && billingData.features.length > 0
      ? billingData.features
      : lastFeaturesRef.current;
  const featuresKey = features.join("|");
  const track = (billingData?.plan_track || "content") as PlanTrack;
  const planLabel = billingData?.plans.find((p) => p.name === billingData?.plan)?.label;
  const suggestedUpgrade = billingData?.suggested_upgrade ?? null;
  const loading = billing.isPending && !billingData;
  const ready = Boolean(billingData);
  const planName = billingData?.plan;
  const error = billing.error;

  return useMemo(() => {
    const stableFeatures = featuresKey ? featuresKey.split("|") : [];
    return {
      loading,
      plan: planName,
      planLabel,
      track,
      features: stableFeatures,
      suggestedUpgrade,
      can: (feature: PlanFeature) => hasFeature(stableFeatures, feature),
      ready,
      isContentTrack: true,
      isStaticTrack: false,
      isAdsTrack: false,
      billing: billingData,
      billingError: error,
      refresh: () => billing.refetch(),
    };
  }, [
    loading,
    planName,
    planLabel,
    track,
    featuresKey,
    suggestedUpgrade,
    ready,
    billingData,
    error,
    billing.refetch,
  ]);
}
