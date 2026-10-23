import type { PlayVoiceOption } from "../../types";

/**
 * Offline fallback when GET /play/voices is unavailable.
 * Prefer the API list (includes cloned voices + live catalog + sort).
 * Featured five first; rest sorted female → male → A–Z (server does the same).
 */
export const DEFAULT_BUILTIN_VOICE_ID = "jessica";

export const BUILTIN_VOICES: PlayVoiceOption[] = [
  { id: "jessica", name: "Jessica", description: "Warm and conversational", source: "builtin", available: true, gender: "female", accent: "american", language: "multilingual" },
  { id: "lily", name: "Lily", description: "Soft British, easygoing", source: "builtin", available: true, gender: "female", accent: "british", language: "multilingual" },
  { id: "alice", name: "Alice", description: "Clear and engaging", source: "builtin", available: true, gender: "female", accent: "british", language: "multilingual" },
  { id: "matilda", name: "Matilda", description: "Calm and professional", source: "builtin", available: true, gender: "female", accent: "american", language: "multilingual" },
  { id: "laura", name: "Laura", description: "Gentle and even", source: "builtin", available: true, gender: "female", accent: "american", language: "multilingual" },
  { id: "aria", name: "Aria", description: "Expressive American", source: "builtin", available: true, gender: "female", accent: "american", language: "multilingual" },
  { id: "charlotte", name: "Charlotte", description: "Bright European", source: "builtin", available: true, gender: "female", accent: "swedish", language: "multilingual" },
  { id: "river", name: "River", description: "Relaxed and even", source: "builtin", available: true, gender: "neutral", accent: "american", language: "multilingual" },
  { id: "brian", name: "Brian", description: "Clear and professional", source: "builtin", available: true, gender: "male", accent: "american", language: "multilingual" },
  { id: "daniel", name: "Daniel", description: "Warm British", source: "builtin", available: true, gender: "male", accent: "british", language: "multilingual" },
  { id: "liam", name: "Liam", description: "Bright and energetic", source: "builtin", available: true, gender: "male", accent: "american", language: "multilingual" },
  { id: "will", name: "Will", description: "Casual American", source: "builtin", available: true, gender: "male", accent: "american", language: "multilingual" },
  { id: "george", name: "George", description: "Smooth and grounded", source: "builtin", available: true, gender: "male", accent: "british", language: "multilingual" },
  { id: "bill", name: "Bill", description: "Warm and steady", source: "builtin", available: true, gender: "male", accent: "american", language: "multilingual" },
  { id: "callum", name: "Callum", description: "Husky British", source: "builtin", available: true, gender: "male", accent: "british", language: "multilingual" },
  { id: "charlie", name: "Charlie", description: "Confident Australian", source: "builtin", available: true, gender: "male", accent: "australian", language: "multilingual" },
  { id: "chris", name: "Chris", description: "Easygoing American", source: "builtin", available: true, gender: "male", accent: "american", language: "multilingual" },
  { id: "eric", name: "Eric", description: "Smooth American", source: "builtin", available: true, gender: "male", accent: "american", language: "multilingual" },
  { id: "roger", name: "Roger", description: "Laid-back American", source: "builtin", available: true, gender: "male", accent: "american", language: "multilingual" },
];

export const FEATURED_VOICE_IDS = ["jessica", "lily", "brian", "daniel", "liam"] as const;
const GENDER_RANK: Record<string, number> = { female: 0, male: 1, neutral: 2 };

const ACCENT_LABELS: Record<string, string> = {
  american: "American",
  british: "British",
  indian: "Indian",
  australian: "Australian",
  canadian: "Canadian",
  irish: "Irish",
  swedish: "Swedish",
  scottish: "Scottish",
  german: "German",
  croatian: "Croatian",
  nigerian: "Nigerian",
  jamaican: "Jamaican",
  malay: "Malaysian",
  "us southern": "Southern US",
  "new york": "New York",
  "south african": "South African",
  "african american": "American",
};

export function isBuiltinVoice(voice: PlayVoiceOption): boolean {
  return (voice.source ?? "builtin") === "builtin";
}

