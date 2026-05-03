/**
 * Bullet-chart zone bounds for "Avg eval at phase entry" cells in
 * MostPlayedOpeningsTable. Two parallel pillars (Phase 80):
 *   - MG-entry (D-07): middlegame-entry eval column.
 *   - EG-entry (D-09): endgame-entry eval column.
 *
 * Calibrated from reports/benchmarks-2026-05-03.md §3 (n=1,731 users for MG,
 * n=1,773 for EG), verified 2026-05-03. Cohen's d collapse verdicts:
 *   - MG TC axis: 0.17 -> collapse; ELO axis: 0.41 -> review (single zone fine).
 *   - EG TC axis: 0.21 -> review; ELO axis: 0.35 -> review (single zone defensible).
 * Both phases collapse to a single global zone per the SKILL methodology
 * (default to single zone unless a UI argument warrants splitting).
 *
 * Per-game CI at small N: per-game SD is much wider than the per-user-mean SD,
 * so the 95% CI whisker (~1.96 x SE) routinely spans much of the domain at
 * N=10 -- this is the desired UX signal "we don't have enough data to tell."
 *
 * Source citations:
 *   - MG: bench §3 lines 407-408 (pooled p25/p75 = -21.8/+22.0 cp; p05/p95 = -112/+60 cp).
 *   - EG: bench §3 lines 462-466 (pooled p25/p75 = -31.0/+41.0 cp; p05/p95 = -338/+239 cp).
 */

// ============================================================================
// MG-entry pillar (D-07) -- middlegame-entry eval column
// ============================================================================

/** MG: lower bound of the neutral zone (in pawns, signed user-perspective). */
export const EVAL_NEUTRAL_MIN_PAWNS = -0.20;

/** MG: upper bound of the neutral zone (in pawns). Symmetric (population mean ~0). */
export const EVAL_NEUTRAL_MAX_PAWNS = 0.20;

/** MG: bullet-chart half-domain (in pawns). Values beyond +-domain clamp; CI whiskers go open-ended. */
export const EVAL_BULLET_DOMAIN_PAWNS = 1.5;

// ============================================================================
// EG-entry pillar (D-09) -- endgame-entry eval column
// ============================================================================

/** EG: lower bound of the neutral zone (in pawns). Wider than MG -- endgame entries are higher-variance. */
export const EVAL_ENDGAME_NEUTRAL_MIN_PAWNS = -0.35;

/** EG: upper bound of the neutral zone (in pawns). Symmetric. */
export const EVAL_ENDGAME_NEUTRAL_MAX_PAWNS = 0.35;

/** EG: bullet-chart half-domain (in pawns). Wider than MG to cover the endgame's longer tails. */
export const EVAL_ENDGAME_BULLET_DOMAIN_PAWNS = 3.5;
