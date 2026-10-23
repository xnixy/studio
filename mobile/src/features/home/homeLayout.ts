import { Platform } from "react-native";
import { isSquarePlatform, threadClipCardWidth } from "@/src/features/create/createConstants";

/** Compact floating compose dock. Phone and iPad. */
export const HOME_TRAY_MAX = 520;
export const HOME_TRAY_GUTTER = 12;

const RECENTS_GAP = 8;
const RECENTS_MIN_THUMB = 76;
const RECENTS_MAX_THUMB = 96;

/** iPhone landscape is wide; do not treat it as iPad. */
export function homeIsRegular(width: number): boolean {
  if (Platform.OS === "ios") return Boolean(Platform.isPad);
  return width >= 768;
}

/** Width inside Screen after iPad safe-area insets. */
export function homeInnerWidth(windowWidth: number, insetLeft: number, insetRight: number): number {
  const padL = insetLeft > 0 ? insetLeft : 0;
  const padR = insetRight > 0 ? insetRight : 0;
  return Math.max(0, windowWidth - padL - padR);
}

/**
 * Featured Home clip. Phone uses the thread card. iPad grows so it is not a
 * postage stamp, with a cap so landscape still has room for recents.
 */
export function homeHeroCardWidth(
  innerWidth: number,
  platform: string | null | undefined,
): number {
  if (!homeIsRegular(innerWidth)) {
    return threadClipCardWidth(innerWidth, platform);
  }
  if (isSquarePlatform(platform)) {
    return Math.min(380, Math.round(innerWidth * 0.42));
  }
  return Math.min(320, Math.round(innerWidth * 0.32));
}

export function homePagePad(innerWidth: number): number {
  return homeIsRegular(innerWidth) ? 24 : 16;
}

export type HomeRecentsLayout = {
  pad: number;
  gap: number;
  count: number;
  thumbW: number;
  thumbH: number;
};

/**
 * One row of recents. Count and thumb size come from the width on screen,
 * so a large iPhone shows 4 and iPad shows as many as fit.
 */
export function homeRecentsLayout(innerWidth: number): HomeRecentsLayout {
  const pad = homePagePad(innerWidth);
  const minThumb = homeIsRegular(innerWidth) ? 96 : RECENTS_MIN_THUMB;
  const maxThumb = homeIsRegular(innerWidth) ? 120 : RECENTS_MAX_THUMB;
  const usable = Math.max(minThumb, innerWidth - pad * 2);
  const count = Math.max(2, Math.floor((usable + RECENTS_GAP) / (minThumb + RECENTS_GAP)));
  const thumbW = Math.min(
    maxThumb,
    Math.max(minThumb, Math.floor((usable - RECENTS_GAP * (count - 1)) / count)),
  );
  return {
    pad,
    gap: RECENTS_GAP,
    count,
    thumbW,
    thumbH: Math.round((thumbW * 16) / 9),
  };
}
