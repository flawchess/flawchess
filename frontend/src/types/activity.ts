/**
 * Mirrors the `Payload` TypedDict in `app/services/activity_queries.py` — the
 * full Activity Pulse dataset served by `GET /api/admin/activity/stats`.
 *
 * Row arrays are heterogeneous (a mix of dates, counts, and labels per row,
 * matching the raw SQL result shape), so they type as tuples of
 * `string | number | null` rather than a named interface per row — the same
 * shape pages/activity/render.js destructures positionally.
 */

/**
 * The four presets the global time-range filter offers. Mirrors
 * `app.services.activity_queries.RangeKey`. These are the only preset keys:
 * an explicit start/end pair is not a fifth preset; it is reported back as
 * `ActivitySelectedRange`'s extra "custom" value.
 */
export type ActivityRangeKey = 'all' | 'd90' | 'd30' | 'd7';

/**
 * What the payload's `range` field reports back: the four presets, plus
 * "custom" when the caller supplied an explicit start/end pair instead of a
 * preset key. Mirrors `app.services.activity_queries.SelectedRange`.
 */
export type ActivitySelectedRange = ActivityRangeKey | 'custom';

export interface ActivityStatsPayload {
  generated_at: string;
  promoted_since: string;
  range: ActivitySelectedRange;
  data_start: string;
  days: string[];
  window_start_index: number;
  last_complete_index: number;
  activity: number[][];
  signups: (string | number | null)[][];
  bot: (string | number | null)[][];
  /**
   * Personalized Puzzles sessions per day, `fetch_train`: [day, sessions, users, completed,
   * abandoned, open, puzzles_served]. Never-started sessions are excluded.
   */
  train: (string | number | null)[][];
  train_funnel: {
    starters: number;
    zero_solve_users: number;
    finishers: number;
    returners: number;
    all_time_starters: number;
    all_time_zero_solve_users: number;
    all_time_finishers: number;
    all_time_returners: number;
    /** YYYY-MM-DD of the first recorded Start press, or null before any. */
    entered_since: string | null;
  };
  solves: (string | number | null)[][];
  /**
   * Blunder Check sessions per day, `fetch_blunder_check_sessions`: [day, sessions, users,
   * completed, abandoned, open, windows_composed].
   */
  blunder_check_sessions: (string | number | null)[][];
  /**
   * Blunder Check judged windows per day, `fetch_blunder_check_windows`: [day, windows, users,
   * points_scored, points_possible, cleared, caught, missed, false_alarm].
   */
  blunder_check_windows: (string | number | null)[][];
  imports: (string | number | null)[][];
  persona: (string | number | null)[][];
  bot_players: number;
  elo: number[][];
  funnel: (string | number | null)[][];
  tti: (string | number | null)[][];
  stick: (string | number | null)[][];
  conversion: Record<string, number | string>;
  conversion_compare: (string | number | null)[][];
  purged_excluded: Record<string, number>;
}
