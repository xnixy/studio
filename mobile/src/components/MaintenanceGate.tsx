import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { api } from "../api/client";
import { useAppColors } from "../ui/theme";

/**
 * Blocks signed-in product use when the API reports maintenance.
 * Welcome, sign-in, and verify stay reachable so people can still get in
 * (or wait it out on a public screen).
 */
export function MaintenanceGate({
  children,
  bypass = false,
}: {
  children: ReactNode;
  bypass?: boolean;
}) {
  const colors = useAppColors();
  const query = useQuery({
    queryKey: ["maintenance"],
    queryFn: () => api.maintenance(),
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: 1,
  });

  if (query.isLoading && !query.data) {
    return <>{children}</>;
  }

  if (query.data?.enabled && !bypass) {
    const message =
      (query.data.message || "").trim() ||
      "Studio is down for a short maintenance window. Try again in a few minutes.";
    return (
      <View style={[styles.wrap, { backgroundColor: colors.bg }]} accessibilityRole="alert">
        <Text style={[styles.title, { color: colors.fg }]}>Back soon</Text>
        <Text style={[styles.body, { color: colors.muted }]}>{message}</Text>
        {query.isFetching ? (
          <ActivityIndicator color={colors.brand} style={{ marginTop: 16 }} />
        ) : null}
      </View>
    );
  }

  return <>{children}</>;
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 28,
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    marginBottom: 10,
  },
  body: {
    fontSize: 16,
    lineHeight: 22,
  },
});
