import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActionSheetIOS,
  ActivityIndicator,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as DocumentPicker from "expo-document-picker";
import { router, useFocusEffect, useLocalSearchParams, useNavigation } from "expo-router";
import { api, ApiError } from "@/src/api/client";
import type { PlayFace, PlayVoiceOption } from "@/src/api/types";
import { useAuth } from "@/src/auth/AuthContext";
import { sessionStorage } from "@/src/auth/storage";
import { GlassCard, GlassSurface } from "@/src/components/GlassSurface";
import { Screen } from "@/src/components/Screen";
import { EmptyState } from "@/src/components/States";
import { alertActions, alertConfirm, alertError } from "@/src/lib/alerts";
import { hapticLight, hapticSuccess } from "@/src/lib/haptics";
import { liquidGlassStackHeaderOptions } from "@/src/ui/nav";
import { useAppColors, type AppColors } from "@/src/ui/theme";
import { useWorkspace } from "@/src/workspace/WorkspaceContext";
import { workspaceActionBlockedMessage } from "@/src/workspace/resolveWorkspaceId";
import {
  cloneLanguageLabel,
  cloneLanguageOf,
  CLONE_LANGUAGES,
  cloneReadAloud,
  cloneLanguageSelectLabel,
  DEFAULT_CLONE_LANGUAGE,
  type CloneLanguageCode,
} from "@/src/lib/cloneVoice";
import {
  DEFAULT_BUILTIN_VOICE_ID,
  FALLBACK_VOICES,
  FEATURED_VOICE_IDS,
  matchesVoiceSearch,
  voiceAccentLabel,
  voiceAccentOptions,
} from "@/src/lib/stockVoices";
import {
  CLONE_AUDIO_PICKER_TYPES,
  cloneRecordingOptions,
  prepareCloneAudioFile,
} from "@/src/lib/prepareCloneAudio";

const GENDER_RANK: Record<string, number> = { female: 0, male: 1, neutral: 2 };

function isBuiltin(v: PlayVoiceOption) {
  return (v.source ?? "builtin") === "builtin";
}

function isCloned(v: PlayVoiceOption) {
  const s = v.source ?? "builtin";
  return s === "cloned" || s === "custom";
}

/** Featured five first, then female → male → A–Z (matches backend). */
function sortPlayVoices(list: PlayVoiceOption[]): PlayVoiceOption[] {
  return [...list].sort((a, b) => {
    const aClone = isCloned(a) ? 1 : 0;
    const bClone = isCloned(b) ? 1 : 0;
    if (aClone !== bClone) return aClone - bClone;

    const ai = FEATURED_VOICE_IDS.indexOf(a.id as (typeof FEATURED_VOICE_IDS)[number]);
    const bi = FEATURED_VOICE_IDS.indexOf(b.id as (typeof FEATURED_VOICE_IDS)[number]);
    const aIn = ai !== -1;
    const bIn = bi !== -1;
    if (aIn && bIn) return ai - bi;
    if (aIn !== bIn) return aIn ? -1 : 1;

    const ag = GENDER_RANK[(a.gender || "").toLowerCase()] ?? 9;
    const bg = GENDER_RANK[(b.gender || "").toLowerCase()] ?? 9;
    if (ag !== bg) return ag - bg;
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  });
}

function genderLabel(gender?: string | null): string | null {
  const g = (gender || "").toLowerCase();
  if (g === "female") return "Female";
  if (g === "male") return "Male";
  if (g === "neutral") return "Neutral";
  return null;
}

function searchParam(value: string | string[] | undefined): string {
  const raw = Array.isArray(value) ? value[value.length - 1] : value;
  return (raw || "").trim();
}

function friendlyVoicesError(err: unknown): string {
  const raw =
    err instanceof ApiError
      ? err.message
      : err instanceof Error
        ? err.message
        : "Could not load voices.";
  const lower = raw.toLowerCase();
  if (err instanceof ApiError && err.status === 404) {
    return "Voice catalog is temporarily unavailable. Built-in voices still work below.";
  }
  if (
    lower.includes("not found") ||
    lower.includes("internal server") ||
    lower === "request failed" ||
    (err instanceof ApiError && err.status >= 500)
  ) {
    return "Could not load the full voice list. Built-in voices still work below. Pull to refresh.";
  }
  return raw || "Could not load voices.";
}

