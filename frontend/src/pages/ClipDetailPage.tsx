import { ArrowLeft, Clapperboard, Loader2, Mic2, Pencil, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { useWorkspace } from "../workspace";
import { BUILTIN_VOICES, DEFAULT_BUILTIN_VOICE_ID } from "../features/play/voices";
import type { PlayMode, PlayPlatform } from "../types";
import { downloadMediaFile, isSignedMediaUrlExpired, openMediaInNewTab, playGenerationPosterUrl, resolveMediaUrl } from "../lib/mediaUrl";
import { isClonedVoice } from "../features/play/voices";
import { estimateVoiceoverSeconds, promptForDisplay, spokenLineFromAvatarPrompt } from "../lib/playPricing";
import { Button, MessageBar, Page, PageBoard, PageHeader, PageSection, Select } from "../ui";

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

export function ClipDetailPage() {
  const { clipId } = useParams<{ clipId: string }>();
  const auth = useAuth();
  const token = auth.accessToken ?? "";
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const navigate = useNavigate();
  const qc = useQueryClient();

  const clipQuery = useQuery({
    queryKey: ["play", "generation", clipId],
    queryFn: () => api.getPlayGeneration(token, clipId!),
    enabled: Boolean(token && clipId),
    staleTime: 5_000,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "processing" || s === "queued" ? 2500 : false;
    },
  });

  const clip = clipQuery.data;
  const [editPrompt, setEditPrompt] = useState("");
  const [editMode, setEditMode] = useState<PlayMode>("avatar");
  const [editPlatform, setEditPlatform] = useState<PlayPlatform>("tiktok");
  const [editDuration, setEditDuration] = useState(10);
  const [revoiceScript, setRevoiceScript] = useState("");
  const [revoiceVoice, setRevoiceVoice] = useState(DEFAULT_BUILTIN_VOICE_ID);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!clip) return;
    setEditPrompt(promptForDisplay(clip.prompt, clip.mode));
    const m = clip.mode as PlayMode;
    if (m === "lipsync") setEditMode("avatar");
    else if (m === "avatar" || m === "video" || m === "image") setEditMode(m);
    const p = clip.platform as PlayPlatform;
    if (p === "tiktok" || p === "feed" || p === "reels" || p === "shorts" || p === "custom") {
      setEditPlatform(p === "feed" ? "feed" : "tiktok");
    }
    const d = clip.metadata?.duration_seconds;
    if (typeof d === "number" && d >= 1 && d <= 15) setEditDuration(d);
    setRevoiceScript(spokenLineFromAvatarPrompt(clip.prompt || "") || clip.prompt || "");
    setRevoiceVoice(voiceFromMeta(clip.metadata));
  }, [clip?.id, clip?.prompt, clip?.mode, clip?.platform, clip?.metadata]);

  useEffect(() => {
    if (!token || !clipId || !clip) return;
    const refreshExpired = () => {
      if (typeof document !== "undefined" && document.visibilityState !== "visible") return;
      if (clip.status === "ready" && isSignedMediaUrlExpired(clip.url)) {
        void clipQuery.refetch();
      }
    };
    refreshExpired();
    document.addEventListener("visibilitychange", refreshExpired);
    return () => document.removeEventListener("visibilitychange", refreshExpired);
  }, [token, clipId, clip, clipQuery]);

  // Poll processing assets via dedicated endpoint
  useEffect(() => {
    if (!clipId || !clip || !token) return;
    if (clip.status !== "processing" && clip.status !== "queued") return;
    if (clip.asset_type !== "video") return;
    let cancelled = false;
    const tick = async () => {
      try {
        await api.pollVideoAsset(token, clipId);
        if (!cancelled) void clipQuery.refetch();
      } catch {
        /* keep trying */
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), 2500);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [clipId, clip?.status, clip?.asset_type, token, clipQuery]);

  const faceId = useMemo(() => faceIdFromMeta(clip?.metadata), [clip?.metadata]);
  const ready = clip?.status === "ready" && Boolean(clip.url);
  const isVideo = clip?.asset_type === "video";
  const canRevoice = Boolean(ready && isVideo && faceId);

  const voicesQuery = useQuery({
    queryKey: ["play", "voices", workspaceId],
    queryFn: () => api.listPlayVoices(token, workspaceId!),
    enabled: Boolean(token && workspaceId && canRevoice),
    staleTime: 60_000,
  });

  const revoiceVoices = useMemo(() => {
    const fromApi = (voicesQuery.data?.voices || []).filter((v) => v.available !== false);
    return fromApi.length ? fromApi : BUILTIN_VOICES;
  }, [voicesQuery.data]);

  const regenerate = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Sign in to regenerate");
      if (!workspaceId) throw new Error("Account still loading");
      const text = editPrompt.trim();
      if (!text) throw new Error("Write a prompt first");
      if ((editMode === "avatar") && !faceId) {
        throw new Error("This clip has no saved face. Open Create and pick a face.");
      }
      const payload: {
        workspace_id: string;
        mode: PlayMode;
        platform: PlayPlatform;
        prompt: string;
        face_asset_id?: string | null;
        voice?: string;
        duration_seconds?: number;
      } = {
        workspace_id: workspaceId,
        mode: editMode === "lipsync" ? "avatar" : editMode,
        platform: editPlatform,
        prompt: text,
        face_asset_id: editMode === "avatar" || editMode === "lipsync" ? faceId : null,
      };
      if (editMode === "avatar" || editMode === "lipsync" || editMode === "video") {
        payload.voice = revoiceVoice || DEFAULT_BUILTIN_VOICE_ID;
      }
      if (editMode === "avatar" || editMode === "video") payload.duration_seconds = editDuration;
      return api.playGenerate(token, payload);
    },
    onSuccess: (res) => {
      setError(null);
      void qc.invalidateQueries({ queryKey: ["play", "generations", workspaceId] });
      void qc.invalidateQueries({ queryKey: ["workspaces", "billing", workspaceId] });
      navigate(`/clips/${res.generation.id}`, { replace: false });
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Regenerate failed");
    },
  });

  const revoice = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Sign in to revoice");
      if (!workspaceId) throw new Error("Account still loading");
      if (!clipId) throw new Error("Missing clip");
      const text = revoiceScript.trim();
      if (!text) throw new Error("Write the exact words to speak");
      if (!faceId) {
        throw new Error("This clip has no saved face. Revoice needs a Talking clip with a face.");
      }
      return api.playGenerate(token, {
        workspace_id: workspaceId,
        mode: "avatar",
        platform: editPlatform === "feed" ? "feed" : "tiktok",
        prompt: text,
        face_asset_id: faceId,
        voice: revoiceVoice || DEFAULT_BUILTIN_VOICE_ID,
        revoice_of_asset_id: clipId,
      });
    },
    onSuccess: (res) => {
      setError(null);
      void qc.invalidateQueries({ queryKey: ["play", "generations", workspaceId] });
      void qc.invalidateQueries({ queryKey: ["workspaces", "billing", workspaceId] });
      navigate(`/clips/${res.generation.id}`, { replace: false });
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Revoice failed");
    },
  });

  const removeClip = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Sign in to delete");
      if (!clipId) throw new Error("Missing clip");
      await api.deletePlayGeneration(token, clipId);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["play", "generations", workspaceId] });
      navigate("/clips", { replace: true });
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Delete failed");
    },
  });

  function openInCreate() {
    const params = new URLSearchParams();
    params.set("mode", editMode);
    params.set("platform", editPlatform === "feed" ? "feed" : "tiktok");
    if (faceId) params.set("face", faceId);
    if (editPrompt.trim()) params.set("prompt", editPrompt.trim());
    if (clipId) params.set("from", clipId);
    navigate(`/play?${params.toString()}`);
  }

  function continueInCreate() {
    if (!clipId) return;
    const params = new URLSearchParams();
    params.set(
      "mode",
      clip?.mode === "avatar" || clip?.mode === "lipsync" || clip?.mode === "video"
        ? clip.mode === "lipsync"
          ? "avatar"
          : clip.mode
        : "video",
    );
    params.set("continue", clipId);
    params.set("from", clipId);
    if (faceId) params.set("face", faceId);
    if (editPrompt.trim()) params.set("prompt", editPrompt.trim());
    navigate(`/play?${params.toString()}`);
  }

  if (clipQuery.isLoading) {
    return (
      <Page>
        <div className="grid place-items-center gap-2 py-20 text-[var(--studio-fg-muted)]">
          <Loader2 className="animate-spin text-[var(--studio-brand)]" size={28} />
          <span className="text-sm">Loading clip…</span>
        </div>
      </Page>
    );
  }

  if (clipQuery.isError || !clip) {
    return (
      <Page>
        <div className="grid gap-3 py-16 text-center">
          <p className="m-0 text-sm text-[var(--color-danger,#f87171)]">Clip not found.</p>
          <Link to="/clips">
            <Button type="button" variant="secondary">
              Back to clips
            </Button>
          </Link>
        </div>
      </Page>
    );
  }

  return (
    <Page>
      <PageBoard>
        <PageHeader
          title={
            <>
              <Clapperboard size={18} className="text-[var(--studio-brand)]" aria-hidden />
              Clip
            </>
          }
          subtitle={
            <>
              <Link
                to="/clips"
                className="inline-flex items-center gap-1 font-semibold text-[var(--studio-brand)] no-underline hover:underline"
              >
                <ArrowLeft size={12} aria-hidden />
                Library
              </Link>
              {" · "}
              {clip.mode} · {clip.platform} · {clip.status}
              {clip.provider_model ? ` · ${clip.provider_model}` : ""}
            </>
          }
          actions={
            <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-wrap sm:justify-end">
              <Button
                type="button"
                variant="secondary"
                size="small"
                className="col-span-2 sm:col-span-1"
                onClick={openInCreate}
              >
                <Sparkles size={14} aria-hidden />
                Open in Create
              </Button>
              {isVideo && ready ? (
                <Button
                  type="button"
                  size="small"
                  onClick={continueInCreate}
                  title="Next shot with Seedance from this clip"
                >
                  Extend
                </Button>
              ) : null}
              <Link to="/play" className="min-w-0">
                <Button type="button" size="small" className="w-full">
                  New clip
                </Button>
              </Link>
              <Button
                type="button"
                variant="secondary"
                size="small"
                disabled={removeClip.isPending}
                onClick={() => {
                  if (window.confirm("Delete this clip? This cannot be undone.")) {
                    removeClip.mutate();
                  }
                }}
              >
                <Trash2 size={14} aria-hidden />
                {removeClip.isPending ? "Deleting…" : "Delete"}
              </Button>
            </div>
          }
        />
        <PageSection>
      {error ? <MessageBar intent="error">{error}</MessageBar> : null}

      <section className="overflow-hidden rounded-[22px] border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] shadow-[var(--studio-card-shadow)] backdrop-blur-md">
        <div className="relative min-h-[14rem] bg-black/40">
          {clip.status === "processing" || clip.status === "queued" ? (
            <div className="grid min-h-[16rem] place-items-center gap-2 text-[var(--studio-fg-muted)]">
              <Loader2 className="animate-spin text-[var(--studio-brand)]" size={28} />
              <span className="text-sm">Generating…</span>
            </div>
          ) : null}
          {ready && isVideo ? (
            <video
              src={resolveMediaUrl(clip.url) || clip.url!}
              poster={resolveMediaUrl(playGenerationPosterUrl(clip)) || undefined}
              controls
              className="max-h-[32rem] w-full"
              playsInline
              preload="metadata"
            />
          ) : null}
          {ready && !isVideo ? (
            <img
              src={resolveMediaUrl(clip.url) || clip.url!}
              alt={clip.prompt || "Clip"}
              className="max-h-[32rem] w-full object-contain"
            />
          ) : null}
          {clip.status === "failed" ? (
            <div className="grid min-h-[10rem] place-items-center px-4 text-center text-sm text-[var(--color-danger,#f87171)]">
              {clip.error_message || "Generation failed"}
            </div>
          ) : null}
        </div>
        <div className="grid gap-2 p-4">
          <p className="m-0 text-sm text-[var(--studio-fg)] whitespace-pre-wrap">
            {promptForDisplay(clip.prompt, clip.mode) || "No prompt"}
          </p>
          {ready && clip.url ? (
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                className="border-0 bg-transparent p-0 text-sm font-semibold text-[var(--studio-brand)] hover:underline"
                onClick={() => openMediaInNewTab(clip.url!)}
              >
                Open
              </button>
              <button
                type="button"
                className="border-0 bg-transparent p-0 text-sm font-semibold text-[var(--studio-brand)] hover:underline"
                onClick={() => {
                  void downloadMediaFile(
                    clip.url!,
                    `studio-clip-${clip.id.slice(0, 8)}.${isVideo ? "mp4" : "jpg"}`,
                  ).catch((err) =>
                    setError(err instanceof Error ? err.message : "Download failed"),
                  );
                }}
              >
                Download
              </button>
            </div>
          ) : null}
          {faceId ? (
            <p className="m-0 text-[0.78rem] text-[var(--studio-fg-muted)]">Avatar face is saved with this clip.</p>
          ) : (
            <p className="m-0 text-[0.78rem] text-[var(--studio-fg-muted)]">
              No face linked (text-only or free video).
            </p>
          )}
        </div>
      </section>

      {ready && isVideo ? (
        <section className="grid gap-3 rounded-[22px] border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-4 shadow-[var(--studio-card-shadow)] backdrop-blur-md">
          <div className="flex items-center gap-2">
            <Mic2 size={16} className="text-[var(--studio-brand)]" aria-hidden />
            <h2 className="m-0 text-base font-bold text-[var(--studio-fg)]">Revoice</h2>
          </div>
          <p className="m-0 text-[0.82rem] text-[var(--studio-fg-muted)]">
            Keep the look of this face. Set exact words and a voice. Makes a <strong>new</strong> Talking
            clip. Revoice locks the script and TTS.
          </p>
          {canRevoice ? (
            <>
              <label className="grid gap-1 text-[0.78rem] text-[var(--studio-fg-muted)]">
                Exact script
                <textarea
                  className="min-h-[4.5rem] resize-y rounded-xl border border-[var(--studio-border)] bg-transparent px-3 py-2 text-base text-[var(--studio-fg)]"
                  value={revoiceScript}
                  onChange={(e) => setRevoiceScript(e.target.value)}
                  rows={3}
                  placeholder="Only the words to speak…"
                  aria-label="Revoice script"
                />
              </label>
              <label className="grid gap-1 text-[0.78rem] text-[var(--studio-fg-muted)]">
                Voice
                <Select
                  size="sm"
                  value={revoiceVoice}
                  onChange={(e) => setRevoiceVoice(e.target.value)}
                  aria-label="Revoice voice"
                >
                  {revoiceVoices.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name}
                      {(v.source === "cloned" || v.source === "custom") ? " (custom)" : ""}
                    </option>
                  ))}
                  {!revoiceVoices.some((v) => v.id === revoiceVoice) && revoiceVoice ? (
                    <option value={revoiceVoice}>{revoiceVoice}</option>
                  ) : null}
                </Select>
              </label>
              <p className="m-0 text-[0.78rem] text-[var(--studio-fg-subtle)]">
                ~{estimateVoiceoverSeconds(revoiceScript)}s voice · spends clip credits
                {revoiceVoices.some(
                  (v) =>
                    v.id === revoiceVoice &&
                    isClonedVoice(v),
                )
                  ? " + voice seconds"
                  : ""}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  disabled={revoice.isPending || !revoiceScript.trim()}
                  onClick={() => revoice.mutate()}
                >
                  {revoice.isPending ? (
                    <>
                      <Loader2 size={16} className="animate-spin" aria-hidden />
                      Revoicing…
                    </>
                  ) : (
                    <>
                      <Mic2 size={16} aria-hidden />
                      Generate revoice
                    </>
                  )}
                </Button>
                <Link to={`/voices`}>
                  <Button type="button" variant="secondary">
                    Manage voices
                  </Button>
                </Link>
              </div>
            </>
          ) : (
            <p className="m-0 text-[0.82rem] text-[var(--studio-fg-muted)]">
              Revoice needs a face saved on the clip. Scene without a face cannot revoice here.
            </p>
          )}
        </section>
      ) : null}

      <section className="grid gap-3 rounded-[22px] border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-4 shadow-[var(--studio-card-shadow)] backdrop-blur-md">
        <div className="flex items-center gap-2">
          <Pencil size={16} className="text-[var(--studio-brand)]" aria-hidden />
          <h2 className="m-0 text-base font-bold text-[var(--studio-fg)]">Edit &amp; regenerate</h2>
        </div>
        <p className="m-0 text-[0.82rem] text-[var(--studio-fg-muted)]">
          Change the prompt (and type if you want). This makes a <strong>new</strong> clip. The original stays in
          your Library. Model pick and credit cost live on Create.
        </p>
        <label className="grid gap-1 text-[0.78rem] text-[var(--studio-fg-muted)]">
          Prompt
          <textarea
            className="min-h-[5rem] resize-y rounded-xl border border-[var(--studio-border)] bg-transparent px-3 py-2 text-base text-[var(--studio-fg)]"
            value={editPrompt}
            onChange={(e) => setEditPrompt(e.target.value)}
            rows={3}
            aria-label="Edit prompt"
          />
        </label>
        <div className="flex flex-wrap gap-3">
          <label className="grid gap-1 text-[0.78rem] text-[var(--studio-fg-muted)]">
            Type
            <Select
              size="sm"
              value={editMode}
              onChange={(e) => setEditMode(e.target.value as PlayMode)}
              aria-label="Clip type"
            >
              <option value="avatar">Talking clip</option>
              <option value="video">Video</option>
              <option value="image">Still</option>
            </Select>
          </label>
          <label className="grid gap-1 text-[0.78rem] text-[var(--studio-fg-muted)]">
            Format
            <Select
              size="sm"
              value={editPlatform}
              onChange={(e) => setEditPlatform(e.target.value as PlayPlatform)}
              aria-label="Format"
            >
              <option value="tiktok">Vertical</option>
              <option value="feed">Square</option>
            </Select>
          </label>
          {editMode === "avatar" || editMode === "video" ? (
            <label className="grid gap-1 text-[0.78rem] text-[var(--studio-fg-muted)]">
              Length
              <Select
                size="sm"
                value={String(editDuration)}
                onChange={(e) => setEditDuration(Number(e.target.value))}
                aria-label="Clip length"
              >
                {[5, 8, 10, 12, 15].map((d) => (
                  <option key={d} value={d}>
                    {d}s
                  </option>
                ))}
              </Select>
            </label>
          ) : null}
          {editMode === "avatar" ? (
            <label className="grid gap-1 text-[0.78rem] text-[var(--studio-fg-muted)]">
              Voice
              <Select
                size="sm"
                value={revoiceVoice}
                onChange={(e) => setRevoiceVoice(e.target.value)}
                aria-label="Talking voice"
              >
                {revoiceVoices.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </Select>
            </label>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            disabled={regenerate.isPending || !editPrompt.trim()}
            onClick={() => regenerate.mutate()}
          >
            {regenerate.isPending ? (
              <>
                <Loader2 size={16} className="animate-spin" aria-hidden />
                Regenerating…
              </>
            ) : (
              <>
                <Sparkles size={16} aria-hidden />
                Generate new version
              </>
            )}
          </Button>
          <Button type="button" variant="secondary" onClick={openInCreate}>
            Fine-tune in Create
          </Button>
        </div>
      </section>
        </PageSection>
      </PageBoard>
    </Page>
  );
}
