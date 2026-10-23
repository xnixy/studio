/** How much of the window the keyboard covers. Prefer screenY, not raw height. */
export function keyboardOverlap(
  endCoordinates: { screenY: number; height: number },
  windowHeight: number,
): number {
  const fromScreen = windowHeight - endCoordinates.screenY;
  if (Number.isFinite(fromScreen) && fromScreen > 0) return Math.round(fromScreen);
  const height = endCoordinates.height;
  return Number.isFinite(height) && height > 0 ? Math.round(height) : 0;
}
