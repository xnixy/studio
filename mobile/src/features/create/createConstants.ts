import type { PlayMode, PlayModelOption } from "@/src/api/types";

export type ComposerTab = "clip" | "still";

export const MODES: { id: ComposerTab; label: string; blurb: string }[] = [
  {
    id: "clip",
    label: "Clip",
    blurb: "A short video. We confirm the kind before you spend.",
  },
  { id: "still", label: "Still", blurb: "One image." },
];

export function composerTabForMode(mode: PlayMode): ComposerTab {
  return mode === "image" ? "still" : "clip";
}

export const MODE_HINT: Partial<Record<PlayMode, string>> = {
  avatar: "Describe the clip. We confirm the kind before you spend credits.",
  lipsync: "Describe the clip. We confirm the kind before you spend credits.",
  video: "Describe the clip. We confirm the kind before you spend credits.",
  image: "Describe the still. No spoken lines.",
};

export const PROMPT_PLACEHOLDER: Record<PlayMode, string> = {
  avatar: "What is the clip about?",
  lipsync: "What is the clip about?",
  video: "What is the clip about?",
  image: "Describe the still",
};

const AVATAR_SAYS_RE = /\bsays?\s*:\s*(.+)\s*$/is;
const SAY_EXACTLY_RE = /(?:say exactly|read this(?: aloud)?)\s*:?\s+(.+)$/is;
const BARE_LINE_RE =
  /^(?:hey|hi|hello|welcome)\b|^(?:i(?:['’]m| am)?|we(?:['’]re| are)?|you)\b/i;
const PLACE_START_RE =
  /^(?:kitchen|bedroom|bathroom|office|cafe|café|street|studio|beach|park|gym|car|apartment|counter|mirror|living room|sidewalk|rooftop)\b/i;
const AVATAR_NATURAL_SAYS_RE =
  /(?:(?:^|[.,;!?]\s+|,\s*)(?:he|she|they|i|we)\s+says?\s+|(?:^|\s+)and\s+(?:(?:he|she|they|i|we)\s+)?says?\s+)(?!that\b)(.+)$/is;
/** Mirrors backend _AVATAR_DANGLING_SAYS_RE. Empty tails must not keep the token. */
const AVATAR_DANGLING_SAYS_RE = /[\s.,;:]*\bsays?\s*:\s*$/is;

/** Mirrors backend _AVATAR_SCENE_LEADIN_RE ("He looks at camera and", bare "She"). */
const SCENE_LEADIN_RE =
  /(?:^|[,.\s]+)(?:he|she|they|i|we)(?:\s+looks?\s+at\s+(?:the\s+)?camera\s+and|\s+leans?\s+towards?\s+(?:the\s+)?camera\s+and|\s+faces?\s+(?:the\s+)?camera\s+and|\s+turns?\s+to\s+(?:the\s+)?camera\s+and)?\s*$/i;

/** Flowing prompts leave "…holds the bottle and" behind; drop the dangling word. */
const TRAILING_CONJUNCTION_RE = /\s+(?:and|then|while|as)\s*$/i;

/**
 * Split a Talking prompt into scene + spoken line.
 * Mirrors backend split_avatar_user_prompt: says: or natural "and says LINE" /
 * "and she says LINE" / "She says LINE". "?" and "!" are sentence breaks.
 * No speech verb means the whole text is scene. Runs only on inbound prompts
 * (starters, reuse, retry), never on live keystrokes.
 */
