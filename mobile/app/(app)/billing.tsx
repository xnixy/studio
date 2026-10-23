import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Platform,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigation } from "expo-router";
import { api } from "@/src/api/client";
import { EmptyState, ErrorState } from "@/src/components/States";
import { GlassCard, GlassSurface } from "@/src/components/GlassSurface";
import { Screen } from "@/src/components/Screen";
import {
  buyWithFeedback,
  formatCatalogPrice,
  loadPaywallProducts,
  processUnfinishedPurchases,
  restoreWithFeedback,
  type StoreProductRow,
} from "@/src/iap/store";
import { openManageSubscriptions, openPrivacyPolicy, openTermsOfUse } from "@/src/lib/legal";
import { liquidGlassStackHeaderOptions } from "@/src/ui/nav";
import { useAppColors } from "@/src/ui/theme";
import { useWorkspace } from "@/src/workspace/WorkspaceContext";

export default function BillingScreen() {
  const colors = useAppColors();
  const navigation = useNavigation();
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const qc = useQueryClient();
  const [buyingId, setBuyingId] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);
  // Local pull state only. Query isFetching on focus freezes iOS RefreshControl.
  const [pullRefreshing, setPullRefreshing] = useState(false);

  useEffect(() => {
    navigation.setOptions({
      title: "Billing",
      ...liquidGlassStackHeaderOptions(colors),
    });
  }, [navigation, colors]);

  const billingQuery = useQuery({
    queryKey: ["billing", workspaceId],
    queryFn: () => api.billingStatus(workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
  });

  const productsQuery = useQuery({
    queryKey: ["iap-products"],
    queryFn: loadPaywallProducts,
    staleTime: 60_000,
  });

  // Recover purchases that Apple charged but the app never finished confirming.
  useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;
    (async () => {
      const n = await processUnfinishedPurchases(workspaceId);
      if (!cancelled && n > 0) {
        await qc.invalidateQueries({ queryKey: ["billing", workspaceId] });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workspaceId, qc]);

  const plans = useMemo(
    () => (productsQuery.data || []).filter((p) => p.kind === "plan"),
    [productsQuery.data],
  );
  const packs = useMemo(
    () => (productsQuery.data || []).filter((p) => p.kind === "pack"),
    [productsQuery.data],
  );

  const onBuy = useCallback(
    async (product: StoreProductRow) => {
      if (!workspaceId) return;
      setBuyingId(product.apple_product_id);
      const ok = await buyWithFeedback(workspaceId, product);
      setBuyingId(null);
      if (ok) {
        await Promise.all([
          qc.invalidateQueries({ queryKey: ["billing", workspaceId] }),
          qc.invalidateQueries({ queryKey: ["iap-products"] }),
        ]);
      }
    },
    [workspaceId, qc],
  );

  const onRestore = useCallback(async () => {
    if (!workspaceId || restoring) return;
    setRestoring(true);
    const count = await restoreWithFeedback(workspaceId);
    setRestoring(false);
    if (count > 0) {
      await qc.invalidateQueries({ queryKey: ["billing", workspaceId] });
    }
  }, [workspaceId, restoring, qc]);

  const billing = billingQuery.data;
  const billingPending = workspace.isLoading || !workspaceId || billingQuery.isPending;
  const productsPending = productsQuery.isPending;

  const onPullRefresh = useCallback(async () => {
    setPullRefreshing(true);
    try {
      await Promise.all([billingQuery.refetch(), productsQuery.refetch()]);
    } finally {
      setPullRefreshing(false);
    }
  }, [billingQuery, productsQuery]);

  return (
    <Screen
      contentContainerStyle={{ padding: 16, gap: 14 }}
      bottomPad={40}
      refreshControl={
        <RefreshControl
          refreshing={pullRefreshing}
          onRefresh={() => void onPullRefresh()}
          tintColor={colors.brand}
        />
      }
    >
      <Text style={{ color: colors.muted, fontSize: 15, lineHeight: 21 }}>
        Your plan and credits. Purchases use Apple In-App Purchase.
      </Text>

      <GlassCard>
        <Text style={[styles.label, { color: colors.muted }]}>Current plan</Text>
        {billingPending ? (
          <View style={{ gap: 10, marginTop: 10, minHeight: 120 }}>
            <View style={{ height: 22, width: "46%", borderRadius: 6, backgroundColor: colors.chipOff }} />
            <View style={{ height: 14, width: "28%", borderRadius: 4, backgroundColor: colors.chipOff }} />
            <View style={styles.meters}>
              {[0, 1, 2, 3, 4].map((i) => (
                <View key={i} style={[styles.meter, { backgroundColor: colors.chipOff, minHeight: 52 }]} />
              ))}
            </View>
          </View>
        ) : null}
        {billingQuery.isError ? (
          <ErrorState
            colors={colors}
            message="Could not load billing."
            onRetry={() => void billingQuery.refetch()}
          />
        ) : null}
        {!billingPending && billing ? (
          <View style={{ gap: 8, marginTop: 4 }}>
            <Text style={{ color: colors.fg, fontSize: 22, fontWeight: "700", letterSpacing: -0.3 }}>
              {(billing.plans || []).find((p) => p.name === billing.plan)?.label || billing.plan}
            </Text>
            <Text style={{ color: colors.muted }}>Status: {billing.status}</Text>
            <View style={styles.meters}>
              <Meter
                label="Clip"
                value={
                  billing.play_clip_remaining ??
                  billing.play_avatar_remaining ??
                  billing.video_generations_remaining
                }
                colors={colors}
              />
              <Meter
                label="Stills"
                value={billing.play_still_remaining ?? billing.image_generations_remaining}
                colors={colors}
              />
              <Meter
                label="Faces"
                value={billing.play_face_remaining ?? 0}
                colors={colors}
              />
            </View>
          </View>
        ) : null}
      </GlassCard>

      {Platform.OS !== "ios" ? (
        <EmptyState
          colors={colors}
          title="iOS only"
          body="In-app purchases run on iPhone/iPad builds."
        />
      ) : null}

      <Text style={[styles.section, { color: colors.muted }]}>Plans</Text>
      {productsPending
        ? [0, 1].map((i) => (
            <GlassCard key={`plan-sk-${i}`} contentStyle={styles.productRow} padded={false}>
              <View style={{ flex: 1, gap: 8 }}>
                <View style={{ height: 14, width: "48%", borderRadius: 4, backgroundColor: colors.chipOff }} />
                <View style={{ height: 12, width: "72%", borderRadius: 4, backgroundColor: colors.chipOff }} />
              </View>
              <View style={[styles.buy, { backgroundColor: colors.chipOff }]} />
            </GlassCard>
          ))
        : null}
      {productsQuery.isError ? (
        <ErrorState
          colors={colors}
          message="Could not load App Store products."
          onRetry={() => void productsQuery.refetch()}
        />
      ) : null}
      {plans.map((p) => (
        <ProductRow
          key={p.apple_product_id}
          product={p}
          colors={colors}
          busy={buyingId === p.apple_product_id}
          disabled={!workspaceId || buyingId !== null || Platform.OS !== "ios"}
          onBuy={() => void onBuy(p)}
        />
      ))}

      <Text style={[styles.section, { color: colors.muted, marginTop: 6 }]}>Credit packs</Text>
      {packs.map((p) => (
        <ProductRow
          key={p.apple_product_id}
          product={p}
          colors={colors}
          busy={buyingId === p.apple_product_id}
          disabled={!workspaceId || buyingId !== null || Platform.OS !== "ios"}
          onBuy={() => void onBuy(p)}
        />
      ))}

      {!productsPending && !productsQuery.isError && plans.length === 0 && packs.length === 0 ? (
        <EmptyState
          colors={colors}
          title="No store products yet"
          body="Products are not available in the App Store for this build yet. Try again later."
        />
      ) : null}

      {Platform.OS === "ios" ? (
        <View style={{ gap: 10, marginTop: 8 }}>
          <Pressable
            onPress={() => void onRestore()}
            disabled={!workspaceId || restoring || buyingId !== null}
            accessibilityRole="button"
            accessibilityLabel="Restore purchases"
          >
            <GlassSurface
              radius={16}
              intensity={48}
              contentStyle={[styles.secondaryBtn, { opacity: restoring ? 0.6 : 1 }]}
            >
              {restoring ? (
                <ActivityIndicator color={colors.brand} />
              ) : (
                <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 16 }}>
                  Restore purchases
                </Text>
              )}
            </GlassSurface>
          </Pressable>
          <Pressable
            onPress={() => void openManageSubscriptions()}
            accessibilityRole="link"
            accessibilityLabel="Manage Apple subscriptions"
            style={styles.linkRow}
          >
            <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 15 }}>
              Manage Apple subscriptions
            </Text>
          </Pressable>
          <View style={styles.legalRow}>
            <Pressable
              onPress={() => void openPrivacyPolicy()}
              accessibilityRole="link"
              accessibilityLabel="Privacy Policy"
            >
              <Text style={{ color: colors.muted, fontSize: 13 }}>Privacy Policy</Text>
            </Pressable>
            <Text style={{ color: colors.muted, fontSize: 13 }}>·</Text>
            <Pressable
              onPress={() => void openTermsOfUse()}
              accessibilityRole="link"
              accessibilityLabel="Terms of Use"
            >
              <Text style={{ color: colors.muted, fontSize: 13 }}>Terms of Use</Text>
            </Pressable>
          </View>
        </View>
      ) : null}
    </Screen>
  );
}

