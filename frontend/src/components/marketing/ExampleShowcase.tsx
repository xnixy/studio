import { Play, Sparkles } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { cn } from "../../lib/cn";
import {
  SHOWCASE_EXAMPLES,
  SHOWCASE_FILTERS,
  type ShowcaseExample,
  type ShowcaseMode,
} from "../../marketing/examples";
import { useMarketingStyles } from "../../ui/marketingStyles";

type Props = {
  activeMode?: ShowcaseMode | "all";
  onPick: (example: ShowcaseExample) => void;
  selectedId?: string | null;
};

export function ExampleShowcase({ activeMode = "all", onPick, selectedId }: Props) {
  const styles = useMarketingStyles();
  const [filter, setFilter] = useState<"all" | ShowcaseMode>(
    activeMode === "all" ? "all" : activeMode,
  );

  const items = useMemo(() => {
    if (filter === "all") return SHOWCASE_EXAMPLES;
    return SHOWCASE_EXAMPLES.filter((e) => e.mode === filter);
  }, [filter]);

  return (
    <div className={styles.showcase}>
      <div className={styles.showcaseHead}>
        <div className={styles.showcaseHeadCopy}>
          <p className={styles.showcaseKicker}>
            <Sparkles size={14} aria-hidden />
            Examples
          </p>
          <h2 className={styles.showcaseTitle}>See what you can make</h2>
          <p className={styles.showcaseLede}>
            Filter by Talking, Scene, or stills. Video cards have real clips. Hover a video card to preview.
          </p>
        </div>
        <div
          className={cn(styles.showcaseFilters, "overflow-x-auto overscroll-x-contain pb-0.5")}
          role="tablist"
          aria-label="Example type"
        >
          {SHOWCASE_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              role="tab"
              aria-selected={filter === f.id}
              className={cn(styles.chip, "shrink-0", filter === f.id && styles.chipActive)}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.showcaseGrid} role="list">
        {items.map((example, index) => (
          <ExampleCard
            key={example.id}
            example={example}
            selected={selectedId === example.id}
            delayMs={(index % 8) * 40}
            onPick={onPick}
          />
        ))}
      </div>
    </div>
  );
}

function ExampleCard({
  example,
  selected,
  delayMs,
  onPick,
}: {
  example: ShowcaseExample;
  selected: boolean;
  delayMs: number;
  onPick: (example: ShowcaseExample) => void;
}) {
  const styles = useMarketingStyles();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [hover, setHover] = useState(false);
  const [imgFailed, setImgFailed] = useState(false);
  const isFaceCard =
    (example.mode === "avatar" || example.mode === "lipsync") && !example.videoUrl;
  const tall = example.aspect === "9:16" && !isFaceCard;
  const wide = example.aspect === "16:9";
  const hasVideo = Boolean(example.videoUrl);

  function onEnter() {
    setHover(true);
    const v = videoRef.current;
    if (v && example.videoUrl) {
      void v.play().catch(() => {
        /* autoplay may be blocked */
      });
    }
  }

  function onLeave() {
    setHover(false);
    const v = videoRef.current;
    if (v) {
      v.pause();
      v.currentTime = 0;
    }
  }

  return (
    <button
      type="button"
      role="listitem"
      className={cn(
        styles.showcaseCard,
        // Face cards stay square; do not stretch to tall 9:16 neighbors in the grid.
        isFaceCard && "h-auto self-start",
        tall && styles.showcaseCardTall,
        wide && styles.showcaseCardWide,
        selected && styles.showcaseCardSelected,
      )}
      style={{ animationDelay: `${delayMs}ms` }}
      onClick={() => onPick(example)}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      onFocus={onEnter}
      onBlur={onLeave}
      aria-label={`${example.title}. Use this example prompt.`}
    >
      <div
        className={cn(
          styles.showcaseScene,
          // 1:1 portraits: keep full head (grid stretch was cropping faces in half)
          isFaceCard && "aspect-square min-h-0 w-full flex-none",
        )}
        style={{ background: imgFailed ? example.scene : isFaceCard ? "#111" : undefined }}
        aria-hidden
      >
        {!imgFailed ? (
          <img
            src={example.posterUrl}
            alt=""
            className={cn(
              "absolute inset-0 h-full w-full transition-opacity duration-200",
              isFaceCard ? "object-cover object-center" : "object-cover",
              hover && hasVideo ? "opacity-0" : "opacity-100",
            )}
            loading="lazy"
            decoding="async"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div className={styles.showcaseSceneGlow} style={{ background: example.accent }} />
        )}
        {/* Only real video examples get hover playback. Face cards never mount a <video>. */}
        {hasVideo && example.videoUrl ? (
          <video
            ref={videoRef}
            src={example.videoUrl}
            className={cn(
              "absolute inset-0 h-full w-full object-cover transition-opacity duration-200",
              hover ? "opacity-100" : "opacity-0",
            )}
            muted
            loop
            playsInline
            preload="metadata"
          />
        ) : null}
        {!isFaceCard ? <div className={styles.showcaseSceneNoise} /> : null}
        {!isFaceCard && example.mockLabel ? (
          <p className={styles.showcaseMockLabel} style={{ color: example.accent }}>
            {example.mockLabel}
          </p>
        ) : null}
        {hasVideo ? (
          <span className={styles.showcasePlay}>
            <Play size={18} fill="currentColor" aria-hidden />
          </span>
        ) : null}
        <div className={styles.showcaseBadges}>
          {/* Face cards are portraits, not finished clips. Label them as faces. */}
          <span className={styles.showcaseBadge}>
            {isFaceCard ? "Face" : labelMode(example.mode)}
          </span>
          {!isFaceCard ? (
            <span className={styles.showcaseBadge}>{labelPlatform(example.platform)}</span>
          ) : null}
          {!isFaceCard && example.duration ? (
            <span className={styles.showcaseBadge}>{example.duration}</span>
          ) : null}
        </div>
      </div>
      <div className={styles.showcaseMeta}>
        <p className={styles.showcaseCardTitle}>{example.title}</p>
        <p className={styles.showcaseCardCaption}>{example.caption}</p>
      </div>
    </button>
  );
}

function labelMode(mode: ShowcaseMode) {
  if (mode === "lipsync" || mode === "avatar") return "Talking";
  if (mode === "image") return "Still";
  return "Scene";
}

function labelPlatform(platform: string) {
  if (platform === "tiktok") return "Vertical";
  if (platform === "reels") return "Reels";
  if (platform === "shorts") return "Shorts";
  if (platform === "feed") return "Square";
  return "Custom";
}

export function ExampleMarquee() {
  const styles = useMarketingStyles();
  const base = SHOWCASE_EXAMPLES.map((e) => e.title);
  const tags = [...base, ...base];

  return (
    <div className={styles.marquee} aria-hidden>
      <div className={styles.marqueeTrack}>
        {tags.map((tag, i) => (
          <span key={`${tag}-${i}`} className={styles.marqueeItem}>
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}
