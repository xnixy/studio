import { Loader2, Mic, Play, Search, Sparkles, Square, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "../api";
import { useAuth } from "../auth";
import {
  BUILTIN_VOICES,
  DEFAULT_BUILTIN_VOICE_ID,
  isBuiltinVoice,
  isClonedVoice,
  matchesVoiceSearch,
  sortPlayVoices,
  voiceAccentLabel,
  voiceAccentOptions,
  voiceGenderLabel,
} from "../features/play/voices";
import {
  CLONE_LANGUAGES,
  cloneLanguageLabel,
  cloneLanguageOf,
  cloneLanguageSelectLabel,
  cloneReadAloud,
  DEFAULT_CLONE_LANGUAGE,
  type CloneLanguageCode,
} from "../features/play/cloneVoice";
import type { PlayVoiceOption } from "../types";
import { useWorkspace } from "../workspace";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Checkbox,
  Field,
  Input,
  MessageBar,
  Page,
  PageBoard,
  PageHeader,
  PageSection,
  Select,
} from "../ui";
import { Body1, Caption1 } from "../ui/Text";
import { cn } from "../lib/cn";
import { VOICE_STORAGE_KEY } from "./playPageModel";
import {
  CLONE_AUDIO_ACCEPT,
  fileFromRecording,
  micRecordErrorMessage,
  pickAudioRecorderMimeType,
  startMediaRecorder,
} from "../lib/recordAudio";

