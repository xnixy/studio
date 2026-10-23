import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  ActionSheetIOS,
  Alert,
  Dimensions,
  Keyboard,
  Platform,
  RefreshControl,
  ScrollView,
  View,
} from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { hapticError, hapticLight, hapticSuccess } from "@/src/lib/haptics";
import { keyboardOverlap } from "@/src/lib/keyboardOverlap";
import * as ImagePicker from "expo-image-picker";
import { prepareImageForUpload } from "@/src/lib/prepareImageUpload";
import { router, useFocusEffect, useLocalSearchParams, useNavigation } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { api, ApiError } from "@/src/api/client";
import type { PlayFace, PlayGeneration, PlayMode, PlayPlatform } from "@/src/api/types";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { sessionStorage } from "@/src/auth/storage";

const PLAY_IDEM_STORAGE = "studio.play.idempotency";
import { CreateComposer, type ComposerPicker } from "@/src/features/create/CreateComposer";
import { CreateEmptyState } from "@/src/features/create/CreateEmptyState";
import { CreateQualityHeader } from "@/src/features/create/CreateHeader";
import { ErrorState } from "@/src/components/States";
import { CreateThread, type ThreadItem } from "@/src/features/create/CreateThread";
import { UpgradeSheet } from "@/src/features/create/UpgradeSheet";
import { useCreateAssist } from "@/src/features/create/useCreateAssist";
import {
  composerTabForMode,
  durationOptionsForProvider,
  avatarPromptPreview,
  estimatePlayTokens,
  estimateTalkingDurationSeconds,
  generateModeForPrompt,
  isSeedance25Model,
  joinAvatarPrompt,
  snapDurationToChoices,
  splitAvatarPrompt,
  modeLabel,
  modeUsesAssist,
  promptHasQuotedSpeech,
  videoPromptFromDraft,
  normalizePlayMode,
} from "@/src/features/create/createConstants";
import { createCostLine } from "@/src/features/create/createCostLine";
import { type LocalRefChip } from "@/src/features/create/RefStrip";
import { alertError } from "@/src/lib/alerts";
import { ensurePushRegistration } from "@/src/hooks/usePushNotifications";
import { useOnlineStatus } from "@/src/hooks/useOnlineStatus";
import {
  SHOWCASE_EXAMPLES,
  type ShowcaseExample,
} from "@/src/lib/examples";
import { isVideoGeneration, resolveMediaUrl } from "@/src/lib/media";
import {
  advancedModelPool,
  faceClearedForModelMessage,
  modelSupportsFaceReference,
  pickAdvancedDefault,
  pickExtendModel,
  pickFastModel,
  pickModelForTier,
  supportsPlayExtend,
  tierForModel,
  type QualityTier,
} from "@/src/lib/qualityTier";
import { DEFAULT_BUILTIN_VOICE_ID, FALLBACK_VOICES, defaultBuiltinVoiceId, isClonedVoice, voicesForCreateBar } from "@/src/lib/stockVoices";
import { useAppColors } from "@/src/ui/theme";
import { useWorkspace } from "@/src/workspace/WorkspaceContext";
import { workspaceActionBlockedMessage } from "@/src/workspace/resolveWorkspaceId";

function clipFaceId(meta: Record<string, unknown> | undefined): string | null {
  if (!meta) return null;
  const a = meta.face_asset_id ?? meta.source_image_asset_id;
  return typeof a === "string" && a.length > 0 ? a : null;
}

function clipVoiceId(meta: Record<string, unknown> | undefined): string | null {
  if (!meta) return null;
  const v = meta.voice ?? meta.workspace_voice_id;
  return typeof v === "string" && v.trim() ? v.trim() : null;
}