function Meter({
  label,
  value,
  colors,
}: {
  label: string;
  value?: number;
  colors: ReturnType<typeof useAppColors>;
}) {
  return (
    <View style={[styles.meter, { backgroundColor: colors.brandSoft }]}>
      <Text style={{ color: colors.muted, fontSize: 11, fontWeight: "600" }}>{label}</Text>
      <Text style={{ color: colors.brand, fontSize: 18, fontWeight: "700" }}>
        {typeof value === "number" ? value : "—"}
      </Text>
    </View>
  );
}

function ProductRow({
  product,
  colors,
  busy,
  disabled,
  onBuy,
}: {
  product: StoreProductRow;
  colors: ReturnType<typeof useAppColors>;
  busy: boolean;
  disabled: boolean;
  onBuy: () => void;
}) {
  const price = product.storePrice || formatCatalogPrice(product.price_cents);
  return (
    <GlassCard contentStyle={styles.productRow} padded={false}>
      <View style={{ flex: 1, gap: 4, paddingRight: 8 }}>
        <Text style={{ color: colors.fg, fontSize: 16, fontWeight: "600" }}>
          {product.storeTitle || product.title}
        </Text>
        <Text style={{ color: colors.muted, fontSize: 13, lineHeight: 18 }}>
          {product.description}
        </Text>
      </View>
      <Pressable
        onPress={onBuy}
        disabled={disabled || busy}
        accessibilityRole="button"
        accessibilityLabel={`Buy ${product.storeTitle || product.title}, ${price}`}
        style={[styles.buy, { backgroundColor: busy || disabled ? colors.border : colors.brand }]}
      >
        {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.buyText}>{price}</Text>}
      </Pressable>
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  label: { fontSize: 12, fontWeight: "700", letterSpacing: 0.3 },
  section: { fontSize: 13, fontWeight: "600", letterSpacing: -0.1 },
  meters: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 8 },
  meter: { minWidth: "28%", flexGrow: 1, borderRadius: 14, padding: 10, gap: 2 },
  productRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    padding: 14,
  },
  buy: {
    minWidth: 84,
    minHeight: 44,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 10,
  },
  buyText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  secondaryBtn: {
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  linkRow: { alignItems: "center", paddingVertical: 4 },
  legalRow: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
    paddingTop: 4,
  },
});