export default function VoicesScreen() {
  const auth = useAuth();
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const colors = useAppColors();
  const navigation = useNavigation();
  const params = useLocalSearchParams<{ bind_face_id?: string | string[] }>();
  const bindFaceId = searchParam(params.bind_face_id);
  const qc = useQueryClient();

  const [selectedId, setSelectedId] = useState(DEFAULT_BUILTIN_VOICE_ID);
  const [search, setSearch] = useState("");
  const [browseBuiltin, setBrowseBuiltin] = useState(false);
  const [genderFilter, setGenderFilter] = useState("all");
  const [accentFilter, setAccentFilter] = useState("all");
  const [cloneLabel, setCloneLabel] = useState("");
  const [consentName, setConsentName] = useState(auth.user?.full_name || "");
  const [consentOk, setConsentOk] = useState(false);
  const [cloneGender, setCloneGender] = useState<"female" | "male" | "neutral">("female");
  const [cloneLanguage, setCloneLanguage] = useState<CloneLanguageCode>(DEFAULT_CLONE_LANGUAGE);
  const [cloneFile, setCloneFile] = useState<{
    uri: string;
    name: string;
    type: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // Local pull state only. Query isFetching on tab focus freezes iOS RefreshControl.
  const [pullRefreshing, setPullRefreshing] = useState(false);
  const [recording, setRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const recorderRef = useRef<{
    isRecording: boolean;
    currentTime: number;
    uri: string | null;
    record: () => void;
    stop: () => Promise<void>;
    prepareToRecordAsync: () => Promise<void>;
  } | null>(null);
  const recordTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    navigation.setOptions({
      title: bindFaceId ? "Choose voice" : "Voices",
      ...liquidGlassStackHeaderOptions(colors),
    });
  }, [navigation, colors, bindFaceId]);

  useEffect(() => {
    void sessionStorage.getActiveVoiceId().then((id) => {
      if (id) setSelectedId(id);
    });
  }, []);

  const voicesQuery = useQuery({
    queryKey: ["play-voices", workspaceId],
    queryFn: () => api.listPlayVoices(workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
    // Built-ins still work offline/fallback if the API route is missing on an old deploy.
    retry: 1,
  });

  const facesQuery = useQuery({
    queryKey: ["play-faces", workspaceId],
    queryFn: () => api.listPlayFaces(workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
  });
  const faceRows: PlayFace[] = facesQuery.data ?? [];

  const voices = useMemo(() => {
    const fromApi = voicesQuery.data?.voices;
    if (fromApi?.length) return sortPlayVoices(fromApi);
    // Always have built-ins even when list fails (prod 404 / network).
    return sortPlayVoices(FALLBACK_VOICES);
  }, [voicesQuery.data]);

  const listDegraded = Boolean(voicesQuery.isError && !voicesQuery.data?.voices?.length);

  const builtin = useMemo(() => voices.filter(isBuiltin), [voices]);
  const custom = useMemo(() => voices.filter(isCloned), [voices]);

  const filteredBuiltin = useMemo(() => {
    return builtin.filter((v) => {
      if (genderFilter !== "all" && (v.gender || "").toLowerCase() !== genderFilter) {
        return false;
      }
      if (accentFilter !== "all" && (v.accent || "").toLowerCase() !== accentFilter) {
        return false;
      }
      return matchesVoiceSearch(v, search);
    });
  }, [accentFilter, builtin, genderFilter, search]);
  const accentOptions = useMemo(() => voiceAccentOptions(builtin), [builtin]);
  const pickingForFace = Boolean(bindFaceId);
  const faceBoundId = (faceRows.find((f) => f.id === bindFaceId)?.bound_voice_id || "").trim();
  const browsingBuiltin =
    pickingForFace ||
    browseBuiltin ||
    search.trim().length > 0 ||
    genderFilter !== "all" ||
    accentFilter !== "all";
  const featuredBuiltin = useMemo(
    () =>
      builtin.filter(
        (v) =>
          FEATURED_VOICE_IDS.includes(v.id as (typeof FEATURED_VOICE_IDS)[number]) ||
          v.id === selectedId ||
          v.id === faceBoundId,
      ),
    [builtin, faceBoundId, selectedId],
  );

  const accessFromList = voicesQuery.data?.custom_voices_access;
  const canClone = accessFromList?.can_clone ?? true;
  const atCap =
    (accessFromList?.clone_count ?? 0) >= (accessFromList?.clone_cap ?? 1) && !canClone;

  const selectVoice = async (id: string) => {
    setSelectedId(id);
    await sessionStorage.setActiveVoiceId(id);
    void hapticLight();
    setNotice(
      `${voices.find((v) => v.id === id)?.name || "Voice"} is the fallback when a Face has no bound voice.`,
    );
    setError(null);
  };

  const [previewId, setPreviewId] = useState<string | null>(null);
  const [previewLoadingId, setPreviewLoadingId] = useState<string | null>(null);
  // expo-audio player (not expo-av — ExponentAV is gone on SDK 55+)
  type PreviewPlayer = {
    play: () => void;
    pause: () => void;
    remove: () => void;
    volume: number;
    isLoaded: boolean;
    addListener: (
      event: "playbackStatusUpdate",
      listener: (status: { isLoaded: boolean; didJustFinish: boolean; playing: boolean }) => void,
    ) => { remove: () => void };
  };
  const playerRef = useRef<PreviewPlayer | null>(null);
  const finishSubRef = useRef<{ remove: () => void } | null>(null);

  const releasePreviewPlayer = () => {
    try {
      finishSubRef.current?.remove();
    } catch {
      /* ignore */
    }
    finishSubRef.current = null;
    const player = playerRef.current;
    playerRef.current = null;
    if (!player) return;
    try {
      player.pause();
    } catch {
      /* ignore */
    }
    try {
      player.remove();
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    return () => {
      releasePreviewPlayer();
    };
  }, []);

  // Leaving Voices (tabs / stack) must stop preview audio.
  useFocusEffect(
    useCallback(() => {
      return () => {
        releasePreviewPlayer();
        setPreviewId(null);
        setPreviewLoadingId(null);
      };
    }, []),
  );

  const playPreview = async (voiceId: string) => {
    if (!workspaceId) return;
    if (previewId === voiceId) {
      releasePreviewPlayer();
      setPreviewId(null);
      setPreviewLoadingId(null);
      return;
    }
    setError(null);
    setPreviewLoadingId(voiceId);
    try {
      releasePreviewPlayer();
      const uri = await api.previewPlayVoice(workspaceId, voiceId);
      if (typeof uri !== "string" || !uri.trim()) throw new Error("Preview unavailable");

      const {
        createAudioPlayer,
        setAudioModeAsync,
        setIsAudioActiveAsync,
      } = await import("expo-audio");

      // Route to speaker even with the silent switch; take exclusive focus.
      await setIsAudioActiveAsync(true);
      await setAudioModeAsync({
        playsInSilentMode: true,
        interruptionMode: "doNotMix",
        shouldPlayInBackground: false,
        allowsRecording: false,
        shouldRouteThroughEarpiece: false,
      });

      // Local file already on disk — do NOT use downloadFirst (that starts with a null
      // source and play() becomes a no-op before replace lands).
      const player = createAudioPlayer({ uri }) as PreviewPlayer;
      player.volume = 1;
      playerRef.current = player;

      // Wait until the native player actually has the file loaded.
      await new Promise<void>((resolve, reject) => {
        if (player.isLoaded) {
          resolve();
          return;
        }
        const timeout = setTimeout(() => {
          sub.remove();
          reject(new Error("Preview audio took too long to load."));
        }, 12_000);
        const sub = player.addListener("playbackStatusUpdate", (status) => {
          if (status.isLoaded) {
            clearTimeout(timeout);
            sub.remove();
            resolve();
          }
        });
      });

      if (playerRef.current !== player) {
        // User stopped while we were loading.
        try {
          player.remove();
        } catch {
          /* ignore */
        }
        return;
      }

      finishSubRef.current = player.addListener("playbackStatusUpdate", (status) => {
        if (status.didJustFinish) {
          releasePreviewPlayer();
          setPreviewId(null);
        }
      });

      player.play();
      setPreviewId(voiceId);
    } catch (e) {
      releasePreviewPlayer();
      const msg = e instanceof ApiError ? e.message : "Could not play preview.";
      setError(
        /internal server/i.test(msg) || /native module/i.test(msg)
          ? "Preview failed. Try again in a moment."
          : msg,
      );
      setPreviewId(null);
    } finally {
      setPreviewLoadingId(null);
    }
  };

  const cloneMutation = useMutation({
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
      if (!cloneFile) throw new ApiError("Record or pick an audio file first.", 400);
      if (!consentOk) throw new ApiError("Confirm you have rights to this voice.", 400);
      if (cloneLabel.trim().length < 1) throw new ApiError("Add a label for this voice.", 400);
      if (consentName.trim().length < 2) throw new ApiError("Enter the rights holder name.", 400);
      const prepared = await prepareCloneAudioFile(cloneFile);
      return api.clonePlayVoice(workspaceId, {
        label: cloneLabel,
        consentName,
        gender: cloneGender,
        language: cloneLanguage,
        file: prepared,
        bindFaceId: bindFaceId || null,
      });
    },
    onSuccess: async (voice) => {
      void hapticSuccess();
      setError(null);
      setCloneLabel("");
      setConsentOk(false);
      setCloneFile(null);
      await qc.invalidateQueries({ queryKey: ["play-voices", workspaceId] });
      await qc.invalidateQueries({ queryKey: ["play-faces", workspaceId] });
      if (bindFaceId) {
        router.back();
        return;
      }
      setNotice(`Cloned "${voice.name}". Bind it to a Face so they speak with it.`);
      await selectVoice(voice.id);
      await playPreview(voice.id);
    },
    onError: (e) => {
      setNotice(null);
      setError(e instanceof ApiError ? e.message : "Could not clone voice.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (voiceId: string) => {
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
      return api.deletePlayVoice(workspaceId, voiceId);
    },
    onSuccess: async (_void, voiceId) => {
      setError(null);
      setNotice("Custom voice removed.");
      if (selectedId === voiceId) {
        await selectVoice(DEFAULT_BUILTIN_VOICE_ID);
      }
      await qc.invalidateQueries({ queryKey: ["play-voices", workspaceId] });
    },
    onError: (e) => {
      setNotice(null);
      alertError("Delete failed", e instanceof ApiError ? e.message : "Could not delete voice.");
    },
  });

  const bindMutation = useMutation({
    mutationFn: ({ faceId, voiceId }: { faceId: string; voiceId: string }) => {
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
      return api.bindPlayFaceVoice(faceId, workspaceId, voiceId);
    },
    onSuccess: async (_face, vars) => {
      void hapticSuccess();
      await qc.invalidateQueries({ queryKey: ["play-faces", workspaceId] });
      const voiceName = voices.find((v) => v.id === vars.voiceId)?.name || "Voice";
      const faceName = faceRows.find((f) => f.id === vars.faceId)?.label || "Face";
      if (bindFaceId) {
        router.back();
        return;
      }
      setNotice(
        `${voiceName} is on ${faceName}. That Face uses it on Talking and spoken Scene.`,
      );
      setError(null);
    },
    onError: (e) => {
      setError(e instanceof ApiError ? e.message : "Could not bind that voice.");
    },
  });

  const bindVoiceToFace = (voiceId: string) => {
    if (bindFaceId) {
      bindMutation.mutate({ faceId: bindFaceId, voiceId });
      return;
    }
    if (faceRows.length === 0) {
      alertActions("Add a Face first", "Bind a voice to a Face so they talk with it.", [
        { label: "Faces", onPress: () => router.push("/(app)/faces") },
        { label: "Use as fallback", onPress: () => void selectVoice(voiceId) },
        { label: "Cancel", style: "cancel" },
      ]);
      return;
    }
    if (faceRows.length === 1) {
      bindMutation.mutate({ faceId: faceRows[0].id, voiceId });
      return;
    }
    const labels = faceRows.map((f) => f.label || "Face");
    if (Platform.OS === "ios") {
      ActionSheetIOS.showActionSheetWithOptions(
        {
          title: "Use on a Face",
          message: "That Face speaks with this voice on Talking and spoken Scene.",
          options: [...labels, "Cancel"],
          cancelButtonIndex: labels.length,
        },
        (i) => {
          if (typeof i === "number" && i >= 0 && i < faceRows.length) {
            bindMutation.mutate({ faceId: faceRows[i].id, voiceId });
          }
        },
      );
      return;
    }
    alertActions(
      "Use on a Face",
      "That Face speaks with this voice on Talking and spoken Scene.",
      [
        ...faceRows.map((f) => ({
          label: f.label || "Face",
          onPress: () => bindMutation.mutate({ faceId: f.id, voiceId }),
        })),
        { label: "Cancel", style: "cancel" },
      ],
    );
  };

  const pickCloneAudio = async () => {
    try {
      const picked = await DocumentPicker.getDocumentAsync({
        type: CLONE_AUDIO_PICKER_TYPES,
        copyToCacheDirectory: true,
        multiple: false,
      });
      if (picked.canceled || !picked.assets?.[0]) return;
      const asset = picked.assets[0];
      const name = asset.name || `voice-${Date.now()}.m4a`;
      const type = asset.mimeType || "audio/mpeg";
      const prepared = await prepareCloneAudioFile({
        uri: asset.uri,
        name,
        type,
      });
      setCloneFile(prepared);
      if (!cloneLabel.trim()) {
        const base = name.replace(/\.[^.]+$/, "").trim();
        if (base) setCloneLabel(base.slice(0, 80));
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open file picker.");
    }
  };

  const stopRecording = async () => {
    if (recordTimerRef.current) {
      clearInterval(recordTimerRef.current);
      recordTimerRef.current = null;
    }
    const rec = recorderRef.current;
    recorderRef.current = null;
    setRecording(false);
    if (!rec) return;
    try {
      await rec.stop();
      await new Promise((resolve) => setTimeout(resolve, 150));
      let uri = rec.uri;
      if (!uri) {
        await new Promise((resolve) => setTimeout(resolve, 250));
        uri = rec.uri;
      }
      if (uri) {
        const extMatch = uri.match(/\.(wav|m4a|caf|mp3|aac)(?:\?|$)/i);
        const ext = `.${(extMatch?.[1] || (Platform.OS === "ios" ? "wav" : "m4a")).toLowerCase()}`;
        const prepared = await prepareCloneAudioFile({
          uri,
          name: `voice-sample-${Date.now()}${ext}`,
          type: ext === ".wav" ? "audio/wav" : "audio/mp4",
        });
        setCloneFile(prepared);
        if (!cloneLabel.trim()) setCloneLabel("My voice");
      } else {
        setError("Could not finish the recording.");
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not finish the recording.");
    }
  };

  const startRecording = async () => {
    setError(null);
    try {
      const {
        AudioModule,
        requestRecordingPermissionsAsync,
        setAudioModeAsync,
      } = await import("expo-audio");
      const perm = await requestRecordingPermissionsAsync();
      if (!perm.granted) {
        setError("Mic permission is required to record.");
        return;
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      const rec = new AudioModule.AudioRecorder(cloneRecordingOptions());
      await rec.prepareToRecordAsync();
      recorderRef.current = rec;
      rec.record();
      setRecording(true);
      setRecordSeconds(0);
      recordTimerRef.current = setInterval(() => {
        setRecordSeconds((s) => {
          const next = s + 1;
          if (next >= 90) void stopRecording();
          return next;
        });
      }, 1000);
    } catch {
      setError("Could not start the mic. Upload a file instead.");
    }
  };

  const cloneReady =
    canClone &&
    consentOk &&
    cloneLabel.trim().length > 0 &&
    consentName.trim().length > 0 &&
    Boolean(cloneFile) &&
    Boolean(cloneGender) &&
    !cloneMutation.isPending;

  const onPullRefresh = async () => {
    setPullRefreshing(true);
    try {
      await Promise.all([voicesQuery.refetch(), facesQuery.refetch()]);
    } finally {
      setPullRefreshing(false);
    }
  };

  return (
    <Screen
      contentContainerStyle={{ padding: 16, gap: 14 }}
      refreshControl={
        <RefreshControl
          refreshing={pullRefreshing}
          onRefresh={() => void onPullRefresh()}
          tintColor={colors.brand}
        />
      }
    >
      <Text style={[styles.lead, { color: colors.muted }]}>
        {bindFaceId
          ? "Tap a voice to bind it to this Face. That Face uses it on Talking and spoken Scene."
          : "Tap a voice to bind it to a Face. Custom voices come first. Built-in voices are a short list unless you browse all. Fallback is only used when a Face has no bind."}
      </Text>

      {error ? (
        <Text
          accessibilityRole="alert"
          style={[styles.banner, { color: colors.danger, backgroundColor: colors.chipOff }]}
        >
          {error}
        </Text>
      ) : null}
      {notice ? (
        <Text style={[styles.banner, { color: colors.success, backgroundColor: colors.chipOff }]}>
          {notice}
        </Text>
      ) : null}

      <View style={styles.headerRow}>
        <Text style={[styles.section, { color: colors.muted }]}>Custom</Text>
        <View style={[styles.badge, { backgroundColor: colors.chipOff, borderColor: colors.border }]}>
          <Text style={{ color: colors.fg, fontSize: 12, fontWeight: "600" }}>
            {canClone ? "Open" : "Full"}
          </Text>
        </View>
      </View>

      {custom.length > 0 ? (
        <View style={styles.list}>
          {custom.map((voice) => (
            <VoiceRow
              key={voice.id}
              voice={voice}
              selected={pickingForFace ? voice.id === faceBoundId : selectedId === voice.id}
              selectedHint={pickingForFace ? "on this Face" : "fallback"}
              colors={colors}
              custom
              onSelect={() => bindVoiceToFace(voice.id)}
              onFallback={bindFaceId ? undefined : () => void selectVoice(voice.id)}
              onPreview={
                voice.available !== false ? () => void playPreview(voice.id) : undefined
              }
              previewLoading={previewLoadingId === voice.id}
              previewPlaying={previewId === voice.id}
              onDelete={() =>
                alertConfirm(
                  "Remove voice",
                  `Remove "${voice.name}"? This cannot be undone.`,
                  () => deleteMutation.mutate(voice.id),
                  "Remove",
                )
              }
              deleting={deleteMutation.isPending && deleteMutation.variables === voice.id}
            />
          ))}
        </View>
      ) : null}

      {canClone ? (
        <GlassCard contentStyle={styles.panel}>
          <Text style={[styles.panelTitle, { color: colors.fg }]}>Clone a voice</Text>
          <Text style={[styles.help, { color: colors.muted }]}>
            Quiet room, one speaker. Read the lines below for 30 to 90 seconds. No music. 20s minimum.
          </Text>

          <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "700", marginTop: 12 }}>
            Language
          </Text>
          <Text style={[styles.help, { color: colors.muted, marginTop: 4 }]}>
            Pick the language you will read. The script below matches it.
          </Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
            {CLONE_LANGUAGES.map((lang) => {
              const on = cloneLanguage === lang.code;
              return (
                <Pressable
                  key={lang.code}
                  onPress={() => {
                    if (lang.code === cloneLanguage) return;
                    setCloneLanguage(lang.code);
                    setCloneFile(null);
                    setError(null);
                  }}
                  accessibilityRole="button"
                  accessibilityLabel={cloneLanguageSelectLabel(lang)}
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
                    {lang.nativeLabel}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          <Field
            label="Label"
            value={cloneLabel}
            onChangeText={setCloneLabel}
            colors={colors}
            placeholder="e.g. Brand narrator"
          />
          <Field
            label="Your name"
            value={consentName}
            onChangeText={setConsentName}
            colors={colors}
            placeholder="Full name"
          />
          <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "700", marginTop: 12 }}>
            Gender
          </Text>
          <View style={{ flexDirection: "row", gap: 8, marginTop: 6 }}>
            {(["female", "male", "neutral"] as const).map((g) => {
              const on = cloneGender === g;
              return (
                <Pressable
                  key={g}
                  onPress={() => setCloneGender(g)}
                  accessibilityRole="button"
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
                    {g === "female" ? "Female" : g === "male" ? "Male" : "Neutral"}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "700", marginTop: 12 }}>
            Read this out loud
          </Text>
          <Text style={[styles.help, { color: colors.muted, marginTop: 4 }]}>
            Like a call. Pause at the periods. If you have extra time, add a short story from today.
          </Text>
          <Text
            style={{
              color: colors.fg,
              fontSize: recording ? 18 : 15,
              lineHeight: recording ? 26 : 22,
              marginTop: 8,
              writingDirection: cloneLanguageOf(cloneLanguage).rtl ? "rtl" : "ltr",
              textAlign: cloneLanguageOf(cloneLanguage).rtl ? "right" : "left",
            }}
          >
            {cloneReadAloud(cloneLanguage)}
          </Text>

          <Pressable
            onPress={() => void (recording ? stopRecording() : startRecording())}
            accessibilityRole="button"
            accessibilityLabel={recording ? "Stop recording" : "Record a sample"}
            style={[styles.fileBtn, { borderColor: colors.brand }]}
          >
            <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 15 }}>
              {recording ? `Stop · ${recordSeconds}s` : "Record"}
            </Text>
          </Pressable>
          <Pressable
            onPress={() => void pickCloneAudio()}
            accessibilityRole="button"
            accessibilityLabel={cloneFile ? `Audio sample, ${cloneFile.name}` : "Upload audio sample"}
            style={[styles.fileBtn, { borderColor: colors.border }]}
          >
            <Text style={{ color: colors.fg, fontWeight: "600", fontSize: 15 }}>
              {cloneFile ? cloneFile.name : "Upload instead"}
            </Text>
          </Pressable>

          <View style={styles.switchRow}>
            <Text style={{ color: colors.fg, flex: 1, fontSize: 15 }}>
              I own this voice or have rights to use it
            </Text>
            <Switch
              value={consentOk}
              onValueChange={setConsentOk}
              accessibilityLabel="I own this voice or have rights to use it"
              trackColor={{ false: colors.border, true: colors.brand }}
              ios_backgroundColor={colors.border}
            />
          </View>

          <Pressable
            onPress={() => cloneMutation.mutate()}
            disabled={!cloneReady}
            accessibilityRole="button"
            accessibilityLabel="Clone voice"
            style={[styles.primaryBtn, { backgroundColor: cloneReady ? colors.brand : colors.border }]}
          >
            {cloneMutation.isPending ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.primaryBtnText}>Clone voice</Text>
            )}
          </Pressable>
        </GlassCard>
      ) : null}

      <View style={styles.headerRow}>
        <Text style={[styles.section, { color: colors.muted }]}>Built-in</Text>
        {pickingForFace ? null : (
        <Pressable
          onPress={() => {
            if (browsingBuiltin) {
              setBrowseBuiltin(false);
              setSearch("");
              setGenderFilter("all");
              setAccentFilter("all");
            } else {
              setBrowseBuiltin(true);
            }
          }}
          accessibilityRole="button"
          accessibilityLabel={browsingBuiltin ? "Hide full built-in list" : "Browse all built-in voices"}
          hitSlop={8}
        >
          <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 13 }}>
            {browsingBuiltin ? "Show less" : "Browse all"}
          </Text>
        </Pressable>
        )}
      </View>
      <Text style={[styles.help, { color: colors.muted, marginTop: 0 }]}>
        {pickingForFace
          ? "Tap a voice. It stays on this Face until you pick another."
          : "Tap to bind to a Face. Fallback is only used when a Face has none."}
      </Text>

      {listDegraded ? (
        <GlassCard>
          <Text style={{ color: colors.muted, fontSize: 14, lineHeight: 20 }}>
            {friendlyVoicesError(voicesQuery.error)}
          </Text>
          <Pressable
            onPress={() => void voicesQuery.refetch()}
            accessibilityRole="button"
            accessibilityLabel="Retry voice list"
            style={{ marginTop: 10 }}
          >
            <Text style={{ color: colors.brand, fontWeight: "700", fontSize: 15 }}>Retry list</Text>
          </Pressable>
        </GlassCard>
      ) : null}

      {!browsingBuiltin ? (
        <View style={styles.featuredRow}>
          {featuredBuiltin.map((voice) => {
            const on = pickingForFace ? voice.id === faceBoundId : selectedId === voice.id;
            return (
              <Pressable
                key={voice.id}
                onPress={() => bindVoiceToFace(voice.id)}
                accessibilityRole="button"
                accessibilityLabel={`${voice.name}${on ? ", fallback" : ""}`}
                accessibilityState={{ selected: on }}
                style={[
                  styles.filterChip,
                  {
                    backgroundColor: on ? colors.chipOn : colors.chipOff,
                    borderColor: on ? colors.brand : "transparent",
                  },
                ]}
              >
                <Text style={{ color: on ? colors.brand : colors.fg, fontWeight: "600", fontSize: 13 }}>
                  {voice.name}
                </Text>
              </Pressable>
            );
          })}
        </View>
      ) : (
        <>
          <GlassSurface intensity={40} radius={14} contentStyle={styles.searchWrap}>
            <TextInput
              value={search}
              onChangeText={setSearch}
              placeholder="Search name, gender, or accent"
              placeholderTextColor={colors.muted}
              accessibilityLabel="Search voices"
              style={[styles.search, { color: colors.fg }]}
            />
          </GlassSurface>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ gap: 8, paddingBottom: 4 }}
          >
            {[
              { id: "all", label: "All" },
              { id: "female", label: "Female" },
              { id: "male", label: "Male" },
            ].map((opt) => {
              const on = genderFilter === opt.id;
              return (
                <Pressable
                  key={opt.id}
                  onPress={() => setGenderFilter(opt.id)}
                  accessibilityRole="button"
                  accessibilityState={{ selected: on }}
                  style={[
                    styles.filterChip,
                    {
                      backgroundColor: on ? colors.chipOn : colors.chipOff,
                      borderColor: on ? colors.brand : "transparent",
                    },
                  ]}
                >
                  <Text style={{ color: on ? colors.brand : colors.fg, fontWeight: "600", fontSize: 13 }}>
                    {opt.label}
                  </Text>
                </Pressable>
              );
            })}
          </ScrollView>
          {accentOptions.length > 1 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ gap: 8, paddingBottom: 4 }}
            >
              <Pressable
                onPress={() => setAccentFilter("all")}
                accessibilityRole="button"
                accessibilityState={{ selected: accentFilter === "all" }}
                style={[
                  styles.filterChip,
                  {
                    backgroundColor: accentFilter === "all" ? colors.chipOn : colors.chipOff,
                    borderColor: accentFilter === "all" ? colors.brand : "transparent",
                  },
                ]}
              >
                <Text
                  style={{
                    color: accentFilter === "all" ? colors.brand : colors.fg,
                    fontWeight: "600",
                    fontSize: 13,
                  }}
                >
                  Any accent
                </Text>
              </Pressable>
              {accentOptions.map((accent) => {
                const on = accentFilter === accent;
                return (
                  <Pressable
                    key={accent}
                    onPress={() => setAccentFilter(accent)}
                    accessibilityRole="button"
                    accessibilityState={{ selected: on }}
                    style={[
                      styles.filterChip,
                      {
                        backgroundColor: on ? colors.chipOn : colors.chipOff,
                        borderColor: on ? colors.brand : "transparent",
                      },
                    ]}
                  >
                    <Text style={{ color: on ? colors.brand : colors.fg, fontWeight: "600", fontSize: 13 }}>
                      {voiceAccentLabel(accent)}
                    </Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          ) : null}
          {!workspace.isLoading &&
          workspaceId &&
          !voicesQuery.isPending &&
          !listDegraded &&
          filteredBuiltin.length === 0 ? (
            <EmptyState
              colors={colors}
              title="No matches"
              body="No built-in voices match those filters."
            />
          ) : null}
          <View style={styles.list}>
            {filteredBuiltin.map((voice) => (
              <VoiceRow
                key={voice.id}
                voice={voice}
                selected={pickingForFace ? voice.id === faceBoundId : selectedId === voice.id}
                selectedHint={pickingForFace ? "on this Face" : "fallback"}
                colors={colors}
                onSelect={() => bindVoiceToFace(voice.id)}
                onFallback={bindFaceId ? undefined : () => void selectVoice(voice.id)}
                onPreview={() => void playPreview(voice.id)}
                previewLoading={previewLoadingId === voice.id}
                previewPlaying={previewId === voice.id}
              />
            ))}
          </View>
        </>
      )}

      {atCap ? (
        <Text style={[styles.help, { color: colors.muted }]}>
          You have one custom voice. Delete it to record a new one.
        </Text>
      ) : null}
    </Screen>
  );
}

