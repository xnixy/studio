import type { PlayMode, PlayPlatform } from "../api/types";

/**
 * Same R2 assets + copy as the marketing site
 * (frontend/src/marketing/examples.ts). Keep order and prompts in sync.
 *
 * Backend Play contracts:
 * - avatar (Talking): scene + wardrobe + `says:` line
 * - video (Scene): visual directions; quoted dialogue when people talk
 * - image: visual still directions
 */
const MEDIA_BASE = "https://storage.example.com/examples";
const MEDIA_VER = "20260724a";
const AVATAR_BASE = "https://storage.example.com/examples/avatars";

function media(id: string, file: string) {
  return `${MEDIA_BASE}/${id}/${file}?v=${MEDIA_VER}`;
}

function avatarFace(id: string) {
  return `${AVATAR_BASE}/${id}.jpg?v=${MEDIA_VER}`;
}

export type ShowcaseExample = {
  id: string;
  mode: PlayMode;
  platform: PlayPlatform;
  title: string;
  caption: string;
  /** Spoken line for Talking; visual directions for Scene / stills. */
  prompt: string;
  duration?: string;
  aspect: "9:16" | "1:1" | "16:9";
  posterUrl: string;
  videoUrl?: string;
  /** Face-only portrait card (no video). */
  isFace?: boolean;
};

/** Matches frontend SHOWCASE_EXAMPLES order and prompts. */
export const SHOWCASE_EXAMPLES: ShowcaseExample[] = [
  // --- Face portraits (square). Talking = scene+line. ---
  {
    id: "maya-serum",
    mode: "avatar",
    platform: "tiktok",
    title: "Maya · serum review",
    caption: "Talking · scene + line",
    prompt:
      "Bright bathroom mirror, soft morning light, white tank top. She holds a small glass bottle and says: stop scrolling if your vitamin C still peels. This one sinks in in ten seconds. Link in bio.",
    aspect: "1:1",
    posterUrl: avatarFace("maya"),
    isFace: true,
  },
  {
    id: "jordan-ship",
    mode: "avatar",
    platform: "shorts",
    title: "Jordan · free shipping",
    caption: "Talking · scene + line",
    prompt:
      "Desk setup, soft window light, black hoodie, phone in hand. He looks at camera and says: free shipping this week only. Order before midnight and it ships today.",
    aspect: "1:1",
    posterUrl: avatarFace("jordan"),
    isFace: true,
  },
  {
    id: "aiko-skincare",
    mode: "avatar",
    platform: "tiktok",
    title: "Aiko · morning tip",
    caption: "Talking · scene + line",
    prompt:
      "Clean bathroom counter, daylight, soft pink top. She pumps serum onto her fingers and says: cleanse, then one pump of this serum. Wait a minute before SPF.",
    aspect: "1:1",
    posterUrl: avatarFace("aiko"),
    isFace: true,
  },
  {
    id: "diego-unbox",
    mode: "avatar",
    platform: "reels",
    title: "Diego · unbox earbuds",
    caption: "Talking · scene + line",
    prompt:
      "Messy desk, matte black box in hand, casual tee. He opens the case and says: case is tiny, sound is clean, and they stay in when I run.",
    aspect: "1:1",
    posterUrl: avatarFace("diego"),
    isFace: true,
  },
  {
    id: "priya-protein",
    mode: "avatar",
    platform: "tiktok",
    title: "Priya · protein bar",
    caption: "Talking · exact words",
    prompt:
      "I actually finish these protein bars. Not chalky, not too sweet, and they keep me full until lunch. Grab a box if you snack at three.",
    aspect: "1:1",
    posterUrl: avatarFace("priya"),
    isFace: true,
  },

  // --- Real product / talking clips (same set + order as web marketing) ---
  {
    id: "serum-ugc",
    mode: "avatar",
    platform: "tiktok",
    title: "Serum review hook",
    caption: "Talking · kitchen · 8s",
    prompt:
      "Kitchen island, soft daylight, black tee. She holds the serum bottle and says: if your vitamin C still peels, switch this. One pump, no sting, glass-skin by week two.",
    duration: "8s",
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
    duration: "6s",
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
    duration: "11s",
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
    duration: "6s",
    aspect: "9:16",
    posterUrl: media("hook-stop", "face-thumb.jpg"),
    videoUrl: media("hook-stop", "clip.mp4"),
  },
  {
    id: "headshot",
    mode: "image",
    // feed = 1:1 on the backend; "custom" renders 9:16 and breaks the square card.
    platform: "feed",
    title: "Founder headshot",
    caption: "Studio · friendly",
    prompt:
      "Founder headshot portrait, clean soft gray studio backdrop, friendly smile, soft key light, sharp eyes, natural skin, no text",
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
    duration: "12s",
    aspect: "9:16",
    posterUrl: media("workout-energy", "face-thumb.jpg"),
    videoUrl: media("workout-energy", "clip.mp4"),
  },
];

/** Face-only cards (Maya, Jordan, Aiko, Diego, Priya). */
export const LANDING_FACES = SHOWCASE_EXAMPLES.filter((e) => e.isFace);

/** Short starters for Home (face examples with poster). Prompt only. */
export const STARTER_EXAMPLES = LANDING_FACES.map(
  ({ id, mode, platform, title, caption, prompt, posterUrl }) => ({
    id,
    mode,
    platform,
    title,
    caption,
    prompt,
    posterUrl,
  }),
);
