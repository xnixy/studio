import { ArrowRight, Sparkles } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { cn } from "../lib/cn";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { EarlyAccessBadge } from "../components/marketing/EarlyAccessBadge";
import { ExampleMarquee, ExampleShowcase } from "../components/marketing/ExampleShowcase";
import { usePageMeta } from "../components/marketing/usePageMeta";
import { DEMO_AVATARS } from "../marketing/demoAvatars";
import { PromptFields } from "../features/play/PromptFields";
import { avatarPromptPreview } from "../lib/playPricing";
import {
  COMPOSER_TABS as CREATE_TABS,
  FORMATS as CREATE_FORMATS,
  clipNoun,
  composerTabForMode,
  composerTabLabel,
} from "./playPageChrome";
import type { ShowcaseExample } from "../marketing/examples";
import { LinkButton } from "../ui";
import { useMarketingStyles } from "../ui/marketingStyles";

type PlayMode = "image" | "video" | "avatar" | "lipsync";
type PlatformId = "tiktok" | "feed";

const CLIP_TYPES = CREATE_TABS;

const FORMATS: { id: PlatformId; label: string; aspect: string }[] = CREATE_FORMATS.map(
  (f) => ({ ...f, id: f.id as PlatformId }),
);

const DEMO_VOICES = ["Jessica", "Lily", "Brian", "Daniel"] as const;

/** Static model catalog matching backend play_models defaults (no auth needed on landing). */
type DemoModel = {
  id: string;
  label: string;
  modality: PlayMode;
  provider: string;
  token_cost: number;
  default?: boolean;
  max_duration_seconds?: number;
};

const DEMO_MODELS: DemoModel[] = [
  {
    id: "xai-image-fast",
    label: "Grok Image Fast",
    modality: "image",
    provider: "xai",
    token_cost: 1,
    default: true,
  },
  {
    id: "xai-image-quality",
    label: "Grok Image 2.0",
    modality: "image",
    provider: "xai",
    token_cost: 2,
  },
  {
    id: "nano-banana-2-lite",
    label: "Nano Banana 2 Lite",
    modality: "image",
    provider: "gemini",
    token_cost: 2,
  },
  {
    id: "nano-banana-2",
    label: "Nano Banana 2",
    modality: "image",
    provider: "gemini",
    token_cost: 3,
  },
  {
    id: "nano-banana-pro",
    label: "Nano Banana Pro",
    modality: "image",
    provider: "gemini",
    token_cost: 5,
  },
  {
    id: "seedance-avatar-fast",
    label: "Seedance Fast",
    modality: "avatar",
    provider: "seedance",
    token_cost: 8,
    default: true,
    max_duration_seconds: 15,
  },
  {
    id: "seedance-avatar",
    label: "Seedance 2.5",
    modality: "avatar",
    provider: "seedance",
    token_cost: 12,
    max_duration_seconds: 30,
  },
  {
    id: "seedance-2-0-fast",
    label: "Seedance Fast",
    modality: "video",
    provider: "seedance",
    token_cost: 8,
    default: true,
    max_duration_seconds: 15,
  },
  {
    id: "seedance-2-5",
    label: "Seedance 2.5",
    modality: "video",
    provider: "seedance",
    token_cost: 12,
    max_duration_seconds: 30,
  },
];