function VoiceRow({
  voice,
  selected,
  selectedHint = "fallback",
  colors,
  custom,
  onSelect,
  onFallback,
  onPreview,
  previewLoading,
  previewPlaying,
  onDelete,
  deleting,
}: {
  voice: PlayVoiceOption;
  selected: boolean;
  selectedHint?: string;
  colors: AppColors;
  custom?: boolean;
  onSelect: () => void;
  onFallback?: () => void;
  onPreview?: () => void;
  previewLoading?: boolean;
  previewPlaying?: boolean;
  onDelete?: () => void;
  deleting?: boolean;
}) {
  return (
    <Pressable
      onPress={onSelect}
      accessibilityRole="button"
      accessibilityLabel={`${voice.name}${selected ? `, ${selectedHint}` : ""}. Tap to use on this Face.`}
      accessibilityState={{ selected }}
    >
      <GlassCard
        style={
          selected
            ? {
                borderWidth: 1.5,
                borderColor: colors.brand,
              }
            : undefined
        }
        contentStyle={styles.row}
      >
        <View style={styles.rowMain}>
          <View style={styles.rowTitleLine}>
            <Text
              style={{
                color: selected ? colors.brand : colors.fg,
                fontWeight: "700",
                fontSize: 15,
              }}
            >
              {voice.name}
              {selected ? ` · ${selectedHint}` : ""}
            </Text>
            {genderLabel(voice.gender) ? (
              <View style={[styles.miniBadge, { backgroundColor: colors.chipOff }]}>
                <Text style={{ color: colors.muted, fontSize: 11, fontWeight: "700" }}>
                  {genderLabel(voice.gender)}
                </Text>
              </View>
            ) : null}
            {!custom && voiceAccentLabel(voice.accent) ? (
              <View style={[styles.miniBadge, { backgroundColor: colors.chipOff }]}>
                <Text style={{ color: colors.muted, fontSize: 11, fontWeight: "700" }}>
                  {voiceAccentLabel(voice.accent)}
                </Text>
              </View>
            ) : null}
            {custom ? (
              <View style={[styles.miniBadge, { backgroundColor: colors.brandSoft }]}>
                <Text style={{ color: colors.brand, fontSize: 11, fontWeight: "700" }}>Custom</Text>
              </View>
            ) : null}
            {custom && cloneLanguageLabel(voice.language) ? (
              <View style={[styles.miniBadge, { backgroundColor: colors.chipOff }]}>
                <Text style={{ color: colors.muted, fontSize: 11, fontWeight: "700" }}>
                  {cloneLanguageLabel(voice.language)}
                </Text>
              </View>
            ) : null}
          </View>
          <Text numberOfLines={2} style={{ color: colors.muted, fontSize: 13, marginTop: 3 }}>
            {voice.description || (custom ? "Custom voice" : "Built-in voice")}
          </Text>
        </View>
        <View style={styles.rowActions}>
          {onPreview ? (
            <Pressable
              onPress={onPreview}
              disabled={previewLoading}
              hitSlop={8}
              accessibilityRole="button"
              accessibilityLabel={previewPlaying ? `Stop preview of ${voice.name}` : `Preview ${voice.name}`}
            >
              {previewLoading ? (
                <ActivityIndicator color={colors.brand} size="small" />
              ) : (
                <Text style={{ color: colors.brand, fontWeight: "600", fontSize: 13 }}>
                  {previewPlaying ? "Stop" : "Preview"}
                </Text>
              )}
            </Pressable>
          ) : null}
          {onFallback ? (
            <Pressable
              onPress={onFallback}
              hitSlop={8}
              accessibilityRole="button"
              accessibilityLabel={`Use ${voice.name} as fallback`}
            >
              <Text style={{ color: colors.muted, fontWeight: "600", fontSize: 13 }}>Fallback</Text>
            </Pressable>
          ) : null}
          {onDelete ? (
            <Pressable
              onPress={onDelete}
              disabled={deleting}
              hitSlop={8}
              accessibilityRole="button"
              accessibilityLabel={`Delete ${voice.name}`}
            >
              {deleting ? (
                <ActivityIndicator color={colors.danger} size="small" />
              ) : (
                <Text style={{ color: colors.danger, fontWeight: "600", fontSize: 13 }}>Delete</Text>
              )}
            </Pressable>
          ) : null}
        </View>
      </GlassCard>
    </Pressable>
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
  colors: AppColors;
  placeholder?: string;
  multiline?: boolean;
}) {
  return (
    <View style={{ marginTop: 12 }}>
      <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "700", marginBottom: 6 }}>
        {label}
      </Text>
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
  lead: { fontSize: 14, lineHeight: 20 },
  banner: {
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    lineHeight: 19,
    overflow: "hidden",
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  section: { fontSize: 13, fontWeight: "600", letterSpacing: -0.1 },
  useBtn: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  useBtnText: { color: "#fff", fontWeight: "700", fontSize: 13 },
  searchWrap: {
    paddingHorizontal: 12,
    paddingVertical: 4,
  },
  search: {
    paddingVertical: 10,
    fontSize: 16,
  },
  filterChip: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderWidth: 1,
  },
  featuredRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  list: { gap: 10 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 2,
  },
  rowMain: { flex: 1, minWidth: 0 },
  rowTitleLine: { flexDirection: "row", alignItems: "center", gap: 8, flexWrap: "wrap" },
  rowActions: { flexDirection: "row", alignItems: "center", gap: 14 },
  badge: {
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  miniBadge: {
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  panel: {
    paddingVertical: 4,
  },
  panelTitle: { fontSize: 16, fontWeight: "700", letterSpacing: -0.2 },
  help: { fontSize: 13, lineHeight: 18, marginTop: 4 },
  fileBtn: {
    marginTop: 14,
    borderRadius: 14,
    minHeight: 48,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 12,
  },
  switchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginTop: 16,
  },
  primaryBtn: {
    marginTop: 16,
    borderRadius: 14,
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  primaryBtnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
