/**
 * Demo faces for landing Create preview (matches web marketing/demoAvatars).
 * scenePrompt follows Talking contract: scene + `says:` line
 * (same as SHOWCASE face examples / backend split_avatar_user_prompt).
 */
import type { ImageSource } from "expo-image";

export type DemoAvatar = {
  id: string;
  label: string;
  caption: string;
  /** Local require() source for expo-image */
  image: ImageSource;
  /** Remote CDN (optional) */
  remoteUrl: string;
  scenePrompt: string;
};

const CDN = "https://storage.example.com/examples/avatars";
const VER = "20260724a";

export const DEMO_AVATARS: DemoAvatar[] = [
  {
    id: "maya",
    label: "Maya",
    caption: "Blonde · natural",
    image: require("../../assets/images/avatars/maya.jpg"),
    remoteUrl: `${CDN}/maya.jpg?v=${VER}`,
    scenePrompt:
      "Bright bathroom mirror, soft morning light, white tank top. She holds a small glass bottle and says: stop scrolling if your vitamin C still peels. This one sinks in in ten seconds. Link in bio.",
  },
  {
    id: "jordan",
    label: "Jordan",
    caption: "Warm · casual",
    image: require("../../assets/images/avatars/jordan.jpg"),
    remoteUrl: `${CDN}/jordan.jpg?v=${VER}`,
    scenePrompt:
      "Desk setup, soft window light, black hoodie, phone in hand. He looks at camera and says: free shipping this week only. Order before midnight and it ships today.",
  },
  {
    id: "aiko",
    label: "Aiko",
    caption: "Soft daylight",
    image: require("../../assets/images/avatars/aiko.jpg"),
    remoteUrl: `${CDN}/aiko.jpg?v=${VER}`,
    scenePrompt:
      "Clean bathroom counter, daylight, soft pink top. She pumps serum onto her fingers and says: cleanse, then one pump of this serum. Wait a minute before SPF.",
  },
  {
    id: "diego",
    label: "Diego",
    caption: "Friendly · outdoor",
    image: require("../../assets/images/avatars/diego.jpg"),
    remoteUrl: `${CDN}/diego.jpg?v=${VER}`,
    scenePrompt:
      "Messy desk, matte black box in hand, casual tee. He opens the case and says: case is tiny, sound is clean, and they stay in when I run.",
  },
  {
    id: "priya",
    label: "Priya",
    caption: "Calm · studio",
    image: require("../../assets/images/avatars/priya.jpg"),
    remoteUrl: `${CDN}/priya.jpg?v=${VER}`,
    // Lip-sync style seed (exact words only) when users copy this line into Lip-sync mode.
    scenePrompt:
      "I actually finish these protein bars. Not chalky, not too sweet, and they keep me full until lunch. Grab a box if you snack at three.",
  },
];