export function HomePage() {
  const auth = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const styles = useMarketingStyles();
  const composeRef = useRef<HTMLFormElement>(null);
  const [mode, setMode] = useState<PlayMode>("avatar");
  const [platform, setPlatform] = useState<PlatformId>("tiktok");
  const [modelId, setModelId] = useState("seedance-avatar-fast");
  const [demoPicker, setDemoPicker] = useState<"none" | "face" | "voice">("none");
  const [demoVoice, setDemoVoice] = useState<string>(DEMO_VOICES[0]);
  const [prompt, setPrompt] = useState(DEMO_AVATARS[0]?.scenePrompt ?? "");
  /** The starting prompt is a face's sample, so it clears on a mode change. */
  const promptIsSampleRef = useRef(true);
  const [selectedExampleId, setSelectedExampleId] = useState<string | null>(null);
  const [demoFaceId, setDemoFaceId] = useState(DEMO_AVATARS[0]?.id ?? "maya");

  usePageMeta(
    "Studio · Talking, Scene, and stills",
    "Pick a face, write the line, and get a finished clip for TikTok, Reels, and Shorts. One box, then Talking or Scene. Clone your voice. Credits show before you spend.",
  );

  useEffect(() => {
    if (location.hash) {
      const id = location.hash.replace(/^#/, "");
      const el = document.getElementById(id);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, [location.pathname, location.hash]);

  const modelsForMode = useMemo(
    () => DEMO_MODELS.filter((m) => m.modality === mode),
    [mode],
  );

  const selectedModel = useMemo(
    () => modelsForMode.find((m) => m.id === modelId) || modelsForMode.find((m) => m.default) || modelsForMode[0],
    [modelsForMode, modelId],
  );

  useEffect(() => {
    if (!modelsForMode.length) return;
    if (!modelsForMode.some((m) => m.id === modelId)) {
      setModelId(modelsForMode.find((m) => m.default)?.id || modelsForMode[0].id);
    }
  }, [modelsForMode, modelId]);

  const needsFace = mode !== "image";
  const canAttachRefs = mode !== "image";
  const totalTokens = selectedModel?.token_cost ?? 8;
  const formatMeta = FORMATS.find((f) => f.id === platform) ?? FORMATS[0];
  const clipType = CLIP_TYPES.find((c) => c.id === composerTabForMode(mode));
  const selectedDemoFace = DEMO_AVATARS.find((f) => f.id === demoFaceId) ?? DEMO_AVATARS[0];
  // Talking prompts are stored joined ("scene. says: line"); show them as prose.
  const promptPreview =
    mode === "avatar" ? avatarPromptPreview(prompt) : prompt.trim();

  function goGenerate(text?: string) {
    const q = new URLSearchParams();
    q.set("intent", "access");
    q.set("mode", mode);
    q.set("platform", platform);
    const body = (text ?? prompt).trim();
    if (body) q.set("prompt", body.slice(0, 280));
    navigate(`/contact?${q.toString()}`);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    goGenerate();
  }

  function selectMode(next: PlayMode) {
    if (mode === next) return;
    if (promptIsSampleRef.current) {
      // Example and face prompts are written for one mode. Do not leave a
      // Talking script sitting in the Video field.
      promptIsSampleRef.current = false;
      setPrompt("");
      setSelectedExampleId(null);
    } else if (mode === "avatar") {
      // Leaving Talking flattens the joined draft so says: never lands in a plain field.
      setPrompt((p) => avatarPromptPreview(p));
    }
    setMode(next);
    setDemoPicker("none");
    if (next === "image") {
      setModelId("xai-image-fast");
    } else if (next === "video") {
      setModelId("seedance-2-0-fast");
    } else {
      setModelId("seedance-avatar-fast");
    }
  }

  function pickExample(example: ShowcaseExample) {
    setMode(example.mode === "lipsync" ? "avatar" : example.mode);
    setPlatform(example.platform === "feed" ? "feed" : "tiktok");
    promptIsSampleRef.current = true;
    setPrompt(example.prompt);
    setSelectedExampleId(example.id);
    // Map gallery avatar cards onto a demo face when the title/caption hints at one
    const hit = DEMO_AVATARS.find(
      (f) =>
        example.id.includes(f.id) ||
        example.title.toLowerCase().includes(f.label.toLowerCase()) ||
        example.prompt.toLowerCase().includes(f.label.toLowerCase()),
    );
    if (hit && (example.mode === "avatar" || example.mode === "lipsync")) {
      setDemoFaceId(hit.id);
    }
    composeRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function pickDemoFace(faceId: string) {
    const face = DEMO_AVATARS.find((f) => f.id === faceId);
    if (!face) return;
    setDemoFaceId(face.id);
    if (mode !== "avatar") setMode("avatar");
    promptIsSampleRef.current = true;
    setPrompt(face.scenePrompt);
    setSelectedExampleId(null);
  }

  if (auth.isAuthenticated) {
    return (
      <div className={styles.page}>
        <section className="mx-auto grid w-full max-w-5xl gap-5 px-4 py-12 sm:py-16" aria-labelledby="home-title">
          <div className="grid gap-2">
            <p className={styles.kicker}>
              <Sparkles size={12} aria-hidden />
              Create
            </p>
            <h1 id="home-title" className="m-0 text-[clamp(1.75rem,4vw,2.4rem)] font-bold tracking-[-0.03em] text-[var(--studio-fg)]">
              What are you making?
            </h1>
            <p className="m-0 max-w-xl text-sm leading-relaxed text-[var(--studio-fg-muted)]">
              Clip is Talking or Scene. Still is a single picture.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <LinkButton to="/play?mode=avatar">Clip</LinkButton>
            <LinkButton variant="secondary" to="/play?mode=image">
              Still
            </LinkButton>
          </div>
        </section>
      </div>
    );
  }

  const summaryParts = [
    formatMeta.aspect,
    "Fast · 720p",
    needsFace && selectedDemoFace ? selectedDemoFace.label : null,
    `${totalTokens} credit${totalTokens === 1 ? "" : "s"}`,
  ].filter(Boolean);

  return (
    <div className={styles.page}>
      <section className={styles.hero} aria-labelledby="hero-title">
        <div className={styles.heroAura} aria-hidden />
        <div className={styles.heroCopy}>
          <p className={styles.kicker}>
            <Sparkles size={12} aria-hidden />
            Clip · Still · Your voice
          </p>
          <h1 id="hero-title" className={styles.heroTitle}>
            Talking clips without the camera
            <span className={styles.heroTitleMuted}>Pick a face. Write the line. Post it.</span>
          </h1>
          <p className={styles.lede}>
            For people who post every day and are tired of setting up a shot. One box: describe the clip. We confirm
            Talking or Scene before you spend credits. Clone your voice once if you want it to sound
            like you. Vertical clip ready for TikTok, Reels, and Shorts.
          </p>
          <p className={styles.lede}>
            Seedance Fast is the default. Ask for 2.5 when you want longer or sharper. Stills stay on Grok. Face and
            Voice sit on the bar. Length follows the line. Every run shows what it costs in credits before you spend
            one.
          </p>
          <EarlyAccessBadge />
        </div>

        <form
          ref={composeRef}
          id="compose"
          className={styles.playShell}
          onSubmit={onSubmit}
          aria-label="Create preview"
        >
          <header className={styles.playTop}>
            <h2 className={styles.playTopTitle}>
              <Sparkles size={16} className="text-[var(--studio-brand)]" aria-hidden />
              Create
            </h2>
            <div className={styles.playTopMeta}>
              <span>One clip at a time</span>
              <span aria-hidden>·</span>
              <span>{selectedExampleId ? "Example loaded" : "Sign up to run for real"}</span>
            </div>
          </header>

          <div className={styles.playThread} aria-label="Sample thread">
            {prompt.trim() ? (
              <>
                <div className={styles.playUserBubble}>
                  {needsFace && selectedDemoFace ? (
                    <div className="mb-2 flex items-center gap-2">
                      <img
                        src={selectedDemoFace.imageUrl}
                        alt=""
                        className="h-8 w-8 rounded-full object-cover ring-1 ring-[var(--studio-border)]"
                      />
                      <span className="text-[0.75rem] font-semibold text-[var(--studio-fg-muted)]">
                        {selectedDemoFace.label}
                      </span>
                    </div>
                  ) : null}
                  <p className="m-0 whitespace-pre-wrap">{promptPreview}</p>
                  <p className="m-0 mt-1 text-[0.7rem] font-semibold uppercase tracking-wide text-[var(--studio-fg-subtle)]">
                    {composerTabLabel(mode)} · {formatMeta.aspect}
                  </p>
                </div>
                <div className={styles.playSystemBubble}>
                  Got it
                  {needsFace && selectedDemoFace ? ` · using ${selectedDemoFace.label}` : ""}. Making a{" "}
                  {clipNoun(mode)} for {platform === "feed" ? "square" : "vertical"}. Create an account to generate for real.
                </div>
              </>
            ) : (
              <p className="m-0 text-center text-sm text-[var(--studio-fg-muted)]">
                {needsFace
                  ? "Write what the clip is about. We confirm Talking or Scene before you spend credits."
                  : "Describe the still. Same composer as Create once you sign up."}
              </p>
            )}
          </div>

          <div className={styles.playComposer}>
            <div
              className="flex rounded-xl bg-[var(--studio-chip-off,var(--studio-fill-quiet))] p-0.5"
              role="tablist"
              aria-label="Create"
            >
              {CLIP_TYPES.map((item) => {
                const on = composerTabForMode(mode) === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    role="tab"
                    aria-selected={on}
                    title={item.blurb}
                    className={cn(
                      "min-h-10 flex-1 rounded-[10px] text-sm font-bold",
                      on
                        ? "bg-[var(--studio-chip-on,var(--studio-fill))] text-[var(--studio-brand)]"
                        : "bg-transparent text-[var(--studio-fg)]",
                    )}
                    onClick={() =>
                      selectMode(item.id === "still" ? "image" : mode === "image" ? "avatar" : mode)
                    }
                  >
                    {item.label}
                  </button>
                );
              })}
            </div>
            {clipType ? <p className={styles.playFieldBlurb}>{clipType.blurb}</p> : null}

            {mode !== "image" ? (
              <button
                type="button"
                className="flex min-h-9 w-full items-center gap-1.5 border-b border-[var(--studio-border-soft)] px-1 pb-2 text-left text-[15px] font-semibold text-[var(--studio-fg)]"
                aria-pressed={demoPicker === "voice"}
                aria-label={`Voice, ${demoVoice}`}
                onClick={() => setDemoPicker((p) => (p === "voice" ? "none" : "voice"))}
              >
                <span className="min-w-0 flex-1 truncate">{demoVoice}</span>
              </button>
            ) : (
              <div className="flex gap-1.5">
                {(
                  [
                    { id: "xai-image-fast", label: "Fast" },
                    { id: "xai-image-quality", label: "Quality" },
                  ] as const
                ).map((tier) => (
                  <button
                    key={tier.id}
                    type="button"
                    className={cn(styles.chip, modelId === tier.id && styles.chipActive)}
                    onClick={() => setModelId(tier.id)}
                  >
                    {tier.label}
                  </button>
                ))}
              </div>
            )}

            {demoPicker === "voice" && mode !== "image" ? (
              <div className="flex flex-wrap gap-1.5">
                {DEMO_VOICES.map((name) => (
                  <button
                    key={name}
                    type="button"
                    className={cn(styles.chip, demoVoice === name && styles.chipActive)}
                    onClick={() => setDemoVoice(name)}
                  >
                    {name}
                  </button>
                ))}
              </div>
            ) : null}

            {demoPicker === "face" && needsFace ? (
              <div className={styles.playFaceRow} role="listbox" aria-label="Demo faces">
                {DEMO_AVATARS.map((face) => {
                  const on = face.id === demoFaceId;
                  return (
                    <button
                      key={face.id}
                      type="button"
                      role="option"
                      aria-selected={on}
                      className={cn(styles.playFaceChip, on && styles.playFaceChipOn)}
                      onClick={() => pickDemoFace(face.id)}
                      title={face.caption}
                    >
                      <img
                        src={face.imageUrl}
                        alt={face.label}
                        className={styles.playFaceImg}
                        width={56}
                        height={56}
                        decoding="async"
                      />
                      <span className={styles.playFaceName}>{face.label}</span>
                    </button>
                  );
                })}
              </div>
            ) : null}

            <div className="flex items-center gap-1.5 rounded-[22px] border border-[var(--studio-border)] bg-[var(--input-bg,var(--studio-fill-quiet))] py-1.5 pl-2 pr-1.5">
              {needsFace ? (
                <button
                  type="button"
                  className={cn(
                    "h-11 w-11 shrink-0 overflow-hidden rounded-full border-[1.5px]",
                    selectedDemoFace
                      ? "border-solid border-[var(--studio-brand)]"
                      : "border-dashed border-[var(--studio-brand)]",
                  )}
                  aria-label={selectedDemoFace ? "Change face" : "Add face"}
                  aria-pressed={demoPicker === "face"}
                  onClick={() => setDemoPicker((p) => (p === "face" ? "none" : "face"))}
                >
                  {selectedDemoFace?.imageUrl ? (
                    <img src={selectedDemoFace.imageUrl} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <span className="text-lg font-bold text-[var(--studio-brand)]">+</span>
                  )}
                </button>
              ) : null}
              <PromptFields
                mode={mode}
                isExtending={false}
                prompt={prompt}
                onPromptChange={(next) => {
                  promptIsSampleRef.current = false;
                  setPrompt(next);
                  setSelectedExampleId(null);
                }}
                classNames={{
                  shell: "min-w-0 flex-1 border-0 bg-transparent",
                  field: "min-h-9 resize-none border-0 bg-transparent px-1 py-2 text-base outline-none placeholder:text-[var(--studio-fg-subtle)]",
                }}
              />
              <div className="flex shrink-0 items-center gap-1.5">
                {canAttachRefs ? (
                  <button
                    type="button"
                    className="flex h-11 w-11 items-center justify-center rounded-full border border-[var(--studio-border)] bg-[var(--studio-chip-off,var(--studio-fill-quiet))] text-lg font-extrabold text-[var(--studio-brand)]"
                    onClick={() => goGenerate()}
                    aria-label="Add reference"
                  >
                    +
                  </button>
                ) : null}
                <button
                  type="submit"
                  className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--studio-brand)] text-white"
                  aria-label="Generate"
                >
                  <ArrowRight size={18} />
                </button>
              </div>
            </div>

            <p className={styles.playHint}>{summaryParts.join(" · ")}</p>
          </div>
        </form>

        <div className={styles.ctaRow}>
          <LinkButton to="/register">
            Create account
            <ArrowRight size={16} />
          </LinkButton>
          <LinkButton variant="secondary" to="/login">
            Sign in
          </LinkButton>
          <LinkButton variant="secondary" to="#examples">
            Browse examples
          </LinkButton>
        </div>
      </section>

      <ExampleMarquee />

      <section id="examples" className="w-full scroll-mt-24" aria-label="Example gallery">
        <ExampleShowcase selectedId={selectedExampleId} onPick={pickExample} />
      </section>

      <div className={styles.ctaPanel}>
        <div className={styles.ctaPanelInner}>
          <div className="grid gap-2">
            <p className={styles.kicker}>Get started</p>
            <h2 className="m-0 text-[clamp(1.35rem,2.5vw,1.75rem)] font-bold tracking-[-0.02em] text-[var(--studio-fg)]">
              Create a free account
            </h2>
            <p className="m-0 max-w-xl text-sm leading-relaxed text-[var(--studio-fg-muted)]">
              Make your first clip tonight. If you want the full picture first, read{" "}
              <Link className="font-semibold text-[var(--studio-brand)] no-underline hover:underline" to="/about">
                about
              </Link>
              {" "}
              or{" "}
              <Link className="font-semibold text-[var(--studio-brand)] no-underline hover:underline" to="/pricing">
                pricing
              </Link>
              .
            </p>
          </div>
          <div className={styles.ctaRow}>
            <LinkButton to="/register">Create account</LinkButton>
            <LinkButton variant="secondary" to="/login">
              Sign in
            </LinkButton>
          </div>
        </div>
      </div>
    </div>
  );
}
