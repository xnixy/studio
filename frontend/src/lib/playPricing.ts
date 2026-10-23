/** Client-side estimate mirroring backend play_pricing (display only; server is authoritative). */
import type { PlayModelOption, PlayMode } from "../types";

export type PlayTokenQuote = {
  meter: string;
  per_item: number;
  count: number;
  total: number;
  base: number;
};

function durationFactor(seconds: number | null | undefined): number {
  if (!seconds || seconds <= 0) return 1;
  return Math.max(0.8, Math.min(3, seconds / 5));
}

function resolutionFactor(resolution: string | null | undefined): number {
  const r = (resolution || "720p").toLowerCase();
  if (r === "480p" || r === "480") return 0.85;
  if (r === "1080p" || r === "1080" || r === "fhd") return 1.5;
  if (r === "4k" || r === "2160p") return 2.5;
  return 1;
}

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
}): PlayTokenQuote {
  const base = Math.max(1, opts.model?.token_cost ?? 1);
  const provider = (opts.model?.provider || "xai").toLowerCase();
  const mode = opts.mode;

  if (mode === "image") {
    return { meter: "play_still", per_item: base, count: 1, total: base, base };
  }

  const batch =
    provider === "seedance" ? Math.max(1, Math.min(opts.batchCount ?? 1, 10)) : 1;
  const fDur = durationFactor(opts.durationSeconds);
  const fRes = resolutionFactor(opts.resolution);
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
  return {
    meter,
    per_item: perItem,
    count: batch,
    total: perItem * batch,
    base,
  };
}

export function meterLabel(meter: string): string {
  switch (meter) {
    case "play_avatar":
      return "talking";
    case "play_video":
      return "video";
    case "play_still":
      return "still";
    case "play_face":
      return "face";
    case "play_lipsync":
      return "clip";
    default:
      return "credits";
  }
}

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
 *
 * Kept byte-identical to mobile createConstants.ts. Change both together.
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

/** Compose the canonical Talking prompt the backend parser expects. */
export function joinAvatarPrompt(scene: string, line: string): string {
  const s = (scene || "").trim().replace(/[.,;:\s]+$/, "");
  const l = (line || "").trim();
  if (!l) return s;
  return s ? `${s}. says: ${l}` : `says: ${l}`;
}

/**
 * Spoken line for Talking prompts with ``says:`` or natural "and says".
 * Mirrors backend split_avatar_user_prompt.
 */
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

/** Live Talking field: hide says: on inbound drafts, keep typed spaces intact. */
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

/** Rough spoken seconds clamped to a clip length (matches backend estimate_speech_seconds). */
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

export function estimateTalkingDurationSeconds(prompt: string): number {
  const line = spokenLineFromAvatarPrompt(prompt);
  // No line means nothing to measure. Measuring the scene text instead sized the
  // clip from a description nobody speaks, which floored most drafts at 4s.
  if (!line) return TOPIC_ONLY_AUTO_SECONDS;
  return estimateVoiceoverSeconds(line);
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
