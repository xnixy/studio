/**
 * Public demo faces for landing Create chat simulation.
 * Served from SPA: /examples/avatars/*.jpg (also mirrored on R2).
 *
 * scenePrompt matches Talking Play contract (scene + says: line),
 * except Priya which is a lip-sync style pure script seed.
 */
const VER = "20260724a";

export type DemoAvatar = {
  id: string;
  label: string;
  /** Short line under the face on the chip. */
  caption: string;
  /** Face still used in the chat face strip. */
  imageUrl: string;
  /** Prompt seed for Create demos. */
  scenePrompt: string;
};

/** Local public path so landing works without CDN and matches git assets. */
export function demoAvatarUrl(id: string) {
  return `/examples/avatars/${id}.jpg?v=${VER}`;
}

/** Diverse, natural-looking portraits for marketing. */
export const DEMO_AVATARS: DemoAvatar[] = [
  {
    id: "maya",
    label: "Maya",
    caption: "Blonde · natural",
    imageUrl: demoAvatarUrl("maya"),
    scenePrompt:
      "Bright bathroom mirror, soft morning light, white tank top. She holds a small glass bottle and says: stop scrolling if your vitamin C still peels. This one sinks in in ten seconds. Link in bio.",
  },
  {
    id: "jordan",
    label: "Jordan",
    caption: "Warm · casual",
    imageUrl: demoAvatarUrl("jordan"),
    scenePrompt:
      "Desk setup, soft window light, black hoodie, phone in hand. He looks at camera and says: free shipping this week only. Order before midnight and it ships today.",
  },
  {
    id: "aiko",
    label: "Aiko",
    caption: "Soft daylight",
    imageUrl: demoAvatarUrl("aiko"),
    scenePrompt:
      "Clean bathroom counter, daylight, soft pink top. She pumps serum onto her fingers and says: cleanse, then one pump of this serum. Wait a minute before SPF.",
  },
  {
    id: "diego",
    label: "Diego",
    caption: "Friendly · outdoor",
    imageUrl: demoAvatarUrl("diego"),
    scenePrompt:
      "Messy desk, matte black box in hand, casual tee. He opens the case and says: case is tiny, sound is clean, and they stay in when I run.",
  },
  {
    id: "priya",
    label: "Priya",
    caption: "Calm · studio",
    imageUrl: demoAvatarUrl("priya"),
    scenePrompt:
      "I actually finish these protein bars. Not chalky, not too sweet, and they keep me full until lunch. Grab a box if you snack at three.",
  },
];
