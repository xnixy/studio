import { useCallback, useMemo, useState } from "react";
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { api, ApiError } from "@/src/api/client";
import type { PlayGeneration } from "@/src/api/types";
import { GlassSurface } from "@/src/components/GlassSurface";
import { MediaThumb } from "@/src/components/MediaThumb";
import { Screen } from "@/src/components/Screen";
import { EmptyState, ErrorState } from "@/src/components/States";
import { HomePosterSkeleton } from "@/src/features/home/HomePosterCard";
import {
  generationKindLabel,
  modeLabel,
  promptForDisplay,
} from "@/src/features/create/createConstants";
import { useGenerationPoll } from "@/src/hooks/useGenerationPoll";
import { alertActions, alertConfirm, alertError } from "@/src/lib/alerts";
import { hapticLight, hapticSelection, hapticSuccess } from "@/src/lib/haptics";
import { saveMediaToPhotos, shareMedia } from "@/src/lib/mediaActions";
import { freshPlayMediaUrl, isVideoGeneration, playGenerationPosterUrl } from "@/src/lib/media";
import { fetchPlayGenerationsList, playGenerationsKey } from "@/src/lib/playList";
import { fitGrid } from "@/src/ui/fitGrid";
import { useAppColors } from "@/src/ui/theme";
import { useWorkspace } from "@/src/workspace/WorkspaceContext";

type FilterId = "all" | "avatar" | "lipsync" | "video" | "image" | "processing";

const FILTERS: { id: FilterId; label: string }[] = [
  { id: "all", label: "All" },
  { id: "avatar", label: modeLabel("avatar") },
  { id: "lipsync", label: modeLabel("lipsync") },
  { id: "video", label: modeLabel("video") },
  { id: "image", label: modeLabel("image") },
  { id: "processing", label: "Working" },
];

function isPending(status: string): boolean {
  return !["ready", "failed", "error", "cancelled", "expired"].includes(status);
}

