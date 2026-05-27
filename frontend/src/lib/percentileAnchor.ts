/**
 * Phase 94.4 Plan 07 — rating-anchor helpers shared by chip call sites.
 *
 * Page-level ΔES chips (Endgame Score Gap, Achievable Score Gap, Parity ΔES,
 * Conversion ΔES, Recovery ΔES) are aggregated across the user's played TCs.
 * Per the plan's <action> Step 2 + CONTEXT 'Claude's Discretion' line 104, the
 * simplest honest disclosure is to display the dominant TC's anchor inline
 * (where "dominant" = the TC with the most games among the user's anchors)
 * and let bullet 1's "aggregated across the time controls you play" framing
 * cover the multi-TC honesty. The full per-TC anchor breakdown is deferred
 * to a v1.1 tooltip per Plan 05c W4.
 *
 * Per-TC chips (`time-pressure-score-gap`, `clock-gap`, `net-flag-rate`) DO
 * NOT use this helper — they pass their own TC's anchor directly.
 */

import type { RatingAnchorOut } from '@/types/endgames';

export type TimeControlBucket = 'bullet' | 'blitz' | 'rapid' | 'classical';

export type RatingAnchorsByTc = Partial<Record<TimeControlBucket, RatingAnchorOut>>;

/**
 * Return the anchor for the TC with the highest game count among the user's
 * available anchors. Returns `undefined` when no anchors are available
 * (Stage A hasn't run, or every TC is below the inclusion floor) — caller
 * MUST suppress the chip in that case.
 *
 * D-12 Reversal Amendment (2026-05-27): dominance computed via total game count
 * `n_chesscom_games + n_lichess_games` (the old `n_games` field is gone).
 *
 * Ties are broken deterministically by TC priority order
 * (bullet → blitz → rapid → classical), matching the volume-weighted
 * ordering most players follow.
 */
export function pickDominantTcAnchor(
  anchors: RatingAnchorsByTc,
): RatingAnchorOut | undefined {
  const tcOrder: ReadonlyArray<TimeControlBucket> = ['bullet', 'blitz', 'rapid', 'classical'];
  let best: RatingAnchorOut | undefined = undefined;
  for (const tc of tcOrder) {
    const candidate = anchors[tc];
    if (candidate === undefined) continue;
    const candidateTotal = candidate.n_chesscom_games + candidate.n_lichess_games;
    const bestTotal = best !== undefined ? best.n_chesscom_games + best.n_lichess_games : -1;
    if (best === undefined || candidateTotal > bestTotal) {
      best = candidate;
    }
  }
  return best;
}
