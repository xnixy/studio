import { ArrowRight, Loader2, Play } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { cn } from "../../lib/cn";
import { downloadMediaFile, playGenerationPosterUrl, resolveMediaUrl } from "../../lib/mediaUrl";
import { promptForDisplay } from "../../lib/playPricing";
import type { PlayGeneration } from "../../types";
import { Button } from "../../ui";
import { generationKindLabel, isSquarePlatform, composerTabLabel, threadClipCardClass } from "../../pages/playPageChrome";
import type { ThreadItem } from "../../pages/playPageModel";

type Props = {
  thread: ThreadItem[];
  generatePending?: boolean;
  assistPending?: boolean;
  onGenerateDraft: () => void;
  onEditDraft: () => void;
  onChooseOption: (value: string) => void;
  onDownloadError: (message: string) => void;
  onRetry: (prompt: string) => void;
  onExtend: (generation: PlayGeneration) => void;
};

export function CreateThread({
  thread,
  generatePending,
  assistPending,
  onGenerateDraft,
  onEditDraft,
  onChooseOption,
  onDownloadError,
  onRetry,
  onExtend,
}: Props) {
  if (thread.length === 0) return null;

  return (
    <>
      {thread.map((item) => {
        if (item.kind === "user") {
          return (
            <div
              key={item.id}
              className="ml-auto max-w-[min(36rem,92%)] rounded-[20px] rounded-br-md bg-[var(--studio-bubble-user,var(--studio-brand))] px-3.5 py-2.5 text-sm text-[var(--studio-bubble-user-fg,#fff)]"
            >
              <p className="m-0 whitespace-pre-wrap">
                {promptForDisplay(item.text, item.mode)}
              </p>
              <p className="m-0 mt-1.5 text-[0.7rem] font-medium text-white/65">
                {composerTabLabel(item.mode)} · {item.platform === "feed" ? "1:1" : "9:16"}
              </p>
            </div>
          );
        }
        if (item.kind === "system") {
          const isError = item.tone === "error";
          return (
            <div
              key={item.id}
              className={cn(
                "max-w-[min(36rem,92%)] rounded-[20px] rounded-bl-md px-3.5 py-2.5 text-sm",
                isError
                  ? "border border-[var(--color-danger-border,rgb(248_113_113_/_0.4))] bg-[var(--color-danger-bg,rgb(248_113_113_/_0.1))] text-[var(--color-danger,#f87171)]"
                  : "bg-[var(--studio-bubble-system,var(--studio-fill-quiet))] text-[var(--studio-bubble-system-fg,var(--studio-fg))]",
              )}
            >
              {item.text}
            </div>
          );
        }
        if (item.kind === "thinking") {
          return (
            <div
              key={item.id}
              className="flex max-w-[min(36rem,92%)] items-center gap-2 rounded-[20px] rounded-bl-md bg-[var(--studio-bubble-system,var(--studio-fill-quiet))] px-3.5 py-2.5 text-sm text-[var(--studio-bubble-system-fg,var(--studio-fg))]"
            >
              <Loader2 size={14} className="animate-spin" />
              Working it out…
            </div>
          );
        }
        if (item.kind === "draft") {
          return (
            <div
              key={item.id}
              className="max-w-[min(36rem,92%)] rounded-[20px] rounded-bl-md border border-[var(--studio-border)] bg-[var(--studio-bubble-system,var(--studio-fill-quiet))] px-4 py-3"
            >
              {item.line ? (
                <>
                  <p className="m-0 text-[0.68rem] font-bold uppercase tracking-wide text-[var(--studio-fg-subtle)]">
                    They say
                  </p>
                  <p className="m-0 mt-1 text-[1.05rem] font-semibold leading-snug text-[var(--studio-fg)]">
                    {item.line}
                  </p>
                </>
              ) : null}
              {item.scene ? (
                <>
                  <p className="m-0 mt-3 text-[0.68rem] font-bold uppercase tracking-wide text-[var(--studio-fg-subtle)]">
                    Scene
                  </p>
                  <p className="m-0 mt-1 text-sm leading-snug text-[var(--studio-fg)]">{item.scene}</p>
                </>
              ) : null}
              {item.summary.length ? (
                <p className="m-0 mt-3 text-[0.78rem] text-[var(--studio-brand)]">
                  {item.summary.join(" \u00b7 ")}
                </p>
              ) : null}
              {item.options?.choices?.length ? (
                <>
                  <p className="m-0 mt-3 text-[0.68rem] font-bold uppercase tracking-wide text-[var(--studio-fg-subtle)]">
                    {item.options.header}
                  </p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {item.options.choices.map((c) => (
                      <button
                        key={c.label}
                        type="button"
                        onClick={() => onChooseOption(c.value)}
                        className={cn(
                          "rounded-full border px-3 py-1.5 text-[0.78rem] font-semibold",
                          c.selected
                            ? "border-[var(--studio-brand)] bg-[var(--studio-brand-soft,var(--studio-fill-quiet))] text-[var(--studio-brand)]"
                            : "border-transparent bg-[var(--studio-fill-quiet)] text-[var(--studio-fg)]",
                        )}
                      >
                        {c.label}
                      </button>
                    ))}
                  </div>
                </>
              ) : null}
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  size="small"
                  onClick={onGenerateDraft}
                  disabled={generatePending || assistPending}
                >
                  {generatePending ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Generating
                    </>
                  ) : (
                    <>
                      Generate
                      <ArrowRight size={14} />
                    </>
                  )}
                </Button>
                <Button
                  type="button"
                  size="small"
                  variant="secondary"
                  onClick={onEditDraft}
                  disabled={generatePending || assistPending}
                >
                  Change
                </Button>
              </div>
            </div>
          );
        }
        return (
          <ThreadGenCard
            key={item.id}
            generation={item.generation}
            note={item.note}
            onDownloadError={onDownloadError}
            onRetry={onRetry}
            onExtend={onExtend}
          />
        );
      })}
    </>
  );
}

