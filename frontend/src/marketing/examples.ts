/**
 * Landing + Create showcase examples.
 * Must match backend Play contracts (play_video_helpers / house TTS):
 * - Talking (avatar): scene + wardrobe + `says:` spoken line
 *   (backend splits on `says:` so only the line is spoken).
 * - Scene: visual directions; quoted dialogue when people talk.
 * - Still (image): visual still only; no spoken lines.
 * - Face portraits: local /examples/avatars/*.jpg
 * - Product / talking clips: R2 https://storage.example.com/examples/<id>/
 */

export type ShowcaseMode = "image" | "video" | "avatar" | "lipsync";
export type ShowcasePlatform = "tiktok" | "reels" | "shorts" | "feed" | "custom";

const MEDIA_BASE = "https://storage.example.com/examples";
/** Bump when replacing example assets so browsers skip stale cache. */
const MEDIA_VER = "20260724a";

function media(id: string, file: string) {
  return `${MEDIA_BASE}/${id}/${file}?v=${MEDIA_VER}`;
}

/** Demo faces from public/examples/avatars. Never pair these with old stock clip.mp4. */
function avatarFace(id: string) {
  return `/examples/avatars/${id}.jpg?v=${MEDIA_VER}`;
}

export type ShowcaseExample = {
  id: string;
  mode: ShowcaseMode;
  platform: ShowcasePlatform;
  title: string;
  /** Short line under the title on the card. */
  caption: string;
  /** Full prompt loaded into the compose box. */
  prompt: string;
  /** CSS fallback if media fails to load. */
  scene: string;
  /** Accent chip color on the card. */
  accent: string;
  /** Optional scene label painted over the media. */
  mockLabel?: string;
  duration?: string;
  aspect: "9:16" | "1:1" | "16:9";
  /** Card still (prefer small thumb/frame). */
  posterUrl: string;
  /** Optional MP4 for hover autoplay. Never set on face-only avatar cards. */
  videoUrl?: string;
};

export const SHOWCASE_FILTERS: { id: "all" | ShowcaseMode; label: string }[] = [
  { id: "all", label: "All" },
  { id: "avatar", label: "Talking" },
  { id: "video", label: "Scene" },
  { id: "image", label: "Still" },
];

