import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import * as Clipboard from "expo-clipboard";
import { useLocalSearchParams, router, useNavigation } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import { SymbolView } from "expo-symbols";
import { api, ApiError } from "@/src/api/client";
import { DEFAULT_BUILTIN_VOICE_ID, FALLBACK_VOICES } from "@/src/lib/stockVoices";
import { ClipPlayer } from "@/src/components/ClipPlayer";
import { GlassCard, GlassSurface } from "@/src/components/GlassSurface";
import { Screen } from "@/src/components/Screen";
import {
  CLIP_ADVANCED_MAX_SECONDS,
  generationKindLabel,
  generationStatusLabel,
  promptForDisplay,
  rawSpeechSeconds,
  spokenLineFromAvatarPrompt,
} from "@/src/features/create/createConstants";
import { alertConfirm, alertError } from "@/src/lib/alerts";
import { hapticLight, hapticSuccess } from "@/src/lib/haptics";
import {
  freshPlayMediaUrl,
  isSignedMediaUrlExpired,
  isVideoGeneration,
  mediaImageSource,
  resolveMediaUrl,
} from "@/src/lib/media";
import { saveMediaToPhotos, shareMedia } from "@/src/lib/mediaActions";
import { useAppColors } from "@/src/ui/theme";
import { useWorkspace } from "@/src/workspace/WorkspaceContext";

function faceIdFromMeta(meta: Record<string, unknown> | undefined): string | null {
  if (!meta) return null;
  const a = meta.face_asset_id ?? meta.source_image_asset_id;
  return typeof a === "string" && a.length > 0 ? a : null;
}

function voiceFromMeta(meta: Record<string, unknown> | undefined): string {
  if (!meta) return DEFAULT_BUILTIN_VOICE_ID;
  const v = meta.voice ?? meta.workspace_voice_id ?? meta.provider_voice_id;
  return typeof v === "string" && v.trim() ? v.trim() : DEFAULT_BUILTIN_VOICE_ID;
}

function lastParam(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return (value[value.length - 1] || "").trim();
  return (value || "").trim();
}