function ThreadGenCard({
  generation: g,
  note,
  onDownloadError,
  onRetry,
  onExtend,
}: {
  generation: PlayGeneration;
  note?: string | null;
  onDownloadError: (message: string) => void;
  onRetry: (prompt: string) => void;
  onExtend: (generation: PlayGeneration) => void;
}) {
  const [playing, setPlaying] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const status = (g.status || "").toLowerCase();
  const pending = !["ready", "failed", "error", "cancelled", "expired"].includes(status);
  const failed = status === "failed" || status === "error" || status === "expired";
  const square = isSquarePlatform(g.platform);
  const src = resolveMediaUrl(g.url) || g.url || null;
  const poster = resolveMediaUrl(playGenerationPosterUrl(g));
  const ready = status === "ready" && Boolean(src);
  const video = g.asset_type === "video";
  const still = g.asset_type === "image";

  return (
    <div className={cn("flex flex-col gap-2", threadClipCardClass(g.platform))}>
      <div
        className={cn(
          "relative overflow-hidden rounded-[22px] bg-black shadow-[var(--studio-card-shadow)]",
          square ? "aspect-square" : "aspect-[9/16]",
        )}
      >
        {pending ? (
          <>
            {poster ? (
              <img src={poster} alt="" className="absolute inset-0 h-full w-full object-cover opacity-40" />
            ) : null}
            <div className="absolute inset-0 grid place-items-center gap-2 text-[var(--studio-fg-muted)]">
              <Loader2 className="animate-spin text-[var(--studio-brand)]" size={28} />
              <span className="text-sm">Generating…</span>
            </div>
          </>
        ) : null}

        {ready && still ? (
          <Link to={`/clips/${g.id}`} className="absolute inset-0 block" aria-label="Open still">
            <img
              src={src!}
              alt={g.prompt || "Generated still"}
              className="h-full w-full object-cover"
            />
          </Link>
        ) : null}

        {ready && video ? (
          <>
            <video
              ref={videoRef}
              src={src!}
              poster={poster || undefined}
              className="absolute inset-0 h-full w-full object-cover"
              playsInline
              preload="metadata"
              onEnded={() => setPlaying(false)}
              onPause={() => setPlaying(false)}
            />
            {playing ? (
              <button
                type="button"
                className="absolute inset-0 border-0 bg-transparent p-0"
                onClick={() => {
                  videoRef.current?.pause();
                  setPlaying(false);
                }}
                aria-label="Pause clip"
              />
            ) : (
              <button
                type="button"
                className="absolute inset-0 block border-0 bg-transparent p-0"
                onClick={() => {
                  const el = videoRef.current;
                  if (!el) return;
                  void el.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
                }}
                aria-label="Play clip"
              >
                {poster ? (
                  <img src={poster} alt="" className="h-full w-full object-cover" />
                ) : null}
                <span className="absolute inset-0 grid place-items-center bg-black/25">
                  <span className="grid h-14 w-14 place-items-center rounded-full bg-black/55 ring-1 ring-white/50">
                    <Play size={22} className="ml-0.5 fill-white text-white" aria-hidden />
                  </span>
                </span>
              </button>
            )}
          </>
        ) : null}

        {failed || (!pending && !src) ? (
          <div className="absolute inset-0 grid place-items-center px-3 text-center text-sm text-[var(--color-danger,#f87171)]">
            {g.error_message || (status === "expired" ? "Clip expired" : "Generation failed")}
          </div>
        ) : null}
      </div>

      <div className="grid gap-1.5 px-0.5">
        <p className="m-0 text-[0.75rem] font-semibold text-[var(--studio-fg-muted)]">
          {generationKindLabel(g)}
          {failed ? " · Failed" : pending ? " · Working" : ""}
        </p>
        {note && !failed ? (
          <p className="m-0 text-[0.78rem] text-[var(--studio-fg-muted)]">{note}</p>
        ) : null}
        {failed ? (
          <p className="m-0 text-[0.78rem] text-[var(--studio-fg-muted)]">Credits for this run were returned.</p>
        ) : null}
        <div className="flex flex-wrap gap-1.5">
          {ready ? (
            <>
              <Link className={chipClass} to={`/clips/${g.id}`}>
                Open
              </Link>
              <button
                type="button"
                className={chipClass}
                onClick={() => {
                  void downloadMediaFile(
                    g.url!,
                    `studio-clip-${g.id.slice(0, 8)}.${still ? "jpg" : "mp4"}`,
                  ).catch((err) =>
                    onDownloadError(err instanceof Error ? err.message : "Download failed"),
                  );
                }}
              >
                Download
              </button>
              {video ? (
                <button type="button" className={chipClass} onClick={() => onExtend(g)}>
                  Extend
                </button>
              ) : null}
            </>
          ) : null}
          {failed ? (
            <button
              type="button"
              className={chipClass}
              onClick={() => onRetry(g.prompt || "")}
            >
              Retry
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

const chipClass =
  "rounded-full border border-[var(--studio-border)] bg-[var(--studio-fill-quiet)] px-2.5 py-1 text-[0.75rem] font-semibold text-[var(--studio-fg)] no-underline hover:bg-[var(--studio-fill-soft)]";
