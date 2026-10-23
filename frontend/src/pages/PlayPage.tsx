import {
  ArrowRight,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { useWorkspace } from "../workspace";
import { workspaceActionBlockedMessage } from "../lib/accountSession";
import { CreateThread } from "../features/play/CreateThread";
import { ModelQualityPicker } from "../features/play/ModelQualityPicker";
import { SHOWCASE_EXAMPLES } from "../marketing/examples";
import type { PlayFace, PlayGeneration, PlayMode, PlayModelOption, PlayPlatform } from "../types";
import {
  BUILTIN_VOICES,
  DEFAULT_BUILTIN_VOICE_ID,
  defaultBuiltinVoiceId,
  isBuiltinVoice,
  isClonedVoice,
  sortPlayVoices,
  voiceGenderLabel,
  voicesForCreateBar,
} from "../features/play/voices";
import { cn } from "../lib/cn";
import { isSignedMediaUrlExpired, resolveMediaUrl } from "../lib/mediaUrl";
import {
  avatarPromptPreview,
  estimatePlayTokens,
  estimateTalkingDurationSeconds,
  generateModeForPrompt,
  joinAvatarPrompt,
  splitAvatarPrompt,
  promptHasQuotedSpeech,
  videoPromptFromDraft,
  normalizePlayMode,
} from "../lib/playPricing";
import { createCostLine } from "../features/play/createCostLine";
import { PromptFields } from "../features/play/PromptFields";
import { useCreateAssist } from "../features/play/useCreateAssist";

import { Button, MessageBar } from "../ui";
import { Caption1 } from "../ui/Text";
import { usePlanFeatures } from "../hooks/usePlanFeatures";
import {
  FACE_STORAGE_KEY,
  VOICE_STORAGE_KEY,
  durationOptionsForProvider,
  snapDurationToChoices,
  resolutionOptionsForProvider,
  advancedModelPool,
  parseMode,
  clipModality,
  pickAdvancedDefault,
  pickExtendModel,
  pickFastModel,
  faceClearedForModelMessage,
  modelSupportsFaceReference,
  isSeedance25Model,
  pickModelForTier,
  supportsPlayExtend,
  tierForModel,
  type QualityTier,
  type ThreadItem,
} from "./playPageModel";
import { FORMATS, MODE_HINT, clipNoun, modeUsesAssist } from "./playPageChrome";
import { pollPlayGenerationUntilReady } from "./playPagePoll";

const PLAY_IDEM_STORAGE = "studio.play.idempotency";

function readStoredPlayIdempotency(): string | null {
  try {
    return sessionStorage.getItem(PLAY_IDEM_STORAGE);
  } catch {
    return null;
  }
}

function writeStoredPlayIdempotency(key: string | null) {
  try {
    if (key) sessionStorage.setItem(PLAY_IDEM_STORAGE, key);
    else sessionStorage.removeItem(PLAY_IDEM_STORAGE);
  } catch {
    /* ignore */
  }
}

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

export function PlayPage() {
  const auth = useAuth();
  const token = auth.accessToken ?? "";
  const workspace = useWorkspace();
  const plan = usePlanFeatures();
  const qc = useQueryClient();
  const [searchParams] = useSearchParams();
  const workspaceId = workspace.activeWorkspaceId;
  const threadEndRef = useRef<HTMLDivElement>(null);
  /** Blocks double form submit (Enter in consent field + click, or double-click) before isPending flips. */
  const submitLockRef = useRef(false);
  const idempotencyKeyRef = useRef<string | null>(readStoredPlayIdempotency());
  const [online, setOnline] = useState(() =>
    typeof navigator === "undefined" ? true : navigator.onLine,
  );
  const extendEngineForRef = useRef<string | null>(null);
  const [mode, setMode] = useState<PlayMode>(() => parseMode(searchParams.get("mode")) || "avatar");
  const [qualityTier, setQualityTier] = useState<QualityTier>("fast");
  const [platform, setPlatform] = useState<PlayPlatform>(() =>
    searchParams.get("platform") === "feed" ? "feed" : "tiktok",
  );
  const [modelId, setModelId] = useState<string>("");
  const [faceAssetId, setFaceAssetId] = useState<string | null>(() => {
    const fromUrl = searchParams.get("face");
    if (fromUrl) return fromUrl;
    try {
      return localStorage.getItem(FACE_STORAGE_KEY);
    } catch {
      return null;
    }
  });
  const [consentName, setConsentName] = useState(auth.user?.full_name || "");
  const [voice, setVoice] = useState(() => {
    const fromUrl = (searchParams.get("voice") || "").trim();
    if (fromUrl) return fromUrl;
    try {
      return (localStorage.getItem(VOICE_STORAGE_KEY) || "").trim();
    } catch {
      return "";
    }
  });
  // null = Auto: backend sizes Talking from the spoken line.
  const [durationSeconds, setDurationSeconds] = useState<number | null>(null);
  const [resolution, setResolution] = useState<string>("720p");
  const [generateAudio, setGenerateAudio] = useState(true);
  const [returnLastFrame, setReturnLastFrame] = useState(false);
  const [batchCount, setBatchCount] = useState(1);
  const [refIds, setRefIds] = useState<
    { id: string; kind: string; label: string; url?: string | null; role?: string }[]
  >([]);
  const [refsUploading, setRefsUploading] = useState(false);
  const [continueFromId, setContinueFromId] = useState<string | null>(
    () => searchParams.get("continue") || null,
  );
  const [prompt, setPrompt] = useState(() => searchParams.get("prompt") || "");
  const promptInputRef = useRef<HTMLTextAreaElement | null>(null);
  const promptRef = useRef("");
  promptRef.current = prompt;
  /**
   * True while the field holds example text the user has not touched. An
   * example written for Talking means nothing in Video, so switching mode
   * clears it. Anything the user typed themselves is kept.
   */
  const promptIsSampleRef = useRef(false);

  /** Fill from a showcase example. */
  const fillSamplePrompt = useCallback((text: string) => {
    promptIsSampleRef.current = true;
    setPrompt(text);
  }, []);

  /** Any edit the user makes, including retry, is theirs to keep. */
  const editPrompt = useCallback((text: string) => {
    promptIsSampleRef.current = false;
    setPrompt(text);
  }, []);
  const assist = useCreateAssist();
  const [thread, setThread] = useState<ThreadItem[]>([]);
  const threadRef = useRef<ThreadItem[]>([]);
  threadRef.current = thread;
  const [error, setError] = useState<string | null>(null);
  const [activeClipId, setActiveClipId] = useState<string | null>(searchParams.get("from"));
  const [composerPicker, setComposerPicker] = useState<"none" | "face" | "voice">("none");
  const refInputRef = useRef<HTMLInputElement>(null);

  // Fresh create session per workspace (do not dump every past clip into this page)
  useEffect(() => {
    setThread([]);
    setActiveClipId(null);
    setError(null);
  }, [workspaceId]);

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  useEffect(() => {
    const m = parseMode(searchParams.get("mode"));
    if (m) setMode(m);
    const face = searchParams.get("face");
    if (face) setFaceAssetId(face);
    const p = searchParams.get("prompt");
    if (p) setPrompt(p);
    if (searchParams.get("platform") === "feed") setPlatform("feed");
    const from = searchParams.get("from");
    if (from) setActiveClipId(from);
    const cont = searchParams.get("continue");
    if (cont) {
      setContinueFromId(cont);
    }
    const voiceParam = (searchParams.get("voice") || "").trim();
    if (voiceParam) {
      setVoice(voiceParam);
    }
  }, [searchParams]);

  const formatMeta = useMemo(() => FORMATS.find((f) => f.id === platform) ?? FORMATS[0], [platform]);

  const voicesQuery = useQuery({
    queryKey: ["play", "voices", workspaceId],
    queryFn: () => api.listPlayVoices(token, workspaceId!),
    enabled: Boolean(token && workspaceId),
    staleTime: 60_000,
    retry: 1,
  });

  const lipsyncVoices = useMemo(() => {
    const fromApi = (voicesQuery.data?.voices || []).filter((v) => v.available !== false);
    if (fromApi.length) return sortPlayVoices(fromApi);
    return sortPlayVoices(BUILTIN_VOICES);
  }, [voicesQuery.data]);

  const lipsyncVoiceGroups = useMemo(() => {
    const hideClones = mode === "video" && !faceAssetId;
    const pickerPool = hideClones ? lipsyncVoices.filter(isBuiltinVoice) : lipsyncVoices;
    const bar = voicesForCreateBar(pickerPool, voice);
    return {
      builtin: bar.filter(isBuiltinVoice),
      cloned: bar.filter(isClonedVoice),
    };
  }, [lipsyncVoices, mode, voice, faceAssetId]);

  const selectedVoice = useMemo(
    () => lipsyncVoices.find((v) => v.id === voice) ?? null,
    [lipsyncVoices, voice],
  );
  const voiceIsCloned = selectedVoice ? isClonedVoice(selectedVoice) : false;

  const modelsQuery = useQuery({
    queryKey: ["play", "models", workspaceId],
    queryFn: () => api.listPlayModels(token, workspaceId),
    staleTime: 120_000,
    enabled: Boolean(token),
  });

  const facesQuery = useQuery({
    queryKey: ["play", "faces", workspaceId],
    queryFn: () => api.listPlayFaces(token, workspaceId!),
    enabled: Boolean(token && workspaceId),
    staleTime: 15_000,
  });

  const modelsForMode = useMemo(() => {
    const all = modelsQuery.data || [];
    return all.filter((m: PlayModelOption) => m.modality === mode && m.enabled);
  }, [modelsQuery.data, mode]);

  const seedanceVideoModels = useMemo(
    () => modelsForMode.filter((m) => m.provider === "seedance"),
    [modelsForMode],
  );

  /** Models available now. Extend filters to engines that can continue a clip. */
  const modelPool = useMemo(() => {
    if (continueFromId) {
      const extendable = modelsForMode.filter((m) => supportsPlayExtend(m.provider));
      return extendable.length ? extendable : modelsForMode;
    }
    return modelsForMode;
  }, [continueFromId, modelsForMode]);

  const applyExtendEngine = useCallback(
    (source: { provider?: string | null; model_id?: string | null; mode?: string | null } | null | undefined) => {
      const modality = clipModality(source?.mode);
      const pool = (modelsQuery.data || []).filter(
        (m) => m.modality === modality && m.enabled && supportsPlayExtend(m.provider),
      );
      const pick = pickExtendModel(pool, source);
      if (!pick) return;
      setModelId(pick.id);
      setQualityTier(tierForModel(pool, pick.id));
    },
    [modelsQuery.data],
  );

  const restoreExtendClip = useCallback(
    (gen: PlayGeneration) => {
      if (gen.mode === "avatar" || gen.mode === "lipsync" || gen.mode === "video") {
        setMode(gen.mode === "lipsync" ? "avatar" : gen.mode);
      }
      applyExtendEngine(gen);
      const face = clipFaceId(gen.metadata);
      if (face) {
        setFaceAssetId(face);
        try {
          localStorage.setItem(FACE_STORAGE_KEY, face);
        } catch {
          /* ignore */
        }
      }
      const nextVoice = clipVoiceId(gen.metadata);
      if (nextVoice) setVoice(nextVoice);
    },
    [applyExtendEngine],
  );

  useEffect(() => {
    if (!continueFromId) {
      extendEngineForRef.current = null;
      return;
    }
    if (extendEngineForRef.current === continueFromId) return;
    if (!(modelsQuery.data || []).length) return;
    const fromThread = thread.find(
      (item): item is Extract<ThreadItem, { kind: "gen" }> =>
        item.kind === "gen" && item.generation.id === continueFromId,
    );
    if (fromThread) {
      extendEngineForRef.current = continueFromId;
      restoreExtendClip(fromThread.generation);
      return;
    }
    if (!token) return;
    let cancelled = false;
    void api.getPlayGeneration(token, continueFromId).then(
      (gen) => {
        if (cancelled || extendEngineForRef.current === continueFromId) return;
        extendEngineForRef.current = continueFromId;
        restoreExtendClip(gen);
      },
      () => {
        /* keep the current engine if the source clip cannot be loaded */
      },
    );
    return () => {
      cancelled = true;
    };
  }, [continueFromId, modelsQuery.data, thread, token, restoreExtendClip]);

  const selectedModel = useMemo(
    () => modelPool.find((m) => m.id === modelId) || pickModelForTier(modelPool, qualityTier),
    [modelPool, modelId, qualityTier],
  );

  // Mode → Fast. Extend picks its own lane from the source clip (Grok stays Fast).
  const advancedUnlocked =
    plan.billing?.entitlements?.advanced_models === true ||
    (plan.plan != null && plan.plan !== "free");

  useEffect(() => {
    if (continueFromId) return;
    setQualityTier("fast");
  }, [mode, continueFromId]);

  const applyQualityTier = useCallback(
    (tier: QualityTier) => {
      if (tier === "advanced" && !advancedUnlocked) {
        setError("Advanced models need Starter. Open Billing to upgrade.");
        return;
      }
      setQualityTier(tier);
      if (tier === "fast") {
        const fast = pickFastModel(modelPool);
        if (fast) setModelId(fast.id);
        return;
      }
      const adv = advancedModelPool(modelPool);
      if (adv.some((m) => m.id === modelId)) return;
      const pick = pickAdvancedDefault(modelPool);
      if (pick) setModelId(pick.id);
    },
    [modelPool, modelId, advancedUnlocked],
  );

  // Keep a valid model when the pool or lane changes.
  useEffect(() => {
    if (!modelPool.length) {
      setModelId("");
      return;
    }
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
      const fast = pickFastModel(modelPool);
      if (fast && modelId !== fast.id) setModelId(fast.id);
      return;
    }
    const adv = advancedModelPool(modelPool);
    if (adv.some((m) => m.id === modelId)) return;
    const pick = pickAdvancedDefault(modelPool);
    if (pick) setModelId(pick.id);
  }, [modelPool, modelId, qualityTier, advancedUnlocked, continueFromId]);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [thread.length]);

  function startNewClip() {
    setThread([]);
    setPrompt("");
    setError(null);
    assist.reset();
    setActiveClipId(null);
    setContinueFromId(null);
    submitLockRef.current = false;
    idempotencyKeyRef.current = null;
    writeStoredPlayIdempotency(null);
    setMode((prev) => (prev === "image" ? "image" : "avatar"));
  }

  const pollUntilReady = useCallback(
    (assetId: string) => pollPlayGenerationUntilReady(token, assetId, setThread),
    [token],
  );

  // Thread items pin the signed URL they were created with. Signatures last two
  // hours, so a Create tab left open serves 401s on play. Re-sign on return.
  useEffect(() => {
    if (!token) return;
    const refreshExpired = () => {
      if (typeof document !== "undefined" && document.visibilityState !== "visible") return;
      const stale = threadRef.current
        .filter(
          (item): item is Extract<ThreadItem, { kind: "gen" }> =>
            item.kind === "gen" &&
            item.generation.status === "ready" &&
            isSignedMediaUrlExpired(item.generation.url),
        )
        .map((item) => item.generation.id);
      stale.forEach((id) => {
        void api
          .getPlayGeneration(token, id)
          .then((fresh) => {
            setThread((prev) =>
              prev.map((item) =>
                item.kind === "gen" && item.generation.id === id
                  ? { ...item, generation: fresh }
                  : item,
              ),
            );
          })
          .catch(() => {
            // Leave the stale URL; the clip page can still refetch it.
          });
      });
      if (
        workspaceId &&
        (facesQuery.data || []).some((f) => isSignedMediaUrlExpired(f.url))
      ) {
        void qc.invalidateQueries({ queryKey: ["play", "faces", workspaceId] });
      }
    };
    refreshExpired();
    document.addEventListener("visibilitychange", refreshExpired);
    return () => document.removeEventListener("visibilitychange", refreshExpired);
  }, [token, workspaceId, facesQuery.data, qc]);

  const needsFace = mode === "avatar";
  // Face and voice wait until assist has confirmed Talking / Scene.
  const kindNeedsFace =
    assist.ready && normalizePlayMode(assist.draft?.kind) === "avatar";
  // Video takes an optional face when the engine supports identity refs (not Veo Lite).
  const videoFaceOk = mode === "video" && modelSupportsFaceReference(selectedModel);
  const allowsFace = needsFace || videoFaceOk;
  const needsDuration = mode !== "image";
  const canAttachRefs = mode !== "image";
  const isSeedanceModel = Boolean(selectedModel?.provider === "seedance");
  const isGeminiModel = Boolean(selectedModel?.provider === "gemini");
  const isKlingModel = Boolean(selectedModel?.provider === "kling");
  const isXaiModel = Boolean(selectedModel?.provider === "xai");
  // Seedance: image/video/audio refs. Always on Clip.

  // Drop face when the selected Video engine cannot take identity refs (e.g. Veo Lite).
  // Only the live selection: FACE_STORAGE_KEY is the shared avatar preference that
  // Talking and the Faces page read, and picking a Video model is no reason to lose it.
  useEffect(() => {
    if (mode !== "video" || !faceAssetId) return;
    if (modelSupportsFaceReference(selectedModel)) return;
    setFaceAssetId(null);
    setError(faceClearedForModelMessage(selectedModel?.label));
  }, [mode, modelId, faceAssetId, selectedModel]);
  const maxDuration = useMemo(() => {
    const m = modelsForMode.find((row) => row.id === modelId);
    return m?.max_duration_seconds ?? 15;
  }, [modelsForMode, modelId]);
  const durationChoices = useMemo(() => {
    const base = durationOptionsForProvider(selectedModel?.provider, {
      modelId: selectedModel?.id,
      maxDuration,
    });
    return base.filter((d) => d <= maxDuration);
  }, [selectedModel?.provider, selectedModel?.id, maxDuration]);
  const resolutionChoices = useMemo(() => {
    return [...resolutionOptionsForProvider(selectedModel?.provider, {
      modelId: selectedModel?.id,
    })];
  }, [selectedModel?.provider, selectedModel?.id]);
  // Veo has no true 1:1 — keep format chips honest for Gemini models.
  // Kling + Grok + Seedance honor square.
  const formatChoices = useMemo(
    () => (isGeminiModel ? FORMATS.filter((f) => f.id !== "feed") : FORMATS),
    [isGeminiModel],
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

  const runQuote = useMemo(() => {
    const imgRefs = refIds.filter((r) => r.kind === "image").length;
    const vidRefs = refIds.filter((r) => r.kind === "video").length;
    const audRefs = refIds.filter((r) => r.kind === "audio").length;
    // Face is not a "ref extra" for pricing on avatar.
    const extraImgs = Math.max(0, imgRefs);
    const costMode = normalizePlayMode(assist.draft?.kind || mode) || mode;
    return estimatePlayTokens({
      mode: costMode,
      model: selectedModel,
      durationSeconds: needsDuration ? effectiveDurationSeconds : null,
      resolution: needsDuration ? resolution : null,
      batchCount: isSeedanceModel && needsDuration ? batchCount : 1,
      generateAudio: isSeedanceModel ? generateAudio : true,
      returnLastFrame: isSeedanceModel ? returnLastFrame : false,
      refImageCount: canAttachRefs ? extraImgs : 0,
      refVideoCount: isSeedanceModel && canAttachRefs ? vidRefs : 0,
      refAudioCount: isSeedanceModel && canAttachRefs ? audRefs : 0,
    });
  }, [
    mode,
    assist.draft?.kind,
    selectedModel,
    needsDuration,
    effectiveDurationSeconds,
    resolution,
    isSeedanceModel,
    batchCount,
    generateAudio,
    returnLastFrame,
    canAttachRefs,
    refIds,
  ]);
  const quoteQuery = useQuery({
    queryKey: [
      "play",
      "quote",
      runQuote,
      selectedModel?.id,
      assist.draft?.kind || mode,
      prompt,
      faceAssetId,
      continueFromId,
      voiceIsCloned,
    ],
    queryFn: () =>
      api.playQuote(token, {
        mode: normalizePlayMode(assist.draft?.kind || mode) || mode,
        model: selectedModel?.id,
        duration_seconds: needsDuration ? effectiveDurationSeconds : null,
        prompt,
        resolution: needsDuration ? resolution : null,
        count: isSeedanceModel && needsDuration ? batchCount : 1,
        generate_audio: isSeedanceModel ? generateAudio : true,
        return_last_frame: isSeedanceModel ? returnLastFrame : false,
        has_face: Boolean(faceAssetId),
        ref_image_count: canAttachRefs ? refIds.filter((r) => r.kind === "image").length : 0,
        ref_video_count: isSeedanceModel && canAttachRefs ? refIds.filter((r) => r.kind === "video").length : 0,
        ref_audio_count: isSeedanceModel && canAttachRefs ? refIds.filter((r) => r.kind === "audio").length : 0,
        continue_from: Boolean(continueFromId),
        cloned_voice: voiceIsCloned,
      }),
    enabled: Boolean(selectedModel),
    staleTime: 8_000,
  });
  const totalTokens = quoteQuery.data?.total ?? runQuote.total;

  useEffect(() => {
    if (
      durationSeconds != null &&
      durationChoices.length &&
      !durationChoices.includes(durationSeconds as (typeof durationChoices)[number])
    ) {
      setDurationSeconds(snapDurationToChoices(durationSeconds, durationChoices));
    }
  }, [durationChoices, durationSeconds]);

  useEffect(() => {
    if (!resolutionChoices.includes(resolution)) {
      setResolution("720p");
    }
  }, [resolutionChoices, resolution]);

  useEffect(() => {
    if (isGeminiModel && platform === "feed") {
      setPlatform("tiktok");
    }
  }, [isGeminiModel, platform]);

  // Veo 1080p is 8s-only on the Gemini API.
  useEffect(() => {
    if (isGeminiModel && resolution === "1080p" && durationSeconds !== 8) {
      setDurationSeconds(8);
    }
  }, [isGeminiModel, resolution, durationSeconds]);

  useEffect(() => {
    if (!isSeedanceModel) {
      setBatchCount(1);
      setReturnLastFrame(false);
      // Seedance-only: video/audio refs. Grok keeps image refs.
      if (!isXaiModel) {
        setRefIds([]);
      } else {
        setRefIds((prev) => prev.filter((r) => r.kind === "image"));
      }
    }
  }, [isSeedanceModel, isXaiModel]);

  const persistVoiceDefault = useCallback((id: string) => {
    const next = id.trim();
    if (!next) return;
    try {
      localStorage.setItem(VOICE_STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  const prevVoiceRef = useRef(voice);
  const prevFaceRef = useRef(faceAssetId);
  const clearPlayIdempotency = () => {
    idempotencyKeyRef.current = null;
    writeStoredPlayIdempotency(null);
  };
  useEffect(() => {
    if (prevVoiceRef.current !== voice) {
      prevVoiceRef.current = voice;
      clearPlayIdempotency();
    }
  }, [voice]);
  useEffect(() => {
    if (prevFaceRef.current !== faceAssetId) {
      prevFaceRef.current = faceAssetId;
      clearPlayIdempotency();
    }
  }, [faceAssetId]);

  useEffect(() => {
    if (mode === "video" && !faceAssetId && voiceIsCloned) {
      setVoice(defaultBuiltinVoiceId(lipsyncVoices));
    }
  }, [mode, voiceIsCloned, faceAssetId]);

  useEffect(() => {
    if (lipsyncVoices.length === 0) return;
    const inList = (id: string | null | undefined) =>
      Boolean(id && lipsyncVoices.some((v) => v.id === id));
    const face = (facesQuery.data || []).find((f) => f.id === faceAssetId);
    const bound = face?.bound_voice_id?.trim() || "";
    // Extend keeps the Voice pick the user set on this shot.
    if (inList(bound) && !continueFromId) {
      if (voice !== bound) setVoice(bound);
      return;
    }
    let stored = "";
    try {
      stored = (localStorage.getItem(VOICE_STORAGE_KEY) || "").trim();
    } catch {
      stored = "";
    }
    const storedRow = lipsyncVoices.find((v) => v.id === stored);
    const storedIsClone = Boolean(
      storedRow && ((storedRow.source ?? "builtin") === "cloned" || storedRow.source === "custom"),
    );
    if (mode === "video" && !faceAssetId && storedIsClone) {
      stored = "";
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
    const clone = lipsyncVoiceGroups.cloned[0];
    const next = clone?.id || defaultBuiltinVoiceId(lipsyncVoices) || "";
    if (!next) return;
    setVoice(next);
    persistVoiceDefault(next);
  }, [
    mode,
    faceAssetId,
    facesQuery.data,
    voice,
    lipsyncVoices,
    lipsyncVoiceGroups.cloned,
    persistVoiceDefault,
    continueFromId,
  ]);

  type GenerateVars = {
    text: string;
    mode: PlayMode;
    platform: PlayPlatform;
    modelId: string;
    faceAssetId: string | null;
    /** False when Video model rejects identity refs (face must not be sent). */
    allowsFace: boolean;
    voice: string;
    workspaceId: string;
    durationSeconds: number | null;
    resolution: string;
    generateAudio: boolean;
    returnLastFrame: boolean;
    batchCount: number;
    referenceAssetIds: string[];
    referenceRoles: string[];
    continueFromId: string | null;
    /** Stable across a resubmit of the same draft, so a timeout cannot double-charge. */
    idempotencyKey: string;
  };

  // Snapshot prompt into mutate() vars. Do not read React state inside mutationFn after
  // onMutate clears the textarea (that caused "Write a prompt first" on valid examples).
  const generate = useMutation({
    mutationFn: async (vars: GenerateVars) => {
      if (!vars.text) throw new Error("Write a prompt first");
      const mode = vars.mode === "lipsync" ? "avatar" : vars.mode;
      if (mode === "avatar" && !vars.faceAssetId) {
        throw new Error("Add a face first");
      }
      if (vars.continueFromId) {
        const model = (modelsQuery.data || []).find((m) => m.id === vars.modelId);
        if (!supportsPlayExtend(model?.provider)) {
          throw new Error("This engine cannot extend a clip.");
        }
      }
      if (mode === "avatar" && !vars.voice) {
        throw new Error("Add your voice or pick a built-in.");
      }
      const payload: {
        workspace_id: string;
        mode: PlayMode;
        platform: PlayPlatform;
        prompt: string;
        model?: string | null;
        face_asset_id?: string | null;
        voice?: string | null;
        duration_seconds?: number | null;
        resolution?: string | null;
        generate_audio?: boolean | null;
        return_last_frame?: boolean | null;
        reference_asset_ids?: string[];
        reference_roles?: string[];
        count?: number;
        continue_from_asset_id?: string | null;
      } = {
        workspace_id: vars.workspaceId,
        mode,
        platform: vars.platform,
        prompt: vars.text,
        model: vars.modelId || null,
        // Talking requires a face; video only when the engine allows it.
        face_asset_id: vars.allowsFace ? vars.faceAssetId : null,
      };
      if (mode === "avatar") {
        payload.voice = vars.voice;
      } else if (mode === "video") {
        payload.voice = vars.voice || DEFAULT_BUILTIN_VOICE_ID;
      }
      if (mode === "avatar" || mode === "video") {
        payload.duration_seconds = vars.durationSeconds;
        payload.resolution = vars.resolution || "720p";
        payload.generate_audio = vars.generateAudio;
        payload.return_last_frame = vars.returnLastFrame;
        payload.reference_asset_ids = vars.referenceAssetIds;
        // Only send roles when at least one is filled in; an all-blank list
        // is noise the backend would just discard.
        if (vars.referenceRoles.some((role) => role)) {
          payload.reference_roles = vars.referenceRoles;
        }
        payload.count = vars.batchCount;
        payload.continue_from_asset_id = vars.continueFromId;
      }
      return api.playGenerate(token, payload, vars.idempotencyKey);
    },
    onMutate: (vars) => {
      setError(null);
      const stamp = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const clipLabel = clipNoun(vars.mode);
      const lengthNote =
        vars.mode === "avatar" || vars.mode === "video"
          ? vars.durationSeconds == null
            ? " · auto length"
            : ` · ${vars.durationSeconds}s`
          : "";
      const batchNote = vars.batchCount > 1 ? ` · ×${vars.batchCount}` : "";
      const contNote = vars.continueFromId ? " Continuing your last clip." : "";
      const lastUser = [...threadRef.current].reverse().find((i) => i.kind === "user");
      const alreadyUser = lastUser?.kind === "user" && lastUser.text === vars.text;
      setThread((prev) => [
        ...prev,
        ...(alreadyUser
          ? []
          : [{ kind: "user" as const, id: `u-${stamp}`, text: vars.text, mode: vars.mode, platform: vars.platform }]),
        {
          kind: "system",
          id: `s-ack-${stamp}`,
          text: `Got it. Making a ${clipLabel} for ${vars.platform === "feed" ? "square" : "vertical"}${lengthNote}${batchNote}.${contNote}`,
        },
      ]);
      setPrompt("");
    },
    onSuccess: (res) => {
      // This draft is done; the next submission is a new clip, not a retry.
      idempotencyKeyRef.current = null;
      writeStoredPlayIdempotency(null);
      // Without this the settled draft stays settled and every later submit
      // would skip the pre-flight entirely.
      assist.reset();
      const list =
        res.generations && res.generations.length > 0 ? res.generations : [res.generation];
      setActiveClipId(list[0]?.id ?? res.generation.id);
      setContinueFromId(null);
      setThread((prev) => {
        const existing = new Set(
          prev.filter((x) => x.kind === "gen").map((x) => (x as { generation: { id: string } }).generation.id),
        );
        const next: ThreadItem[] = [...prev];
        list.forEach((gen, i) => {
          if (existing.has(gen.id)) return;
          next.push({
            kind: "gen",
            id: `g-${gen.id}`,
            generation: gen,
            note: i === 0 ? res.message : null,
          });
          if (gen.status === "processing" || gen.status === "queued") {
            next.push({
              kind: "system",
              id: `s-wait-${gen.id}`,
              text: "Working on it. This can take a bit. Hang tight.",
            });
          }
        });
        return next;
      });
      void qc.invalidateQueries({ queryKey: ["workspaces", "billing", workspaceId] });
      void qc.invalidateQueries({ queryKey: ["play", "generations", workspaceId] });
      for (const gen of list) {
        if (
          (gen.status === "processing" || gen.status === "queued") &&
          gen.asset_type === "video"
        ) {
          void pollUntilReady(gen.id);
        }
      }
    },
    onError: (err) => {
      submitLockRef.current = false;
      const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Generate failed";
      setError(msg);
      if (err instanceof ApiError && (err.code === "plan_advanced_required" || err.status === 403)) {
        setError(
          msg.includes("Upgrade")
            ? msg
            : "Advanced models need Starter. Open Billing to upgrade.",
        );
      }
      setThread((prev) => [
        ...prev,
        { kind: "system", id: `s-${Date.now()}`, text: msg, tone: "error" },
      ]);
    },
    onSettled: () => {
      submitLockRef.current = false;
    },
  });

  const selectMode = useCallback(
    (next: PlayMode) => {
      if (mode === next) return;
      if (promptIsSampleRef.current) {
        promptIsSampleRef.current = false;
        setPrompt("");
      } else if (next === "image" && mode !== "image") {
        setPrompt((p) => avatarPromptPreview(p));
      } else if (mode === "avatar" && next !== "avatar") {
        setPrompt((p) => avatarPromptPreview(p));
      }
      assist.reset();
      setMode(next);
    },
    [mode, assist],
  );

  /** The clip being extended, so the planner can propose a next beat, not a repeat. */
  const continueSourcePrompt = useMemo(() => {
    if (!continueFromId) return "";
    const found = threadRef.current.find(
      (item): item is Extract<ThreadItem, { kind: "gen" }> =>
        item.kind === "gen" && item.generation.id === continueFromId,
    );
    return found?.generation.prompt ?? "";
  }, [continueFromId]);

  /**
   * Pre-flight turn. Talks the clip through before any credits move. A down
   * helper must not spend. The next send retries Assist.
   */
  const runAssist = useCallback(
    async (text: string) => {
      if (!workspaceId || !token) return null;
      const { scene, line } = splitAvatarPrompt(text);
      const chip = text.startsWith("kind:");
      const thinkingId = `thinking-${Date.now()}`;
      setThread((prev) => [...prev, { kind: "thinking", id: thinkingId }]);
      const clipBucket = mode === "image" ? "image" : "avatar";
      const turn = await assist.send({
        token,
        workspaceId,
        mode: clipBucket,
        source: continueFromId
          ? { kind: "continue" as const, prompt: continueSourcePrompt }
          : null,
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
      setThread((prev) => {
        const rest = prev.filter((i) => i.id !== thinkingId);
        if (turn.reply) {
          rest.push({
            kind: "system",
            id: `assist-${Date.now()}`,
            text: turn.reply,
            tone: "chat",
          });
        }
        if (turn.draft && (turn.draft.line.trim() || turn.draft.scene.trim())) {
          // The draft is a thing to read, not a form to fill in, so it lands in
          // the thread rather than silently rewriting the box.
          rest.push({
            kind: "draft",
            id: `draft-${Date.now()}`,
            line: turn.draft.line,
            scene: turn.draft.scene,
            summary: turn.summary,
            options: turn.options,
          });
        }
        if (!turn.reply && !turn.draft) {
          rest.push({
            kind: "system",
            id: `assist-err-${Date.now()}`,
            text: "Could not work that out. Send again. Nothing was spent.",
            tone: "chat",
          });
        }
        return rest;
      });
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
        else if (kind === "avatar" || (!kind && mode === "avatar")) {
          setDurationSeconds(turn.draft.duration_seconds ?? null);
        }
      }
      return turn;
    },
    [assist, token, workspaceId, mode, durationSeconds, voice, continueFromId, continueSourcePrompt],
  );

  /** Focus the box so "Change" lands the cursor where the edit happens. */
  function focusPromptForEdit() {
    promptInputRef.current?.focus();
    promptInputRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  /** Card action. Same path as submitting, so nothing forks off its own rules. */
  async function generateSettledDraft() {
    await onSubmit();
  }

  async function onSubmit(event?: FormEvent) {
    event?.preventDefault();
    event?.stopPropagation();
    if (submitLockRef.current || generate.isPending || assist.pending) return;
    const text = prompt.trim();
    if (!text) {
      setError("Write a prompt first");
      return;
    }
    if (!workspaceId) {
      void workspace.refresh();
      setError(
        workspaceActionBlockedMessage({
          loading: workspace.loading,
          error: workspace.error,
        }),
      );
      return;
    }
    if (refsUploading) {
      setError("Wait for references to finish uploading");
      return;
    }
    if (!online) {
      setError("You're offline. Connect, then send.");
      return;
    }
    // Kind is confirmed on the draft card. Face and voice wait until we know it.
    // A down helper must not spend. The next send retries Assist.
    if (modeUsesAssist(mode) && !assist.ready && event) {
      setThread((prev) => [
        ...prev,
        { kind: "user", id: `u-${Date.now()}`, text, mode, platform },
      ]);
      const turn = await runAssist(text);
      if (!turn) return;
      if (turn.draft) return;
      return;
    }
    const lastKind = assist.draft?.kind ?? (mode !== "image" ? mode : null);
    const genMode = generateModeForPrompt({
      tabMode: mode,
      draftKind: lastKind,
      prompt: text,
      hasFace: Boolean(faceAssetId),
    });
    const genText =
      genMode === "video"
        ? videoPromptFromDraft(assist.draft, text)
        : text;
    if (genMode === "avatar" && !faceAssetId) {
      setError("Add a face");
      return;
    }
    if (genMode === "avatar" && !voice) {
      setError("Add your voice");
      return;
    }
    submitLockRef.current = true;
    // Reused when a submission errors out, so retrying the same draft dedupes
    // server-side instead of starting a second paid job. Cleared on success.
    if (!online) {
      setError("You're offline. Connect, then send.");
      submitLockRef.current = false;
      return;
    }
    if (!idempotencyKeyRef.current) {
      idempotencyKeyRef.current =
        typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      writeStoredPlayIdempotency(idempotencyKeyRef.current);
    }
    generate.mutate({
      idempotencyKey: idempotencyKeyRef.current,
      text: genText,
      mode: genMode,
      platform,
      modelId: assist.draft?.model || modelId,
      faceAssetId,
      allowsFace,
      voice,
      workspaceId,
      durationSeconds:
        assist.draft?.duration_seconds ??
        (genMode === "avatar" ? effectiveDurationSeconds : durationSeconds),
      resolution: assist.draft?.resolution || resolution,
      generateAudio,
      returnLastFrame,
      batchCount: isSeedanceModel && needsDuration ? batchCount : 1,
      referenceAssetIds: canAttachRefs ? refIds.map((r) => r.id) : [],
      referenceRoles: canAttachRefs ? refIds.map((r) => (r.role ?? "").trim()) : [],
      continueFromId:
        continueFromId && supportsPlayExtend(selectedModel?.provider) ? continueFromId : null,
    });
  }

  async function onRefFilesSelected(files: FileList | null) {
    if (!files?.length || !workspaceId || !canAttachRefs) return;
    setRefsUploading(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
        const kind = file.type.startsWith("video/")
          ? "video"
          : file.type.startsWith("audio/")
            ? "audio"
            : "image";
        // Grok reference-to-video is photos only.
        if (isXaiModel && kind !== "image") {
          setError("This model only accepts photo references (JPEG, PNG, or WebP).");
          continue;
        }
        if (!isSeedanceModel && kind !== "image") {
          setError("This model only accepts photo references.");
          continue;
        }
        const ref = await api.uploadPlayRef(token, workspaceId, file, kind);
        setRefIds((prev) => [
          ...prev,
          { id: ref.id, kind: ref.kind, label: ref.label || file.name, url: ref.url },
        ]);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Upload failed");
    } finally {
      setRefsUploading(false);
      if (refInputRef.current) refInputRef.current.value = "";
    }
  }

  const onSelectFace = useCallback((face: PlayFace | null) => {
    setFaceAssetId(face?.id ?? null);
    const bound = face?.bound_voice_id?.trim() || "";
    if (bound && lipsyncVoices.some((v) => v.id === bound)) {
      setVoice(bound);
    } else if (face) {
      const stored = (() => {
        try {
          return (localStorage.getItem(VOICE_STORAGE_KEY) || "").trim();
        } catch {
          return "";
        }
      })();
      const storedOk = stored && lipsyncVoices.some((v) => v.id === stored);
      const clone = lipsyncVoiceGroups.cloned[0];
      const next = storedOk
        ? stored
        : clone?.id || defaultBuiltinVoiceId(lipsyncVoices) || "";
      if (next) setVoice(next);
    }
    try {
      if (face?.id) localStorage.setItem(FACE_STORAGE_KEY, face.id);
      else localStorage.removeItem(FACE_STORAGE_KEY);
    } catch {
      /* ignore */
    }
    setConsentName((prev) => (prev.trim() ? prev : face?.consent_name || prev));
  }, [lipsyncVoices, lipsyncVoiceGroups.cloned]);

  async function loadExample(ex: (typeof SHOWCASE_EXAMPLES)[number]) {
    setMode(ex.mode);
    setPlatform(ex.platform === "feed" ? "feed" : "tiktok");
    fillSamplePrompt(ex.prompt);
    setError(null);
  }

  const credits = plan.billing;
  const clipLeft =
    credits?.play_clip_remaining ??
    credits?.play_avatar_remaining ??
    credits?.video_generations_remaining;
  const stillLeft = credits?.play_still_remaining ?? credits?.image_generations_remaining;
  const emptyExamples = useMemo(() => {
    const clip = SHOWCASE_EXAMPLES.find((ex) => ex.mode === "avatar");
    const still = SHOWCASE_EXAMPLES.find((ex) => ex.mode === "image");
    return [clip, still].filter((ex): ex is NonNullable<typeof ex> => Boolean(ex));
  }, []);
  const faces = facesQuery.data || [];
  const selectedFace = faces.find((f) => f.id === faceAssetId) ?? null;
  const selectedVoiceLabel = selectedVoice?.name || "Voice";
  const chipClass = (on: boolean) =>
    cn(
      "inline-flex min-h-10 shrink-0 items-center gap-1.5 rounded-full border px-3 py-2 text-sm font-semibold transition-colors",
      on
        ? "border-[var(--studio-brand)] bg-[var(--studio-chip-on,var(--studio-fill))] text-[var(--studio-brand)]"
        : "border-transparent bg-[var(--studio-chip-off,var(--studio-fill-quiet))] text-[var(--studio-fg-muted)] hover:text-[var(--studio-fg)]",
    );
  const showResolution =
    needsDuration && (isSeedanceModel || isGeminiModel || isKlingModel || isXaiModel);
  const talkingDraft = useMemo(() => splitAvatarPrompt(prompt), [prompt]);
  const improvisedLine =
    mode === "avatar" &&
    !continueFromId &&
    (!needsFace || Boolean(faceAssetId)) &&
    Boolean(talkingDraft.scene.trim()) &&
    !talkingDraft.line.trim();
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
  const persistChipVoice = (id: string) => {
    setVoice(id);
    if (!boundVoiceId || !lipsyncVoices.some((v) => v.id === boundVoiceId)) {
      persistVoiceDefault(id);
    }
  };
  const costLine = createCostLine({
    mode: normalizePlayMode(assist.draft?.kind || mode) || mode,
    prompt: costSpeech,
    totalCredits: totalTokens,
    durationSeconds,
    autoSeconds: effectiveDurationSeconds,
    needsDuration,
    isExtending: Boolean(continueFromId),
    isSeedanceModel,
    isSeedance25: isSeedance25Model(selectedModel?.id),
    resolution,
    showResolution,
    generateAudio,
    batchCount,
    hasModel: Boolean(selectedModel),
    refsUploading,
    clonedVoice:
      effectiveIsClone &&
      ((mode === "avatar" && Boolean(talkingLine)) ||
        (mode === "video" &&
          Boolean(faceAssetId) &&
          promptHasQuotedSpeech(sceneSpeechSource))),
    voiceoverSeconds: effectiveDurationSeconds ?? estimateTalkingDurationSeconds(costSpeech),
  });
  // Web shows format and references outside the collapsed options block, so the
  // footer carries them next to the shared credits copy.
  const metaLine = [
    `${formatMeta.label} · ${formatMeta.aspect}`,
    costLine,
    refIds.length ? `${refIds.length} reference${refIds.length === 1 ? "" : "s"}` : null,
    needsFace && faceAssetId ? "face locked in" : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="mx-auto flex h-[calc(100dvh-7.25rem)] w-full max-w-5xl min-h-0 flex-col gap-0 sm:h-auto sm:min-h-0 sm:gap-3 md:h-auto">
      <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[22px] border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] shadow-[var(--studio-card-shadow,0_16px_48px_rgba(0,0,0,0.22))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 sm:rounded-[28px] sm:min-h-[calc(100dvh-6rem)]">
        <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-[var(--studio-border-soft)] px-3 py-2.5 sm:px-4 sm:py-3">
          <div className="grid min-w-0 gap-0.5">
            <h1 className="m-0 flex items-center gap-2 text-base font-bold text-[var(--studio-fg)] sm:text-lg">
              <Sparkles size={18} className="text-[var(--studio-brand)]" aria-hidden />
              {mode === "image" ? "Still" : "Clip"}
            </h1>
            <Caption1 className="hidden sm:block">
              One clip at a time. Pick a face, write a prompt, generate.{" "}
              <Link className="font-semibold text-[var(--studio-brand)] no-underline hover:underline" to="/avatars">
                Faces
              </Link>
              {" · "}
              <Link className="font-semibold text-[var(--studio-brand)] no-underline hover:underline" to="/voices">
                Voices
              </Link>
              {" · "}
              <Link className="font-semibold text-[var(--studio-brand)] no-underline hover:underline" to="/clips">
                All clips
              </Link>
            </Caption1>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.78rem] sm:hidden">
              <Link className="font-semibold text-[var(--studio-brand)] no-underline" to="/avatars">
                Faces
              </Link>
              <Link className="font-semibold text-[var(--studio-brand)] no-underline" to="/voices">
                Voices
              </Link>
              <Link className="font-semibold text-[var(--studio-brand)] no-underline" to="/clips">
                Library
              </Link>
              <Link className="font-semibold text-[var(--studio-brand)] no-underline" to="/billing">
                Billing
              </Link>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[0.78rem] text-[var(--studio-fg-muted)]">
            <span className="hidden sm:inline">
              {typeof clipLeft === "number" ? <span>{clipLeft} clip</span> : null}
              {typeof stillLeft === "number" ? <span> · {stillLeft} stills</span> : null}
            </span>
            <Link
              className="hidden font-semibold text-[var(--studio-brand)] no-underline hover:underline sm:inline"
              to="/billing"
            >
              Billing
            </Link>
            {thread.length > 0 ? (
              <Button type="button" size="small" variant="secondary" onClick={startNewClip}>
                New clip
              </Button>
            ) : null}
            {activeClipId ? (
              <Link
                className="font-semibold text-[var(--studio-brand)] no-underline hover:underline"
                to={`/clips/${activeClipId}`}
              >
                Open clip
              </Link>
            ) : null}
          </div>
        </header>

        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto overscroll-contain px-3 py-3 sm:px-4 sm:py-4">
          {thread.length === 0 ? (
            <div className="grid gap-3 py-2 sm:gap-4 sm:py-4">
              <p className="m-0 text-center text-sm text-[var(--studio-fg-muted)]">
                This page is for what you are making now. Past work lives in your Library.
              </p>
              <div className="flex justify-center gap-2">
                <button
                  type="button"
                  className={cn(
                    "min-h-10 rounded-full border px-4 text-sm font-bold",
                    mode !== "image"
                      ? "border-[var(--studio-brand)] bg-[var(--studio-chip-on,var(--studio-fill))] text-[var(--studio-brand)]"
                      : "border-[var(--studio-border)] text-[var(--studio-fg)]",
                  )}
                  onClick={() => selectMode("avatar")}
                >
                  Clip
                </button>
                <button
                  type="button"
                  className={cn(
                    "min-h-10 rounded-full border px-4 text-sm font-bold",
                    mode === "image"
                      ? "border-[var(--studio-brand)] bg-[var(--studio-chip-on,var(--studio-fill))] text-[var(--studio-brand)]"
                      : "border-[var(--studio-border)] text-[var(--studio-fg)]",
                  )}
                  onClick={() => selectMode("image")}
                >
                  Still
                </button>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {emptyExamples.map((ex) => (
                  <button
                    key={ex.id}
                    type="button"
                    className="rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-fill-quiet))] p-3 text-left shadow-[var(--studio-card-shadow)] backdrop-blur-md transition-colors hover:bg-[var(--studio-fill-soft)] sm:p-3.5"
                    onClick={() => void loadExample(ex)}
                  >
                    <span className="block text-[0.7rem] font-bold uppercase tracking-wide text-[var(--studio-brand)]">
                      {ex.mode === "image" ? "Still" : "Clip"}
                    </span>
                    <span className="mt-1 block text-sm font-semibold text-[var(--studio-fg)]">{ex.title}</span>
                    <span className="mt-0.5 block text-[0.78rem] text-[var(--studio-fg-muted)]">{ex.caption}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <CreateThread
            thread={thread}
            generatePending={generate.isPending}
            assistPending={assist.pending}
            onGenerateDraft={() => void generateSettledDraft()}
            onEditDraft={() => promptRef.current && focusPromptForEdit()}
            onChooseOption={(value) => void runAssist(value)}
            onDownloadError={setError}
            onRetry={(prompt) => {
              editPrompt(prompt);
              setError(null);
            }}
            onExtend={(g) => {
              setContinueFromId(g.id);
              assist.reset();
              restoreExtendClip(g);
              setError(null);
              extendEngineForRef.current = g.id;
            }}
          />
          <div ref={threadEndRef} />
        </div>

        <form
          onSubmit={onSubmit}
          onKeyDown={(event) => {
            // Enter in single-line fields would submit the form and can double-fire with Generate.
            if (event.key !== "Enter") return;
            const target = event.target as HTMLElement | null;
            if (target && target.tagName === "TEXTAREA") return;
            if (target && target.tagName === "BUTTON" && (target as HTMLButtonElement).type === "submit") return;
            event.preventDefault();
          }}
          className="flex max-h-[min(64dvh,36rem)] shrink-0 flex-col border-t border-[var(--studio-border-soft)] bg-[var(--studio-glass,var(--studio-fill-quiet))] backdrop-blur-md sm:max-h-none sm:block sm:p-4"
        >
          <div className="grid min-h-0 flex-1 gap-2 overflow-y-auto overscroll-contain p-2.5 sm:gap-2 sm:overflow-visible sm:p-0">
          {error ? <MessageBar intent="error">{error}</MessageBar> : null}
          {!workspaceId && workspace.error && !workspace.loading ? (
            <MessageBar intent="error">
              Could not load your space.{" "}
              <button
                type="button"
                className="font-semibold underline"
                onClick={() => void workspace.refresh()}
              >
                Retry
              </button>
            </MessageBar>
          ) : null}
          {!online ? (
            <MessageBar intent="warning">You're offline. Connect, then send.</MessageBar>
          ) : null}
          {facesQuery.isError ? (
            <MessageBar intent="error">
              Could not load faces.{" "}
              <button
                type="button"
                className="font-semibold underline"
                onClick={() => void facesQuery.refetch()}
              >
                Retry
              </button>
            </MessageBar>
          ) : null}

          {mode !== "image" ? (
            <div className="flex items-center gap-1 border-b border-[var(--studio-border-soft)] pb-2">
              <button
                type="button"
                className="flex min-h-9 min-w-0 flex-1 items-center gap-1.5 px-1 text-left text-[15px] font-semibold text-[var(--studio-fg)]"
                aria-pressed={composerPicker === "voice"}
                aria-label={`Voice, ${selectedVoiceLabel}`}
                onClick={() => setComposerPicker((p) => (p === "voice" ? "none" : "voice"))}
              >
                <span className="min-w-0 flex-1 truncate">{selectedVoiceLabel}</span>
              </button>
            </div>
          ) : (
            <div className="grid gap-1.5">
              <ModelQualityPicker
                models={modelPool}
                modelId={modelId}
                qualityTier={qualityTier}
                onTierChange={applyQualityTier}
                advancedUnlocked={advancedUnlocked}
                onAdvancedLocked={() =>
                  setError("Advanced stills need Starter. Open Billing to upgrade.")
                }
                onModelChange={(id) => {
                  if (!advancedUnlocked) {
                    setError("Advanced stills need Starter. Open Billing to upgrade.");
                    return;
                  }
                  setModelId(id);
                  setQualityTier("advanced");
                }}
              />
            </div>
          )}

          {continueFromId ? (
            <div className="flex items-center gap-2.5 rounded-2xl bg-[var(--studio-chip-on,var(--studio-fill))] p-2.5">
              <span className="flex-1 text-[13px] font-bold text-[var(--studio-brand)]">Extending</span>
              <button
                type="button"
                className="text-[13px] font-bold text-[var(--studio-brand)]"
                onClick={() => setContinueFromId(null)}
              >
                Cancel
              </button>
            </div>
          ) : null}

          {refIds.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {refIds.map((r) => (
                <div key={r.id} className="flex items-center gap-1.5">
                  <span className="inline-flex items-center gap-1 rounded-full border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] px-2 py-1 text-[0.72rem] text-[var(--studio-fg-muted)]">
                    {r.kind === "video" ? "Clip" : r.kind === "audio" ? "Audio" : "Photo"}: {r.label}
                    <button
                      type="button"
                      className="min-h-6 min-w-6 border-0 bg-transparent p-0 font-bold text-[var(--studio-fg)]"
                      onClick={() => setRefIds((prev) => prev.filter((x) => x.id !== r.id))}
                      aria-label={`Remove ${r.label}`}
                    >
                      ×
                    </button>
                  </span>
                  {r.kind === "image" ? (
                    <input
                      type="text"
                      value={r.role ?? ""}
                      maxLength={80}
                      placeholder="her friend"
                      className="min-w-0 flex-1 rounded-full border border-[var(--studio-border)] bg-transparent px-2.5 py-1 text-[0.72rem] text-[var(--studio-fg)] placeholder:text-[var(--studio-fg-muted)]"
                      onChange={(event) =>
                        setRefIds((prev) =>
                          prev.map((x) => (x.id === r.id ? { ...x, role: event.target.value } : x)),
                        )
                      }
                      aria-label={`What ${r.label} shows`}
                    />
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}

          {composerPicker === "voice" && mode !== "image" ? (
            <div className="flex flex-wrap gap-1.5">
              {lipsyncVoiceGroups.cloned.map((v) => (
                <button
                  key={v.id}
                  type="button"
                  className={chipClass(voice === v.id)}
                  onClick={() => persistChipVoice(v.id)}
                >
                  {v.name}
                </button>
              ))}
              {lipsyncVoiceGroups.builtin.map((v) => (
                <button
                  key={v.id}
                  type="button"
                  className={chipClass(voice === v.id)}
                  onClick={() => persistChipVoice(v.id)}
                >
                  {v.name}
                </button>
              ))}
              {mode !== "video" || faceAssetId ? (
                <Link
                  className="inline-flex min-h-10 items-center rounded-full px-3 text-sm font-semibold text-[var(--studio-brand)] no-underline"
                  to={`/voices?return=play${faceAssetId ? `&bind_face_id=${encodeURIComponent(faceAssetId)}` : ""}`}
                >
                  More
                </Link>
              ) : null}
            </div>
          ) : null}

          {composerPicker === "face" && allowsFace ? (
            <div className="flex gap-2 overflow-x-auto pb-1">
              <Link
                className="inline-flex min-h-10 shrink-0 items-center rounded-full border border-[var(--studio-border)] px-3 text-sm font-bold text-[var(--studio-brand)] no-underline"
                to="/avatars"
              >
                + New
              </Link>
              {facesQuery.isError ? (
                <button
                  type="button"
                  className="inline-flex min-h-10 shrink-0 items-center rounded-full border border-[var(--studio-border)] px-3 text-sm font-semibold text-[var(--studio-brand)]"
                  onClick={() => void facesQuery.refetch()}
                >
                  Retry faces
                </button>
              ) : null}
              {faces.slice(0, 16).map((f) => {
                const on = f.id === faceAssetId;
                return (
                  <button
                    key={f.id}
                    type="button"
                    className={cn(
                      "flex shrink-0 flex-col items-center gap-1 rounded-2xl border p-1.5",
                      on
                        ? "border-[var(--studio-brand)] bg-[var(--studio-chip-on,var(--studio-fill))]"
                        : "border-[var(--studio-border)]",
                    )}
                    onClick={() => onSelectFace(f)}
                  >
                    {f.url ? (
                      <img src={resolveMediaUrl(f.url) || f.url} alt="" className="h-12 w-12 rounded-full object-cover" />
                    ) : (
                      <span className="h-12 w-12 rounded-full bg-[var(--studio-chip-off,var(--studio-fill-quiet))]" />
                    )}
                    <span className="max-w-14 truncate text-[11px] text-[var(--studio-fg)]">
                      {f.label || "Face"}
                    </span>
                  </button>
                );
              })}
            </div>
          ) : null}

          <div
            className={cn(
              "flex items-center gap-1.5 rounded-[22px] border bg-[var(--input-bg,var(--studio-fill-quiet))] py-1.5 pl-2 pr-1.5",
              kindNeedsFace && !faceAssetId
                ? "border-[var(--studio-brand)]"
                : "border-[var(--studio-border)]",
            )}
          >
            {allowsFace ? (
              <button
                type="button"
                className={cn(
                  "h-11 w-11 shrink-0 overflow-hidden rounded-full border-[1.5px]",
                  selectedFace ? "border-solid border-[var(--studio-brand)]" : "border-dashed border-[var(--studio-brand)]",
                )}
                aria-label={selectedFace ? "Change face" : "Add face"}
                aria-pressed={composerPicker === "face"}
                onClick={() => setComposerPicker((p) => (p === "face" ? "none" : "face"))}
              >
                {selectedFace?.url ? (
                  <img src={resolveMediaUrl(selectedFace.url) || selectedFace.url} alt="" className="h-full w-full object-cover" />
                ) : (
                  <span className="text-lg font-bold text-[var(--studio-brand)]">+</span>
                )}
              </button>
            ) : null}
            <PromptFields
              mode={mode}
              isExtending={Boolean(continueFromId)}
              prompt={prompt}
              onPromptChange={editPrompt}
              disabled={generate.isPending}
              inputRef={promptInputRef}
              classNames={{
                shell: "min-w-0 flex-1 border-0 bg-transparent",
                field: "min-h-9 resize-none border-0 bg-transparent px-1 py-2 text-base outline-none placeholder:text-[var(--studio-fg-subtle)]",
              }}
            />
            <div className="flex shrink-0 items-center gap-1.5">
              {canAttachRefs ? (
                <>
                  <input
                    ref={refInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,audio/mpeg,audio/wav,audio/mp4"
                    multiple
                    className="hidden"
                    onChange={(e) => void onRefFilesSelected(e.target.files)}
                  />
                  <button
                    type="button"
                    className="flex h-11 w-11 items-center justify-center rounded-full border border-[var(--studio-border)] bg-[var(--studio-chip-off,var(--studio-fill-quiet))] text-lg font-extrabold text-[var(--studio-brand)]"
                    onClick={() => refInputRef.current?.click()}
                    disabled={refsUploading}
                    aria-label="Add reference"
                  >
                    +
                  </button>
                </>
              ) : null}
              <button
                type="submit"
                className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--studio-brand)] text-white disabled:bg-[var(--studio-chip-off,var(--studio-fill-quiet))]"
                disabled={
                  submitLockRef.current ||
                  generate.isPending ||
                  assist.pending ||
                  !prompt.trim() ||
                  (!workspaceId && workspace.loading) ||
                  (kindNeedsFace && !faceAssetId) ||
                  (kindNeedsFace && !voice)
                }
                aria-label={assist.ready || !modeUsesAssist(mode) ? "Generate" : "Send"}
              >
                {generate.isPending || assist.pending ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <ArrowRight size={18} />
                )}
              </button>
            </div>
          </div>

          {kindNeedsFace && !faceAssetId ? (
            <p className="m-0 text-xs text-[var(--studio-brand)]">Add a face. Tap the face button.</p>
          ) : kindNeedsFace && !voice ? (
            <p className="m-0 text-xs text-[var(--studio-brand)]">Add your voice, or pick a built-in.</p>
          ) : assist.summary.length ? (
            <p className="m-0 text-xs text-[var(--studio-brand)]">{assist.summary.join(" \u00b7 ")}</p>
          ) : (
            <p className="m-0 text-xs leading-snug text-[var(--studio-fg-subtle)]">{metaLine}</p>
          )}
          </div>
        </form>
      </section>
    </div>
  );
}