export default function ClipDetailScreen() {
  const params = useLocalSearchParams<{ id?: string | string[] }>();
  const id = lastParam(params.id);
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const qc = useQueryClient();
  const colors = useAppColors();
  const navigation = useNavigation();
  const [busyAction, setBusyAction] = useState<"share" | "save" | "refresh" | null>(null);
  const [copied, setCopied] = useState(false);
  const [revoiceScript, setRevoiceScript] = useState("");
  const [revoiceVoice, setRevoiceVoice] = useState(DEFAULT_BUILTIN_VOICE_ID);

  // Header (transparent liquid glass + "Clip" title) comes from the (app) stack
  // layout, same mechanism the auth glass pages use.

  const genQuery = useQuery({
    queryKey: ["play-generation", id],
    queryFn: () => api.getPlayGeneration(id),
    enabled: Boolean(id),
    refetchInterval: (q) => {
      const data = q.state.data;
      const status = (data?.status || "").toLowerCase();
      const terminal = ["ready", "failed", "error", "cancelled"].includes(status);
      if (terminal && data?.url && isSignedMediaUrlExpired(data.url)) {
        return 15_000;
      }
      if (terminal && data?.url) {
        return false;
      }
      return 3000;
    },
  });

  const gen = genQuery.data;

  useEffect(() => {
    if (!gen) return;
    navigation.setOptions({ title: generationKindLabel(gen) });
  }, [gen, navigation]);

  const mediaUrl = resolveMediaUrl(gen?.url);
  const isVideo = gen ? isVideoGeneration(gen) : false;
  const status = (gen?.status || "").toLowerCase();
  const pending = Boolean(gen && !["ready", "failed", "error", "cancelled"].includes(status));
  const ext = isVideo ? "mp4" : "jpg";
  const filename = `studio-${(id || "clip").slice(0, 8)}.${ext}`;
  const faceId = useMemo(() => faceIdFromMeta(gen?.metadata), [gen?.metadata]);
  const canRevoice = Boolean(status === "ready" && isVideo && faceId && workspaceId);

  useEffect(() => {
    if (!gen) return;
    setRevoiceScript(spokenLineFromAvatarPrompt(gen.prompt || "") || gen.prompt || "");
    setRevoiceVoice(voiceFromMeta(gen.metadata));
  }, [gen?.id, gen?.prompt, gen?.mode, gen?.metadata]);

  useEffect(() => {
    if (!id || !pending) return;
    const t = setInterval(() => {
      void api.pollVideoAsset(id).catch(() => undefined);
    }, 4000);
    return () => clearInterval(t);
  }, [id, pending]);

  const voicesQuery = useQuery({
    queryKey: ["play-voices", workspaceId],
    queryFn: () => api.listPlayVoices(workspaceId!),
    enabled: Boolean(workspaceId && canRevoice),
    staleTime: 60_000,
  });

  const revoiceVoices = useMemo(() => {
    const rows = (voicesQuery.data?.voices || []).filter((v) => v.available !== false);
    return rows.length ? rows : FALLBACK_VOICES;
  }, [voicesQuery.data]);

  const revoice = useMutation({
    mutationFn: async () => {
      if (!workspaceId || !id) throw new Error("Missing account or clip");
      const text = revoiceScript.trim();
      if (!text) throw new Error("Write the exact words to speak");
      if (rawSpeechSeconds(text) > CLIP_ADVANCED_MAX_SECONDS) {
        throw new Error(
          `Script is ~${Math.round(rawSpeechSeconds(text))}s of speech. One take is 30s. Trim it, or Extend after the first clip.`,
        );
      }
      if (!faceId) throw new Error("This clip has no saved face");
      const platform =
        gen?.platform === "feed" ? ("feed" as const) : ("tiktok" as const);
      return api.playGenerate({
        workspace_id: workspaceId,
        mode: "avatar",
        platform,
        prompt: text,
        face_asset_id: faceId,
        voice: revoiceVoice || DEFAULT_BUILTIN_VOICE_ID,
        revoice_of_asset_id: id,
      });
    },
    onSuccess: async (res) => {
      await qc.invalidateQueries({
        queryKey: ["play-generations", workspaceId],
      });
      router.replace(`/(app)/clip/${res.generation.id}`);
    },
    onError: (e) => {
      alertError(
        "Revoice failed",
        e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Could not revoice.",
      );
    },
  });

  const del = useMutation({
    mutationFn: () => api.deletePlayGeneration(id!),
    onSuccess: async () => {
      await qc.invalidateQueries({
        queryKey: ["play-generations", workspace.activeWorkspaceId],
      });
      router.back();
    },
    onError: (e) => {
      alertError("Delete failed", e instanceof ApiError ? e.message : "Could not delete.");
    },
  });

  const onShare = async () => {
    if (!gen?.url) return;
    setBusyAction("share");
    try {
      const url = await freshPlayMediaUrl(gen, (gid) => api.getPlayGeneration(gid));
      await shareMedia(url, filename);
    } finally {
      setBusyAction(null);
    }
  };

  const onSave = async () => {
    if (!gen?.url) return;
    setBusyAction("save");
    try {
      const url = await freshPlayMediaUrl(gen, (gid) => api.getPlayGeneration(gid));
      await saveMediaToPhotos(url, filename);
    } finally {
      setBusyAction(null);
    }
  };

  const onCopyPrompt = async () => {
    const text = promptForDisplay(gen?.prompt, gen?.mode);
    if (!text) return;
    try {
      await Clipboard.setStringAsync(text);
      void hapticSuccess();
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      alertError("Copy failed", "Could not copy the prompt.");
    }
  };

  const onRefresh = async () => {
    if (!id) return;
    setBusyAction("refresh");
    void hapticLight();
    try {
      try {
        await api.pollVideoAsset(id);
      } catch {
        /* optional */
      }
      await genQuery.refetch();
    } finally {
      setBusyAction(null);
    }
  };

  const onRetryInCreate = () => {
    if (!gen) return;
    const face = faceIdFromMeta(gen.metadata);
    const p = (gen.prompt || "").trim();
    router.push({
      pathname: "/(app)/play",
      params: {
        mode: gen.mode === "lipsync" ? "avatar" : gen.mode || "avatar",
        ...(face ? { face } : {}),
        ...(p ? { prompt: p } : {}),
        // Lets Create rework the prompt instead of re-firing the one that failed.
        ...(gen.error_message ? { retryError: gen.error_message } : {}),
      },
    });
  };

  const errorMessage = useMemo(() => {
    if (genQuery.error instanceof ApiError) return genQuery.error.message;
    if (gen?.error_message) return gen.error_message;
    return null;
  }, [genQuery.error, gen?.error_message]);

  const ready = Boolean(gen?.url && status === "ready");
  const failed = status === "failed" || status === "error" || status === "expired";

  return (
    <Screen contentContainerStyle={{ paddingBottom: 24 }} bottomPad={32}>
      {errorMessage ? (
        <Text style={{ color: colors.danger, padding: 16 }}>{errorMessage}</Text>
      ) : null}

      {(genQuery.isLoading || (pending && !ready)) && !(mediaUrl && isVideo && ready) ? (
        <View style={styles.mediaPad}>
          <View
            style={[
              styles.playerPlate,
              {
                aspectRatio: gen?.platform === "feed" ? 1 : 9 / 16,
                width: "100%",
                maxWidth: 360,
                alignSelf: "center",
                backgroundColor: colors.chipOff,
              },
            ]}
          />
          {pending ? (
            <Text style={{ color: colors.muted, textAlign: "center", marginTop: 12, fontSize: 14 }}>
              Still working…
            </Text>
          ) : null}
        </View>
      ) : null}

      {mediaUrl && isVideo && ready ? (
        <ClipPlayer
          uri={mediaUrl}
          // Backend PLATFORM_PRESETS: feed = 1:1, everything else (incl. custom) = 9:16.
          aspectRatio={gen?.platform === "feed" ? 1 : 9 / 16}
        />
      ) : null}
      {mediaUrl && !isVideo ? (
        <View style={styles.stillWrap}>
          <GlassSurface radius={24} intensity={40} contentStyle={{ overflow: "hidden" }}>
            <Image
              source={mediaImageSource(gen?.url) ?? { uri: mediaUrl }}
              style={styles.still}
              contentFit="contain"
            />
          </GlassSurface>
        </View>
      ) : null}

      <View style={{ paddingHorizontal: 16, marginTop: 14 }}>
        <GlassCard>
          <View
            style={{
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 6,
            }}
          >
            <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "700" }}>Prompt</Text>
            {gen?.prompt ? (
              <Pressable
                onPress={() => void onCopyPrompt()}
                hitSlop={8}
                accessibilityRole="button"
                accessibilityLabel={copied ? "Copied prompt" : "Copy prompt"}
              >
                <Text style={{ color: colors.brand, fontWeight: "700", fontSize: 13 }}>
                  {copied ? "Copied" : "Copy"}
                </Text>
              </Pressable>
            ) : null}
          </View>
          <Text
            style={{ color: colors.fg, fontSize: 16, lineHeight: 22 }}
            selectable
          >
            {promptForDisplay(gen?.prompt, gen?.mode) || "No prompt"}
          </Text>
          <Text style={{ color: colors.muted, marginTop: 10, fontSize: 13 }}>
            {gen ? generationKindLabel(gen) : "—"} · {generationStatusLabel(status) || "unknown"}
            {gen?.provider_model ? ` · ${gen.provider_model}` : ""}
          </Text>
        </GlassCard>
      </View>

      {/* Always show recovery actions when not ready media-only */}
      {pending || failed || ready ? (
        <View style={styles.actionPad}>
          <GlassSurface radius={18} intensity={48} contentStyle={styles.actionRow}>
            {ready ? (
              <>
                <ActionCell
                  label="Share"
                  colors={colors}
                  busy={busyAction === "share"}
                  disabled={busyAction !== null}
                  onPress={() => void onShare()}
                  symbol={{ ios: "square.and.arrow.up", android: "share", web: "share" }}
                />
                <View style={[styles.actionDivider, { backgroundColor: colors.divider }]} />
                <ActionCell
                  label="Save"
                  colors={colors}
                  busy={busyAction === "save"}
                  disabled={busyAction !== null}
                  onPress={() => void onSave()}
                  symbol={{ ios: "square.and.arrow.down", android: "download", web: "download" }}
                />
                {isVideo ? (
                  <>
                    <View style={[styles.actionDivider, { backgroundColor: colors.divider }]} />
                    <ActionCell
                      label="Extend"
                      colors={colors}
                      disabled={busyAction !== null}
                      onPress={() => {
                        const face = faceIdFromMeta(gen.metadata);
                        const nextMode =
                          gen.mode === "avatar" || gen.mode === "lipsync"
                            ? "avatar"
                            : gen.mode === "video"
                              ? "video"
                              : "video";
                        router.push({
                          pathname: "/(app)/play",
                          params: {
                            continue: id,
                            mode: nextMode,
                            ...(face ? { face } : {}),
                          },
                        });
                      }}
                      symbol={{ ios: "forward.end", android: "fast_forward", web: "fast_forward" }}
                    />
                  </>
                ) : null}
              </>
            ) : (
              <>
                <ActionCell
                  label="Refresh"
                  colors={colors}
                  busy={busyAction === "refresh"}
                  disabled={busyAction !== null}
                  onPress={() => void onRefresh()}
                  symbol={{ ios: "arrow.clockwise", android: "refresh", web: "refresh" }}
                />
                <View style={[styles.actionDivider, { backgroundColor: colors.divider }]} />
                <ActionCell
                  label="Retry"
                  colors={colors}
                  disabled={busyAction !== null}
                  onPress={onRetryInCreate}
                  symbol={{ ios: "arrow.uturn.forward", android: "replay", web: "replay" }}
                />
                <View style={[styles.actionDivider, { backgroundColor: colors.divider }]} />
                <ActionCell
                  label={copied ? "Copied" : "Copy"}
                  colors={colors}
                  disabled={!gen?.prompt || busyAction !== null}
                  onPress={() => void onCopyPrompt()}
                  symbol={{ ios: "doc.on.doc", android: "content_copy", web: "content_copy" }}
                />
              </>
            )}
          </GlassSurface>
          {ready && isVideo ? (
            <Text style={{ color: colors.muted, fontSize: 12, lineHeight: 17, textAlign: "center" }}>
              Extend opens Create with this clip as the next shot.
            </Text>
          ) : null}
          {failed ? (
            <Text style={{ color: colors.muted, fontSize: 12, lineHeight: 17, textAlign: "center" }}>
              Refresh checks status again. Retry opens Create with this prompt.
            </Text>
          ) : null}
          {pending ? (
            <Text style={{ color: colors.muted, fontSize: 12, lineHeight: 17, textAlign: "center" }}>
              Still generating. Pull Refresh to check the provider.
            </Text>
          ) : null}
        </View>
      ) : null}

      {canRevoice ? (
        <View style={{ paddingHorizontal: 16, marginTop: 14 }}>
          <GlassCard>
            <Text style={{ color: colors.fg, fontSize: 16, fontWeight: "700", marginBottom: 4 }}>
              Revoice
            </Text>
            <Text style={{ color: colors.muted, fontSize: 13, lineHeight: 18, marginBottom: 12 }}>
              Same face. New words and voice. Makes a Talking clip.
            </Text>
            <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "700", marginBottom: 4 }}>
              Exact script
            </Text>
            <TextInput
              value={revoiceScript}
              onChangeText={setRevoiceScript}
              placeholder="Only the words to speak…"
              placeholderTextColor={colors.muted}
              multiline
              style={{
                minHeight: 72,
                borderRadius: 12,
                borderWidth: StyleSheet.hairlineWidth,
                borderColor: colors.border,
                backgroundColor: colors.field,
                color: colors.fg,
                padding: 10,
                fontSize: 15,
                marginBottom: 10,
              }}
            />
            <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "700", marginBottom: 6 }}>
              Voice
            </Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
              <View style={{ flexDirection: "row", gap: 8 }}>
                {revoiceVoices.map((v) => {
                  const on = revoiceVoice === v.id;
                  return (
                    <Pressable
                      key={v.id}
                      onPress={() => setRevoiceVoice(v.id)}
                      accessibilityRole="button"
                      accessibilityLabel={v.name}
                      accessibilityState={{ selected: on }}
                      style={{
                        paddingHorizontal: 12,
                        paddingVertical: 8,
                        borderRadius: 999,
                        borderWidth: StyleSheet.hairlineWidth,
                        borderColor: on ? colors.brand : colors.border,
                        backgroundColor: on ? colors.brandSoft : "transparent",
                      }}
                    >
                      <Text style={{ color: on ? colors.brand : colors.fg, fontWeight: "600", fontSize: 13 }}>
                        {v.name}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </ScrollView>
            <Pressable
              onPress={() => revoice.mutate()}
              disabled={revoice.isPending || !revoiceScript.trim()}
              accessibilityRole="button"
              accessibilityLabel="Generate revoice"
              style={[
                styles.btn,
                {
                  backgroundColor:
                    revoice.isPending || !revoiceScript.trim()
                      ? colors.chipOff
                      : colors.brand,
                },
              ]}
            >
              {revoice.isPending ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.btnText}>Generate revoice</Text>
              )}
            </Pressable>
          </GlassCard>
        </View>
      ) : null}

      <View style={styles.secondaryPad}>
        <Pressable
          onPress={() =>
            alertConfirm("Delete from library", "This cannot be undone.", () => del.mutate())
          }
          disabled={del.isPending}
          hitSlop={8}
          accessibilityRole="button"
          accessibilityLabel="Delete from library"
          style={styles.secondaryLink}
        >
          <SymbolView
            name={{ ios: "trash", android: "delete", web: "delete" }}
            size={15}
            tintColor={colors.danger}
            weight="medium"
          />
          <Text style={{ color: colors.danger, fontWeight: "600", fontSize: 15 }}>
            {del.isPending ? "Deleting…" : "Delete"}
          </Text>
        </Pressable>
        <Pressable
          onPress={() => router.push("/(app)/library")}
          hitSlop={8}
          style={styles.secondaryLink}
          accessibilityRole="button"
          accessibilityLabel="Back to library"
        >
          <Text style={{ color: colors.muted, fontWeight: "600", fontSize: 15 }}>Back to library</Text>
        </Pressable>
      </View>
    </Screen>
  );
}

