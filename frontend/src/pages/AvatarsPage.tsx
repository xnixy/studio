import { ArrowRight, Loader2, Sparkles, UserRound, Video } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth";
import { FaceEditPanel } from "../features/play/FaceEditPanel";
import { FaceLibraryPanel } from "../features/play/FaceLibraryPanel";
import type { PlayFace } from "../types";
import { useWorkspace } from "../workspace";
import { Button, MessageBar, Page, PageBoard, PageHeader, PageSection } from "../ui";
import { Caption1 } from "../ui/Text";

const FACE_STORAGE_KEY = "studio-active-face";

export function AvatarsPage() {
  const auth = useAuth();
  const token = auth.accessToken ?? "";
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editId = (searchParams.get("edit") || "").trim() || null;
  const [consentName, setConsentName] = useState(auth.user?.full_name || "");
  const [selectedFaceId, setSelectedFaceId] = useState<string | null>(() => {
    try {
      return localStorage.getItem(FACE_STORAGE_KEY);
    } catch {
      return null;
    }
  });
  const [selectedFace, setSelectedFace] = useState<PlayFace | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (editId) setSelectedFaceId(editId);
  }, [editId]);

  const onSelectFace = useCallback((face: PlayFace | null) => {
    setSelectedFace(face);
    setSelectedFaceId(face?.id ?? null);
    try {
      if (face?.id) localStorage.setItem(FACE_STORAGE_KEY, face.id);
      else localStorage.removeItem(FACE_STORAGE_KEY);
    } catch {
      /* ignore */
    }
    setConsentName((prev) => (prev.trim() ? prev : face?.consent_name || prev));
  }, []);

  function makeVideo(mode: "avatar" | "video") {
    if (!selectedFaceId && mode !== "video") return;
    const params = new URLSearchParams();
    params.set("mode", mode);
    if (selectedFaceId) params.set("face", selectedFaceId);
    navigate(`/play?${params.toString()}`);
  }

  if (!workspaceId) {
    return (
      <Page wide>
        <div className="grid place-items-center gap-3 py-16 text-center">
          {workspace.error && !workspace.loading ? (
            <>
              <p className="m-0 text-sm text-[var(--studio-fg-muted)]">Could not load your space.</p>
              <Button type="button" onClick={() => void workspace.refresh()}>
                Try again
              </Button>
            </>
          ) : (
            <>
              <Loader2 className="animate-spin text-[var(--studio-brand)]" size={28} />
              <p className="m-0 text-sm text-[var(--studio-fg-muted)]">Loading your space…</p>
            </>
          )}
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
              <UserRound size={18} className="text-[var(--studio-brand)]" aria-hidden />
              Faces
            </>
          }
          subtitle="Upload or generate a face. Edit to polish or save a new look. Scene and clothes for a clip still come from the prompt unless the look already has them."
          actions={
            <Link to="/play">
              <Button type="button" size="small">
                <Sparkles size={14} aria-hidden />
                Create
              </Button>
            </Link>
          }
        />
        <PageSection>
          {error ? <MessageBar intent="error">{error}</MessageBar> : null}

          {editId && selectedFace && selectedFace.id === editId ? (
            <div className="grid gap-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Link
                  className="text-sm font-semibold text-[var(--studio-brand)] no-underline hover:underline"
                  to="/avatars"
                >
                  Back to faces
                </Link>
                <Caption1>{selectedFace.label || "Selected face"}</Caption1>
              </div>
              <FaceEditPanel
                token={token}
                workspaceId={workspaceId}
                face={selectedFace}
                onUpdated={(face) => {
                  setSelectedFace(face);
                  setSelectedFaceId(face.id);
                  if (face.id !== editId) {
                    navigate(`/avatars?edit=${encodeURIComponent(face.id)}`, { replace: true });
                  }
                }}
              />
            </div>
          ) : editId ? (
            <p className="m-0 flex items-center gap-2 text-sm text-[var(--studio-fg-muted)]">
              <Loader2 size={16} className="animate-spin" aria-hidden />
              Opening editor…
            </p>
          ) : (
            <>
          <FaceLibraryPanel
            token={token}
            workspaceId={workspaceId}
            consentName={consentName}
            onConsentNameChange={setConsentName}
            selectedFaceId={selectedFaceId}
            onSelectFace={onSelectFace}
            onError={setError}
            modeLabel="faces"
          />

          <div className="grid gap-2 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-3 shadow-[var(--studio-card-shadow)] backdrop-blur-md">
            <Caption1>
              {selectedFace
                ? `Using “${selectedFace.label || "selected face"}”. Choose how to use it:`
                : "Select a face, then jump into Create."}
            </Caption1>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="small"
                disabled={!selectedFaceId}
                onClick={() => makeVideo("avatar")}
              >
                <UserRound size={14} aria-hidden />
                Talking clip
                <ArrowRight size={14} aria-hidden />
              </Button>
              <Button
                type="button"
                size="small"
                variant="secondary"
                onClick={() => makeVideo("video")}
              >
                <Video size={14} aria-hidden />
                Scene
              </Button>
            </div>
          </div>
            </>
          )}
        </PageSection>
      </PageBoard>
    </Page>
  );
}
