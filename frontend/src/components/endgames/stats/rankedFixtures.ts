/**
 * Test fixtures for the ranked-sample payload (GET /api/endgames/ranked-stats).
 * Only test files import this module.
 */

import type {
  CdfMetricId,
  EndgameRankedStatsResponse,
  EndgameWDLSummary,
  RankedMetricOut,
  RankedTcStats,
  RatingAnchorOut,
  TimeControlBucket,
} from '@/types/endgames';

export const ALL_METRIC_IDS: readonly CdfMetricId[] = [
  'score_gap',
  'achievable_score_gap',
  'score_gap_conv',
  'score_gap_parity',
  'recovery_score_gap',
  'time_pressure_score_gap',
  'clock_gap',
  'net_flag_rate',
  'conversion_rate',
  'parity_rate',
  'recovery_rate',
];

/** A ranked metric with a value, 120 games and a mid-table percentile. */
export function buildMetric(
  metric: CdfMetricId,
  overrides: Partial<RankedMetricOut> = {},
): RankedMetricOut {
  return {
    metric,
    value: 0.05,
    n: 120,
    floor_n: 120,
    floor_required: 30,
    percentile: 46,
    status: 'ranked',
    ci_low: 0.01,
    ci_high: 0.09,
    p_value: 0.032,
    ...overrides,
  };
}

export function buildWdl(wins: number, draws: number, losses: number): EndgameWDLSummary {
  const total = wins + draws + losses;
  const safe = total === 0 ? 1 : total;
  return {
    wins,
    draws,
    losses,
    total,
    win_pct: (wins / safe) * 100,
    draw_pct: (draws / safe) * 100,
    loss_pct: (losses / safe) * 100,
  };
}

export const MIXED_ANCHOR: RatingAnchorOut = {
  anchor_rating: 1788,
  n_chesscom_games: 657,
  n_lichess_games: 741,
  chesscom_median_native: 1466,
  lichess_median_native: 1765,
};

/** One TC of the ranked payload with all 11 metrics ranked; overrides patch any field. */
export function buildRankedTc(
  tc: TimeControlBucket,
  overrides: Partial<RankedTcStats> = {},
  metricOverrides: Partial<Record<CdfMetricId, Partial<RankedMetricOut>>> = {},
): RankedTcStats {
  const metrics = Object.fromEntries(
    ALL_METRIC_IDS.map((id) => [id, buildMetric(id, metricOverrides[id])]),
  ) as Record<CdfMetricId, RankedMetricOut>;
  return {
    tc,
    ranked_games: 300,
    anchor_games: 300,
    anchor_min_games: 30,
    anchor: MIXED_ANCHOR,
    eval_pending_games: 0,
    metrics,
    overall: {
      endgame_wdl: buildWdl(45, 9, 46),
      non_endgame_wdl: buildWdl(57, 4, 39),
      entry_flow: {
        entry_eval_mean_pawns: 0.31,
        entry_eval_n: 100,
        expected_score: 0.53,
        actual_score: 0.487,
        n: 100,
      },
    },
    buckets: [],
    time_pressure: { quintiles: [] },
    score_gap_timeline: [],
    score_gap_timeline_window: 100,
    clock_diff_timeline: [],
    elo_timeline: [],
    elo_timeline_window: 100,
    type_categories: [],
    ...overrides,
  };
}

export function buildRankedResponse(tcs: RankedTcStats[]): EndgameRankedStatsResponse {
  return { tcs };
}