export const SHOWCASE_EXAMPLES: ShowcaseExample[] = [
  // --- Face portraits (square). Talking = scene + line. ---
  {
    id: "maya-serum",
    mode: "avatar",
    platform: "tiktok",
    title: "Maya · serum review",
    caption: "Talking · scene + line",
    prompt:
      "Bright bathroom mirror, soft morning light, white tank top. She holds a small glass bottle and says: stop scrolling if your vitamin C still peels. This one sinks in in ten seconds. Link in bio.",
    scene: "linear-gradient(160deg, #f0abfc 0%, #fb7185 35%, #1c0a14 100%)",
    accent: "#f9a8d4",
    aspect: "1:1",
    posterUrl: avatarFace("maya"),
  },
  {
    id: "jordan-ship",
    mode: "avatar",
    platform: "shorts",
    title: "Jordan · free shipping",
    caption: "Talking · scene + line",
    prompt:
      "Desk setup, soft window light, black hoodie, phone in hand. He looks at camera and says: free shipping this week only. Order before midnight and it ships today.",
    scene: "linear-gradient(165deg, #67e8f9 0%, #0369a1 40%, #082f49 100%)",
    accent: "#7dd3fc",
    aspect: "1:1",
    posterUrl: avatarFace("jordan"),
  },
  {
    id: "aiko-skincare",
    mode: "avatar",
    platform: "tiktok",
    title: "Aiko · morning tip",
    caption: "Talking · scene + line",
    prompt:
      "Clean bathroom counter, daylight, soft pink top. She pumps serum onto her fingers and says: cleanse, then one pump of this serum. Wait a minute before SPF.",
    scene: "linear-gradient(150deg, #fda4af 0%, #9f1239 45%, #1c0a14 100%)",
    accent: "#fda4af",
    aspect: "1:1",
    posterUrl: avatarFace("aiko"),
  },
  {
    id: "diego-unbox",
    mode: "avatar",
    platform: "reels",
    title: "Diego · unbox earbuds",
    caption: "Talking · scene + line",
    prompt:
      "Messy desk, matte black box in hand, casual tee. He opens the case and says: case is tiny, sound is clean, and they stay in when I run.",
    scene: "linear-gradient(180deg, #a78bfa 0%, #4c1d95 50%, #0b0614 100%)",
    accent: "#c4b5fd",
    aspect: "1:1",
    posterUrl: avatarFace("diego"),
  },
  {
    id: "priya-protein",
    mode: "avatar",
    platform: "tiktok",
    title: "Priya · protein bar",
    caption: "Talking · exact words",
    prompt:
      "I actually finish these protein bars. Not chalky, not too sweet, and they keep me full until lunch. Grab a box if you snack at three.",
    scene: "linear-gradient(150deg, #fde68a 0%, #f59e0b 40%, #431407 100%)",
    accent: "#fcd34d",
    aspect: "1:1",
    posterUrl: avatarFace("priya"),
  },

  // --- Real product / talking clips ---
  {
    id: "serum-ugc",
    mode: "avatar",
    platform: "tiktok",
    title: "Serum review hook",
    caption: "Talking · kitchen · 15s",
    prompt:
      "Kitchen island, soft daylight, black tee. She holds the serum bottle and says: if your vitamin C still peels, switch this. One pump, no sting, glass-skin by week two.",
    scene: "linear-gradient(160deg, #f0abfc 0%, #fb7185 35%, #1c0a14 100%)",
    accent: "#f9a8d4",
    mockLabel: "Stop scrolling if your skin…",
    duration: "15s",
    aspect: "9:16",
    posterUrl: media("serum-ugc", "thumb.jpg"),
    videoUrl: media("serum-ugc", "clip.mp4"),
  },
  {
    id: "sneaker-hero",
    mode: "image",
    platform: "feed",
    title: "Sneaker hero still",
    caption: "Product · wet concrete · 1:1",
    prompt:
      "Product still: white and black sneaker on wet concrete, dramatic side light, sharp focus on the shoe, shallow depth of field, 1:1 feed crop, no text, no watermark",
    scene: "linear-gradient(145deg, #94a3b8 0%, #334155 45%, #0f172a 100%)",
    accent: "#cbd5e1",
    mockLabel: "DROP 01",
    aspect: "1:1",
    posterUrl: media("sneaker-hero", "face-thumb.jpg"),
  },
  {
    id: "unbox-cut",
    mode: "video",
    platform: "reels",
    title: "Unboxing open",
    caption: "Hands · box · product cut",
    prompt:
      "Vertical 9:16 product video: hands open a matte black box under soft studio light, cut to clean product close-up, quick energetic pace, no talking, light paper-rustle sound only",
    scene: "linear-gradient(180deg, #a78bfa 0%, #4c1d95 50%, #0b0614 100%)",
    accent: "#c4b5fd",
    mockLabel: "Open it",
    duration: "12s",
    aspect: "9:16",
    posterUrl: media("unbox-cut", "frame.jpg"),
    videoUrl: media("unbox-cut", "clip.mp4"),
  },
  {
    id: "founder-ship",
    mode: "avatar",
    platform: "shorts",
    title: "Founder free shipping",
    caption: "Talking · office · scene",
    prompt:
      "Home office, soft window light, navy hoodie. He leans toward the camera and says: free shipping this week only. Order before midnight and it ships today.",
    scene: "linear-gradient(165deg, #67e8f9 0%, #0369a1 40%, #082f49 100%)",
    accent: "#7dd3fc",
    mockLabel: "Free shipping this week",
    duration: "15s",
    aspect: "9:16",
    posterUrl: media("founder-ship", "face-thumb.jpg"),
    videoUrl: media("founder-ship", "clip.mp4"),
  },
  {
    id: "protein-testimonial",
    mode: "avatar",
    platform: "tiktok",
    title: "Protein bar testimonial",
    caption: "Talking · exact words",
    prompt:
      "I actually finish these. Not chalky, not too sweet, and they keep me full until lunch. If you snack at three, grab a box.",
    scene: "linear-gradient(150deg, #fde68a 0%, #f59e0b 40%, #431407 100%)",
    accent: "#fcd34d",
    mockLabel: "I actually finish these",
    duration: "6s",
    aspect: "9:16",
    posterUrl: media("protein-testimonial", "face-thumb.jpg"),
    videoUrl: media("protein-testimonial", "clip.mp4"),
  },
  {
    id: "night-broll",
    mode: "video",
    platform: "reels",
    title: "Night city b-roll",
    caption: "Neon · slow push-in",
    prompt:
      "Vertical 9:16 night city b-roll: wet streets, neon reflections, slow push-in, cinematic grade, no people talking, ambient city hum only",
    scene: "linear-gradient(200deg, #22d3ee 0%, #7c3aed 40%, #020617 85%)",
    accent: "#67e8f9",
    mockLabel: "CITY · NIGHT",
    duration: "8s",
    aspect: "9:16",
    posterUrl: media("night-broll", "frame.jpg"),
    videoUrl: media("night-broll", "clip.mp4"),
  },
  {
    id: "desk-before-after",
    mode: "video",
    platform: "shorts",
    title: "Desk before / after",
    caption: "Quick cuts · energetic",
    prompt:
      "Vertical 9:16 desk makeover: messy desk then clean setup, fast cuts, bright daylight, no dialogue, soft whoosh transitions",
    scene: "linear-gradient(135deg, #86efac 0%, #15803d 45%, #052e16 100%)",
    accent: "#86efac",
    mockLabel: "BEFORE → AFTER",
    duration: "10s",
    aspect: "9:16",
    posterUrl: media("desk-before-after", "frame.jpg"),
    videoUrl: media("desk-before-after", "clip.mp4"),
  },
  {
    id: "kitchen-product",
    mode: "image",
    platform: "feed",
    title: "Morning product still",
    caption: "Counter · soft light",
    prompt:
      "Lifestyle product still on a kitchen counter, soft morning window light, light steam, clean packaging hero, 1:1 feed crop, no text",
    scene: "linear-gradient(170deg, #fdba74 0%, #ea580c 35%, #1c0a00 100%)",
    accent: "#fdba74",
    mockLabel: "AM RITUAL",
    aspect: "1:1",
    posterUrl: media("kitchen-product", "face-thumb.jpg"),
  },
  {
    id: "hook-stop",
    mode: "avatar",
    platform: "tiktok",
    title: "Stop-scrolling hook",
    caption: "Talking · punchy open",
    prompt: "Stop scrolling if you still do this with your skincare.",
    scene: "linear-gradient(155deg, #f472b6 0%, #db2777 40%, #1a0510 100%)",
    accent: "#f9a8d4",
    mockLabel: "Stop scrolling if…",
    duration: "6s",
    aspect: "9:16",
    posterUrl: media("hook-stop", "face-thumb.jpg"),
    videoUrl: media("hook-stop", "clip.mp4"),
  },
  {
    id: "headshot",
    mode: "image",
    platform: "custom",
    title: "Founder headshot",
    caption: "Studio · friendly",
    prompt:
      "Founder headshot portrait, clean soft gray studio backdrop, friendly smile, soft key light, sharp eyes, natural skin, no text",
    scene: "linear-gradient(180deg, #e9d5ff 0%, #6d28d9 50%, #1e1b4b 100%)",
    accent: "#d8b4fe",
    mockLabel: "PORTRAIT",
    aspect: "1:1",
    posterUrl: media("headshot", "face-thumb.jpg"),
  },
  {
    id: "bottle-spin",
    mode: "video",
    platform: "reels",
    title: "Bottle beauty spin",
    caption: "Product · glossy · slow orbit",
    prompt:
      "Vertical 9:16 product shot: glossy skincare bottle slow orbit on pure black, soft specular highlights, premium commercial, no people, quiet room tone",
    scene: "linear-gradient(160deg, #f5d0fe 0%, #86198f 40%, #0a0010 100%)",
    accent: "#e879f9",
    mockLabel: "GLOSS",
    duration: "6s",
    aspect: "9:16",
    posterUrl: media("bottle-spin", "frame.jpg"),
    videoUrl: media("bottle-spin", "clip.mp4"),
  },
  {
    id: "workout-energy",
    mode: "avatar",
    platform: "tiktok",
    title: "Gym energy UGC",
    caption: "Talking · gym · scene + line",
    prompt:
      "Gym floor, bright overhead lights, black tank top. He faces the camera and says: if your pre-workout still tastes like chalk, try this. Clean energy, no crash, and I actually look forward to the gym. Link below.",
    scene: "linear-gradient(150deg, #fbbf24 0%, #dc2626 40%, #1c0505 100%)",
    accent: "#fbbf24",
    mockLabel: "ENERGY CHECK",
    duration: "12s",
    aspect: "9:16",
    posterUrl: media("workout-energy", "face-thumb.jpg"),
    videoUrl: media("workout-energy", "clip.mp4"),
  },
];

export const MARQUEE_TAGS = [
  "TikTok hooks",
  "Reels b-roll",
  "Shorts openers",
  "Product stills",
  "Avatar faces",
  "Talking lines",
  "Feed 1:1",
  "Talking heads",
  "Unboxing cuts",
  "Night city",
  "Seedance · Grok stills",
];
