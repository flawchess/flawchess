/**
 * Types of GET /api/openings/out-of-opening-stats, mirroring app/schemas/opening_out.py
 * field for field (snake_case). Units: `rate` and the peer bands are fractions 0..1;
 * `percentile_favorable` is 0..100 where HIGHER IS BETTER FOR THE USER (the worse
 * rate is already inverted server-side).
 */

import type { RankStatus, TimeControlBucket } from '@/types/endgames';

export type OpeningOutSide = 'worse' | 'better';

/** One time control's rate for one colour (popover per-TC list). */
export interface OpeningOutTcOut {
  tc: TimeControlBucket;
  status: RankStatus;
  k: number;
  n: number;
  rate: number | null;
  floor_n: number;
  floor_required: number;
  /** Set only when status === 'ranked'. */
  percentile_favorable: number | null;
}

/** One colour x rate card row, collapsed over the time controls that qualify. */
export interface OpeningOutRateOut {
  status: RankStatus;
  k: number;
  n: number;
  rate: number | null;
  floor_n: number;
  floor_required: number;
  percentile_favorable: number | null;
  /** 95% Wilson bounds of the pooled rate (null unless ranked). */
  ci_low: number | null;
  ci_high: number | null;
  /** Two-sided Wilson score-test p of the pooled rate vs peer_p50 (null unless ranked). */
  p_value: number | null;
  /** Game-weighted peer band (null unless ranked). */
  peer_p25: number | null;
  peer_p50: number | null;
  peer_p75: number | null;
  /** The 95% CI excludes the peer median on the headline's side; red/green needs it. */
  significant: boolean;
  /** Every listed time control, fastest to slowest. */
  tcs: OpeningOutTcOut[];
}

export interface OpeningOutColorOut {
  worse: OpeningOutRateOut;
  better: OpeningOutRateOut;
}

export interface OutOfOpeningStatsResponse {
  white: OpeningOutColorOut;
  black: OpeningOutColorOut;
}
