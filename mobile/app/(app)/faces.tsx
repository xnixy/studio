import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from "react-native";
import { Swipeable } from "react-native-gesture-handler";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { hapticLight, hapticSuccess } from "@/src/lib/haptics";
import { router } from "expo-router";
import { api, ApiError } from "@/src/api/client";
import type { PlayFace } from "@/src/api/types";
import { useAuth } from "@/src/auth/AuthContext";
import { sessionStorage } from "@/src/auth/storage";
import { GlassCard } from "@/src/components/GlassSurface";
import { MediaThumb } from "@/src/components/MediaThumb";
import { Screen } from "@/src/components/Screen";
import { EmptyState, ErrorState } from "@/src/components/States";
import { alertActions, alertConfirm, alertError } from "@/src/lib/alerts";
import { saveMediaToPhotos, shareMedia } from "@/src/lib/mediaActions";
import { pickAndPrepareFaceImage } from "@/src/lib/prepareImageUpload";
import { faceVoiceCaption } from "@/src/lib/stockVoices";
import { fitGrid } from "@/src/ui/fitGrid";
import { useAppColors } from "@/src/ui/theme";
import { useWorkspace } from "@/src/workspace/WorkspaceContext";
import { workspaceActionBlockedMessage } from "@/src/workspace/resolveWorkspaceId";

