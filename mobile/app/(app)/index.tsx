import { useState } from "react";
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { SymbolView } from "expo-symbols";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { api } from "@/src/api/client";
import type { PlayGeneration } from "@/src/api/types";
import { useAuth } from "@/src/auth/AuthContext";
import { sessionStorage } from "@/src/auth/storage";
import { Screen } from "@/src/components/Screen";
import { HomeComposeTray } from "@/src/features/home/HomeComposeTray";
import { HomeHeroCard } from "@/src/features/home/HomeHeroCard";
import { HomeRecentsStrip } from "@/src/features/home/HomeRecentsStrip";
import { HomeShortcuts } from "@/src/features/home/HomeShortcuts";
import {
  homeInnerWidth,
  homePagePad,
  homeRecentsLayout,
} from "@/src/features/home/homeLayout";
import { hapticLight } from "@/src/lib/haptics";
import { fetchPlayGenerationsList, playGenerationsKey } from "@/src/lib/playList";
import { useAppColors } from "@/src/ui/theme";
import { useWorkspace } from "@/src/workspace/WorkspaceContext";

function openClip() {
  router.push({ pathname: "/(app)/play", params: { mode: "avatar" } });
}

function openStill() {
  router.push({ pathname: "/(app)/play", params: { mode: "image" } });
}

function faceIdFromMeta(meta: Record<string, unknown> | undefined): string | null {
  if (!meta) return null;
  const a = meta.face_asset_id ?? meta.source_image_asset_id;
  return typeof a === "string" && a.length > 0 ? a : null;
}

function retryInCreate(gen: PlayGeneration) {
  const face = faceIdFromMeta(gen.metadata);
  const p = (gen.prompt || "").trim();
  router.push({
    pathname: "/(app)/play",
    params: {
      mode: gen.mode === "lipsync" ? "avatar" : gen.mode || "avatar",
      ...(face ? { face } : {}),
      ...(p ? { prompt: p } : {}),
      ...(gen.error_message ? { retryError: gen.error_message } : {}),
    },
  });
}

function extendInCreate(gen: PlayGeneration) {
  const face = faceIdFromMeta(gen.metadata);
  const mode = gen.mode === "avatar" || gen.mode === "lipsync" ? "avatar" : "video";
  router.push({
    pathname: "/(app)/play",
    params: {
      continue: gen.id,
      mode,
      ...(face ? { face } : {}),
    },
  });
}

export default function HomeScreen() {
  const auth = useAuth();
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const qc = useQueryClient();
  const colors = useAppColors();
  const insets = useSafeAreaInsets();
  const { width: windowW } = useWindowDimensions();
  const innerW = homeInnerWidth(windowW, insets.left, insets.right);
  const pagePad = homePagePad(innerW);
  const recents = homeRecentsLayout(innerW);
  const [trayH, setTrayH] = useState(168);

  const name = auth.user?.full_name?.split(" ")[0] || "there";

  const billing = useQuery({
    queryKey: ["billing", workspaceId],
    queryFn: () => api.billingStatus(workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
  });

  const gens = useQuery({
    queryKey: playGenerationsKey(workspaceId),
    queryFn: () => fetchPlayGenerationsList(qc, workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
  });

  const faces = useQuery({
    queryKey: ["play-faces", workspaceId],
    queryFn: () => api.listPlayFaces(workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
  });

  const voices = useQuery({
    queryKey: ["play-voices", workspaceId],
    queryFn: () => api.listPlayVoices(workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
  });

  const list = gens.data ?? [];
  const gensLoading = gens.data === undefined && (gens.isPending || !workspaceId);
  const hero = list[0] ?? null;
  const rest = list.slice(1, 1 + recents.count);
  const b = billing.data;

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }} collapsable={false}>
      <Screen
        safeTop
        safeBottom={false}
        contentContainerStyle={{ gap: 18, paddingTop: 12 }}
        bottomPad={trayH + 8}
      >
        <View style={[styles.padH, { paddingHorizontal: pagePad }]}>
          <View style={styles.topRow}>
            <Text accessibilityRole="header" style={[styles.greeting, { color: colors.fg, flex: 1 }]}>
              Hey {name}
            </Text>
            <Pressable
              onPress={() => router.push("/(app)/profile")}
              accessibilityRole="button"
              accessibilityLabel="Account"
              hitSlop={10}
              style={({ pressed }) => [styles.accountBtn, { opacity: pressed ? 0.7 : 1 }]}
            >
              <SymbolView
                name={{ ios: "person.circle", android: "account_circle", web: "account_circle" }}
                size={28}
                tintColor={colors.brand}
                weight="regular"
                fallback={
                  <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 15 }}>Account</Text>
                }
              />
            </Pressable>
          </View>
          {b ? (
            <View style={styles.chips}>
              <CreditChip
                colors={colors}
                label="Clip"
                value={
                  b.play_clip_remaining ??
                  b.play_avatar_remaining ??
                  b.video_generations_remaining
                }
              />
            </View>
          ) : null}
          <HomeShortcuts colors={colors} />
        </View>

        <HomeHeroCard
          colors={colors}
          generation={hero}
          loading={gensLoading}
          onOpen={(id) => router.push(`/(app)/clip/${id}`)}
          onEmptyClip={openClip}
          onRetry={retryInCreate}
          onExtend={extendInCreate}
        />
        {!gensLoading && list.length > 0 ? (
          <HomeRecentsStrip
            colors={colors}
            items={rest}
            onOpen={(id) => router.push(`/(app)/clip/${id}`)}
            onSeeAll={() => router.push("/(app)/library")}
          />
        ) : null}
      </Screen>

      <View
        onLayout={(e) => setTrayH(e.nativeEvent.layout.height)}
        style={styles.trayWrap}
      >
        <HomeComposeTray
          colors={colors}
          faces={faces.data ?? []}
          voices={voices.data?.voices ?? []}
          onNewFace={() => router.push("/(app)/faces")}
          onSelectFace={(id) => {
            void hapticLight();
            void sessionStorage.setActiveFaceId(id);
            const face = faces.data?.find((f) => f.id === id);
            router.push({
              pathname: "/(app)/play",
              params: {
                mode: "avatar",
                face: id,
                ...(face?.bound_voice_id ? { voice: face.bound_voice_id } : {}),
              },
            });
          }}
          onEditFace={(id) => {
            router.push({ pathname: "/(app)/face-edit", params: { id } });
          }}
          onClip={() => {
            void hapticLight();
            openClip();
          }}
          onStill={() => {
            void hapticLight();
            openStill();
          }}
        />
      </View>
    </View>
  );
}

function CreditChip({
  colors,
  label,
  value,
}: {
  colors: ReturnType<typeof useAppColors>;
  label: string;
  value?: number;
}) {
  const text = typeof value === "number" ? String(value) : "—";
  return (
    <Pressable
      onPress={() => router.push("/(app)/billing" as never)}
      accessibilityRole="button"
      accessibilityLabel={`${label} ${text} credits`}
      style={[styles.chip, { backgroundColor: colors.chipOff }]}
    >
      <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "600" }}>{label}</Text>
      <Text style={{ color: colors.fg, fontSize: 13, fontWeight: "700" }}>{text}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  greeting: {
    fontSize: 22,
    fontWeight: "700",
    letterSpacing: -0.4,
  },
  padH: { gap: 10 },
  topRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  accountBtn: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
  },
  chips: { flexDirection: "row", gap: 8 },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
  },
  trayWrap: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
  },
});
