/**
 * Phase 81 (D-15, RESEARCH §Open Question 1): zone constants for the
 * endgame-entry-eval bullet on the Endgames page.
 *
 * Values are pawn units, signed user-perspective. The neutral band ±0.75 is
 * benchmark-derived: pooled equal-footing population gives [p25, p75] ≈
 * [-53.8, +75.3] cp at endgame entry (reports/benchmarks-2026-05-04.md §3c),
 * so a symmetric ±0.75 pawn band rejects centered users without false-positive
 * coloring at typical effect sizes.
 *
 * Why a separate module from openingStatsZones.ts: the MG-entry baseline (±0.30
 * pawns there) is calibrated for the middlegame-entry distribution (per-game
 * SD ≈ 2.4 pawns); endgame entry has ≈4.4 pawn SD and a wider centered
 * population. Reusing the MG band would over-report green/red at small effects.
 */

import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

/** EG-entry: lower bound of the neutral zone in pawns (signed user-perspective). */
export const ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS = -0.75;

/** EG-entry: upper bound of the neutral zone in pawns. Symmetric around 0. */
export const ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS = 0.75;

/** EG-entry: bullet-chart half-domain in pawns (D-15). Values beyond clamp; CI whiskers go open-ended. */
export const ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS = 2.0;

/** Center of the bullet axis (Tile 1 H0 per D-07). */
export const ENDGAME_ENTRY_EVAL_CENTER = 0;

/**
 * Pick the zone color for the EG-entry-eval bullet relative to 0 cp.
 * Pure presentation — gating on confidence happens in the consumer
 * (matches Openings ExplorerTab pattern).
 */
export function endgameEntryEvalZoneColor(value: number): string {
  if (value >= ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS) return ZONE_SUCCESS;
  if (value <= ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS) return ZONE_DANGER;
  return ZONE_NEUTRAL;
}
