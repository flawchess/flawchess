/**
 * Zone constants for the endgame-entry-eval bullet on the Endgames page.
 *
 * Values are pawn units, signed user-perspective. The neutral band is ±0.75
 * pawns, derived from the pooled benchmark IQR `max(|p25|, |p75|) = 75 cp`
 * (reports/benchmarks-2026-05-10.md §3, line 281). Aligned with the backend
 * ZoneSpec (app/services/endgame_zones.py::ZONE_REGISTRY["entry_eval_pawns"])
 * and the LLM narration threshold.
 *
 * History: Phase 82 D-09 had editorially tightened the band to ±0.50 to
 * narrate half-pawn swings; reverted to the benchmark-recommended ±0.75 so
 * the green/red zones track the actual cohort distribution.
 *
 * Why a separate module from openingStatsZones.ts: the MG-entry baseline (±0.30
 * pawns there) is calibrated for the middlegame-entry distribution (per-game
 * SD ≈ 2.4 pawns); endgame entry has ≈4.4 pawn SD and a wider centered
 * population. Reusing the MG band would over-report green/red at small effects.
 */

import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

/** EG-entry: lower bound of the neutral zone in pawns (signed user-perspective).
 * Pooled benchmark IQR ≈ [-0.56, +0.75]; symmetric `max(|p25|, |p75|) = 0.75`. */
export const ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS = -0.75;

/** EG-entry: upper bound of the neutral zone in pawns. Symmetric around 0. */
export const ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS = 0.75;

/** EG-entry: bullet-chart half-domain in pawns. Sized so the neutral band
 * (width 1.5 pawns) fills 20% of the axis, matching the visual proportion of
 * the Achievable-score neutral band (0.45–0.55 inside the 0.25–0.75 axis).
 * Wider than the cohort p05/p95 range (±1.99 pawns) — values cluster near
 * center by design; CI whiskers past ±domain render open-ended. */
export const ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS = 3.75;

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