function ActionCell({
  label,
  colors,
  onPress,
  symbol,
  busy,
  disabled,
}: {
  label: string;
  colors: ReturnType<typeof useAppColors>;
  onPress: () => void;
  symbol: { ios: string; android: string; web: string };
  busy?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={[styles.actionCell, { opacity: disabled && !busy ? 0.5 : 1 }]}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      {busy ? (
        <ActivityIndicator color={colors.brand} size="small" />
      ) : (
        <SymbolView
          name={symbol as never}
          size={20}
          tintColor={colors.brand}
          weight="medium"
        />
      )}
      <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 13 }}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  mediaPad: { paddingHorizontal: 16, paddingTop: 8 },
  playerPlate: {
    borderRadius: 24,
    overflow: "hidden",
    borderWidth: StyleSheet.hairlineWidth,
    backgroundColor: "#000",
  },
  stillWrap: {
    width: "100%",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 8,
  },
  still: {
    width: "100%",
    maxWidth: 360,
    aspectRatio: 1,
    backgroundColor: "#111",
  },
  actionPad: {
    paddingHorizontal: 16,
    marginTop: 14,
    gap: 8,
  },
  actionRow: {
    flexDirection: "row",
    alignItems: "stretch",
    minHeight: 64,
    paddingVertical: 6,
  },
  actionCell: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
    paddingVertical: 8,
  },
  actionDivider: {
    width: StyleSheet.hairlineWidth,
    marginVertical: 10,
  },
  btn: {
    borderRadius: 16,
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  secondaryPad: {
    paddingHorizontal: 16,
    marginTop: 20,
    gap: 14,
    alignItems: "center",
  },
  secondaryLink: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    minHeight: 36,
  },
});