export default function AvatarsScreen() {
  const auth = useAuth();
  const workspace = useWorkspace();
  const qc = useQueryClient();
  const workspaceId = workspace.activeWorkspaceId;
  const colors = useAppColors();
  const { width: screenW } = useWindowDimensions();
  const gridPad = 16;
  const gridGap = 10;
  const { cols, cellW: cardW } = fitGrid(screenW, { pad: gridPad, gap: gridGap, minCell: 108 });
  const thumbSize = Math.max(72, cardW - 16);
  const skeletonCount = cols * 2;

  const [prompt, setPrompt] = useState("");
  const [label, setLabel] = useState("");
  const [consentName, setConsentName] = useState(auth.user?.full_name || "");
  // Default on when we already know a rights holder name (avoids silent iOS upload failures).
  const [consentOk, setConsentOk] = useState(() => (auth.user?.full_name || "").trim().length >= 2);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [activeFace, setActiveFace] = useState<string | null>(null);
  const [modelId, setModelId] = useState("");
  // Local pull state only. Query isFetching on tab focus freezes iOS RefreshControl.
  const [pullRefreshing, setPullRefreshing] = useState(false);

  useEffect(() => {
    void sessionStorage.getActiveFaceId().then(setActiveFace);
  }, []);

  const facesQuery = useQuery({
    queryKey: ["play-faces", workspaceId],
    queryFn: () => api.listPlayFaces(workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
  });

  const voicesQuery = useQuery({
    queryKey: ["play-voices", workspaceId],
    queryFn: () => api.listPlayVoices(workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
  });

  const modelsQuery = useQuery({
    queryKey: ["play-models", workspaceId],
    queryFn: () => api.listPlayModels(workspaceId),
    staleTime: 120_000,
  });

  const imageModels = (modelsQuery.data ?? []).filter(
    (m) => m.enabled && m.modality === "image",
  );
  // Prefer unlocked (Grok) models on free plans for face generate.
  const selectableImageModels = imageModels.filter((m) => !m.locked);
  const faceModelChoices = selectableImageModels.length ? selectableImageModels : imageModels;

  useEffect(() => {
    if (!faceModelChoices.length) return;
    if (!faceModelChoices.some((m) => m.id === modelId)) {
      setModelId(faceModelChoices.find((m) => m.default)?.id || faceModelChoices[0].id);
    }
  }, [faceModelChoices, modelId]);

  const faces = facesQuery.data ?? [];
  const voiceRows = voicesQuery.data?.voices ?? [];

  const invalidate = async () => {
    await qc.invalidateQueries({ queryKey: ["play-faces", workspaceId] });
  };

  const generateFace = useMutation({
    mutationFn: async () => {
      if (!workspaceId) {
        void workspace.refresh();
        throw new ApiError(
          workspaceActionBlockedMessage({
            isLoading: workspace.isLoading,
            error: workspace.error,
          }),
          400,
        );
      }
      if (!consentOk) throw new ApiError("Confirm rights to use this likeness.", 400);
      if (prompt.trim().length < 3) throw new ApiError("Describe the face (a few words).", 400);
      if (consentName.trim().length < 2) throw new ApiError("Enter the rights holder name.", 400);
      return api.generatePlayFace({
        workspace_id: workspaceId,
        prompt: prompt.trim(),
        label: label.trim() || null,
        consent_name: consentName.trim(),
        consent_confirmed: true,
        model: modelId || null,
      });
    },
    onSuccess: async () => {
      void hapticSuccess();
      setNote("Face saved to library.");
      setError(null);
      setPrompt("");
      await invalidate();
    },
    onError: (e) => {
      setError(e instanceof ApiError ? e.message : "Face generate failed.");
      setNote(null);
    },
  });

  const uploadFace = useMutation({
    mutationFn: async () => {
      if (!workspaceId) {
        void workspace.refresh();
        throw new ApiError(
          workspaceActionBlockedMessage({
            isLoading: workspace.isLoading,
            error: workspace.error,
          }),
          400,
        );
      }
      if (!consentOk) {
        throw new ApiError('Turn on "I have rights to use this likeness" first.', 400);
      }
      if (consentName.trim().length < 2) {
        throw new ApiError("Enter the rights holder name (2+ characters) first.", 400);
      }
      // Permissions + HEIC→JPEG + file:// normalization live in the helper (iOS-safe).
      const file = await pickAndPrepareFaceImage();
      return api.uploadPlayFace(
        workspaceId,
        file,
        consentName.trim(),
        label.trim() || undefined,
      );
    },
    onSuccess: async () => {
      void hapticSuccess();
      setNote("Upload saved.");
      setError(null);
      await invalidate();
    },
    onError: (e) => {
      if (e instanceof ApiError && e.message === "No photo selected.") {
        setError(null);
        return;
      }
      const msg =
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Upload failed.";
      setError(msg);
      setNote(null);
      // Surface above the fold on iOS when the inline error is easy to miss.
      if (!(e instanceof ApiError && e.message === "No photo selected.")) {
        alertError("Upload failed", msg);
      }
    },
  });

  const deleteFace = useMutation({
    mutationFn: (id: string) => api.deletePlayFace(id),
    onSuccess: async (_, id) => {
      if (activeFace === id) {
        setActiveFace(null);
        await sessionStorage.clearActiveFaceId();
      }
      await invalidate();
    },
    onError: (e) => {
      alertError("Delete failed", e instanceof ApiError ? e.message : "Could not delete face.");
      setError(e instanceof ApiError ? e.message : "Could not delete face.");
    },
  });

  const selectFace = async (id: string) => {
    setActiveFace(id);
    await sessionStorage.setActiveFaceId(id);
    void hapticLight();
    setNote("Face selected for Create.");
    setError(null);
  };

  /** Persist face, then open Create. */
  const useFaceInCreate = async (id: string, mode: "avatar" | "lipsync" = "avatar") => {
    await selectFace(id);
    router.push({
      pathname: "/(app)/play",
      params: { face: id, mode },
    });
  };

  const faceFilename = (face: PlayFace) =>
    `studio-face-${(face.label || face.id).slice(0, 24).replace(/[^a-zA-Z0-9_-]/g, "-")}.jpg`;

  /** Same management set that used to live on Clips when faces appeared there. */
  const onFaceActions = (face: PlayFace) => {
    const filename = faceFilename(face);
    alertActions(face.label || "Face", "Library face for talking clips", [
      {
        label: "Use for Create",
        onPress: () => {
          void useFaceInCreate(face.id, "avatar");
        },
      },
      {
        label: "Voice",
        onPress: () => {
          router.push(`/(app)/face-voice?id=${encodeURIComponent(face.id)}` as never);
        },
      },
      {
        label: "Edit",
        onPress: () => {
          router.push({ pathname: "/(app)/face-edit", params: { id: face.id } } as never);
        },
      },
      {
        label: "Share",
        onPress: () => void shareMedia(face.url, filename),
      },
      {
        label: "Save to Photos",
        onPress: () => void saveMediaToPhotos(face.url, filename),
      },
      {
        label: "Delete",
        style: "destructive",
        onPress: () =>
          alertConfirm("Delete face", "Remove this face from the library?", () =>
            deleteFace.mutate(face.id),
          ),
      },
      { label: "Cancel", style: "cancel" },
    ]);
  };

  const busy = generateFace.isPending || uploadFace.isPending;
  const workspacePending = workspace.isLoading || !workspaceId;
  const facesPending = workspacePending || facesQuery.isPending;

  const onPullRefresh = async () => {
    setPullRefreshing(true);
    try {
      if (!workspaceId) await workspace.refresh();
      else await Promise.all([facesQuery.refetch()]);
    } finally {
      setPullRefreshing(false);
    }
  };

  return (
    <Screen contentContainerStyle={{ padding: 16, gap: 14 }} bottomPad={28}
      refreshControl={
        <RefreshControl
          refreshing={pullRefreshing}
          onRefresh={() => void onPullRefresh()}
          tintColor={colors.brand}
        />
      }
    >
      {error ? (
        <GlassCard>
          <Text style={{ color: colors.danger, fontSize: 14, fontWeight: "600" }}>{error}</Text>
        </GlassCard>
      ) : null}
      {workspace.error && !workspaceId && !workspace.isLoading ? (
        <ErrorState
          colors={colors}
          message="Could not load your space."
          onRetry={() => void workspace.refresh()}
        />
      ) : null}
      {note ? (
        <GlassCard>
          <Text style={{ color: colors.success, fontSize: 14, fontWeight: "600" }}>{note}</Text>
        </GlassCard>
      ) : null}

      <GlassCard>
        <Text style={[styles.cardTitle, { color: colors.fg }]}>New face</Text>
        <Text style={[styles.help, { color: colors.muted }]}>
          Face only. Head and shoulders on a plain background. Do not include a room. Generated faces cost 1 face credit. Uploads are free.
        </Text>

        <Field
          label="Describe the face"
          value={prompt}
          onChangeText={setPrompt}
          colors={colors}
          multiline
          placeholder="e.g. woman, 30s, warm smile, soft daylight"
        />
        {faceModelChoices.length ? (
          <View style={{ gap: 6 }}>
            <Text style={{ color: colors.muted, fontSize: 13, fontWeight: "600" }}>Model</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
              {faceModelChoices.map((m) => {
                const on = m.id === modelId;
                return (
                  <Pressable
                    key={m.id}
                    onPress={() => setModelId(m.id)}
                    accessibilityRole="button"
                    accessibilityLabel={m.label}
                    accessibilityState={{ selected: on }}
                    style={{
                      borderRadius: 999,
                      paddingHorizontal: 12,
                      paddingVertical: 8,
                      backgroundColor: on ? colors.chipOn : colors.chipOff,
                      borderWidth: StyleSheet.hairlineWidth,
                      borderColor: on ? colors.brand : "transparent",
                    }}
                  >
                    <Text style={{ color: on ? colors.brand : colors.fg, fontWeight: "600", fontSize: 13 }}>
                      {m.label}
                      {m.token_cost > 1 ? ` · ${m.token_cost}` : ""}
                    </Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          </View>
        ) : null}
        <Field label="Label (optional)" value={label} onChangeText={setLabel} colors={colors} />
        <Field
          label="Rights holder name"
          value={consentName}
          onChangeText={setConsentName}
          colors={colors}
          placeholder="Your name or the person who approved this"
        />

        <View style={styles.switchRow}>
          <Text style={{ color: colors.fg, flex: 1, fontSize: 15 }} nativeID="consent-label">
            I have rights to use this likeness
          </Text>
          <Switch
            value={consentOk}
            onValueChange={setConsentOk}
            accessibilityLabel="I have rights to use this likeness"
            trackColor={{ false: colors.border, true: colors.brand }}
            ios_backgroundColor={colors.border}
          />
        </View>

        <Pressable
          onPress={() => generateFace.mutate()}
          disabled={busy || !workspaceId}
          accessibilityRole="button"
          accessibilityLabel="Generate face"
          style={[styles.btn, { backgroundColor: busy ? colors.border : colors.brand }]}
        >
          {generateFace.isPending ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.btnText}>Generate face</Text>
          )}
        </Pressable>

        <Pressable
          onPress={() => uploadFace.mutate()}
          disabled={busy || !workspaceId}
          accessibilityRole="button"
          accessibilityLabel="Upload photo"
          style={[styles.btnSecondary, { borderColor: colors.brand }]}
        >
          {uploadFace.isPending ? (
            <ActivityIndicator color={colors.brand} />
          ) : (
            <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 16 }}>Upload photo</Text>
          )}
        </Pressable>
      </GlassCard>

      <Text style={[styles.section, { color: colors.muted }]}>Library</Text>

      {facesQuery.isError ? (
        <ErrorState
          colors={colors}
          message="Could not load faces."
          onRetry={() => void facesQuery.refetch()}
        />
      ) : null}

      {!facesPending && !facesQuery.isError && faces.length === 0 ? (
        <EmptyState
          colors={colors}
          title="No faces yet"
          body="Generate or upload one, then use it in Create for talking clips."
        />
      ) : null}

      {facesPending ? (
        <View style={[styles.grid, { gap: gridGap }]}>
          {Array.from({ length: skeletonCount }, (_, i) => (
            <GlassCard key={`face-sk-${i}`} style={{ width: cardW }} contentStyle={styles.faceCard} padded={false}>
              <View
                style={{
                  width: thumbSize,
                  height: thumbSize,
                  borderRadius: 14,
                  backgroundColor: colors.chipOff,
                }}
              />
              <View
                style={{
                  height: 12,
                  width: "60%",
                  borderRadius: 4,
                  marginTop: 8,
                  backgroundColor: colors.chipOff,
                }}
              />
            </GlassCard>
          ))}
        </View>
      ) : null}

      <View style={[styles.grid, { gap: gridGap }]}>
        {faces.map((face) => {
          const on = activeFace === face.id;
          const filename = faceFilename(face);
          const voiceCaption = faceVoiceCaption(face, voiceRows);
          return (
            <Swipeable
              key={face.id}
              overshootRight={false}
              containerStyle={{ width: cardW }}
              renderRightActions={() => (
                <View style={styles.swipeRow}>
                  <Pressable
                    onPress={() => void shareMedia(face.url, filename)}
                    accessibilityRole="button"
                    accessibilityLabel={`Share ${face.label || "face"}`}
                    style={[styles.swipeBtn, { backgroundColor: colors.brand }]}
                  >
                    <Text style={styles.swipeText}>Share</Text>
                  </Pressable>
                  <Pressable
                    onPress={() =>
                      alertConfirm("Delete face", "Remove this face?", () =>
                        deleteFace.mutate(face.id),
                      )
                    }
                    accessibilityRole="button"
                    accessibilityLabel={`Delete ${face.label || "face"}`}
                    style={[styles.swipeBtn, styles.swipeDelete]}
                  >
                    <Text style={styles.swipeText}>Delete</Text>
                  </Pressable>
                </View>
              )}
            >
              <GlassCard
                style={{
                  width: cardW,
                  borderWidth: on ? 1.5 : 0,
                  borderColor: on ? colors.brand : "transparent",
                }}
                contentStyle={styles.faceCard}
                padded={false}
              >
                <Pressable
                  onPress={() => void selectFace(face.id)}
                  onLongPress={() => onFaceActions(face)}
                  accessibilityRole="button"
                  accessibilityLabel={`${face.label || "Face"}${on ? ", selected" : ""}`}
                  accessibilityState={{ selected: on }}
                >
                  <MediaThumb
                    url={face.url}
                    assetType="image"
                    size={thumbSize}
                    borderRadius={14}
                    contentPosition="top"
                  />
                </Pressable>
                <Text
                  numberOfLines={1}
                  style={{ color: on ? colors.brand : colors.fg, fontWeight: "600", marginTop: 8 }}
                >
                  {face.label || "Face"}
                  {on ? " · active" : ""}
                </Text>
                {voiceCaption ? (
                  <Text
                    numberOfLines={1}
                    style={{ color: colors.muted, fontSize: 12, fontWeight: "600", marginTop: 2 }}
                  >
                    {voiceCaption}
                  </Text>
                ) : null}
                <View style={styles.faceActions}>
                  <Pressable
                    onPress={() => {
                      void useFaceInCreate(face.id, "avatar");
                    }}
                    hitSlop={6}
                    accessibilityRole="button"
                    accessibilityLabel={`Use ${face.label || "face"} in Create`}
                  >
                    <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 12 }}>Use</Text>
                  </Pressable>
                  <Pressable
                    onPress={() =>
                      router.push(`/(app)/face-voice?id=${encodeURIComponent(face.id)}` as never)
                    }
                    hitSlop={6}
                    accessibilityRole="button"
                    accessibilityLabel={`Choose voice for ${face.label || "face"}`}
                  >
                    <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 12 }}>Voice</Text>
                  </Pressable>
                  <Pressable
                    onPress={() =>
                      router.push({ pathname: "/(app)/face-edit", params: { id: face.id } } as never)
                    }
                    hitSlop={6}
                    accessibilityRole="button"
                    accessibilityLabel={`Edit ${face.label || "face"} look and voice`}
                  >
                    <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 12 }}>Edit</Text>
                  </Pressable>
                  <Pressable
                    onPress={() => void shareMedia(face.url, filename)}
                    hitSlop={6}
                    accessibilityRole="button"
                    accessibilityLabel={`Share ${face.label || "face"}`}
                  >
                    <Text style={{ color: colors.muted, fontWeight: "600", fontSize: 12 }}>Share</Text>
                  </Pressable>
                  <Pressable
                    onPress={() => void saveMediaToPhotos(face.url, filename)}
                    hitSlop={6}
                    accessibilityRole="button"
                    accessibilityLabel={`Save ${face.label || "face"} to Photos`}
                  >
                    <Text style={{ color: colors.muted, fontWeight: "600", fontSize: 12 }}>Save</Text>
                  </Pressable>
                  <Pressable
                    onPress={() => onFaceActions(face)}
                    hitSlop={6}
                    accessibilityRole="button"
                    accessibilityLabel={`More actions for ${face.label || "face"}`}
                  >
                    <Text style={{ color: colors.muted, fontWeight: "600", fontSize: 12 }}>More</Text>
                  </Pressable>
                </View>
              </GlassCard>
            </Swipeable>
          );
        })}
      </View>
    </Screen>
  );
}

