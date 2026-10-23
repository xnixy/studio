/** Create page chrome constants (modes, formats). */
import type { ReactNode } from "react";
import { Image as ImageIcon, Video } from "lucide-react";
import type { PlayMode, PlayPlatform } from "../types";

export type ComposerTab = "clip" | "still";

/** Primary Create tabs. Kind (talking / scene) is confirmed on the draft card. */
export const COMPOSER_TABS: { id: ComposerTab; label: string; blurb: string; icon: ReactNode }[] = [
  {
    id: "clip",
    label: "Clip",
    blurb: "A short video. We confirm the kind before you spend.",
    icon: <Video size={14} aria-hidden />,
  },
  {
    id: "still",
    label: "Still",
    blurb: "One image",
    icon: <ImageIcon size={14} aria-hidden />,
  },
];

/** @deprecated Use COMPOSER_TABS. Kept so older imports fail loudly if they expect four modes. */
export const CLIP_TYPES = COMPOSER_TABS;

export function composerTabForMode(mode: PlayMode): ComposerTab {
  return mode === "image" ? "still" : "clip";
}

export function modeForComposerTab(tab: ComposerTab, current: PlayMode): PlayMode {
  if (tab === "still") return "image";
  if (current === "image") return "avatar";
  return current;
}

/**
 * Short helper under Create tabs.
 * Mirrors mobile createConstants.ts MODE_HINT. Change both together.
 */
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

/** Human kind name for Library and ready clips. Create user bubbles use composerTabLabel. */
export function modeLabel(mode: PlayMode): string {
  if (mode === "avatar" || mode === "lipsync") return "Talking";
  if (mode === "image") return "Still";
  return "Scene";
}

export function composerTabLabel(mode: PlayMode): string {
  return mode === "image" ? "Still" : "Clip";
}

/**
 * Noun for mid-sentence use ("Making a clip for vertical").
 */
export function clipNoun(mode: PlayMode): string {
  if (mode === "image") return "still";
  return "clip";
}

/** Every Create send talks the clip through first. Kind chips are the override. */
export function modeUsesAssist(_mode?: PlayMode): boolean {
  return true;
}

export const FORMATS: { id: PlayPlatform; label: string; aspect: string }[] = [
  { id: "tiktok", label: "Vertical", aspect: "9:16" },
  { id: "feed", label: "Square", aspect: "1:1" },
];

/** Talking / Scene / Still from a generation row. Mirrors mobile. */
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
 * Create-thread clip card width. Vertical stays phone-narrow so a 9:16 clip is
 * not letterboxed inside a wide bubble. Mirror: createConstants.threadClipCardWidth.
 */
export function threadClipCardClass(platform: string | null | undefined): string {
  return isSquarePlatform(platform) ? "w-[min(18.75rem,78%)]" : "w-[min(14.25rem,58%)]";
}
