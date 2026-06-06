/**
 * TypeScript mirrors of the Phase 106 + Phase 107 library backend schemas
 * (app/schemas/library.py + app/services/flaws_service.py).
 *
 * Literal unions only — no loose `string` types.
 * noUncheckedIndexedAccess: dict types use Record<K, V> (access returns V | undefined).
 */

import type { UserResult } from '@/types/api';

// ─── Taxonomy unions ──────────────────────────────────────────────────────────

/** All possible flaw tag strings (backend FlawTag literal). */
export type FlawTag =
  | 'low-clock'
  | 'impatient'
  | 'considered'
  | 'miss'
  | 'lucky-escape'
  | 'while-ahead'
  | 'result-changing'
  | 'opening'
  | 'middlegame'
  | 'endgame';

/** Flaw severity tiers (backend FlawSeverity literal). */
export type FlawSeverity = 'inaccuracy' | 'mistake' | 'blunder';

/** Tempo-family tags — subset of FlawTag (backend TempoTag literal). */
export type TempoTag = 'low-clock' | 'impatient' | 'considered';

/** Analysis state of a game (whether engine evals are present). */
export type AnalysisState = 'analyzed' | 'no_engine_analysis';

// ─── Game card (GET /api/library/games) ──────────────────────────────────────

/**
 * Per-game severity counts over the user's moves (mirrors backend SeverityCounts TypedDict).
 * Null-safe: nullable on the GameFlawCard when analysis_state === 'no_engine_analysis'.
 */
export interface SeverityCountsData {
  inaccuracy: number;
  mistake: number;
  blunder: number;
}

/**
 * A single game card for the Games subtab archive (mirrors backend GameFlawCard).
 * Re-uses UserResult from api.ts; never contains internal hash fields.
 */
export interface GameFlawCard {
  game_id: number;
  user_result: UserResult;
  played_at: string | null;
  time_control_bucket: string | null;
  platform: string;
  platform_url: string | null;
  white_username: string | null;
  black_username: string | null;
  white_rating: number | null;
  black_rating: number | null;
  opening_name: string | null;
  opening_eco: string | null;
  user_color: string;
  move_count: number | null;
  termination: string | null;
  time_control_str: string | null;
  result_fen: string | null;
  // Phase 106 flaw fields — discriminated by analysis_state:
  // severity_counts is null (never 0/0/0) for unanalyzed games.
  severity_counts: SeverityCountsData | null;
  chips: FlawTag[];
  analysis_state: AnalysisState;
}

/** Response for GET /api/library/games — paginated game archive (mirrors LibraryGamesResponse). */
export interface LibraryGamesResponse {
  games: GameFlawCard[];
  matched_count: number;
  offset: number;
  limit: number;
}

// ─── Flaw stats (GET /api/library/flaw-stats) ─────────────────────────────────

/**
 * Per-severity rates normalized two ways (mirrors backend SeverityRates).
 * Both dicts keyed by FlawSeverity; access returns number | undefined per noUncheckedIndexedAccess.
 */
export interface SeverityRates {
  per_game: Record<FlawSeverity, number>;
  per_100_moves: Record<FlawSeverity, number>;
}

/**
 * Tag distribution over the analyzed-set M+B FlawRecords (mirrors backend TagDistribution).
 *
 * tempo                = count of each tempo tag; sums to <= M+B flaws (optional — no tag
 *                        when clock data is missing). Panel must show unmeasured remainder.
 * result_changing_rate = result-changing M+B flaws / total M+B flaws; 0.0 when none.
 * phase_histogram      = count of flaws in each game phase.
 * miss_rate            = miss M+B flaws / total M+B flaws; 0.0 when none. (D-01, Phase 107)
 * lucky_escape_rate    = lucky-escape M+B flaws / total M+B flaws; 0.0 when none. (D-01)
 * while_ahead_rate     = while-ahead M+B flaws / total M+B flaws; 0.0 when none. (D-01)
 */
export interface TagDistribution {
  tempo: Record<TempoTag, number>;
  result_changing_rate: number;
  phase_histogram: Record<'opening' | 'middlegame' | 'endgame', number>;
  // D-01 flat rate fields (Phase 107):
  miss_rate: number;
  lucky_escape_rate: number;
  while_ahead_rate: number;
}

/**
 * One rolling-game-window trend datapoint (mirrors backend FlawTrendPoint).
 * `date` is the played_at date of the LAST game in the trailing window (label only, not a bucket).
 */
export interface FlawTrendPoint {
  date: string;
  rate: number;
  game_count: number;
  window_size: number;
}

/**
 * Response for GET /api/library/flaw-stats (mirrors backend FlawStatsResponse).
 * Stats over the filtered analyzed-only set.
 */
export interface FlawStatsResponse {
  per_severity_counts: SeverityCountsData;
  rates: SeverityRates;
  tag_distribution: TagDistribution;
  trend: FlawTrendPoint[];
  analyzed_pct: number;
  analyzed_n: number;
  total_n: number;
}

// ─── Per-flaw list (GET /api/library/flaws) ───────────────────────────────────

/**
 * One row in the Flaws subtab — one flawed position (mirrors backend FlawListItem).
 * Carries full miniboard display payload + game metadata. No *_hash fields.
 */
export interface FlawListItem {
  game_id: number;
  ply: number;
  fen: string;
  move_san: string | null;
  severity: 'mistake' | 'blunder';
  tags: FlawTag[];
  es_before: number;
  es_after: number;
  // Game metadata row header
  user_result: 'win' | 'draw' | 'loss';
  played_at: string | null;
  time_control_bucket: string | null;
  platform: string;
  platform_url: string | null;
  white_username: string | null;
  black_username: string | null;
  user_color: string;
}

/** Response for GET /api/library/flaws — paginated per-flaw list (mirrors LibraryFlawsResponse). */
export interface LibraryFlawsResponse {
  flaws: FlawListItem[];
  matched_count: number;
  offset: number;
  limit: number;
}