/** Mirrors backend _QUOTED_SPAN_RE, anchored to the start of the spoken tail. */
const QUOTED_LINE_RE = /^["\u201C]([^"\u201C\u201D]{2,})["\u201D]/;

export function splitAvatarPrompt(prompt: string): { scene: string; line: string } {
  const text = (prompt || "").trim();
  if (!text) return { scene: "", line: "" };
  const match =
    text.match(AVATAR_SAYS_RE) || text.match(SAY_EXACTLY_RE) || text.match(AVATAR_NATURAL_SAYS_RE);
  const tail = (match?.[1] || "").trim();
  if (!match || !tail) {
    const scene = text.replace(AVATAR_DANGLING_SAYS_RE, "").trim();
    if (scene && BARE_LINE_RE.test(scene) && !PLACE_START_RE.test(scene)) {
      return { scene: "", line: scene };
    }
    return { scene, line: "" };
  }
  // A quote opening the line bounds it, so trailing stage direction goes back to
  // the scene. Anchored, matching the backend: a mid-line quote is emphasis
  // ('I call it "the fix"'), not a boundary.
  const quoted = tail.match(QUOTED_LINE_RE);
  const line = quoted ? (quoted[1] || "").trim() : tail;
  const trailing = quoted ? tail.slice(quoted[0].length).replace(/^[.,;:\s]+/, "").trim() : "";
  let scene = text
    .slice(0, match.index)
    .trim()
    .replace(SCENE_LEADIN_RE, "")
    .replace(TRAILING_CONJUNCTION_RE, "")
    .replace(/[.,;:\s]+$/, "");
  if (trailing) scene = scene ? `${scene}. ${trailing}` : trailing;
  if (!line) return { scene, line: "" };
  return { scene, line };
}

/** Compose the canonical Talking prompt the backend parser expects. */
export function joinAvatarPrompt(scene: string, line: string): string {
  const s = (scene || "").trim().replace(/[.,;:\s]+$/, "");
  const l = (line || "").trim();
  if (!l) return s;
  return s ? `${s}. says: ${l}` : `says: ${l}`;
}

/** Spoken line only for Talking prompts that use ``says:``. Empty when absent. */
export function spokenLineFromAvatarPrompt(prompt: string): string {
  return splitAvatarPrompt(prompt).line;
}

/**
 * Plain prose for anywhere a Talking prompt is shown back to the user
 * (thread bubbles, sample cards). The joined form carries the says: parser
 * token, which nobody should ever have to read.
 */
export function avatarPromptPreview(prompt: string): string {
  const { scene, line } = splitAvatarPrompt(prompt);
  if (!line) return scene;
  return scene ? `${scene}. ${line}` : line;
}

/**
 * Live Talking field value. Joined inbound drafts hide the says: token.
 * Typed text is shown as-is so trailing spaces and "and" are not eaten by
 * scene cleanup on every keystroke.
 */
export function avatarPromptForField(prompt: string): string {
  if (!AVATAR_SAYS_RE.test(prompt || "")) return prompt;
  return avatarPromptPreview(prompt);
}

/** Longest Talking take. Longer talk is Extend. Fast is 15s. */
export const CLIP_FAST_MAX_SECONDS = 15;
export const CLIP_ADVANCED_MAX_SECONDS = 30;

/** Old Photo (`lipsync`) is Talking. The schema still accepts the token. */
export function normalizePlayMode(mode: string | null | undefined): PlayMode | null {
  if (mode === "lipsync") return "avatar";
  if (mode === "avatar" || mode === "video" || mode === "image") return mode;
  return null;
}

/** Spoken line we can TTS on Scene. Quotes, says:, or natural and says. Signage quotes do not count. */
const WRITTEN_QUOTE_LEAD_RE =
  /\b(sign|signage|poster|banner|billboard|label|sticker|screen|display|caption|subtitle|logo|menu|placard|note|card|headline|title)s?\b.{0,48}(?:reads?|reading|says?)\s*$/is;

export function promptHasQuotedSpeech(text: string): boolean {
  const body = text || "";
  const quoteRe = /["“]([^"“”]{2,})["”]/g;
  let prev = 0;
  for (const match of body.matchAll(quoteRe)) {
    const lead = body.slice(prev, match.index);
    prev = (match.index ?? 0) + match[0].length;
    if (WRITTEN_QUOTE_LEAD_RE.test(lead)) continue;
    return true;
  }
  return spokenLineFromAvatarPrompt(text).trim().length > 0;
}

/** Client estimate. Mirror frontend playPricing.estimatePlayTokens. Server is authority. */
export function estimatePlayTokens(opts: {
  mode: PlayMode;
  model: PlayModelOption | null | undefined;
  durationSeconds?: number | null;
  resolution?: string | null;
  batchCount?: number;
  generateAudio?: boolean;
  returnLastFrame?: boolean;
  refImageCount?: number;
  refVideoCount?: number;
  refAudioCount?: number;
}): { meter: string; per_item: number; count: number; total: number; base: number } {
  const base = Math.max(1, opts.model?.token_cost ?? 1);
  const provider = (opts.model?.provider || "xai").toLowerCase();
  const mode = opts.mode;
  const fDur =
    !opts.durationSeconds || opts.durationSeconds <= 0
      ? 1
      : Math.max(0.8, Math.min(3, opts.durationSeconds / 5));
  const r = (opts.resolution || "720p").toLowerCase();
  const fRes =
    r === "480p" || r === "480"
      ? 0.85
      : r === "1080p" || r === "1080" || r === "fhd"
        ? 1.5
        : r === "4k" || r === "2160p"
          ? 2.5
          : 1;

  if (mode === "image") {
    return { meter: "play_still", per_item: base, count: 1, total: base, base };
  }

  const batch = provider === "seedance" ? Math.max(1, Math.min(opts.batchCount ?? 1, 10)) : 1;
  const fAudio = opts.generateAudio === false ? 0.9 : 1;
  const fLast = opts.returnLastFrame ? 1.1 : 1;
  let refsExtra = 0;
  const img = Math.max(0, opts.refImageCount ?? 0);
  const vid = Math.max(0, opts.refVideoCount ?? 0);
  const aud = Math.max(0, opts.refAudioCount ?? 0);
  if (provider === "seedance") {
    refsExtra += Math.min(img, 9) + Math.min(vid, 3) * 2 + Math.min(aud, 3) * 2;
  } else {
    refsExtra += Math.min(img, 7);
  }
  const perItem = Math.max(1, Math.ceil(base * fDur * fRes * fAudio * fLast) + refsExtra);
  const meter = mode === "avatar" || mode === "lipsync" ? "play_avatar" : "play_video";
  return { meter, per_item: perItem, count: batch, total: perItem * batch, base };
}

/**
 * Domains are spoken out before TTS ("example.com" becomes "example dot com"), and the
 * server counts words after that. Mirrors backend expand_spoken_domains so the
 * composer cannot promise a length the API then rejects.
 */
function expandSpokenDomains(text: string): string {
  return text.replace(
    /\b([a-zA-Z0-9-]{2,40})\.(com|io|ai|app|co|dev|net|org)\b/g,
    (match, host: string, tld: string, offset: number) =>
      offset > 0 && text[offset - 1] === "@" ? match : `${host} dot ${tld}`,
  );
}

/** Unclamped spoken seconds (matches backend raw_speech_seconds). */
export function rawSpeechSeconds(script: string): number {
  const words = expandSpokenDomains(script)
    .trim()
    .split(/\s+/)
    .filter((w) => w.length > 0);
  if (!words.length) return 0;
  return words.length / 2.4 + 1;
}

/** ~spoken length clamped to a clip length (matches backend estimate_speech_seconds). */
export function estimateVoiceoverSeconds(script: string): number {
  const seconds = rawSpeechSeconds(script);
  if (!seconds) return 5;
  return Math.max(4, Math.min(CLIP_ADVANCED_MAX_SECONDS, Math.round(seconds)));
}

/**
 * Auto length for a topic with no line (backend TOPIC_ONLY_AUTO_SECONDS).
 * Mid-range for every provider list and worth about 16 words at 2.4 w/s.
 */
export const TOPIC_ONLY_AUTO_SECONDS = 8;

/** Auto length for Talking (backend parity with estimate_speech_seconds). */
export function estimateTalkingDurationSeconds(prompt: string): number {
  const line = spokenLineFromAvatarPrompt(prompt);
  // No line means nothing to measure. Measuring the scene text instead sized the
  // clip from a description nobody speaks, which floored most drafts at 4s.
  if (!line) return TOPIC_ONLY_AUTO_SECONDS;
  return estimateVoiceoverSeconds(line);
}

/** Snap auto estimate to a provider's allowed discrete lengths. */
export function snapDurationToChoices(
  seconds: number,
  choices: readonly number[],
): number {
  if (!choices.length) return seconds;
  let best = choices[0];
  let bestDist = Math.abs(best - seconds);
  for (const c of choices) {
    const d = Math.abs(c - seconds);
    if (d < bestDist || (d === bestDist && c > best)) {
      best = c;
      bestDist = d;
    }
  }
  return best;
}

export const DURATION_OPTIONS = [4, 5, 6, 8, 10, 12, 15] as const;
export const VEO_DURATION_OPTIONS = [4, 6, 8] as const;
export const SEEDANCE_DURATION_OPTIONS = [4, 5, 6, 8, 10, 12, 15, 20, 25, 30] as const;
export const GROK_DURATION_OPTIONS = [5, 8, 10, 12, 15] as const;
export const KLING_DURATION_OPTIONS = [5, 6, 8, 10, 12, 15] as const;
export const RESOLUTION_OPTIONS = ["480p", "720p", "1080p", "4k"] as const;
export const BATCH_OPTIONS = [1, 2, 3, 4, 5, 6, 8, 10] as const;

/** Seedance 2.5 catalog ids (Talking / Scene) cap at 720p. */
export function isSeedance25Model(modelId?: string | null): boolean {
  const id = (modelId || "").toLowerCase();
  return (
    id === "seedance-2-5" ||
    id === "seedance-avatar" ||
    id === "seedance-photo" ||
    id.includes("2-5") ||
    id.includes("2.5")
  );
}

export function durationOptionsForProvider(
  provider: string | undefined | null,
  opts?: { modelId?: string | null; maxDuration?: number | null },
): readonly number[] {
  const p = (provider || "").toLowerCase();
  if (p === "gemini") return VEO_DURATION_OPTIONS;
  if (p === "seedance") {
    const max = opts?.maxDuration ?? 15;
    return SEEDANCE_DURATION_OPTIONS.filter((d) => d <= max);
  }
  if (p === "xai") return GROK_DURATION_OPTIONS;
  if (p === "kling") {
    const mid = (opts?.modelId || "").toLowerCase();
    if (mid.includes("v2-6") || mid.includes("v2.6") || mid.includes("v1")) {
      return [5, 10] as const;
    }
    const max = opts?.maxDuration ?? 15;
    return KLING_DURATION_OPTIONS.filter((d) => d <= max);
  }
  return DURATION_OPTIONS;
}

export function resolutionOptionsForProvider(
  provider: string | undefined | null,
  opts?: { modelId?: string | null },
): readonly string[] {
  const p = (provider || "").toLowerCase();
  if (p === "seedance") {
    if (isSeedance25Model(opts?.modelId)) return ["480p", "720p"] as const;
    return RESOLUTION_OPTIONS;
  }
  if (p === "gemini" || p === "kling") return ["720p", "1080p"] as const;
  if (p === "xai") return ["480p", "720p"] as const;
  return ["720p"] as const;
}

export function modeLabel(mode: PlayMode): string {
  if (mode === "avatar" || mode === "lipsync") return "Talking";
  if (mode === "image") return "Still";
  return "Scene";
}

export function composerTabLabel(mode: PlayMode): string {
  return mode === "image" ? "Still" : "Clip";
}

/** Every Create send talks the clip through first. Kind chips are the override. */
export function modeUsesAssist(_mode?: PlayMode): boolean {
  return true;
}

/** Mirrors backend _looks_like_two_hander. A man/woman who asks is Scene. */
const OTHER_SPEAKER_RE =
  /\b(?:a |the |another |her |his )?(?:man|men|woman|women|guy|girl|boy|lady|stranger|friend)\b[^.?!\n]{0,48}\b(?:asks?|says?|replies|replied|asked)\b/i;
const FRIEND_SPEAKS_RE = /\b(?:the |her |his )?friend (?:replies|says|asks)\b/i;

export function promptLooksLikeTwoHander(text: string): boolean {
  const raw = text || "";
  const quotes = raw.match(/["\u201C]([^"\u201C\u201D]{2,})["\u201D]/g);
  if (quotes && quotes.length >= 2) return true;
  if (FRIEND_SPEAKS_RE.test(raw)) return true;
  return OTHER_SPEAKER_RE.test(raw);
}

/**
 * Paid generate kind. Assist confirms Talking or Scene.
 * If assist never settled, do not assume Talking (that needs a face and a line).
 * Two people speaking is Scene even if the last "and says" looks like a Face line.
 */
export function generateModeForPrompt(opts: {
  tabMode: PlayMode;
  draftKind?: PlayMode | null;
  prompt: string;
  hasFace: boolean;
}): PlayMode {
  if (opts.tabMode === "image") return "image";
  const kind = normalizePlayMode(opts.draftKind);
  const line = spokenLineFromAvatarPrompt(opts.prompt || "").trim();
  if (kind === "avatar" || kind === "video") {
    if (kind === "avatar" && !opts.hasFace) return "video";
    if (kind === "avatar" && !line) return "video";
    return kind;
  }
  if (promptLooksLikeTwoHander(opts.prompt || "")) return "video";
  if (opts.hasFace && line) return "avatar";
  return "video";
}

/** A scene generate only sends SCENE. Fold a leftover Talking line in as quotes. */
export function videoPromptFromDraft(
  draft: { scene?: string | null; line?: string | null } | null | undefined,
  fallback: string,
): string {
  const scene = (draft?.scene || "").trim();
  const line = (draft?.line || "").trim().replace(/^["\u201C]|["\u201D]$/g, "");
  if (!line) return scene || fallback;
  if (!scene) return `"${line}"`;
  if (scene.toLowerCase().includes(line.toLowerCase())) return scene;
  return `${scene.replace(/[.]+$/, "")}. "${line}"`;
}

/** Talking / Scene / Still from a generation row. */
export function generationKindLabel(gen: {
  mode?: string | null;
  asset_type?: string | null;
}): string {
  if (gen.mode === "lipsync") return modeLabel("lipsync");
  if (gen.mode === "avatar") return modeLabel("avatar");
  if (gen.mode === "image" || gen.asset_type === "image") return modeLabel("image");
  return modeLabel("video");
}

export function generationStatusLabel(status: string | null | undefined): string {
  const s = (status || "").toLowerCase();
  if (s === "ready") return "Ready";
  if (s === "failed" || s === "error") return "Failed";
  if (s === "cancelled") return "Cancelled";
  if (s === "expired") return "Expired";
  if (!s) return "";
  return "Working";
}

/** Feed is 1:1. Everything else (incl. custom) is 9:16. */
export function isSquarePlatform(platform: string | null | undefined): boolean {
  return platform === "feed";
}

/**
 * Create-thread clip card size. Vertical stays phone-narrow so a 9:16 clip is
 * not letterboxed inside a wide bubble. Mirror: playPageChrome.threadClipCardClass.
 */
export function threadClipCardWidth(
  screenWidth: number,
  platform: string | null | undefined,
): number {
  if (isSquarePlatform(platform)) return Math.min(300, Math.round(screenWidth * 0.78));
  return Math.min(228, Math.round(screenWidth * 0.56));
}

/**
 * Anything a person reads or copies. Talking may still be stored joined
 * (`scene. says: line`); this is the prose form.
 */
export function promptForDisplay(
  prompt: string | null | undefined,
  mode?: string | null,
): string {
  const text = (prompt || "").trim();
  if (!text) return "";
  if (mode === "avatar" || /\bsays?\s*:/i.test(text)) return avatarPromptPreview(text);
  return text;
}
