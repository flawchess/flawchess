/**
 * Phase 94.4 Plan 07 — rating-anchor types shared by chip call sites.
 *
 * 260529-l1i: the `pickDominantTcAnchor` helper was deleted. Aggregated
 * page-level ΔES chips no longer display a single dominant-TC anchor; the
 * per-TC anchors now live inline on each row of the chip tooltip's per-TC
 * breakdown ("anchored at ~X Lichess Elo"), threaded from the backend
 * `PerTcBreakdownOut.anchor` field.
 *
 * Per-TC chips (`time-pressure-score-gap`, `clock-gap`, `net-flag-rate`) still
 * pass their own TC's anchor directly via `RatingAnchorsByTc` (threaded through
 * EndgameTimePressureSection).
 */

import type { RatingAnchorOut } from '@/types/endgames';

export type TimeControlBucket = 'bullet' | 'blitz' | 'rapid' | 'classical';

export type RatingAnchorsByTc = Partial<Record<TimeControlBucket, RatingAnchorOut>>;