export function VoicesPage() {
  const auth = useAuth();
  const token = auth.accessToken ?? "";
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const [searchParams] = useSearchParams();
  const bindFaceId = (searchParams.get("bind_face_id") || "").trim() || null;
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const blobUrlRef = useRef<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordChunksRef = useRef<Blob[]>([]);
  const recordTimerRef = useRef<number | null>(null);
  const recordStreamRef = useRef<MediaStream | null>(null);

  const [selectedId, setSelectedId] = useState(() => {
    try {
      return localStorage.getItem(VOICE_STORAGE_KEY) || DEFAULT_BUILTIN_VOICE_ID;
    } catch {
      return DEFAULT_BUILTIN_VOICE_ID;
    }
  });
  const [search, setSearch] = useState("");
  const [genderFilter, setGenderFilter] = useState("all");
  const [accentFilter, setAccentFilter] = useState("all");
  const [cloneLabel, setCloneLabel] = useState("");
  const [consentName, setConsentName] = useState(auth.user?.full_name || "");
  const [consentOk, setConsentOk] = useState(false);
  const [cloneFile, setCloneFile] = useState<File | null>(null);
  const [cloneGender, setCloneGender] = useState<"female" | "male" | "neutral">("female");
  const [cloneLanguage, setCloneLanguage] = useState<CloneLanguageCode>(DEFAULT_CLONE_LANGUAGE);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [previewingId, setPreviewingId] = useState<string | null>(null);
  const [previewLoadingId, setPreviewLoadingId] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [recordBusy, setRecordBusy] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
      if (recordTimerRef.current) {
        window.clearInterval(recordTimerRef.current);
        recordTimerRef.current = null;
      }
      mediaRecorderRef.current?.stop();
      recordStreamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  function stopPreview() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = null;
    }
    setPreviewingId(null);
    setPreviewLoadingId(null);
  }

  async function startRecording() {
    if (!window.isSecureContext) {
      setError(micRecordErrorMessage(null));
      return;
    }
    if (typeof MediaRecorder === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setError("This browser cannot record. Upload a file instead.");
      return;
    }
    setError(null);
    setRecordBusy(true);
    let micTimeout = 0;
    try {
      const stream = await Promise.race([
        navigator.mediaDevices.getUserMedia({ audio: true }),
        new Promise<never>((_, reject) => {
          micTimeout = window.setTimeout(
            () => reject(new DOMException("Mic prompt timed out", "AbortError")),
            20_000,
          );
        }),
      ]);
      window.clearTimeout(micTimeout);
      recordStreamRef.current = stream;
      recordChunksRef.current = [];
      const mimeType = pickAudioRecorderMimeType();
      const rec = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      mediaRecorderRef.current = rec;
      rec.ondataavailable = (event) => {
        if (event.data.size) recordChunksRef.current.push(event.data);
      };
      rec.onerror = () => {
        stream.getTracks().forEach((t) => t.stop());
        recordStreamRef.current = null;
        setRecording(false);
        setRecordBusy(false);
        setError("Could not start the mic. Upload a file instead.");
      };
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        recordStreamRef.current = null;
        const blob = new Blob(recordChunksRef.current, {
          type: rec.mimeType || mimeType || "audio/mp4",
        });
        setCloneFile(fileFromRecording(blob, rec.mimeType || mimeType || "audio/mp4"));
        if (!cloneLabel.trim()) setCloneLabel("My voice");
        setRecording(false);
        setRecordBusy(false);
        if (recordTimerRef.current) {
          window.clearInterval(recordTimerRef.current);
          recordTimerRef.current = null;
        }
      };
      startMediaRecorder(rec);
      setRecording(true);
      setRecordSeconds(0);
      recordTimerRef.current = window.setInterval(() => {
        setRecordSeconds((s) => {
          const next = s + 1;
          if (next >= 90) stopRecording();
          return next;
        });
      }, 1000);
    } catch (err) {
      window.clearTimeout(micTimeout);
      recordStreamRef.current?.getTracks().forEach((t) => t.stop());
      recordStreamRef.current = null;
      setRecording(false);
      setError(micRecordErrorMessage(err));
    } finally {
      setRecordBusy(false);
    }
  }

  function stopRecording() {
    if (recordTimerRef.current) {
      window.clearInterval(recordTimerRef.current);
      recordTimerRef.current = null;
    }
    const rec = mediaRecorderRef.current;
    mediaRecorderRef.current = null;
    if (rec && rec.state !== "inactive") rec.stop();
    setRecording(false);
  }

  async function playPreview(voiceId: string) {
    if (!workspaceId || !token) return;
    if (previewingId === voiceId) {
      stopPreview();
      return;
    }
    stopPreview();
    setError(null);
    setPreviewLoadingId(voiceId);
    try {
      const url = await api.previewPlayVoice(token, workspaceId, voiceId);
      blobUrlRef.current = url;
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => stopPreview();
      audio.onerror = () => {
        setError("Could not play this preview.");
        stopPreview();
      };
      setPreviewingId(voiceId);
      setPreviewLoadingId(null);
      await audio.play();
    } catch (err) {
      setPreviewLoadingId(null);
      setPreviewingId(null);
      setError(err instanceof ApiError ? err.message : "Could not load preview");
    }
  }

  const voicesQuery = useQuery({
    queryKey: ["play", "voices", workspaceId],
    queryFn: () => api.listPlayVoices(token, workspaceId!),
    enabled: Boolean(token && workspaceId),
    staleTime: 60_000,
    retry: 1,
  });

  const cloneMutation = useMutation({
    mutationFn: () => {
      if (!cloneFile) throw new Error("Pick an audio file first.");
      return api.clonePlayVoice(token, workspaceId!, {
        label: cloneLabel,
        consentName,
        gender: cloneGender,
        language: cloneLanguage,
        file: cloneFile,
        bindFaceId,
      });
    },
    onSuccess: async (voice) => {
      setError(null);
      setNotice(`Cloned "${voice.name}". Listen to the preview, then use it in Create.`);
      setCloneLabel("");
      setConsentOk(false);
      setCloneFile(null);
      if (fileRef.current) fileRef.current.value = "";
      selectVoice(voice.id);
      await qc.invalidateQueries({ queryKey: ["play", "voices", workspaceId] });
      await playPreview(voice.id);
    },
    onError: (err) => {
      setNotice(null);
      setError(err instanceof Error ? err.message : "Could not clone voice");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (voiceId: string) => api.deletePlayVoice(token, workspaceId!, voiceId),
    onSuccess: async (_void, voiceId) => {
      setError(null);
      setNotice("Custom voice removed.");
      if (selectedId === voiceId) selectVoice(DEFAULT_BUILTIN_VOICE_ID);
      await qc.invalidateQueries({ queryKey: ["play", "voices", workspaceId] });
    },
    onError: (err) => {
      setNotice(null);
      setError(err instanceof Error ? err.message : "Could not delete voice");
    },
  });

  const voices = useMemo(() => {
    const fromApi = voicesQuery.data?.voices;
    if (fromApi?.length) return sortPlayVoices(fromApi);
    return sortPlayVoices(BUILTIN_VOICES);
  }, [voicesQuery.data]);

  const builtin = useMemo(() => voices.filter(isBuiltinVoice), [voices]);
  const custom = useMemo(() => voices.filter(isClonedVoice), [voices]);
  const accentOptions = useMemo(() => voiceAccentOptions(builtin), [builtin]);

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

  const accessFromList = voicesQuery.data?.custom_voices_access;
  const canClone = accessFromList?.can_clone ?? true;
  const atCap = (accessFromList?.clone_count ?? 0) >= (accessFromList?.clone_cap ?? 1) && !canClone;

  const cloneReady =
    canClone &&
    consentOk &&
    cloneLabel.trim().length > 0 &&
    consentName.trim().length > 0 &&
    Boolean(cloneFile) &&
    Boolean(cloneGender) &&
    !cloneMutation.isPending;

  function selectVoice(id: string) {
    if (bindFaceId && workspaceId) {
      void api
        .bindPlayFaceVoice(token, bindFaceId, workspaceId, id)
        .then(async () => {
          await qc.invalidateQueries({ queryKey: ["play", "faces", workspaceId] });
          const name = voices.find((v) => v.id === id)?.name || "Voice";
          setNotice(`${name} is on this Face.`);
          setError(null);
        })
        .catch((e) => {
          setError(e instanceof ApiError ? e.message : "Could not bind that voice.");
        });
      return;
    }
    setSelectedId(id);
    try {
      localStorage.setItem(VOICE_STORAGE_KEY, id);
    } catch {
      /* ignore */
    }
    const name = voices.find((v) => v.id === id)?.name || "Voice";
    setNotice(`${name} is the fallback when a Face has no bound voice.`);
    setError(null);
  }

  if (!workspaceId) {
    return (
      <Page wide>
        <div className="grid place-items-center gap-2 py-16 text-center">
          <Loader2 className="animate-spin text-[var(--studio-brand)]" size={28} />
          <p className="m-0 text-sm text-[var(--studio-fg-muted)]">Loading your space…</p>
        </div>
      </Page>
    );
  }

  return (
    <Page wide>
      <PageBoard>
        <PageHeader
          title={
            <>
              <Mic size={18} className="text-[var(--studio-brand)]" aria-hidden />
              Voices
            </>
          }
          subtitle={
            bindFaceId
              ? "Tap a voice to bind it to this Face. That Face uses it on Talking and spoken Scene."
              : "Tap a voice to bind it to a Face. Fallback is only used when a Face has no bind. One custom voice per workspace."
          }
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <Link to="/play">
                <Button type="button" size="small" variant="secondary">
                  <Sparkles size={14} aria-hidden />
                  Create
                </Button>
              </Link>
            </div>
          }
        />
        <PageSection>
          {error ? <MessageBar intent="error">{error}</MessageBar> : null}
          {notice ? <MessageBar intent="success">{notice}</MessageBar> : null}

          <div className="grid gap-2">
            <div className="flex flex-wrap items-end justify-between gap-2">
              <div className="grid gap-1">
                <h2 className="m-0 text-sm font-bold text-[var(--studio-fg)]">Built-in</h2>
                <Caption1>Search by name, gender, or accent. Create keeps five on the bar.</Caption1>
              </div>
              <div className="flex min-w-[12rem] max-w-3xl flex-1 flex-wrap items-end gap-2">
                <Field label="Search" className="min-w-[10rem] flex-1">
                  <Input
                    size="small"
                    value={search}
                    placeholder="Name, gender, or accent"
                    aria-label="Search built-in voices"
                    contentBefore={<Search size={14} className="text-[var(--studio-fg-muted)]" aria-hidden />}
                    onChange={(_, data) => setSearch(data.value)}
                  />
                </Field>
                <Field label="Gender" className="w-[8.5rem]">
                  <Select
                    size="sm"
                    aria-label="Filter by gender"
                    value={genderFilter}
                    onChange={(e) => setGenderFilter(e.target.value)}
                  >
                    <option value="all">All</option>
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                    <option value="neutral">Neutral</option>
                  </Select>
                </Field>
                <Field label="Accent" className="w-[10rem]">
                  <Select
                    size="sm"
                    aria-label="Filter by accent"
                    value={accentFilter}
                    onChange={(e) => setAccentFilter(e.target.value)}
                  >
                    <option value="all">All</option>
                    {accentOptions.map((accent) => (
                      <option key={accent} value={accent}>
                        {voiceAccentLabel(accent)}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>
            </div>
            <div className="max-h-[28rem] overflow-y-auto rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-2">
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {filteredBuiltin.map((voice) => (
                  <VoiceCard
                    key={voice.id}
                    voice={voice}
                    selected={selectedId === voice.id}
                    onSelect={() => selectVoice(voice.id)}
                    onPreview={() => void playPreview(voice.id)}
                    previewLoading={previewLoadingId === voice.id}
                    previewPlaying={previewingId === voice.id}
                  />
                ))}
              </div>
              {filteredBuiltin.length === 0 ? (
                <Caption1 className="block p-3">No built-in voices match those filters.</Caption1>
              ) : null}
            </div>
          </div>

          <div className="grid gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="m-0 text-sm font-bold text-[var(--studio-fg)]">Custom</h2>
              <Badge color={canClone ? "success" : "subtle"}>{canClone ? "Open" : "Full"}</Badge>
            </div>

            {custom.length > 0 ? (
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {custom.map((voice) => (
                  <VoiceCard
                    key={voice.id}
                    voice={voice}
                    selected={selectedId === voice.id}
                    onSelect={() => selectVoice(voice.id)}
                    onPreview={
                      voice.available !== false ? () => void playPreview(voice.id) : undefined
                    }
                    previewLoading={previewLoadingId === voice.id}
                    previewPlaying={previewingId === voice.id}
                    onDelete={() => {
                            if (
                              window.confirm(
                                `Remove “${voice.name}”? This cannot be undone.`,
                              )
                            ) {
                              deleteMutation.mutate(voice.id);
                            }
                          }}
                    deleting={deleteMutation.isPending && deleteMutation.variables === voice.id}
                  />
                ))}
              </div>
            ) : null}

            {canClone ? (
              <div className="grid gap-3 rounded-2xl border border-[var(--color-success-border)] bg-[var(--studio-fill-quiet)] p-3">
                <div className="grid gap-1">
                  <Body1 className="m-0">Clone a voice for this workspace</Body1>
                  <Caption1>
                    Quiet room, one speaker. Read the lines below for 30 to 90 seconds. No music.
                  </Caption1>
                </div>
                <Field
                  label="Language"
                  hint="Pick the language you will read. The script below matches it."
                >
                  <Select
                    aria-label="Clone language"
                    value={cloneLanguage}
                    onChange={(e) => {
                      const next = e.target.value as CloneLanguageCode;
                      if (next === cloneLanguage) return;
                      setCloneLanguage(next);
                      setCloneFile(null);
                      if (fileRef.current) fileRef.current.value = "";
                      setError(null);
                    }}
                  >
                    {CLONE_LANGUAGES.map((lang) => (
                      <option key={lang.code} value={lang.code}>
                        {cloneLanguageSelectLabel(lang)}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Label" hint="Shown in the Voice list.">
                  <Input
                    value={cloneLabel}
                    maxLength={80}
                    placeholder="e.g. Brand narrator"
                    onChange={(_, data) => setCloneLabel(data.value)}
                  />
                </Field>
                <Field label="Your name" hint="For consent record.">
                  <Input
                    value={consentName}
                    maxLength={120}
                    placeholder="Full name"
                    onChange={(_, data) => setConsentName(data.value)}
                  />
                </Field>
                <Field label="Gender" hint="Used so Talking can match a stand-in voice.">
                  <select
                    className="min-h-10 w-full rounded-lg border border-[var(--studio-border)] bg-[var(--studio-panel)] px-3 text-sm"
                    value={cloneGender}
                    onChange={(e) =>
                      setCloneGender(e.target.value as "female" | "male" | "neutral")
                    }
                  >
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                    <option value="neutral">Neutral</option>
                  </select>
                </Field>
                <Field
                  label="Audio sample"
                  hint="Quiet room, one speaker, 30 to 90 seconds. Voice Memos: Share, Save to Files, then pick the .m4a."
                >
                  <div className="grid gap-2">
                    <p className="m-0 text-[0.78rem] font-semibold text-[var(--studio-fg)]">
                      Read this out loud
                    </p>
                    <Caption1>
                      Like a call. Pause at the periods. If you have extra time, add a short story from today.
                    </Caption1>
                    <pre
                      dir={cloneLanguageOf(cloneLanguage).rtl ? "rtl" : "ltr"}
                      className="m-0 whitespace-pre-wrap rounded-xl border border-[var(--studio-border)] bg-[var(--studio-panel)] p-3 text-[0.92rem] leading-relaxed text-[var(--studio-fg)]"
                    >
                      {cloneReadAloud(cloneLanguage)}
                    </pre>
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      type="button"
                      size="small"
                      variant="secondary"
                      disabled={recordBusy}
                      onClick={() => (recording ? stopRecording() : void startRecording())}
                    >
                      {recording
                        ? `Stop · ${recordSeconds}s`
                        : recordBusy
                          ? "Allow mic…"
                          : "Record"}
                    </Button>
                    <input
                    ref={fileRef}
                    type="file"
                    accept={CLONE_AUDIO_ACCEPT}
                    className="block min-w-0 flex-1 text-sm text-[var(--studio-fg)] file:mr-3 file:rounded-lg file:border-0 file:bg-[var(--studio-brand)] file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-white"
                    onChange={(e) => {
                      const file = e.target.files?.[0] ?? null;
                      setCloneFile(file);
                      if (file && !cloneLabel.trim()) {
                        const base = file.name.replace(/\.[^.]+$/, "").trim();
                        if (base) setCloneLabel(base.slice(0, 80));
                      }
                    }}
                  />
                  </div>
                  {cloneFile ? <Caption1>{cloneFile.name}</Caption1> : null}
                  {error ? (
                    <Caption1 className="text-[var(--studio-danger)]">{error}</Caption1>
                  ) : null}
                  </div>
                </Field>
                <Checkbox
                  checked={consentOk}
                  label="I own this voice or have rights to use it."
                  onChange={(_, data) => setConsentOk(data.checked)}
                />
                <div>
                  <Button
                    type="button"
                    size="small"
                    disabled={!cloneReady}
                    onClick={() => {
                      setError(null);
                      setNotice(null);
                      cloneMutation.mutate();
                    }}
                  >
                    {cloneMutation.isPending ? (
                      <>
                        <Loader2 size={14} className="animate-spin" aria-hidden />
                        Cloning…
                      </>
                    ) : (
                      "Clone voice"
                    )}
                  </Button>
                </div>
              </div>
            ) : null}

            {atCap ? (
              <Caption1>You have one custom voice. Delete it to record a new one.</Caption1>
            ) : null}
          </div>
        </PageSection>
      </PageBoard>
    </Page>
  );
}

function VoiceCard({
  voice,
  selected,
  onSelect,
  onPreview,
  previewLoading,
  previewPlaying,
  onDelete,
  deleting,
}: {
  voice: PlayVoiceOption;
  selected: boolean;
  onSelect: () => void;
  onPreview?: () => void;
  previewLoading?: boolean;
  previewPlaying?: boolean;
  onDelete?: () => void;
  deleting?: boolean;
}) {
  const custom = isClonedVoice(voice);
  return (
    <Card
      className={cn(
        "cursor-pointer transition-colors",
        selected && "border-[var(--studio-brand)] shadow-[0_0_0_1px_var(--studio-brand)]",
      )}
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
    >
      <CardHeader
        header={
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm font-semibold text-[var(--studio-fg)]">{voice.name}</span>
            <div className="flex flex-wrap items-center gap-1">
              {selected ? <Badge color="brand">Default</Badge> : null}
              {voiceGenderLabel(voice.gender) ? (
                <Badge color="subtle">{voiceGenderLabel(voice.gender)}</Badge>
              ) : null}
              {voiceAccentLabel(voice.accent) ? (
                <Badge color="subtle">{voiceAccentLabel(voice.accent)}</Badge>
              ) : null}
              {custom ? <Badge color="brand">Custom</Badge> : null}
              {custom && cloneLanguageLabel(voice.language) ? (
                <Badge color="subtle">{cloneLanguageLabel(voice.language)}</Badge>
              ) : null}
            </div>
          </div>
        }
        description={
          <p className="m-0 text-sm text-[var(--studio-fg-muted)]">
            {voice.description || (custom ? "Custom voice" : "Built-in voice")}
          </p>
        }
      >
        {onPreview || onDelete ? (
          <div className="flex flex-wrap items-center gap-2 pt-1">
            {onPreview ? (
              <Button
                type="button"
                size="small"
                variant="secondary"
                disabled={previewLoading}
                aria-label={
                  previewPlaying ? `Stop ${voice.name} preview` : `Preview ${voice.name}`
                }
                onClick={(e) => {
                  e.stopPropagation();
                  onPreview();
                }}
              >
                {previewLoading ? (
                  <Loader2 size={14} className="animate-spin" aria-hidden />
                ) : previewPlaying ? (
                  <Square size={14} aria-hidden />
                ) : (
                  <Play size={14} aria-hidden />
                )}
                {previewLoading ? "Loading…" : previewPlaying ? "Stop" : "Preview"}
              </Button>
            ) : null}
            {onDelete ? (
              <Button
                type="button"
                size="small"
                variant="secondary"
                disabled={deleting}
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
              >
                {deleting ? (
                  <Loader2 size={14} className="animate-spin" aria-hidden />
                ) : (
                  <Trash2 size={14} aria-hidden />
                )}
                Delete
              </Button>
            ) : null}
          </div>
        ) : null}
      </CardHeader>
    </Card>
  );
}
