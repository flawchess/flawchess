/**
 * Zone constants for the endgame-entry-eval bullet on the Endgames page.
 *
 * Values are pawn units, signed user-perspective. The neutral band is ±0.60
 * pawns, editorially tightened inside the IQR so the 0-centered EG-entry tile
 * actually paints green/red (live ±0.75 painted neutral for ~70% of users).
 * Aligned with the backend ZoneSpec
 * (app/services/endgame_zones.py::ZONE_REGISTRY["entry_eval_pawns"])
 * per reports/benchmarks-diff-2026-05-17-vs-2026-05-19.md item A.
 *
 * History: Phase 82 D-09 had editorially tightened the band to ±0.50 to
 * narrate half-pawn swings; reverted to benchmark-recommended ±0.75; then
 * re-tightened to ±0.60 per diff item A (game-time bucketing pass).
 *
 * Why a separate module from openingStatsZones.ts: the MG-entry baseline (±0.30
 * pawns there) is calibrated for the middlegame-entry distribution (per-game
 * SD ≈ 2.4 pawns); endgame entry has ≈4.4 pawn SD and a wider centered
 * population. Reusing the MG band would over-report green/red at small effects.
 */

import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

/** EG-entry: lower bound of the neutral zone in pawns (signed user-perspective).
 * Editorially tightened to ±0.60 per diff item A (2026-05-17 vs 2026-05-19).
 * Must match ZONE_REGISTRY["entry_eval_pawns"].typical_lower in endgame_zones.py. */
export const ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS = -0.60;

/** EG-entry: upper bound of the neutral zone in pawns. Symmetric around 0.
 * Must match ZONE_REGISTRY["entry_eval_pawns"].typical_upper in endgame_zones.py. */
export const ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS = 0.60;

/** EG-entry: bullet-chart half-domain in pawns. Sized so the neutral band
 * (width 1.5 pawns) fills ≈1/3 of the axis (1.5 / 4.5), matching the visual
 * proportion of the Achievable- and Endgame-score bullets on the same page.
 * Slightly wider than the cohort p05/p95 range (±1.99 pawns); CI whiskers
 * past ±domain render open-ended. */
export const ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS = 2.25;

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