export default function PlayScreen() {
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const qc = useQueryClient();
  const colors = useAppColors();
  const navigation = useNavigation();
  const online = useOnlineStatus();
  const params = useLocalSearchParams<{
    continue?: string;
    mode?: string;
    from?: string;
    starter?: string;
    voice?: string;
    /** Face library id from Faces → Use */
    face?: string;
    /** Showcase example id from Home / marketing (loads prompt + face). */
    example?: string;
    /** Prefill composer (retry / reuse from clip detail). */
    prompt?: string;
    /** Why the clip being retried failed, so the pre-flight can work from it. */
    retryError?: string;
  }>();
  const scrollRef = useRef<ScrollView>(null);
  /** Signature of the last inbound param batch (one-shot dedupe). */
  const lastInboundRef = useRef("");
  const defaultVoiceIdRef = useRef<string | null>(null);
  const defaultVoiceReadyRef = useRef(false);
  const voiceStorageLoadStartedRef = useRef(false);
  /**
   * Set when Create was opened from a failed clip. The pre-flight works from the
   * failure reason instead of re-sending the prompt that already failed, and it
   * clears once that conversation starts.
   */
  const retrySourceRef = useRef<{ kind: "retry"; prompt: string; error: string } | null>(null);
  /** Set by the composer so the draft card's Change action can focus the box. */
  const composerFocusRef = useRef<(() => void) | null>(null);
  /** Held across retries of the same draft so a timeout cannot double-charge. */
  const idempotencyKeyRef = useRef<string | null>(null);
  useEffect(() => {
    void AsyncStorage.getItem(PLAY_IDEM_STORAGE).then((stored) => {
      if (stored && !idempotencyKeyRef.current) idempotencyKeyRef.current = stored;
    });
  }, []);
  const bubbleCostRef = useRef("");
  const extendEngineForRef = useRef<string | null>(null);
  const skipStoredFaceRef = useRef(false);
  const insets = useSafeAreaInsets();
  /**
   * Lift the absolute composer by keyboard overlap. Native stack does not
   * move this overlay, so native-only left the field under the keyboard.
   */
  const [keyboardLift, setKeyboardLift] = useState(0);
  const [composerH, setComposerH] = useState(72);
  const threadRef = useRef<ThreadItem[]>([]);

  useEffect(() => {
    const showEvent = Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const hideEvent = Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide";
    const onShow = Keyboard.addListener(showEvent, (e) => {
      setKeyboardLift(keyboardOverlap(e.endCoordinates, Dimensions.get("window").height));
    });
    const onHide = Keyboard.addListener(hideEvent, () => {
      setKeyboardLift(0);
    });
    return () => {
      onShow.remove();
      onHide.remove();
    };
  }, []);

  const [mode, setMode] = useState<PlayMode>("avatar");
  const [qualityTier, setQualityTier] = useState<QualityTier>("fast");
  const [platform, setPlatform] = useState<PlayPlatform>("tiktok");
  const [modelId, setModelId] = useState("");
  const [faceId, setFaceId] = useState<string | null>(null);
  const [voice, setVoice] = useState("");
  // null = Auto: size clip from spoken line (Talking). Fixed values override.
  const [durationSeconds, setDurationSeconds] = useState<number | null>(null);
  const [resolution, setResolution] = useState<string>("720p");
  const [refChips, setRefChips] = useState<LocalRefChip[]>([]);
  const [continueFromId, setContinueFromId] = useState<string | null>(null);
  /** Ready clip we're extending (for banner + validation). */
  const [continueSource, setContinueSource] = useState<PlayGeneration | null>(null);
  const [prompt, setPrompt] = useState("");
  const promptRef = useRef("");
  promptRef.current = prompt;
  /**
   * True while the field holds sample or example text the user has not touched.
   * A sample written for Talking means nothing in Video, so switching mode
   * clears it. Anything the user typed themselves is kept.
   */
  const promptIsSampleRef = useRef(false);

  /** Fill from a sample, example, or marketing deep link. */
  const fillSamplePrompt = useCallback((text: string) => {
    promptIsSampleRef.current = true;
    setPrompt(text);
  }, []);

  /** Any edit the user makes, including reuse and retry, is theirs to keep. */
  const editPrompt = useCallback((text: string) => {
    promptIsSampleRef.current = false;
    setPrompt(text);
  }, []);
  const assist = useCreateAssist();
  const [thread, setThread] = useState<ThreadItem[]>([]);
  threadRef.current = thread;
  const [error, setError] = useState<string | null>(null);
  /** Local only. Never bind RefreshControl to query isFetching (sticks on tab focus refetch). */
  const [pullRefreshing, setPullRefreshing] = useState(false);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [picker, setPicker] = useState<ComposerPicker>("none");

  const clearContinue = useCallback(() => {
    setContinueFromId(null);
    setContinueSource(null);
  }, []);

  /** Pin a ready video as the next-shot source. Engine follows the source clip. */
  const beginContinue = useCallback(
    async (genId: string, gen?: PlayGeneration | null) => {
      const applyIdentity = (source: PlayGeneration) => {
        if (source.mode === "avatar" || source.mode === "lipsync" || source.mode === "video") {
          setMode(source.mode === "lipsync" ? "avatar" : source.mode);
        } else {
          setMode("video");
        }
        const face = clipFaceId(source.metadata);
        if (face) {
          skipStoredFaceRef.current = false;
          setFaceId(face);
          void sessionStorage.setActiveFaceId(face);
        }
        const nextVoice = clipVoiceId(source.metadata);
        if (nextVoice) setVoice(nextVoice);
      };
      setContinueFromId(genId);
      if (gen) applyIdentity(gen);
      else setMode("video");
      setPicker("none");
      setError(null);
      assist.reset();
      if (gen && (gen.status || "").toLowerCase() === "ready" && isVideoGeneration(gen)) {
        setContinueSource(gen);
        return;
      }
      try {
        const latest = await api.getPlayGeneration(genId);
        if ((latest.status || "").toLowerCase() !== "ready" || !isVideoGeneration(latest)) {
          clearContinue();
          alertError(
            "Cannot extend",
            "Extend needs a ready video clip. Wait until it finishes, then try again.",
          );
          return;
        }
        applyIdentity(latest);
        setContinueSource(latest);
      } catch {
        setContinueSource(null);
      }
    },
    [clearContinue, assist],
  );

  /**
   * Apply deep-links from Faces / Voices / Home.
   * Inbound params are one-shot: applied once, then cleared from the route.
   */
  const applyInboundSelection = useCallback(() => {
    const signature = JSON.stringify([
      params.continue ?? "",
      params.mode ?? "",
      params.starter ?? "",
      params.example ?? "",
      params.face ?? "",
      params.voice ?? "",
      params.prompt ?? "",
      params.retryError ?? "",
    ]);
    const fresh = signature !== lastInboundRef.current;
    lastInboundRef.current = signature;

    const cont = fresh && typeof params.continue === "string" ? params.continue.trim() : "";
    if (cont) {
      void beginContinue(cont);
    }

    const modeParam = fresh && typeof params.mode === "string" ? params.mode : "";
    if (
      modeParam === "avatar" ||
      modeParam === "video" ||
      modeParam === "lipsync" ||
      modeParam === "image"
    ) {
      setMode(modeParam === "lipsync" ? "avatar" : modeParam);
      if (modeParam === "image") {
        setPrompt((p) => avatarPromptPreview(p));
      }
    }

    const exampleId = fresh && typeof params.example === "string" ? params.example.trim() : "";
    const showcase = exampleId
      ? SHOWCASE_EXAMPLES.find((e) => e.id === exampleId)
      : undefined;
    if (showcase) {
      setMode(showcase.mode === "lipsync" ? "avatar" : showcase.mode);
      setPlatform(showcase.platform === "feed" ? "feed" : showcase.platform);
      fillSamplePrompt(showcase.prompt);
    } else {
      const starter = fresh && typeof params.starter === "string" ? params.starter.trim() : "";
      if (starter) {
        fillSamplePrompt(starter);
      }
    }

    const faceParam = fresh && typeof params.face === "string" ? params.face.trim() : "";
    if (faceParam) {
      skipStoredFaceRef.current = false;
      setFaceId(faceParam);
      void sessionStorage.setActiveFaceId(faceParam);
      // Talking is the default when bringing a face from Faces.
      if (!modeParam && !showcase) {
        setMode("avatar");
      }
    }

    const voiceParam = fresh && typeof params.voice === "string" ? params.voice.trim() : "";
    if (voiceParam) {
      setVoice(voiceParam);
    }

    // Retry / reuse from Clip detail: prefill composer without starting generate.
    const promptParam = fresh && typeof params.prompt === "string" ? params.prompt.trim() : "";
    if (promptParam && !showcase) {
      editPrompt(promptParam);
      const retryError =
        fresh && typeof params.retryError === "string" ? params.retryError.trim() : "";
      // Re-sending the prompt that just failed is the least useful thing to do.
      // Hand the reason to the pre-flight so it can offer a version that avoids it.
      retrySourceRef.current = retryError
        ? { kind: "retry", prompt: promptParam, error: retryError }
        : null;
    }

    // Consume the batch so identical future pushes still count as new, and stale
    // values never replay. Clearing re-runs this callback with empty params, which
    // safely lands in the storage fallbacks below.
    if (fresh && (cont || modeParam || exampleId || faceParam || voiceParam || promptParam || params.retryError)) {
      router.setParams({
        continue: undefined,
        mode: undefined,
        starter: undefined,
        example: undefined,
        face: undefined,
        voice: undefined,
        prompt: undefined,
        retryError: undefined,
      } as never);
    }

    // Fallback when navigated via tab switch after select-only (no params).
    // Do not revive a face the current Video engine just rejected.
    if (!faceParam) {
      void sessionStorage.getActiveFaceId().then((id) => {
        if (!id) return;
        setFaceId((current) => {
          if (skipStoredFaceRef.current) return current;
          return current || id;
        });
      });
    }
    if (!voiceStorageLoadStartedRef.current) {
      voiceStorageLoadStartedRef.current = true;
      const applyStoredToChip = !voiceParam;
      void sessionStorage.getActiveVoiceId().then((id) => {
        defaultVoiceReadyRef.current = true;
        defaultVoiceIdRef.current = id;
        if (applyStoredToChip && id) setVoice(id);
      });
    }
  }, [
    params.continue,
    params.mode,
    params.starter,
    params.example,
    params.face,
    params.voice,
    params.prompt,
    params.retryError,
    beginContinue,
    fillSamplePrompt,
    editPrompt,
  ]);

  useEffect(() => {
    applyInboundSelection();
  }, [applyInboundSelection]);

  useFocusEffect(
    useCallback(() => {
      applyInboundSelection();
      // Ensure face list is fresh so selectedFace resolves after Use.
      if (workspaceId) {
        void qc.invalidateQueries({ queryKey: ["play-faces", workspaceId] });
      }
    }, [applyInboundSelection, workspaceId, qc]),
  );

  useEffect(() => {
    setThread([]);
    setError(null);
  }, [workspaceId]);

  const modelsQuery = useQuery({
    queryKey: ["play-models", workspaceId],
    queryFn: () => api.listPlayModels(workspaceId),
    staleTime: 120_000,
  });

  const billingQuery = useQuery({
    queryKey: ["billing", workspaceId],
    queryFn: () => api.billingStatus(workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
  });

  const advancedUnlocked = billingQuery.data?.entitlements?.advanced_models === true
    || (billingQuery.data?.plan != null && billingQuery.data.plan !== "free");
  const upgradePlanLabel =
    billingQuery.data?.entitlements?.min_plan_for_advanced === "starter"
      ? "Starter"
      : "Starter";

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

  const lipsyncVoices = useMemo(() => {
    const rows = (voicesQuery.data?.voices || []).filter((v) => v.available !== false);
    if (rows.length) return rows;
    return FALLBACK_VOICES;
  }, [voicesQuery.data]);

  const pickerVoices = useMemo(() => {
    const hideClones = mode === "video" && !faceId;
    const list = hideClones
      ? lipsyncVoices.filter((v) => (v.source ?? "builtin") === "builtin")
      : lipsyncVoices;
    return voicesForCreateBar(list, voice);
  }, [lipsyncVoices, mode, voice, faceId]);

  const selectedVoice = lipsyncVoices.find((v) => v.id === voice) ?? null;
  const voiceIsCloned = Boolean(
    selectedVoice &&
      ((selectedVoice.source ?? "builtin") === "cloned" ||
        selectedVoice.source === "custom"),
  );
  const selectedVoiceLabel = useMemo(() => {
    if (!voice) return "Add your voice";
    const hit = lipsyncVoices.find((v) => v.id === voice);
    return hit?.name || voice;
  }, [lipsyncVoices, voice]);

  const modelsForMode = useMemo(() => {
    const all = modelsQuery.data ?? [];
    const filtered = all.filter((m) => m.enabled && m.modality === mode);
    return filtered.length ? filtered : all.filter((m) => m.enabled);
  }, [modelsQuery.data, mode]);

  const modelPool = useMemo(() => {
    if (continueFromId) {
      const extendable = modelsForMode.filter((m) => supportsPlayExtend(m.provider));
      return extendable.length ? extendable : modelsForMode;
    }
    return modelsForMode;
  }, [continueFromId, modelsForMode]);

  useEffect(() => {
    if (continueFromId) return;
    setQualityTier("fast");
  }, [mode, continueFromId]);

  useEffect(() => {
    if (!continueFromId) {
      extendEngineForRef.current = null;
      return;
    }
    if (extendEngineForRef.current === continueFromId) return;
    const gen = continueSource?.id === continueFromId ? continueSource : null;
    if (!gen) return;
    const pool = (modelsQuery.data ?? []).filter(
      (m) => m.modality === "video" && m.enabled && supportsPlayExtend(m.provider),
    );
    if (!pool.length) return;
    const metaProvider =
      typeof gen.metadata?.provider === "string" ? gen.metadata.provider : null;
    const pick = pickExtendModel(pool, {
      provider: gen.provider ?? metaProvider,
      model_id: gen.model_id,
    });
    if (!pick) return;
    extendEngineForRef.current = continueFromId;
    setModelId(pick.id);
    setQualityTier(tierForModel(pool, pick.id));
  }, [continueFromId, continueSource, modelsQuery.data]);

  useEffect(() => {
    if (!modelPool.length) return;
    if (continueFromId) {
      if (extendEngineForRef.current !== continueFromId) return;
      if (modelPool.some((m) => m.id === modelId)) return;
      return;
    }
    if (qualityTier === "advanced" && !advancedUnlocked) {
      setQualityTier("fast");
      return;
    }
    if (qualityTier === "fast") {
      const fast = pickModelForTier(modelPool, "fast");
      if (fast && modelId !== fast.id) setModelId(fast.id);
      return;
    }
    const adv = advancedModelPool(modelPool);
    if (adv.some((m) => m.id === modelId)) return;
    const pick = pickModelForTier(modelPool, "advanced", modelId);
    if (pick) setModelId(pick.id);
  }, [modelPool, modelId, qualityTier, advancedUnlocked, continueFromId]);

  const selectedFace = useMemo(
    () => (facesQuery.data ?? []).find((f) => f.id === faceId) ?? null,
    [facesQuery.data, faceId],
  );

  const selectedModel =
    modelPool.find((m) => m.id === modelId) || pickModelForTier(modelPool, qualityTier) || modelPool[0];
  const isSeedanceModel = selectedModel?.provider === "seedance";
  const needsDuration = mode !== "image";
  const canAttachRefs = mode !== "image";
  const isExtending = Boolean(continueFromId);
  const maxDuration = useMemo(() => {
    return selectedModel?.max_duration_seconds ?? 15;
  }, [selectedModel?.max_duration_seconds]);
  const durationChoices = useMemo(() => {
    const base = durationOptionsForProvider(selectedModel?.provider, {
      modelId: selectedModel?.id,
      maxDuration,
    });
    return base.filter((d) => d <= maxDuration);
  }, [selectedModel?.provider, selectedModel?.id, maxDuration]);
  const showResolution = needsDuration && isSeedanceModel;
  const refsUploading = refChips.some((c) => c.status === "uploading");
  const readyRefs = useMemo(
    () =>
      refChips.filter(
        (c): c is Extract<LocalRefChip, { status: "ready" }> => c.status === "ready",
      ),
    [refChips],
  );
  const readyRefIds = useMemo(() => readyRefs.map((c) => c.ref.id), [readyRefs]);
  // Positional, matching readyRefIds: a blank role still holds its slot.
  const readyRefRoles = useMemo(
    () => readyRefs.map((c) => (c.role ?? "").trim()),
    [readyRefs],
  );
  const effectiveDurationSeconds = useMemo(() => {
    if (!needsDuration) return null;
    if (durationSeconds != null) return durationSeconds;
    if (mode === "avatar") {
      return snapDurationToChoices(
        estimateTalkingDurationSeconds(prompt),
        durationChoices.length ? durationChoices : [5, 8, 10, 12, 15],
      );
    }
    return durationChoices[0] ?? 5;
  }, [needsDuration, durationSeconds, mode, prompt, durationChoices]);

  const costMode: PlayMode = normalizePlayMode(assist.draft?.kind || mode) || mode;
  const localQuoteTotal = useMemo(() => {
    const ready = refChips.filter((c) => c.status === "ready");
    const imgs = ready.filter((c) => c.kind === "image").length;
    const vids = ready.filter((c) => c.kind === "video").length;
    const auds = ready.filter((c) => c.kind === "audio").length;
    return estimatePlayTokens({
      mode: costMode,
      model: selectedModel,
      durationSeconds: needsDuration ? effectiveDurationSeconds : null,
      resolution: needsDuration ? resolution : null,
      batchCount: 1,
      generateAudio: true,
      returnLastFrame: false,
      refImageCount: canAttachRefs ? imgs : 0,
      refVideoCount: isSeedanceModel && canAttachRefs ? vids : 0,
      refAudioCount: isSeedanceModel && canAttachRefs ? auds : 0,
    }).total;
  }, [
    selectedModel,
    costMode,
    isSeedanceModel,
    needsDuration,
    effectiveDurationSeconds,
    resolution,
    canAttachRefs,
    refChips,
  ]);
  const quoteQuery = useQuery({
    queryKey: [
      "play",
      "quote",
      costMode,
      selectedModel?.id,
      prompt,
      assist.draft?.line,
      effectiveDurationSeconds,
      resolution,
      faceId,
      continueFromId,
      voiceIsCloned,
    ],
    queryFn: () =>
      api.playQuote({
        mode: costMode,
        model: selectedModel?.id,
        duration_seconds: needsDuration ? effectiveDurationSeconds : null,
        prompt,
        resolution: needsDuration ? resolution : null,
        count: 1,
        generate_audio: true,
        has_face: Boolean(faceId),
        continue_from: Boolean(continueFromId),
        cloned_voice: voiceIsCloned,
      }),
    enabled: Boolean(selectedModel),
    staleTime: 8_000,
  });
  const totalTokens = quoteQuery.data?.total ?? localQuoteTotal;

  useEffect(() => {
    // Keep manual picks valid for the engine; leave Auto alone.
    if (
      durationSeconds != null &&
      durationChoices.length &&
      !durationChoices.includes(durationSeconds as (typeof durationChoices)[number])
    ) {
      setDurationSeconds(snapDurationToChoices(durationSeconds, durationChoices));
    }
  }, [durationChoices, durationSeconds]);

  useEffect(() => {
    if (!isSeedanceModel && refChips.length) setRefChips([]);
  }, [isSeedanceModel]); // eslint-disable-line react-hooks/exhaustive-deps

  const scrollToEnd = useCallback(() => {
    requestAnimationFrame(() => scrollRef.current?.scrollToEnd({ animated: true }));
  }, []);

  useEffect(() => {
    if (thread.length === 0) return;
    scrollToEnd();
  }, [thread.length, scrollToEnd]);

  const pollUntilReady = useCallback(
    async (assetId: string) => {
      const fastAttempts = 48;
      const totalAttempts = 168; // keep going after soft timeout; worker also polls
      let softTimeout = false;
      for (let i = 0; i < totalAttempts; i++) {
        await new Promise((r) => setTimeout(r, i < fastAttempts ? 2500 : 5000));
        try {
          try {
            await api.pollVideoAsset(assetId);
          } catch {
            /* worker may own provider poll */
          }
          const mapped = await api.getPlayGeneration(assetId);
          const status = (mapped.status || "").toLowerCase();
          setThread((prev) =>
            prev.map((item) =>
              item.kind === "gen" && item.generation.id === assetId
                ? { ...item, generation: mapped }
                : item,
            ),
          );
          if (status === "ready") {
            setThread((prev) => [
              ...prev.filter(
                (x) =>
                  !(
                    x.kind === "system" &&
                    (x.id === `wait-${assetId}` ||
                      x.id === `timeout-${assetId}` ||
                      x.id === `nudge-${assetId}`)
                  ),
              ),
              {
                kind: "system",
                id: `done-${assetId}`,
                text: "Ready. Tap the card to open the clip.",
              },
            ]);
            await qc.invalidateQueries({ queryKey: ["play-generations", workspaceId] });
            return;
          }
          if (status === "failed" || status === "error" || status === "expired") {
            setThread((prev) =>
              // The card renders the failure with the provider's reason and the
              // Retry / Edit actions, so a matching error bubble under it just
              // said the same sentence twice.
              prev
                .filter(
                  (x) =>
                    !(
                      x.kind === "system" &&
                      (x.id === `wait-${assetId}` ||
                        x.id === `timeout-${assetId}` ||
                        x.id === `nudge-${assetId}` ||
                        x.id === `fail-${assetId}` ||
                        x.id.startsWith("wait-pending-"))
                    ),
                )
                .map((item) =>
                  item.kind === "gen" && item.generation.id === assetId
                    ? { ...item, generation: mapped }
                    : item,
                ),
            );
            return;
          }
          if (i === 4) {
            setThread((prev) => {
              if (prev.some((x) => x.id === `nudge-${assetId}`)) return prev;
              return [
                ...prev,
                { kind: "system", id: `nudge-${assetId}`, text: "Still rendering. Almost there." },
              ];
            });
          }
          if (!softTimeout && i >= fastAttempts - 1) {
            softTimeout = true;
            setThread((prev) => {
              if (prev.some((x) => x.id === `timeout-${assetId}`)) return prev;
              return [
                ...prev,
                {
                  kind: "system",
                  id: `timeout-${assetId}`,
                  text: "This is taking longer than usual. Still checking in the background…",
                },
              ];
            });
          }
        } catch {
          /* keep polling */
        }
      }
      setThread((prev) => {
        if (prev.some((x) => x.id === `timeout-${assetId}`)) return prev;
        return [
          ...prev,
          {
            kind: "system",
            id: `timeout-${assetId}`,
            text: "This is taking longer than usual. Check Library in a minute.",
          },
        ];
      });
    },
    [qc, workspaceId],
  );

  const generate = useMutation({
    mutationFn: async (vars: { text: string; mode: PlayMode; cost?: string }) => {
      const genMode = vars.mode === "lipsync" ? "avatar" : vars.mode;
      const text = vars.text;
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
      if (genMode === "avatar" && !faceId) {
        throw new ApiError("Add a face first.", 400);
      }
      if (genMode === "avatar" && !voice) {
        throw new ApiError("Add your voice or pick a built-in.", 400);
      }
      if (refsUploading) throw new ApiError("Wait for references to finish uploading.", 400);
      if (continueFromId) {
        if (!supportsPlayExtend(selectedModel?.provider)) {
          throw new ApiError("This engine cannot extend a clip.", 400);
        }
      }
      // Reused when a send errors out, so retrying the same draft dedupes
      // server-side instead of starting a second paid job. Cleared on success.
      if (!idempotencyKeyRef.current) {
        idempotencyKeyRef.current = `mob-${Date.now().toString(36)}-${Math.random()
          .toString(36)
          .slice(2, 12)}`;
        void AsyncStorage.setItem(PLAY_IDEM_STORAGE, idempotencyKeyRef.current);
      }
      return api.playGenerate({
        client_request_id: idempotencyKeyRef.current,
        workspace_id: workspaceId,
        mode: genMode,
        platform,
        prompt: text,
        model: assist.draft?.model || modelId || null,
        face_asset_id: allowsFace ? faceId : null,
        // Talking and Scene: Seedance audio_urls after house TTS.
        voice:
          genMode === "avatar"
            ? voice || null
            : genMode === "video"
              ? voice || DEFAULT_BUILTIN_VOICE_ID
              : null,
        // null = Auto (backend sizes Talking from spoken line; video uses engine default).
        duration_seconds:
          genMode === "image"
            ? null
            : (assist.draft?.duration_seconds ??
              (genMode === "avatar" ? effectiveDurationSeconds : durationSeconds)),
        resolution: genMode === "image" ? null : assist.draft?.resolution || resolution,
        generate_audio: genMode === "image" ? null : true,
        return_last_frame: null,
        reference_asset_ids: canAttachRefs ? readyRefIds : [],
        ...(canAttachRefs && readyRefRoles.some((role) => role)
          ? { reference_roles: readyRefRoles }
          : {}),
        count: 1,
        continue_from_asset_id:
          continueFromId && supportsPlayExtend(selectedModel?.provider) ? continueFromId : null,
      });
    },
    onMutate: (vars) => {
      const text = vars.text;
      const lastUser = [...threadRef.current].reverse().find((i) => i.kind === "user");
      const alreadyUser = lastUser?.kind === "user" && lastUser.text === text;
      const userId = `u-${Date.now()}`;
      setThread((prev) => [
        ...prev,
        ...(alreadyUser
          ? []
          : [{ kind: "user" as const, id: userId, text, mode: vars.mode, platform, cost: vars.cost ?? bubbleCostRef.current }]),
        {
          kind: "system",
          id: `wait-pending-${userId}`,
          text: continueFromId
            ? "Extending previous clip…"
            : "Generating…",
        },
      ]);
      setPrompt("");
      setError(null);
    },
    onSuccess: async (res) => {
      void hapticSuccess();
      // This draft landed; the next send is a new clip, not a retry.
      idempotencyKeyRef.current = null;
      void AsyncStorage.removeItem(PLAY_IDEM_STORAGE);
      // Without this the settled draft stays settled and every later send would
      // skip the pre-flight entirely.
      assist.reset();
      const list =
        res.generations && res.generations.length > 0 ? res.generations : [res.generation];
      clearContinue();
      setThread((prev) => {
        const withoutPending = prev.filter((x) => !x.id.startsWith("wait-pending-"));
        const cards: ThreadItem[] = list.map((gen, i) => ({
          kind: "gen" as const,
          id: `g-${gen.id}`,
          generation: gen,
          note: i === 0 ? res.message : null,
        }));
        const waits: ThreadItem[] = list.map((gen) => ({
          kind: "system" as const,
          id: `wait-${gen.id}`,
          text: "Working on it…",
        }));
        return [...withoutPending, ...cards, ...waits];
      });
      for (const gen of list) {
        void pollUntilReady(gen.id);
      }
      await qc.invalidateQueries({ queryKey: ["play-generations", workspaceId] });
      await qc.invalidateQueries({ queryKey: ["billing", workspaceId] });
      void ensurePushRegistration();
    },
    onError: (e, vars) => {
      void hapticError();
      if (!promptRef.current.trim()) setPrompt(vars.text);
      if (e instanceof ApiError && e.code === "plan_advanced_required") {
        setUpgradeOpen(true);
      }
      let msg = e instanceof ApiError ? e.message : "Generation failed.";
      if (e instanceof ApiError && e.status === 402) {
        msg = `${msg} Open Billing to add credits or upgrade.`;
      }
      setError(msg);
      // Chat only (no alert) so the same line is not shown twice.
      setThread((prev) => {
        const cleaned = prev.filter(
          (x) => !x.id.startsWith("wait-pending-") && !(x.kind === "system" && x.tone === "error"),
        );
        // Drop a trailing identical error if Strict Mode double-fired.
        const last = cleaned[cleaned.length - 1];
        if (last?.kind === "system" && last.text === msg) {
          return cleaned;
        }
        return [
          ...cleaned,
          { kind: "system" as const, id: `err-${Date.now()}`, text: msg, tone: "error" as const },
        ];
      });
    },
  });

  /** Put a prior prompt back in the field (copy/edit flow). */
  const reusePrompt = useCallback((text: string) => {
    editPrompt(text);
    setError(null);
    void hapticLight();
    requestAnimationFrame(() => scrollToEnd());
  }, [scrollToEnd, editPrompt]);

  /** Re-run a failed (or any) generation with the same prompt and current settings. */
  const retryGeneration = useCallback(
    (gen: PlayGeneration) => {
      const text = (gen.prompt || "").trim();
      if (!text) {
        setError("Nothing to retry. Write a prompt first.");
        return;
      }
      const m = normalizePlayMode(gen.mode) || mode;
      if (m) {
        setMode(m);
      }
      if (gen.platform === "feed" || gen.platform === "tiktok" || gen.platform === "reels" || gen.platform === "shorts") {
        setPlatform(gen.platform);
      }
      const mid =
        gen.model_id ||
        (typeof gen.metadata?.model_id === "string" ? gen.metadata.model_id : null);
      if (mid) setModelId(mid);
      const face =
        typeof gen.metadata?.face_asset_id === "string" ? gen.metadata.face_asset_id : null;
      if (face) setFaceId(face);
      const v = typeof gen.metadata?.voice === "string" ? gen.metadata.voice : null;
      if (v) setVoice(v);
      setPrompt(text);
      setError(null);
      // Send on next tick so mode/face state settle.
      setTimeout(() => {
        generate.mutate({
          text,
          mode: m,
        });
      }, 50);
    },
    [generate, mode],
  );

  /** Poll once and update the card (stuck processing or failed that may now be ready). */
  const refreshGenerationStatus = useCallback(
    async (genId: string) => {
      void hapticLight();
      try {
        try {
          await api.pollVideoAsset(genId);
        } catch {
          /* poll optional */
        }
        const mapped = await api.getPlayGeneration(genId);
        setThread((prev) =>
          prev.map((item) =>
            item.kind === "gen" && item.generation.id === genId
              ? { ...item, generation: mapped }
              : item,
          ),
        );
        const st = (mapped.status || "").toLowerCase();
        if (st === "ready") {
          void hapticSuccess();
          setThread((prev) => [
            ...prev.filter((x) => x.id !== `wait-${genId}` && x.id !== `fail-${genId}`),
            {
              kind: "system",
              id: `ready-${genId}-${Date.now()}`,
              text: "Clip is ready.",
            },
          ]);
        } else if (st === "failed" || st === "error" || st === "expired") {
          // Card already carries the reason; nothing to add under it.
        } else {
          // Still processing: keep polling in background.
          void pollUntilReady(genId);
        }
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Could not refresh status.");
      }
    },
    [pollUntilReady],
  );

  const uploadRefFile = useCallback(
    async (kind: "image" | "video" | "audio", uri: string, name: string, mime: string) => {
      if (!workspaceId) return;
      const localId = `local-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setRefChips((prev) => [
        ...prev,
        { localId, status: "uploading", kind, previewUri: kind === "image" ? uri : undefined },
      ]);
      try {
        let fileUri = uri;
        let fileName = name;
        let fileType = mime;
        if (kind === "image") {
          const prepared = await prepareImageForUpload(
            { uri, fileName: name, mimeType: mime },
            { maxWidth: 1600, namePrefix: "ref" },
          );
          fileUri = prepared.uri;
          fileName = prepared.name;
          fileType = prepared.type;
        }
        const ref = await api.uploadPlayRef(
          workspaceId,
          { uri: fileUri, name: fileName, type: fileType },
          kind,
        );
        setRefChips((prev) =>
          prev.map((c) =>
            c.localId === localId
              ? { localId, status: "ready", kind, ref, previewUri: kind === "image" ? fileUri : undefined }
              : c,
          ),
        );
      } catch (e) {
        const msg = e instanceof ApiError ? e.message : "Upload failed";
        setRefChips((prev) =>
          prev.map((c) =>
            c.localId === localId ? { localId, status: "error", kind, message: msg } : c,
          ),
        );
        alertError("Could not add reference", msg);
      }
    },
    [workspaceId],
  );

  const pickRef = useCallback(
    async (kind: "image" | "video" | "audio") => {
      if (kind === "audio") {
        alertError(
          "Audio reference",
          "Add audio references from the web app at example.com. Here, use a photo or video reference.",
        );
        return;
      }
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        alertError(
          "Photos access",
          "Allow photo library access in Settings to add a reference.",
        );
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        // SDK 57: MediaTypeOptions is deprecated; use the string-array form.
        mediaTypes: kind === "video" ? ["videos"] : ["images"],
        quality: 0.9,
        videoMaxDuration: 15,
      });
      if (result.canceled || !result.assets?.[0]) return;
      const asset = result.assets[0];
      const uri = asset.uri;
      const name =
        asset.fileName ||
        (kind === "video" ? `ref-${Date.now()}.mp4` : `ref-${Date.now()}.jpg`);
      const mime =
        asset.mimeType ||
        (kind === "video" ? "video/mp4" : "image/jpeg");
      await uploadRefFile(kind, uri, name, mime);
    },
    [uploadRefFile],
  );

  const openAttachSheet = useCallback(() => {
    if (!canAttachRefs) return;
    const options = ["Photo", "Video", "Cancel"];
    if (Platform.OS === "ios") {
      ActionSheetIOS.showActionSheetWithOptions(
        {
          options,
          cancelButtonIndex: 2,
          title: "Add reference",
          message: "These materials go with your prompt.",
        },
        (idx) => {
          if (idx === 0) void pickRef("image");
          if (idx === 1) void pickRef("video");
        },
      );
    } else {
      Alert.alert("Add reference", undefined, [
        { text: "Photo", onPress: () => void pickRef("image") },
        { text: "Video", onPress: () => void pickRef("video") },
        { text: "Cancel", style: "cancel" },
      ]);
    }
  }, [canAttachRefs, pickRef]);

  /**
   * Pre-flight turn. Talks the clip through before any credits move. A down
   * helper must not spend. The next send retries Assist.
   */
  const runAssist = useCallback(
    async (text: string) => {
      if (!workspaceId) return null;
      const { scene, line } = splitAvatarPrompt(text);
      const chip = text.startsWith("kind:");
      const thinkingId = `thinking-${Date.now()}`;
      setThread((prev) => [...prev, { kind: "thinking" as const, id: thinkingId }]);
      const clipBucket = mode === "image" ? "image" : "avatar";
      const turn = await assist.send({
        workspaceId,
        mode: clipBucket,
        // Extend proposes the next beat, so the planner needs the shot it follows.
        source: continueFromId
          ? { kind: "continue" as const, prompt: continueSource?.prompt || "" }
          : retrySourceRef.current,
        draft: {
          scene: chip
            ? assist.draft?.scene ?? ""
            : mode === "image"
              ? text
              : scene || assist.draft?.scene || "",
          line: chip ? assist.draft?.line ?? "" : mode === "image" ? "" : line || assist.draft?.line || "",
          duration_seconds: durationSeconds,
          voice,
          kind: assist.draft?.kind ?? null,
        },
        userText: text,
      });
      retrySourceRef.current = null;
      setThread((prev) => {
        const rest = prev.filter((i) => i.id !== thinkingId);
        if (turn.reply) {
          rest.push({
            kind: "system" as const,
            id: `assist-${Date.now()}`,
            text: turn.reply,
            tone: "chat" as const,
          });
        }
        if (turn.draft && (turn.draft.line.trim() || turn.draft.scene.trim())) {
          // The draft is a thing to read, not a form to fill in, so it lands in
          // the thread rather than silently rewriting the box.
          rest.push({
            kind: "draft" as const,
            id: `draft-${Date.now()}`,
            line: turn.draft.line,
            scene: turn.draft.scene,
            summary: turn.summary,
            options: turn.options,
          });
        }
        return rest;
      });
      if (!turn.reply && !turn.draft) {
        setThread((prev) => [
          ...prev.filter((i) => i.id !== thinkingId),
          {
            kind: "system" as const,
            id: `assist-err-${Date.now()}`,
            text: "Could not work that out. Send again. Nothing was spent.",
            tone: "chat" as const,
          },
        ]);
      }
      if (turn.draft) {
        const kind = turn.draft.kind === "lipsync" ? "avatar" : turn.draft.kind;
        if (kind && mode !== "image") setMode(kind);
        setPrompt(
          kind === "avatar" || (!kind && mode !== "image")
            ? joinAvatarPrompt(turn.draft.scene, turn.draft.line)
            : turn.draft.scene || turn.draft.line,
        );
        if (turn.draft.model) setModelId(turn.draft.model);
        if (turn.draft.resolution) setResolution(turn.draft.resolution);
        if (turn.draft.duration_seconds) setDurationSeconds(turn.draft.duration_seconds);
        if (turn.draft.platform === "feed") setPlatform("feed");
      }
      return turn;
    },
    [assist, workspaceId, mode, durationSeconds, voice, continueFromId, continueSource],
  );

  const startGenerate = (text: string, draftKind: PlayMode | null | undefined) => {
    if (!workspaceId) {
      void workspace.refresh();
      setError(
        workspaceActionBlockedMessage({
          isLoading: workspace.isLoading,
          error: workspace.error,
        }),
      );
      return;
    }
    const genMode = generateModeForPrompt({
      tabMode: mode,
      draftKind: draftKind ?? null,
      prompt: text,
      hasFace: Boolean(faceId),
    });
    const fromDraft = Boolean(draftKind);
    const genText =
      genMode === "video"
        ? videoPromptFromDraft(fromDraft ? assist.draft : null, text)
        : text;
    if (genMode === "avatar" && !faceId) {
      setPicker("face");
      alertError("Add a face", "Tap the face button next to the prompt, then choose one.");
      return;
    }
    if (genMode === "avatar" && !voice) {
      setPicker("voice");
      alertError("Add your voice", "Tap the mic, then record yours or pick a built-in.");
      return;
    }
    generate.mutate({
      text: genText,
      mode: genMode,
      cost: bubbleCostRef.current,
    });
  };

  const onSend = () => {
    const text = prompt.trim();
    if (!text || generate.isPending || assist.pending || refsUploading) return;
    if (!online) {
      setError("You're offline. Connect, then send.");
      return;
    }
    if (!workspaceId) {
      void workspace.refresh();
      setError(
        workspaceActionBlockedMessage({
          isLoading: workspace.isLoading,
          error: workspace.error,
        }),
      );
      return;
    }
    void hapticLight();
    // Kind is confirmed on the draft card. Face and voice wait until we know it.
    if (modeUsesAssist(mode) && !assist.ready) {
      setThread((prev) => [
        ...prev,
        { kind: "user" as const, id: `u-${Date.now()}`, text, mode, platform, cost: bubbleCostRef.current },
      ]);
      void (async () => {
        const turn = await runAssist(text);
        if (!turn) return;
        if (turn.draft) return;
      })();
      return;
    }
    startGenerate(text, assist.draft?.kind ?? null);
  };

  const startNew = useCallback(() => {
    void hapticLight();
    setThread([]);
    setPrompt("");
    setError(null);
    assist.reset();
    clearContinue();
    setPicker("none");
    idempotencyKeyRef.current = null;
    void AsyncStorage.removeItem(PLAY_IDEM_STORAGE);
    setMode((prev) => (prev === "image" ? "image" : "avatar"));
  }, [clearContinue, assist]);

  const prevVoiceRef = useRef(voice);
  const prevFaceRef = useRef(faceId);
  useEffect(() => {
    if (prevVoiceRef.current !== voice) {
      prevVoiceRef.current = voice;
      idempotencyKeyRef.current = null;
      void AsyncStorage.removeItem(PLAY_IDEM_STORAGE);
    }
  }, [voice]);
  useEffect(() => {
    if (prevFaceRef.current !== faceId) {
      prevFaceRef.current = faceId;
      idempotencyKeyRef.current = null;
      void AsyncStorage.removeItem(PLAY_IDEM_STORAGE);
    }
  }, [faceId]);

  useEffect(() => {
    if (mode === "video" && !faceId && voiceIsCloned) {
      setVoice(defaultBuiltinVoiceId(lipsyncVoices));
    }
  }, [mode, voiceIsCloned, faceId]);

  useEffect(() => {
    if (lipsyncVoices.length === 0) return;
    const inList = (id: string | null | undefined) =>
      Boolean(id && lipsyncVoices.some((v) => v.id === id));
    const bound = selectedFace?.bound_voice_id?.trim() || "";
    if (inList(bound) && !continueFromId) {
      if (voice !== bound) setVoice(bound);
      return;
    }
    if (!defaultVoiceReadyRef.current) return;
    let stored = defaultVoiceIdRef.current;
    const storedRow = lipsyncVoices.find((v) => v.id === stored);
    const storedIsClone = Boolean(
      storedRow &&
        ((storedRow.source ?? "builtin") === "cloned" || storedRow.source === "custom"),
    );
    if (mode === "video" && !faceId && storedIsClone) {
      stored = null;
    }
    if (inList(stored)) {
      if (voice !== stored) setVoice(stored);
      return;
    }
    if (inList(voice)) return;
    if (stored) {
      const fallback = defaultBuiltinVoiceId(lipsyncVoices) || "";
      if (fallback && voice !== fallback) setVoice(fallback);
      return;
    }
    const clone = lipsyncVoices.find(
      (v) => (v.source ?? "builtin") === "cloned" || v.source === "custom",
    );
    const next = clone?.id || defaultBuiltinVoiceId(lipsyncVoices) || "";
    if (!next) return;
    setVoice(next);
    defaultVoiceIdRef.current = next;
    void sessionStorage.setActiveVoiceId(next);
  }, [lipsyncVoices, voice, selectedFace, mode, faceId, continueFromId]);

  const selectQualityTier = useCallback(
    (tier: QualityTier) => {
      if (tier === "advanced" && !advancedUnlocked) {
        setUpgradeOpen(true);
        return;
      }
      setQualityTier(tier);
      if (tier === "fast") {
        const fast = pickFastModel(modelPool);
        if (fast) setModelId(fast.id);
      } else {
        const keep =
          advancedModelPool(modelPool).some((m) => m.id === modelId) &&
          tierForModel(modelPool, modelId) === "advanced"
            ? modelId
            : pickAdvancedDefault(modelPool)?.id;
        if (keep) setModelId(keep);
      }
    },
    [modelPool, modelId, advancedUnlocked],
  );

  useLayoutEffect(() => {
    const still = composerTabForMode(mode) === "still";
    navigation.setOptions({
      title: still ? "Still" : "Clip",
      headerTitle: undefined,
      headerRight: still
        ? () => (
            <CreateQualityHeader
              colors={colors}
              qualityTier={qualityTier}
              onQualityTierChange={selectQualityTier}
            />
          )
        : () => null,
    });
  }, [navigation, colors, mode, qualityTier, selectQualityTier]);

  /** Reload faces, models, and refresh any generation cards still in the thread. */
  const refreshCreate = useCallback(async () => {
    setPullRefreshing(true);
    // Cap spinner so a hung poll never freezes the header refresh control.
    const safety = setTimeout(() => setPullRefreshing(false), 12_000);
    try {
      await Promise.all([
        modelsQuery.refetch(),
        facesQuery.refetch(),
        workspaceId
          ? qc.invalidateQueries({ queryKey: ["play-generations", workspaceId] })
          : Promise.resolve(),
      ]);

      const genIds = threadRef.current
        .filter((item): item is Extract<ThreadItem, { kind: "gen" }> => item.kind === "gen")
        .map((item) => item.generation.id);

      if (genIds.length) {
        const updates = await Promise.all(
          genIds.map(async (id) => {
            try {
              try {
                await api.pollVideoAsset(id);
              } catch {
                /* optional */
              }
              return await api.getPlayGeneration(id);
            } catch {
              return null;
            }
          }),
        );
        const byId = new Map(
          updates.filter((u): u is NonNullable<typeof u> => Boolean(u)).map((u) => [u.id, u]),
        );
        setThread((prev) =>
          prev.map((item) => {
            if (item.kind !== "gen") return item;
            const next = byId.get(item.generation.id);
            return next ? { ...item, generation: next } : item;
          }),
        );
      }
    } finally {
      clearTimeout(safety);
      setPullRefreshing(false);
    }
  }, [modelsQuery, facesQuery, workspaceId, qc]);

  const loadExample = useCallback(
    async (ex: ShowcaseExample) => {
      setMode(ex.mode);
      setPlatform(ex.platform === "feed" ? "feed" : ex.platform);
      fillSamplePrompt(ex.prompt);
      setError(null);
      setPicker("none");
    },
    [],
  );

  const exampleDeepLinkRef = useRef<string | null>(null);
  useEffect(() => {
    const exampleId = typeof params.example === "string" ? params.example.trim() : "";
    if (!exampleId || !workspaceId) return;
    if (exampleDeepLinkRef.current === exampleId) return;
    const showcase = SHOWCASE_EXAMPLES.find((e) => e.id === exampleId);
    if (!showcase) return;
    exampleDeepLinkRef.current = exampleId;
    void loadExample(showcase);
  }, [params.example, workspaceId, loadExample]);

  const continuePoster = resolveMediaUrl(
    continueSource?.poster_url ||
      (typeof continueSource?.metadata?.poster_url === "string"
        ? continueSource.metadata.poster_url
        : null) ||
      continueSource?.url ||
      null,
  );

  const needsFace = mode === "avatar";
  // Video face only when the engine supports identity refs (not Veo Lite).
  const videoFaceOk = mode === "video" && modelSupportsFaceReference(selectedModel);
  const allowsFace = needsFace || videoFaceOk;

  // Drop face when the selected Video engine cannot take identity refs.
  // Only the live selection: the stored active face is the shared preference Talking
  // and Faces, and picking a Video model is no reason to lose it.
  useEffect(() => {
    if (mode !== "video" || !faceId) {
      if (mode === "avatar") skipStoredFaceRef.current = false;
      return;
    }
    if (modelSupportsFaceReference(selectedModel)) {
      skipStoredFaceRef.current = false;
      return;
    }
    skipStoredFaceRef.current = true;
    setFaceId(null);
    setError(faceClearedForModelMessage(selectedModel?.label));
    setPicker((p) => (p === "face" ? "none" : p));
  }, [mode, modelId, faceId, selectedModel]);

  const talkingDraft = useMemo(() => splitAvatarPrompt(prompt), [prompt]);
  const boundVoiceId = selectedFace?.bound_voice_id?.trim() || "";
  const effectiveVoiceId =
    boundVoiceId && lipsyncVoices.some((v) => v.id === boundVoiceId) ? boundVoiceId : voice;
  const effectiveVoice = lipsyncVoices.find((v) => v.id === effectiveVoiceId);
  const effectiveIsClone = Boolean(effectiveVoice && isClonedVoice(effectiveVoice));
  const talkingLine = talkingDraft.line.trim() || assist.draft?.line?.trim() || "";
  const sceneSpeechSource = [prompt, assist.draft?.line, assist.draft?.scene]
    .filter(Boolean)
    .join(" ");
  const costSpeech =
    normalizePlayMode(assist.draft?.kind) === "avatar"
      ? assist.draft?.line || prompt
      : assist.draft?.kind === "video"
        ? [assist.draft.scene, assist.draft.line].filter(Boolean).join(" ")
        : prompt;
  const costLine = createCostLine({
    mode: costMode,
    prompt: costSpeech,
    totalCredits: totalTokens,
    durationSeconds,
    autoSeconds: effectiveDurationSeconds,
    needsDuration,
    isExtending,
    isSeedanceModel,
    isSeedance25: isSeedance25Model(selectedModel?.id),
    resolution,
    showResolution,
    generateAudio: true,
    batchCount: 1,
    hasModel: Boolean(selectedModel),
    refsUploading,
    clonedVoice:
      effectiveIsClone &&
      ((mode === "avatar" && Boolean(talkingLine)) ||
        (mode === "video" && Boolean(faceId) && promptHasQuotedSpeech(sceneSpeechSource))),
    voiceoverSeconds: effectiveDurationSeconds ?? estimateTalkingDurationSeconds(costSpeech),
  });
  const bubbleCost = [modeLabel(costMode), costLine].filter(Boolean).join(" · ");
  bubbleCostRef.current = bubbleCost;

  // Native stack header holds Clip | Still. Composer floats over the thread like iMessage.
  const composerPadBottom = keyboardLift > 0 ? 8 : Math.max(insets.bottom, 8);
  const threadBottomPad = composerH + 8;

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }} collapsable={false}>
      <ScrollView
        ref={scrollRef}
        style={{ flex: 1 }}
        contentContainerStyle={{
          paddingHorizontal: 14,
          paddingTop: 12,
          paddingBottom: threadBottomPad,
          gap: 10,
          flexGrow: 1,
        }}
        contentInsetAdjustmentBehavior="automatic"
        automaticallyAdjustsScrollIndicatorInsets
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="interactive"
        scrollEventThrottle={16}
        refreshControl={
          <RefreshControl
            refreshing={pullRefreshing}
            onRefresh={() => void refreshCreate()}
            tintColor={colors.brand}
          />
        }
      >
        {modelsQuery.isError ? (
          <ErrorState
            colors={colors}
            message="Could not load models. Pull to retry."
            onRetry={() => void modelsQuery.refetch()}
          />
        ) : null}
        {facesQuery.isError ? (
          <ErrorState
            colors={colors}
            message="Could not load faces. Pull to retry."
            onRetry={() => void facesQuery.refetch()}
          />
        ) : null}
        {thread.length === 0 ? (
          <CreateEmptyState colors={colors} mode={mode} />
        ) : (
          <CreateThread
            colors={colors}
            thread={thread}
            onStartNew={startNew}
            onExtend={(id, gen) => void beginContinue(id, gen)}
            onChooseOption={(value) => void runAssist(value)}
            onGenerateDraft={() => onSend()}
            onEditDraft={() => composerFocusRef.current?.()}
            generatePending={generate.isPending}
            onReusePrompt={reusePrompt}
            onRetry={retryGeneration}
            onRefreshStatus={(id) => void refreshGenerationStatus(id)}
          />
        )}
      </ScrollView>

      <View
        onLayout={(e) => setComposerH(e.nativeEvent.layout.height)}
        pointerEvents="box-none"
        style={{ position: "absolute", left: 0, right: 0, bottom: 0 }}
      >
      <CreateComposer
        colors={colors}
        padBottom={composerPadBottom}
        keyboardLift={keyboardLift}
        error={error}
        mode={mode}
        isExtending={isExtending}
        assistPending={assist.pending}
        assistReady={assist.ready || !modeUsesAssist(mode)}
        picker={picker}
        selectedVoiceLabel={selectedVoiceLabel}
        lipsyncVoices={pickerVoices}
        voice={voice}
        faces={facesQuery.data ?? []}
        selectedFace={selectedFace}
        needsFace={
          assist.ready && normalizePlayMode(assist.draft?.kind) === "avatar"
        }
        allowsFace={allowsFace}
        prompt={prompt}
        generatePending={generate.isPending}
        offline={!online}
        canAttachRefs={canAttachRefs}
        refsUploading={refsUploading}
        refChips={refChips}
        continuePoster={continuePoster}
        onToggleVoicePicker={() => {
          void hapticLight();
          setPicker((p) => (p === "voice" ? "none" : "voice"));
        }}
        onToggleFacePicker={() => {
          void hapticLight();
          setPicker((p) => (p === "face" ? "none" : "face"));
        }}
        onSelectVoice={(id) => {
          setVoice(id);
          const bound = selectedFace?.bound_voice_id?.trim() || "";
          if (!bound || !lipsyncVoices.some((v) => v.id === bound)) {
            defaultVoiceIdRef.current = id;
            defaultVoiceReadyRef.current = true;
            void sessionStorage.setActiveVoiceId(id);
          }
          setPicker("none");
          void hapticLight();
        }}
        onSelectFace={(id) => {
          const next = !needsFace && faceId === id ? null : id;
          setFaceId(next);
          if (next) {
            void sessionStorage.setActiveFaceId(next);
            const face = (facesQuery.data ?? []).find((f) => f.id === next);
            const bound = face?.bound_voice_id?.trim() || "";
            if (bound && lipsyncVoices.some((v) => v.id === bound)) {
              setVoice(bound);
            } else {
              const stored = defaultVoiceIdRef.current;
              const storedOk = Boolean(stored && lipsyncVoices.some((v) => v.id === stored));
              const clone = lipsyncVoices.find(
                (v) => (v.source ?? "builtin") === "cloned" || v.source === "custom",
              );
              const nextVoice =
                (storedOk ? stored : null) ||
                clone?.id ||
                defaultBuiltinVoiceId(lipsyncVoices) ||
                "";
              if (nextVoice) setVoice(nextVoice);
            }
          } else void sessionStorage.clearActiveFaceId();
          setPicker("none");
          void hapticLight();
        }}
        onClearContinue={clearContinue}
        onPromptChange={editPrompt}
        onSend={onSend}
        onOpenAttach={openAttachSheet}
        onRemoveRef={(localId) => setRefChips((prev) => prev.filter((c) => c.localId !== localId))}
        onRefRoleChange={(localId, role) =>
          setRefChips((prev) =>
            prev.map((c) =>
              c.localId === localId && c.status === "ready" ? { ...c, role } : c,
            ),
          )
        }
        registerFocus={(focus) => {
          composerFocusRef.current = focus;
        }}
        onFieldFocus={() => {
          setPicker("none");
          requestAnimationFrame(() => scrollToEnd());
        }}
      />
      </View>

      <UpgradeSheet
        visible={upgradeOpen}
        onClose={() => setUpgradeOpen(false)}
        colors={colors}
        planLabel={upgradePlanLabel}
      />
    </View>
  );
}
