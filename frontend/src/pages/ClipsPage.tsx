import { Clapperboard, Image as ImageIcon, Loader2, Sparkles, UserRound } from "lucide-react";
import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { useAuth } from "../auth";
import { useWorkspace } from "../workspace";
import type { PlayGeneration } from "../types";
import { isSignedMediaUrlExpired, playGenerationPosterUrl, resolveMediaUrl } from "../lib/mediaUrl";
import { promptForDisplay } from "../lib/playPricing";
import { generationKindLabel, generationStatusLabel } from "./playPageChrome";
import { Button, Page, PageBoard, PageHeader, PageSection } from "../ui";
import { Caption1 } from "../ui/Text";

function ClipCard({ g }: { g: PlayGeneration }) {
  const isVideo = g.asset_type === "video";
  const ready = g.status === "ready" && Boolean(g.url);
  const poster = resolveMediaUrl(playGenerationPosterUrl(g));
  const media = resolveMediaUrl(g.url) || g.url || undefined;
  return (
    <Link
      to={`/clips/${g.id}`}
      className="overflow-hidden rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] text-inherit no-underline shadow-[var(--studio-card-shadow)] backdrop-blur-md transition hover:border-[var(--studio-border)]"
    >
      <article>
        <div className="relative aspect-[9/14] max-h-72 bg-black/40">
          {g.status === "processing" || g.status === "queued" ? (
            <div className="grid h-full place-items-center gap-2 text-[var(--studio-fg-muted)]">
              <Loader2 className="animate-spin text-[var(--studio-brand)]" size={24} />
              <span className="text-xs">Working…</span>
            </div>
          ) : null}
          {ready && isVideo && (poster || media) ? (
            poster ? (
              <img
                src={poster}
                alt={g.prompt || "Clip"}
                className="h-full w-full object-cover"
              />
            ) : (
              <video
                src={media}
                className="h-full w-full object-cover"
                muted
                playsInline
                preload="metadata"
              />
            )
          ) : null}
          {ready && !isVideo && media ? (
            <img
              src={media}
              alt={g.prompt || "Clip"}
              className="h-full w-full object-cover"
            />
          ) : null}
          {g.status === "failed" ? (
            <div className="grid h-full place-items-center p-3 text-center text-xs text-[var(--color-danger,#f87171)]">
              {g.error_message || "Failed"}
            </div>
          ) : null}
          {!ready && g.status !== "processing" && g.status !== "queued" && g.status !== "failed" ? (
            <div className="grid h-full place-items-center text-[var(--studio-fg-muted)]">
              {isVideo ? <Clapperboard size={22} /> : <ImageIcon size={22} />}
            </div>
          ) : null}
        </div>
        <div className="grid gap-1 p-2.5">
          <p className="m-0 text-[0.65rem] font-bold uppercase tracking-wide text-[var(--studio-fg-subtle)]">
            {generationKindLabel(g)} · {generationStatusLabel(g.status)}
          </p>
          <p className="m-0 line-clamp-2 text-[0.8rem] text-[var(--studio-fg)]">
            {promptForDisplay(g.prompt, g.mode) || "Untitled"}
          </p>
          <span className="text-[0.75rem] font-semibold text-[var(--studio-brand)]">Open / edit</span>
        </div>
      </article>
    </Link>
  );
}

export function ClipsPage() {
  const auth = useAuth();
  const token = auth.accessToken ?? "";
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;

  const clips = useQuery({
    queryKey: ["play", "generations", workspaceId],
    queryFn: () => api.listPlayGenerations(token, workspaceId!, 60),
    enabled: Boolean(token && workspaceId),
    staleTime: 15_000,
  });

  const items = (clips.data || []).filter((g) => {
    const meta = g.metadata || {};
    return meta.mode !== "avatar_source_image" && meta.face_library !== true;
  });

  useEffect(() => {
    if (!token || !workspaceId) return;
    const refreshExpired = () => {
      if (typeof document !== "undefined" && document.visibilityState !== "visible") return;
      const stale = (clips.data || []).some(
        (g) => g.status === "ready" && isSignedMediaUrlExpired(g.url),
      );
      if (stale) void clips.refetch();
    };
    refreshExpired();
    document.addEventListener("visibilitychange", refreshExpired);
    return () => document.removeEventListener("visibilitychange", refreshExpired);
  }, [token, workspaceId, clips]);

  return (
    <Page wide>
      <PageBoard>
        <PageHeader
          title={
            <>
              <Clapperboard size={18} className="text-[var(--studio-brand)]" aria-hidden />
              Library
            </>
          }
          subtitle="Each card is one clip. Open it to preview, edit the prompt, or make a new version."
          actions={
            <>
              <Link to="/avatars">
                <Button type="button" variant="secondary" size="small">
                  <UserRound size={14} aria-hidden />
                  Faces
                </Button>
              </Link>
              <Link to="/play">
                <Button type="button" size="small">
                  <Sparkles size={14} aria-hidden />
                  Create
                </Button>
              </Link>
            </>
          }
        />
        <PageSection>
          {clips.isLoading ? (
            <p className="m-0 flex items-center gap-2 text-sm text-[var(--studio-fg-muted)]">
              <Loader2 size={16} className="animate-spin text-[var(--studio-brand)]" aria-hidden />
              Loading clips…
            </p>
          ) : null}
          {!clips.isLoading && items.length === 0 ? (
            <div className="grid gap-3 rounded-xl border border-dashed border-[var(--studio-border)] px-4 py-10 text-center">
              <Caption1>No clips yet. Make one in Create, then it shows up here.</Caption1>
              <div className="flex flex-wrap justify-center gap-2">
                <Link to="/play">
                  <Button type="button" size="small">
                    Open Create
                  </Button>
                </Link>
              </div>
            </div>
          ) : null}
          {items.length > 0 ? (
            <div className="grid grid-cols-[repeat(auto-fill,minmax(10.5rem,1fr))] gap-3">
              {items.map((g) => (
                <ClipCard key={g.id} g={g} />
              ))}
            </div>
          ) : null}
        </PageSection>
      </PageBoard>
    </Page>
  );
}
