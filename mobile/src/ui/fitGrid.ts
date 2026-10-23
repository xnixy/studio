/** How many equal cells fit in a padded row. Width-driven, not phone vs iPad. */
export function fitGrid(
  innerWidth: number,
  opts: { pad: number; gap: number; minCell: number },
): { cols: number; cellW: number } {
  const usable = Math.max(0, innerWidth - opts.pad * 2);
  const cols = Math.max(2, Math.floor((usable + opts.gap) / (opts.minCell + opts.gap)));
  const cellW = Math.max(1, Math.floor((usable - opts.gap * (cols - 1)) / cols));
  return { cols, cellW };
}