function Field({
  label,
  value,
  onChangeText,
  colors,
  placeholder,
  multiline,
}: {
  label: string;
  value: string;
  onChangeText: (t: string) => void;
  colors: { muted: string; field: string; fg: string; border: string };
  placeholder?: string;
  multiline?: boolean;
}) {
  return (
    <View style={{ marginTop: 12 }}>
      <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "700", marginBottom: 6 }}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.muted}
        multiline={multiline}
        style={{
          backgroundColor: colors.field,
          color: colors.fg,
          borderRadius: 14,
          paddingHorizontal: 12,
          paddingVertical: multiline ? 12 : 10,
          minHeight: multiline ? 72 : 44,
          fontSize: 16,
          textAlignVertical: multiline ? "top" : "center",
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  cardTitle: { fontSize: 18, fontWeight: "700", letterSpacing: -0.2 },
  help: { fontSize: 13, lineHeight: 18, marginTop: 4 },
  switchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginTop: 16,
  },
  btn: {
    marginTop: 16,
    borderRadius: 14,
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  btnSecondary: {
    marginTop: 10,
    borderRadius: 14,
    minHeight: 48,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
  },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  section: { fontSize: 13, fontWeight: "600", letterSpacing: -0.1, marginTop: 4 },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  faceCard: {
    padding: 10,
  },
  faceActions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginTop: 8,
  },
  swipeRow: {
    flexDirection: "row",
    marginLeft: 6,
  },
  swipeBtn: {
    justifyContent: "center",
    alignItems: "center",
    width: 64,
    borderRadius: 14,
  },
  swipeDelete: {
    backgroundColor: "#FF453A",
  },
  swipeText: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 12,
  },
});
