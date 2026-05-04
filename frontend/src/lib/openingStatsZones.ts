/**
 * Bullet-chart zone bounds for the "Avg eval at MG entry" cell in
 * MostPlayedOpeningsTable (Phase 80, D-07).
 *
 * Calibrated from reports/benchmarks-2026-05-04-section-3.md (per-(user, color)
 * centered, n=3,496 user-color pairs ≥20 games each). Pooled centered
 * [p25, p75] = [-26.8, +27.9] cp -> symmetric ±0.30 pawns. White vs black
 * Cohen's d = 0.013 confirms color collapse: one symmetric zone applies after
 * baseline subtraction.
 *
 * Per-game CI at small N: per-game SD is much wider than the per-user-mean SD,
 * so the 95% CI whisker (~1.96 x SE) routinely spans much of the domain at
 * N=20 -- this is the desired UX signal "we don't have enough data to tell."
 *
 * Zone helper: evalZoneColor(value, center) compares value against the active
 * baseline (per-color) so the visual matches the backend z-test reference.
 */

import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

/** MG: lower bound of the neutral zone (in pawns, signed user-perspective, relative to center). */
export const EVAL_NEUTRAL_MIN_PAWNS = -0.30;

/** MG: upper bound of the neutral zone (in pawns, relative to center). Symmetric. */
export const EVAL_NEUTRAL_MAX_PAWNS = 0.30;

/** MG: bullet-chart half-domain (in pawns). Values beyond +-domain clamp; CI whiskers go open-ended. */
export const EVAL_BULLET_DOMAIN_PAWNS = 1.5;

/** Engine-asymmetry baseline for white-color cells in pawns (per-game mean,
 * 2026-05-04 Lichess benchmark). Used as the chart center fallback for
 * bookmark sections where no per-API baseline is available. */
export const EVAL_BASELINE_PAWNS_WHITE = 0.315;

/** Engine-asymmetry baseline for black-color cells in pawns. */
export const EVAL_BASELINE_PAWNS_BLACK = -0.189;

/** Pick the zone color for the MG-entry eval bullet relative to the active center.
 *
 * Uses delta = value - center so the same neutral-band thresholds apply across
 * white-color and black-color tables (each with its own baseline). Mirrors the
 * absolute-bound logic in MiniBulletChart's fill-color test.
 */
export function evalZoneColor(value: number, center: number): string {
  const delta = value - center;
  if (delta >= EVAL_NEUTRAL_MAX_PAWNS) return ZONE_SUCCESS;
  if (delta <= EVAL_NEUTRAL_MIN_PAWNS) return ZONE_DANGER;
  return ZONE_NEUTRAL;
}

/** Build the per-row tooltip text for the MG-entry eval column.
 *
 * The chart is centered on the active engine baseline for the user's color,
 * so the bullet visual matches the per-row z-test reference. Built per-call
 * because the active baseline varies by color (white +0.32, black -0.19) and
 * the tooltip surfaces it numerically. No em-dashes per CLAUDE.md user-facing
 * copy rule.
 */
export function buildMgEvalHeaderTooltip(evalBaselinePawns: number): string {
  const sign = evalBaselinePawns >= 0 ? '+' : '';
  return (
    "The chart is centered on the engine baseline for your color. " +
    "According to the FlawChess benchmark, the mean evaluation when transitioning from the opening to the middlegame " +
    "is +0.32 pawns for white and -0.19 pawns for black. " +
    "Position relative to the center reflects performance vs that baseline; the displayed number is the raw evaluation. " +
    `Active baseline: ${sign}${evalBaselinePawns.toFixed(2)} pawns.`
  );
}
