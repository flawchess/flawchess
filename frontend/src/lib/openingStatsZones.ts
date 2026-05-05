/**
 * Bullet-chart zone bounds for the "Avg eval at MG entry" cell in
 * MostPlayedOpeningsTable (Phase 80, D-07).
 *
 * Calibrated from reports/benchmarks-2026-05-04-section-3.md (per-(user, color)
 * centered, n=3,496 user-color pairs >=20 games each). Pooled centered
 * [p25, p75] = [-26.8, +27.9] cp -> symmetric +-0.30 pawns. White vs black
 * Cohen's d = 0.013 confirms color collapse: one symmetric zone applies
 * around 0 cp.
 *
 * Per-game CI at small N: per-game SD is much wider than the per-user-mean SD,
 * so the 95% CI whisker (~1.96 x SE) routinely spans much of the domain at
 * N=20, this is the desired UX signal "we don't have enough data to tell."
 *
 * Zones are anchored on 0 cp (engine-balanced) for every cell, regardless of
 * color. The per-color engine asymmetry (symmetric ±0.25 pawns, white's
 * first-move tempo, recalibrated from the 2026-05-04 v3 deduped benchmark)
 * is rendered as a small reference tick on the bullet chart, not as the
 * chart's center or the test H0 (260504-rvh).
 */

import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

/** MG: lower bound of the neutral zone in pawns (signed user-perspective, around 0 cp). */
export const EVAL_NEUTRAL_MIN_PAWNS = -0.30;

/** MG: upper bound of the neutral zone in pawns. Symmetric around 0. */
export const EVAL_NEUTRAL_MAX_PAWNS = 0.30;

/** MG: bullet-chart half-domain (in pawns). Values beyond +-domain clamp; CI whiskers go open-ended. */
export const EVAL_BULLET_DOMAIN_PAWNS = 1.5;

/** Engine-asymmetry tick position for white-color cells. Symmetric around 0
 * cp from the 2026-05-04 v3 deduped benchmark (white first-move tempo
 * baseline +25.18 cp, rounded to ±0.25 pawns). Used as the bullet-chart
 * tick fallback for sections without a per-API baseline (e.g. bookmark
 * sections). */
export const EVAL_BASELINE_PAWNS_WHITE = 0.25;

/** Engine-asymmetry tick position for black-color cells (mirror of white). */
export const EVAL_BASELINE_PAWNS_BLACK = -0.25;

/** Pick the zone color for the MG-entry eval bullet relative to 0 cp.
 *
 * Anchored on 0 cp (engine-balanced) for every cell regardless of color.
 * Mirrors the absolute-bound logic in MiniBulletChart's fill-color test.
 */
export function evalZoneColor(value: number): string {
  if (value >= EVAL_NEUTRAL_MAX_PAWNS) return ZONE_SUCCESS;
  if (value <= EVAL_NEUTRAL_MIN_PAWNS) return ZONE_DANGER;
  return ZONE_NEUTRAL;
}
