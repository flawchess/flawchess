/**
 * Bullet-chart zone bounds for the "Avg eval at MG entry" cell in
 * MostPlayedOpeningsTable (Phase 80, D-07).
 *
 * Calibrated from reports/benchmarks-2026-05-03.md §3 (n=1,731 users), verified
 * 2026-05-03. Cohen's d collapse verdicts: TC axis 0.17 -> collapse; ELO axis
 * 0.41 -> review. Single global zone per the SKILL methodology.
 *
 * Per-game CI at small N: per-game SD is much wider than the per-user-mean SD,
 * so the 95% CI whisker (~1.96 x SE) routinely spans much of the domain at
 * N=10 -- this is the desired UX signal "we don't have enough data to tell."
 *
 * Source citation: bench §3 lines 407-408 (pooled p25/p75 = -21.8/+22.0 cp;
 * p05/p95 = -112/+60 cp).
 */

/** MG: lower bound of the neutral zone (in pawns, signed user-perspective). */
export const EVAL_NEUTRAL_MIN_PAWNS = -0.20;

/** MG: upper bound of the neutral zone (in pawns). Symmetric (population mean ~0). */
export const EVAL_NEUTRAL_MAX_PAWNS = 0.20;

/** MG: bullet-chart half-domain (in pawns). Values beyond +-domain clamp; CI whiskers go open-ended. */
export const EVAL_BULLET_DOMAIN_PAWNS = 1.5;
