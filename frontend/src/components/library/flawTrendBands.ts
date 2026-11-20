/** 257 D-17: the two stacked bands of the Flaws Timeline's Blunders area. */
import type { FlawTrendPoint } from '@/types/library';

/**
 * A trend point plus the two stacked bands of the Blunders area (257 D-17). The bands are
 * undefined where the window has too few scored blunders (facepalm_rate null, D-18), which
 * leaves a gap in the area while the Blunders line stays.
 */
interface ChartPoint extends FlawTrendPoint {
  facepalm_band?: number;
  other_band?: number;
}

export function toChartPoint(point: FlawTrendPoint): ChartPoint {
  // `== null`: a backend without the facepalm fields (mid-deploy) sends undefined, which a
  // strict null check let through and turned other_band into NaN (PR #495 review).
  if (point.facepalm_rate == null) return point;
  return {
    ...point,
    facepalm_band: point.facepalm_rate,
    // Floored at 0: the Blunders line reads the games-table counts, the band game_flaws; they
    // agree on 99.9% of games, so the band can rarely poke above the line by a hair.
    other_band: Math.max(0, point.blunder_rate - point.facepalm_rate),
  };
}