export default function ClipsScreen() {
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const colors = useAppColors();
  const qc = useQueryClient();
  const { width: screenW } = useWindowDimensions();
  const [filter, setFilter] = useState<FilterId>("all");
  // Local pull state only. Query isFetching on tab focus freezes iOS RefreshControl.
  const [pullRefreshing, setPullRefreshing] = useState(false);

  const gridPad = 16;
  const gap = 10;
  const { cols, cellW: colW } = fitGrid(screenW, { pad: gridPad, gap, minCell: 108 });
  const cellH = Math.round(colW * (16 / 10));
  const skeletonCount = cols * 2;

  const gensQuery = useQuery({
    queryKey: playGenerationsKey(workspaceId),
    queryFn: () => fetchPlayGenerationsList(qc, workspaceId!),
    enabled: Boolean(workspaceId),
    // Poll only while something is still generating — constant 12s re-sign
    // made every poster look like it was refreshing.
    refetchInterval: (q) => {
      const rows = q.state.data ?? [];
      const pending = rows.some((g) => isPending((g.status || "").toLowerCase()));
      return pending ? 8_000 : false;
    },
    staleTime: 15_000,
  });

  const workspacePending = workspace.isLoading || !workspaceId;
  const listPending = workspacePending || gensQuery.isPending;
  const generations = gensQuery.data ?? [];
  useGenerationPoll(generations, workspaceId);

  const filtered = useMemo(() => {
    return generations.filter((gen) => {
      const status = (gen.status || "").toLowerCase();
      if (filter === "all") return true;
      if (filter === "processing") return isPending(status);
      if (filter === "image") {
        return gen.mode === "image" || gen.asset_type === "image";
      }
      return gen.mode === filter;
    });
  }, [generations, filter]);

  const del = useMutation({
    mutationFn: (id: string) => api.deletePlayGeneration(id),
    onSuccess: async () => {
      void hapticSuccess();
      await qc.invalidateQueries({ queryKey: playGenerationsKey(workspaceId) });
    },
    onError: (e) => {
      alertError("Delete failed", e instanceof ApiError ? e.message : "Could not delete.");
    },
  });

  const onLongPress = useCallback(
    (gen: PlayGeneration) => {
      void hapticLight();
      const ext = isVideoGeneration(gen) ? "mp4" : "jpg";
      const filename = `studio-${gen.id.slice(0, 8)}.${ext}`;
      const ready = (gen.status || "").toLowerCase() === "ready" && Boolean(gen.url);
      const title = promptForDisplay(gen.prompt, gen.mode)?.slice(0, 80) || undefined;
      alertActions(generationKindLabel(gen), title, [
        {
          label: "Open",
          onPress: () => router.push(`/(app)/clip/${gen.id}`),
        },
        ...(ready
          ? [
              {
                label: "Share",
                onPress: () => {
                  void (async () => {
                    const url = await freshPlayMediaUrl(gen, (id) => api.getPlayGeneration(id));
                    await shareMedia(url, filename);
                  })();
                },
              },
              {
                label: "Save to Photos",
                onPress: () => {
                  void (async () => {
                    const url = await freshPlayMediaUrl(gen, (id) => api.getPlayGeneration(id));
                    await saveMediaToPhotos(url, filename);
                  })();
                },
              },
            ]
          : []),
        {
          label: "Delete",
          style: "destructive",
          onPress: () =>
            alertConfirm("Delete from library", "This cannot be undone.", () => del.mutate(gen.id)),
        },
        { label: "Cancel", style: "cancel" },
      ]);
    },
    [del],
  );

  return (
    <Screen contentContainerStyle={{ padding: gridPad, gap: 12 }} bottomPad={28}
      refreshControl={
        <RefreshControl
          refreshing={pullRefreshing}
          onRefresh={() => {
            void (async () => {
              setPullRefreshing(true);
              try {
                await gensQuery.refetch();
              } finally {
                setPullRefreshing(false);
              }
            })();
          }}
          tintColor={colors.brand}
        />
      }
    >
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filterRow}
      >
        {FILTERS.map((f) => {
          const on = filter === f.id;
          return (
            <Pressable
              key={f.id}
              onPress={() => {
                if (f.id !== filter) void hapticSelection();
                setFilter(f.id);
              }}
              accessibilityRole="button"
              accessibilityLabel={f.label}
              accessibilityState={{ selected: on }}
              style={[
                styles.filterChip,
                {
                  backgroundColor: on ? colors.chipOn : colors.chipOff,
                  borderColor: on ? colors.brand : "transparent",
                },
              ]}
            >
              <Text
                style={{
                  color: on ? colors.brand : colors.fg,
                  fontWeight: "600",
                  fontSize: 13,
                }}
              >
                {f.label}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>

      {gensQuery.isError ? (
        <ErrorState
          colors={colors}
          message={gensQuery.error instanceof Error ? gensQuery.error.message : "Could not load."}
          onRetry={() => void gensQuery.refetch()}
        />
      ) : null}

      {!listPending && !gensQuery.isError && filtered.length === 0 ? (
        <EmptyState
          colors={colors}
          title={filter === "all" ? "Nothing in your library yet" : "Nothing in this filter"}
          body={
            filter === "all"
              ? "Clips and stills from Create show up here."
              : "Try another filter, or make something in Create."
          }
          actionLabel="Open Create"
          onAction={() => router.push("/(app)/play")}
        />
      ) : null}

      {listPending ? (
        <View style={[styles.grid, { gap }]}>
          {Array.from({ length: skeletonCount }, (_, i) => (
            <View key={`sk-${i}`} style={{ width: colW }}>
              <HomePosterSkeleton width={colW} mediaHeight={cellH} />
            </View>
          ))}
        </View>
      ) : null}

      <View style={[styles.grid, { gap }]}>
        {filtered.map((gen) => {
          const status = (gen.status || "").toLowerCase();
          const pending = isPending(status);
          const failed = status === "failed" || status === "error";
          return (
            <Pressable
              key={gen.id}
              onPress={() => router.push(`/(app)/clip/${gen.id}`)}
              onLongPress={() => onLongPress(gen)}
              accessibilityRole="button"
              accessibilityLabel={`${generationKindLabel(gen)}, ${promptForDisplay(gen.prompt, gen.mode) || "Untitled"}`}
              style={{ width: colW }}
            >
              <GlassSurface
                intensity={42}
                radius={18}
                style={styles.cellShadow}
                contentStyle={styles.cell}
              >
                <MediaThumb
                  url={gen.url}
                  posterUrl={playGenerationPosterUrl(gen)}
                  assetType={gen.asset_type}
                  width={colW}
                  height={cellH}
                  borderRadius={0}
                />
                <View style={styles.cellMeta}>
                  <Text numberOfLines={2} style={{ color: colors.fg, fontSize: 13, fontWeight: "600" }}>
                    {promptForDisplay(gen.prompt, gen.mode) || "Untitled"}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 12, marginTop: 3 }}>
                    {generationKindLabel(gen)}
                    {pending ? " · working" : failed ? " · failed" : ""}
                  </Text>
                </View>
                {pending ? (
                  <View style={[styles.badge, { backgroundColor: colors.brand }]}>
                    <Text style={styles.badgeText}>…</Text>
                  </View>
                ) : null}
                {failed ? (
                  <View style={[styles.badge, { backgroundColor: colors.danger }]}>
                    <Text style={styles.badgeText}>!</Text>
                  </View>
                ) : null}
              </GlassSurface>
            </Pressable>
          );
        })}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  filterRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingBottom: 2,
  },
  filterChip: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    minHeight: 44,
    justifyContent: "center",
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  cellShadow: {
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  cell: {
    overflow: "hidden",
  },
  cellMeta: {
    paddingHorizontal: 10,
    paddingVertical: 8,
    minHeight: 56,
  },
  badge: {
    position: "absolute",
    top: 8,
    right: 8,
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 6,
  },
  badgeText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 12,
  },
});
