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
  | 'hasty'
  | 'unrushed'
  | 'miss'
  | 'lucky'
  | 'reversed'
  | 'squandered'
  | 'opening'
  | 'middlegame'
  | 'endgame';

/** Flaw severity tiers (backend FlawSeverity literal). */
export type FlawSeverity = 'inaccuracy' | 'mistake' | 'blunder';

/** Tempo-family tags — subset of FlawTag (backend TempoTag literal). */
export type TempoTag = 'low-clock' | 'hasty' | 'unrushed';

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
  ply_count: number | null;
  termination: string | null;
  time_control_str: string | null;
  result_fen: string | null;
  // Phase 106 flaw fields — discriminated by analysis_state:
  // severity_counts is null (never 0/0/0) for unanalyzed games.
  severity_counts: SeverityCountsData | null;
  chips: FlawTag[];
  analysis_state: AnalysisState;
  // Phase 109 additions — null for unanalyzed games (analysis_state === 'no_engine_analysis'):
  eval_series: EvalPoint[] | null;
  flaw_markers: FlawMarker[] | null;
  phase_transitions: PhaseTransitions | null;
  // SAN mainline (one entry per ply, ordered). moves[i] is the move played at
  // ply i, so replaying moves[0..i] yields the position at eval_series[i].
  // Null for unanalyzed games. Drives the live miniboard on eval-chart hover.
  moves: string[] | null;
}

/** One ply's white-perspective ES datapoint (mirrors backend EvalPoint). */
export interface EvalPoint {
  ply: number;
  es: number | null;       // white-perspective ES in (0,1); null = missing eval
  eval_cp: number | null;  // raw cp for tooltip
  eval_mate: number | null; // signed, white-perspective
  clock_seconds: number | null; // mover's remaining clock after this move; null = no %clk
  move_seconds: number | null;  // time spent on this move (1dp); null when prior clock unknown
}

/**
 * One flaw dot for the eval chart (both colors, B/M/I).
 * is_user=true → filled circle (player); is_user=false → hollow circle (opponent).
 */
export interface FlawMarker {
  ply: number;
  severity: FlawSeverity;
  tags: FlawTag[];    // empty for inaccuracies
  is_user: boolean;
  move_san: string | null; // SAN of the flawed move — tooltip move label (null on final position)
}

/** First ply of middlegame and endgame phases (at most two phase lines). */
export interface PhaseTransitions {
  middlegame_ply: number | null;
  endgame_ply: number | null;
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
 * tempo             = count of each tempo tag; sums to <= M+B flaws (optional — no tag
 *                     when clock data is missing). Panel must show unmeasured remainder.
 * reversed_rate     = reversed M+B flaws / total M+B flaws; 0.0 when none. (Phase 110)
 * squandered_rate   = squandered M+B flaws / total M+B flaws; 0.0 when none. (Phase 110)
 * phase_histogram   = count of flaws in each game phase.
 * miss_rate         = miss M+B flaws / total M+B flaws; 0.0 when none. (D-01, Phase 107)
 * lucky_rate = lucky M+B flaws / total M+B flaws; 0.0 when none. (D-01)
 */
export interface TagDistribution {
  tempo: Record<TempoTag, number>;
  reversed_rate: number;
  squandered_rate: number;
  phase_histogram: Record<'opening' | 'middlegame' | 'endgame', number>;
  // D-01 flat rate fields (Phase 107):
  miss_rate: number;
  lucky_rate: number;
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
 *
 * Phase 112 (SC-2 + SC-4): added white_rating/black_rating and before/after raw eval;
 * dropped es_before/es_after (D-07). move_san now join-sourced from game_positions (D-08).
 */
export interface FlawListItem {
  game_id: number;
  ply: number;
  fen: string;
  /** SAN of the flawed move — sourced from game_positions at ply=N (Phase 112, D-08). */
  move_san: string | null;
  severity: 'mistake' | 'blunder';
  tags: FlawTag[];
  /** Before/after eval from game_positions join (white-POV). Phase 112, D-05. */
  eval_cp_before: number | null;
  eval_mate_before: number | null;
  eval_cp_after: number | null;
  eval_mate_after: number | null;
  /** Player ratings from the games join (Phase 112, D-03). */
  white_rating: number | null;
  black_rating: number | null;
  // Game metadata row header
  user_result: 'win' | 'draw' | 'loss';
  played_at: string | null;
  time_control_bucket: string | null;
  /** Game-info line parity with the Games card (Phase 112 follow-up). */
  time_control_str: string | null;
  ply_count: number | null;
  termination: string | null;
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