export function isClonedVoice(voice: PlayVoiceOption): boolean {
  const source = voice.source ?? "builtin";
  return source === "cloned" || source === "custom";
}

/** First built-in when the current pick is missing. */
export function defaultBuiltinVoiceId(voices: PlayVoiceOption[] = BUILTIN_VOICES): string {
  if (voices.some((v) => v.id === DEFAULT_BUILTIN_VOICE_ID)) return DEFAULT_BUILTIN_VOICE_ID;
  const first = voices.find((v) => (v.source ?? "builtin") === "builtin");
  return first?.id || DEFAULT_BUILTIN_VOICE_ID;
}

/** Match server sort when the client only has a fallback list or mixed data. */
export function sortPlayVoices(voices: PlayVoiceOption[]): PlayVoiceOption[] {
  return [...voices].sort((a, b) => {
    const aClone = isClonedVoice(a) ? 1 : 0;
    const bClone = isClonedVoice(b) ? 1 : 0;
    if (aClone !== bClone) return aClone - bClone;

    const ai = FEATURED_VOICE_IDS.indexOf(a.id as (typeof FEATURED_VOICE_IDS)[number]);
    const bi = FEATURED_VOICE_IDS.indexOf(b.id as (typeof FEATURED_VOICE_IDS)[number]);
    const aInFeatured = ai !== -1;
    const bInFeatured = bi !== -1;
    if (aInFeatured && bInFeatured) return ai - bi;
    if (aInFeatured !== bInFeatured) return aInFeatured ? -1 : 1;

    const ag = GENDER_RANK[(a.gender || "").toLowerCase()] ?? 9;
    const bg = GENDER_RANK[(b.gender || "").toLowerCase()] ?? 9;
    if (ag !== bg) return ag - bg;
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  });
}

export function voiceGenderLabel(gender?: string | null): string | null {
  const g = (gender || "").toLowerCase();
  if (g === "female") return "Female";
  if (g === "male") return "Male";
  if (g === "neutral") return "Neutral";
  return null;
}

export function voiceAccentLabel(accent?: string | null): string | null {
  const key = (accent || "").trim().toLowerCase();
  if (!key) return null;
  return ACCENT_LABELS[key] || key.replace(/\b\w/g, (ch) => ch.toUpperCase());
}

export function voiceAccentOptions(voices: PlayVoiceOption[]): string[] {
  const seen = new Set<string>();
  for (const v of voices) {
    const key = (v.accent || "").trim().toLowerCase();
    if (key) seen.add(key);
  }
  return [...seen].sort((a, b) => (voiceAccentLabel(a) || a).localeCompare(voiceAccentLabel(b) || b));
}

export function matchesVoiceSearch(voice: PlayVoiceOption, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const gender = (voice.gender || "").toLowerCase();
  const accent = (voice.accent || "").toLowerCase();
  const accentLabel = (voiceAccentLabel(voice.accent) || "").toLowerCase();
  return (
    voice.name.toLowerCase().includes(q) ||
    voice.id.toLowerCase().includes(q) ||
    (voice.description || "").toLowerCase().includes(q) ||
    gender.includes(q) ||
    accent.includes(q) ||
    accentLabel.includes(q) ||
    (gender === "female" && "woman".includes(q)) ||
    (gender === "male" && "man".includes(q))
  );
}

/** Featured five plus clones and the current pick. Full catalog lives on Voices. */
export function voicesForCreateBar(
  voices: PlayVoiceOption[],
  selectedId?: string | null,
  featuredIds: readonly string[] = FEATURED_VOICE_IDS,
): PlayVoiceOption[] {
  const byId = new Map(voices.map((v) => [v.id, v]));
  const out: PlayVoiceOption[] = [];
  const seen = new Set<string>();
  const push = (v: PlayVoiceOption | undefined) => {
    if (!v || seen.has(v.id)) return;
    out.push(v);
    seen.add(v.id);
  };
  for (const v of voices) {
    if (isClonedVoice(v)) push(v);
  }
  for (const id of featuredIds) push(byId.get(id));
  if (selectedId) push(byId.get(selectedId));
  return out;
}
