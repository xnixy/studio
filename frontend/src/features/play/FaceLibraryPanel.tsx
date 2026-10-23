import { Check, Loader2, Sparkles, Trash2, Upload } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../api";
import type { PlayFace, PlayModelOption } from "../../types";
import { cn } from "../../lib/cn";
import { isSignedMediaUrlExpired, resolveMediaUrl } from "../../lib/mediaUrl";
import { Button, Select } from "../../ui";

type AddMode = "idle" | "upload" | "generate";

function shortFaceTitle(face: PlayFace): string {
  if (face.label?.trim()) return face.label.trim();
  if (face.prompt?.trim()) {
    const t = face.prompt.trim();
    return t.length > 40 ? `${t.slice(0, 40)}…` : t;
  }
  if (face.source_kind === "starter") return "Starter face";
  return face.source_kind === "generated" ? "Generated face" : "Uploaded face";
}

export function FaceLibraryPanel({
  token,
  workspaceId,
  consentName,
  onConsentNameChange,
  selectedFaceId,
  onSelectFace,
  onError,
  modeLabel,
  compact = false,
  required = true,
}: {
  token: string;
  workspaceId: string;
  consentName: string;
  onConsentNameChange: (value: string) => void;
  selectedFaceId: string | null;
  onSelectFace: (face: PlayFace | null) => void;
  onError: (message: string | null) => void;
  modeLabel: string;
  /** Slim strip for Create: pick face + quick add, less copy. */
  compact?: boolean;
  /**
   * When true (Talking / lip-sync), auto-select the first face if none is picked.
   * When false (optional Video face), leave empty and allow re-tapping to clear.
   */
  required?: boolean;
}) {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [addMode, setAddMode] = useState<AddMode>("idle");
  const [genPrompt, setGenPrompt] = useState("");
  const [faceName, setFaceName] = useState("");
  const [imageModelId, setImageModelId] = useState("");

  const facesQuery = useQuery({
    queryKey: ["play", "faces", workspaceId],
    queryFn: () => api.listPlayFaces(token, workspaceId),
    enabled: Boolean(workspaceId),
    staleTime: 15_000,
  });

  useEffect(() => {
    const refreshExpired = () => {
      if (typeof document !== "undefined" && document.visibilityState !== "visible") return;
      if ((facesQuery.data || []).some((f) => isSignedMediaUrlExpired(f.url))) {
        void facesQuery.refetch();
      }
    };
    refreshExpired();
    document.addEventListener("visibilitychange", refreshExpired);
    return () => document.removeEventListener("visibilitychange", refreshExpired);
  }, [facesQuery]);

  const modelsQuery = useQuery({
    queryKey: ["play", "models"],
    queryFn: () => api.listPlayModels(token, workspaceId),
    staleTime: 120_000,
  });

  const imageModels = useMemo(() => {
    const all = modelsQuery.data || [];
    const enabled = all.filter((m: PlayModelOption) => m.modality === "image" && m.enabled);
    const unlocked = enabled.filter((m) => !m.locked);
    return unlocked.length ? unlocked : enabled;
  }, [modelsQuery.data]);

  useEffect(() => {
    if (!imageModels.length) {
      setImageModelId("");
      return;
    }
    const preferred =
      imageModels.find((m) => m.id === imageModelId) ||
      imageModels.find((m) => m.default) ||
      imageModels[0];
    setImageModelId(preferred.id);
  }, [imageModels, imageModelId]);

  const faces = facesQuery.data || [];
  const syncedSelectIdRef = useRef<string | null>(null);

  useEffect(() => {
    // Keep a pending selection while the library is loading/refreshing so
    // a just-uploaded face is not overwritten by faces[0].
    if (!faces.length) {
      if (facesQuery.isError || facesQuery.isLoading || facesQuery.isFetching) return;
      if (selectedFaceId) {
        syncedSelectIdRef.current = null;
        onSelectFace(null);
      }
      return;
    }
    if (selectedFaceId) {
      const match = faces.find((f) => f.id === selectedFaceId);
      if (match) {
        // Parent may only have the id (localStorage or ?edit=). Push the row once.
        if (syncedSelectIdRef.current !== match.id) {
          syncedSelectIdRef.current = match.id;
          onSelectFace(match);
        }
        return;
      }
      if (facesQuery.isLoading || facesQuery.isFetching) return;
    }
    syncedSelectIdRef.current = null;
    // Optional Video face: do not force a pick (and re-pick after a clear).
    if (!required) {
      if (selectedFaceId) onSelectFace(null);
      return;
    }
    onSelectFace(faces[0]);
  }, [faces, selectedFaceId, onSelectFace, facesQuery.isLoading, facesQuery.isFetching, required]);

  const uploadFace = useMutation({
    mutationFn: async (file: File) => {
      const rights = consentName.trim();
      if (rights.length < 2) throw new Error("Enter your name for rights (2+ characters)");
      return api.playUploadAvatar(token, workspaceId, file, rights, faceName.trim() || undefined);
    },
    onSuccess: (gen) => {
      onError(null);
      setAddMode("idle");
      setFaceName("");
      void qc.invalidateQueries({ queryKey: ["play", "faces", workspaceId] }).then(() => {
        onSelectFace({
          id: gen.id,
          workspace_id: gen.workspace_id,
          label: faceName.trim() || "Uploaded face",
          url: gen.url || null,
          source_kind: "upload",
          consent_name: consentName.trim() || null,
          prompt: gen.prompt,
          status: gen.status,
          created_at: gen.created_at,
        });
      });
    },
    onError: (err) => {
      onError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Upload failed");
    },
  });

  const generateFace = useMutation({
    mutationFn: async () => {
      const rights = consentName.trim();
      if (rights.length < 2) throw new Error("Enter your name for rights (2+ characters)");
      const prompt = genPrompt.trim();
      if (prompt.length < 3) throw new Error("Describe the face to generate");
      return api.generatePlayFace(token, {
        workspace_id: workspaceId,
        prompt,
        label: faceName.trim() || null,
        consent_name: rights,
        consent_confirmed: true,
        model: imageModelId || null,
      });
    },
    onSuccess: (face) => {
      onError(null);
      setGenPrompt("");
      setFaceName("");
      setAddMode("idle");
      void qc.invalidateQueries({ queryKey: ["play", "faces", workspaceId] });
      void qc.invalidateQueries({ queryKey: ["workspaces", "billing", workspaceId] });
      onSelectFace(face);
    },
    onError: (err) => {
      onError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Generate failed");
    },
  });

  const deleteFace = useMutation({
    mutationFn: async (faceId: string) => {
      await api.deletePlayFace(token, faceId);
      return faceId;
    },
    onSuccess: (faceId) => {
      onError(null);
      void qc.invalidateQueries({ queryKey: ["play", "faces", workspaceId] });
      if (selectedFaceId === faceId) onSelectFace(null);
    },
    onError: (err) => {
      onError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Delete failed");
    },
  });

  const busy = uploadFace.isPending || generateFace.isPending || deleteFace.isPending;
  const selected = faces.find((f) => f.id === selectedFaceId) || null;
  const rightsFieldsVisible = !compact || addMode === "generate" || addMode === "upload";

  function openUploadPicker() {
    setAddMode("upload");
    if (consentName.trim().length < 2) {
      return;
    }
    fileRef.current?.click();
  }

  return (
    <div
      className={cn(
        "grid gap-3 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] shadow-[var(--studio-card-shadow)] backdrop-blur-md",
        compact ? "gap-2 p-2.5" : "p-4",
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="m-0 text-[0.75rem] font-bold uppercase tracking-wide text-[var(--studio-fg-subtle)]">
          {compact ? "Avatar" : "Your faces"}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {compact && selectedFaceId ? (
            <Link to={`/avatars?edit=${encodeURIComponent(selectedFaceId)}`}>
              <Button type="button" size="small" variant="secondary" disabled={busy}>
                Edit
              </Button>
            </Link>
          ) : null}
          <Button
            type="button"
            size="small"
            variant="secondary"
            disabled={busy}
            onClick={() => setAddMode((m) => (m === "generate" ? "idle" : "generate"))}
          >
            <Sparkles size={14} aria-hidden />
            {compact ? "New" : "Generate"}
          </Button>
          <Button
            type="button"
            size="small"
            variant="secondary"
            disabled={busy}
            onClick={openUploadPicker}
          >
            <Upload size={14} aria-hidden />
            Upload
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) uploadFace.mutate(file);
            }}
          />
        </div>
      </div>

      {!compact ? (
        <p className="m-0 text-[0.78rem] text-[var(--studio-fg-muted)]">
          Face only. Head and shoulders on a plain background. Do not include a room. Place and clothes are set per clip. Uploads are free.
        </p>
      ) : null}

      {facesQuery.isError ? (
        <div className="flex items-center gap-2">
          <p className="m-0 text-[0.82rem] text-[var(--color-danger,#f87171)]">
            Could not load faces.
          </p>
          <Button type="button" size="small" variant="secondary" onClick={() => void facesQuery.refetch()}>
            Retry
          </Button>
        </div>
      ) : facesQuery.isLoading ? (
        <p className="m-0 flex items-center gap-2 text-[0.8rem] text-[var(--studio-fg-muted)]">
          <Loader2 size={14} className="animate-spin" aria-hidden />
          Loading faces…
        </p>
      ) : faces.length === 0 ? (
        <p className="m-0 rounded-lg border border-dashed border-[var(--studio-border)] px-3 py-6 text-center text-[0.82rem] text-[var(--studio-fg-muted)]">
          No faces yet. Clear face, plain background. Upload a photo or generate one.
        </p>
      ) : compact ? (
        <div className="grid gap-1.5">
        <div className="grid auto-cols-[4.5rem] grid-flow-col gap-2 overflow-x-auto overscroll-x-contain pb-0.5 [-webkit-overflow-scrolling:touch]">
          {faces.map((face) => {
            const active = face.id === selectedFaceId;
            return (
              <button
                key={face.id}
                type="button"
                title={shortFaceTitle(face)}
                aria-pressed={active}
                className={cn(
                  "relative w-[4.5rem] shrink-0 overflow-hidden rounded-xl border-2 bg-[var(--studio-fill-soft)] transition",
                  active
                    ? "border-[var(--studio-brand)] ring-2 ring-[var(--studio-border)]"
                    : "border-transparent hover:border-[var(--studio-border)]",
                )}
                onClick={() => onSelectFace(active && !required ? null : face)}
              >
                {face.url ? (
                  <img
                    src={resolveMediaUrl(face.url) || face.url}
                    alt={shortFaceTitle(face)}
                    className="aspect-square w-full object-cover"
                  />
                ) : (
                  <div className="grid aspect-square place-items-center text-[0.65rem] text-[var(--studio-fg-muted)]">
                    Face
                  </div>
                )}
                {active ? (
                  <span className="absolute right-0.5 top-0.5 grid h-5 w-5 place-items-center rounded-full bg-[var(--studio-brand)] text-white">
                    <Check size={12} aria-hidden />
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
        </div>
      ) : (
        <div className="grid gap-4">
          {selected?.url ? (
            <div className="mx-auto w-full max-w-[16rem]">
              <img
                src={resolveMediaUrl(selected.url) || selected.url}
                alt={shortFaceTitle(selected)}
                className="aspect-square w-full rounded-2xl border border-[var(--studio-border)] object-cover shadow-[var(--studio-shadow)]"
              />
              <p className="m-0 mt-2 text-center text-sm font-semibold text-[var(--studio-fg)]">
                {shortFaceTitle(selected)}
              </p>
              <p className="m-0 text-center text-[0.75rem] text-[var(--studio-fg-muted)]">
                {selected.source_kind === "generated"
                  ? "Generated"
                  : selected.source_kind === "starter"
                    ? "Starter"
                    : "Uploaded"}
                {selected.prompt ? ` · ${selected.prompt.slice(0, 60)}${selected.prompt.length > 60 ? "…" : ""}` : ""}
              </p>
              <div className="mt-2 flex justify-center gap-2">
                <Link to={`/avatars?edit=${encodeURIComponent(selected.id)}`}>
                  <Button type="button" size="small" variant="secondary" disabled={busy}>
                    Edit
                  </Button>
                </Link>
                <Button
                  type="button"
                  size="small"
                  variant="secondary"
                  disabled={busy}
                  onClick={() => {
                    if (window.confirm(`Delete “${shortFaceTitle(selected)}”? Anything that used this face stays, but you cannot pick it again.`)) {
                      deleteFace.mutate(selected.id);
                    }
                  }}
                >
                  <Trash2 size={14} aria-hidden />
                  {deleteFace.isPending ? "Deleting…" : "Delete face"}
                </Button>
              </div>
            </div>
          ) : null}

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {faces.map((face) => {
              const active = face.id === selectedFaceId;
              return (
                <button
                  key={face.id}
                  type="button"
                  title={shortFaceTitle(face)}
                  className={cn(
                    "relative overflow-hidden rounded-xl border-2 bg-[var(--studio-fill-soft)] text-left transition",
                    active
                      ? "border-[var(--studio-brand)] ring-2 ring-[var(--studio-border)]"
                      : "border-transparent hover:border-[var(--studio-border)]",
                  )}
                  onClick={() => onSelectFace(active && !required ? null : face)}
                >
                  {face.url ? (
                    <img
                      src={resolveMediaUrl(face.url) || face.url}
                      alt={shortFaceTitle(face)}
                      className="aspect-square w-full object-cover"
                    />
                  ) : (
                    <div className="grid aspect-square place-items-center text-sm text-[var(--studio-fg-muted)]">
                      Face
                    </div>
                  )}
                  {active ? (
                    <span className="absolute right-2 top-2 grid h-6 w-6 place-items-center rounded-full bg-[var(--studio-brand)] text-white">
                      <Check size={14} aria-hidden />
                    </span>
                  ) : null}
                  <span className="absolute inset-x-0 bottom-0 truncate bg-black/60 px-2 py-1.5 text-[0.75rem] font-medium text-white">
                    {shortFaceTitle(face)}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {rightsFieldsVisible ? (
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="grid gap-1 text-[0.78rem] text-[var(--studio-fg-muted)]">
            Face name (optional)
            <input
              className="min-h-10 rounded-lg border border-[var(--studio-border)] bg-transparent px-2.5 py-2 text-base text-[var(--studio-fg)]"
              placeholder="e.g. Maya, Founder look"
              value={faceName}
              onChange={(e) => setFaceName(e.target.value)}
              aria-label="Face display name"
            />
          </label>
          <label className="grid gap-1 text-[0.78rem] text-[var(--studio-fg-muted)]">
            Your name (rights)
            <input
              className="min-h-10 rounded-lg border border-[var(--studio-border)] bg-transparent px-2.5 py-2 text-base text-[var(--studio-fg)]"
              placeholder="Who has rights to use this face"
              value={consentName}
              onChange={(e) => onConsentNameChange(e.target.value)}
              aria-label="Consent name"
            />
          </label>
        </div>
      ) : null}

      {addMode === "upload" && compact ? (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-2.5">
          <p className="m-0 flex-1 text-[0.78rem] text-[var(--studio-fg-muted)]">
            {consentName.trim().length < 2
              ? "Enter your name for rights, then pick a headshot."
              : "Ready. Pick a headshot (face only, plain background)."}
          </p>
          <Button
            type="button"
            size="small"
            disabled={busy || consentName.trim().length < 2}
            onClick={() => fileRef.current?.click()}
          >
            <Upload size={14} aria-hidden />
            Choose file
          </Button>
          <Button type="button" size="small" variant="secondary" disabled={busy} onClick={() => setAddMode("idle")}>
            Cancel
          </Button>
        </div>
      ) : null}

      {addMode === "generate" ? (
        <div className="grid gap-2 rounded-lg border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] p-2.5">
          <label className="grid gap-1 text-[0.78rem] text-[var(--studio-fg-muted)]">
            Describe the face only (not the scene)
            <textarea
              className="min-h-[4rem] resize-y rounded-lg border border-[var(--studio-border)] bg-transparent px-2.5 py-2 text-base text-[var(--studio-fg)]"
              placeholder="e.g. 30s woman, short brown hair, freckles, soft smile"
              value={genPrompt}
              onChange={(e) => setGenPrompt(e.target.value)}
              aria-label="Face generate prompt"
              rows={2}
            />
          </label>
          {imageModels.length > 0 ? (
            <label className="inline-flex min-w-0 items-center gap-1.5 text-[0.78rem] text-[var(--studio-fg-muted)]">
              Model
              <Select
                size="sm"
                value={imageModelId}
                onChange={(e) => setImageModelId(e.target.value)}
                aria-label="Face image model"
              >
                {imageModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                    {m.token_cost > 1 ? ` · ${m.token_cost} credits` : " · 1 credit"}
                  </option>
                ))}
              </Select>
            </label>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="small"
              disabled={busy || genPrompt.trim().length < 3 || consentName.trim().length < 2}
              onClick={() => generateFace.mutate()}
            >
              {generateFace.isPending ? (
                <>
                  <Loader2 size={14} className="animate-spin" aria-hidden />
                  Generating…
                </>
              ) : (
                <>
                  <Sparkles size={14} aria-hidden />
                  Save to library
                </>
              )}
            </Button>
            <Button type="button" size="small" variant="secondary" disabled={busy} onClick={() => setAddMode("idle")}>
              Cancel
            </Button>
          </div>
        </div>
      ) : null}

      {uploadFace.isPending ? (
        <p className="m-0 flex items-center gap-2 text-[0.8rem] text-[var(--studio-fg-muted)]">
          <Loader2 size={14} className="animate-spin" aria-hidden />
          Uploading face…
        </p>
      ) : null}
    </div>
  );
}
