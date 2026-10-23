import type { PlayVoiceOption } from "@/src/api/types";

export const DEFAULT_BUILTIN_VOICE_ID = "jessica";

export const FALLBACK_VOICES: PlayVoiceOption[] = [
  { id: "jessica", name: "Jessica", description: "Warm and conversational", source: "builtin", gender: "female", accent: "american" },
  { id: "lily", name: "Lily", description: "Soft British, easygoing", source: "builtin", gender: "female", accent: "british" },
  { id: "alice", name: "Alice", description: "Clear and engaging", source: "builtin", gender: "female", accent: "british" },
  { id: "matilda", name: "Matilda", description: "Calm and professional", source: "builtin", gender: "female", accent: "american" },
  { id: "laura", name: "Laura", description: "Gentle and even", source: "builtin", gender: "female", accent: "american" },
  { id: "aria", name: "Aria", description: "Expressive American", source: "builtin", gender: "female", accent: "american" },
  { id: "charlotte", name: "Charlotte", description: "Bright European", source: "builtin", gender: "female", accent: "swedish" },
  { id: "river", name: "River", description: "Relaxed and even", source: "builtin", gender: "neutral", accent: "american" },
  { id: "brian", name: "Brian", description: "Clear and professional", source: "builtin", gender: "male", accent: "american" },
  { id: "daniel", name: "Daniel", description: "Warm British", source: "builtin", gender: "male", accent: "british" },
  { id: "liam", name: "Liam", description: "Bright and energetic", source: "builtin", gender: "male", accent: "american" },
  { id: "will", name: "Will", description: "Casual American", source: "builtin", gender: "male", accent: "american" },
  { id: "george", name: "George", description: "Smooth and grounded", source: "builtin", gender: "male", accent: "british" },
  { id: "bill", name: "Bill", description: "Warm and steady", source: "builtin", gender: "male", accent: "american" },
  { id: "callum", name: "Callum", description: "Husky British", source: "builtin", gender: "male", accent: "british" },
  { id: "charlie", name: "Charlie", description: "Confident Australian", source: "builtin", gender: "male", accent: "australian" },
  { id: "chris", name: "Chris", description: "Easygoing American", source: "builtin", gender: "male", accent: "american" },
  { id: "eric", name: "Eric", description: "Smooth American", source: "builtin", gender: "male", accent: "american" },
  { id: "roger", name: "Roger", description: "Laid-back American", source: "builtin", gender: "male", accent: "american" },
];

export const FEATURED_VOICE_IDS = ["jessica", "lily", "brian", "daniel", "liam"] as const;

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

export function defaultBuiltinVoiceId(voices: PlayVoiceOption[] = FALLBACK_VOICES): string {
  if (voices.some((v) => v.id === DEFAULT_BUILTIN_VOICE_ID)) return DEFAULT_BUILTIN_VOICE_ID;
  const first = voices.find((v) => (v.source ?? "builtin") === "builtin");
  return first?.id || DEFAULT_BUILTIN_VOICE_ID;
}

export function isClonedVoice(voice: PlayVoiceOption): boolean {
  const source = voice.source ?? "builtin";
  return source === "cloned" || source === "custom";
}

/** Home / Faces caption. Bound name, or No voice so bind is obvious. */
export function faceVoiceCaption(
  face: { bound_voice_id?: string | null },
  voices: PlayVoiceOption[],
): string {
  const bound = (face.bound_voice_id || "").trim();
  if (bound) {
    const row = voices.find((v) => v.id === bound);
    if (row) return row.name;
    return "Voice";
  }
  return "No voice";
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
  return [...seen].sort((a, b) =>
    (voiceAccentLabel(a) || a).localeCompare(voiceAccentLabel(b) || b),
  );
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
    accentLabel.includes(q)
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
