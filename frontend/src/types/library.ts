/**
 * TypeScript mirrors of the library backend schemas
 * (app/schemas/library.py + app/services/flaws_service.py).
 *
 * Literal unions only — no loose `string` types.
 * noUncheckedIndexedAccess: dict types use Record<K, V> (access returns V | undefined).
 */

import type { UserResult } from '@/types/api';
import type { TimeControlBucket } from '@/types/endgames';
import type { TacticFamily } from '@/lib/tacticComparisonMeta';

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

/**
 * Tactic orientation filter.
 * Mirrors backend TacticOrientation Literal["either","missed","allowed"].
 * 'either' = OR across both missed+allowed column sets (the default).
 */
export type TacticOrientation = 'either' | 'missed' | 'allowed';

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
  // Lichess-blitz-normalized ratings; optional + nullable so
  // existing fixtures compile and a missing/older value falls back to raw.
  white_rating_lichess_blitz?: number | null;
  black_rating_lichess_blitz?: number | null;
  opening_name: string | null;
  opening_eco: string | null;
  user_color: string;
  ply_count: number | null;
  termination: string | null;
  time_control_str: string | null;
  result_fen: string | null;
  // Flaw fields, discriminated by analysis_state:
  // severity_counts is null (never 0/0/0) for unanalyzed games.
  severity_counts: SeverityCountsData | null;
  // Canonical per-color accuracy (0-100). Null when not yet computed. No ACPL
  // field and no per-side count fields (counts are client-derived).
  white_accuracy: number | null;
  black_accuracy: number | null;
  chips: FlawTag[];
  analysis_state: AnalysisState;
  // Null for unanalyzed games (analysis_state === 'no_engine_analysis'):
  eval_series: EvalPoint[] | null;
  flaw_markers: FlawMarker[] | null;
  phase_transitions: PhaseTransitions | null;
  // SAN mainline (one entry per ply, ordered). moves[i] is the move played at
  // ply i, so replaying moves[0..i] yields the position at eval_series[i].
  // Null for unanalyzed games. Drives the live miniboard on eval-chart hover.
  moves: string[] | null;
  // The position `moves` is replayed FROM. Null means the
  // standard start (the overwhelming majority); non-null for chess.com
  // thematic/custom-position games and pasted [SetUp] PGNs. Anything replaying
  // `moves` must seed from this, not from STARTING_FEN.
  initial_fen: string | null;
  // Active eval-job state for the on-demand analyze pill; null when no active job
  // (unanalyzed-and-unqueued, or already analyzed).
  active_eval_status: 'pending' | 'leased' | null;
  // 1-based ply depth of the deepest opening-book
  // match, computed on-read by the backend from `moves` (no column, no
  // migration/backfill). 0 = no known opening prefix matched. Always present
  // (backend field defaults to 0, never omitted) — non-optional, non-nullable.
  // Gates the background gem sweep and marks theory plies with the book badge.
  opening_ply_count: number;
}

/** One ply's white-perspective ES datapoint (mirrors backend EvalPoint). */
export interface EvalPoint {
  ply: number;
  es: number | null;       // white-perspective ES in (0,1); null = missing eval
  eval_cp: number | null;  // raw cp for tooltip
  eval_mate: number | null; // signed, white-perspective
  clock_seconds: number | null; // mover's remaining clock after this move; null = no %clk
  move_seconds: number | null;  // time spent on this move (1dp); null when prior clock unknown
  // Engine best move FROM this position, in UCI (e.g. "g1f3") — NOT SAN. Null
  // when no PV was captured. moves[i] / MoveNode.san are SAN (e.g. "Nf3"): a
  // direct `played === best_move` string comparison silently never matches.
  // Convert first via sanToUci() (frontend/src/lib/sanToSquares.ts) — this is
  // the free prefilter's data source for the gem sweep.
  best_move: string | null;
  // Pre-classified gem/great tier for this ply's stored mainline move, computed
  // server-side from `game_best_moves` via the authoritative
  // classify_best_move. Null when no candidate row exists OR the
  // row classifies "neither" — the board never re-derives this from cp/margin
  // math for an analyzed game (that's the fallback-only classifyGem/
  // classifyGreat path in gemMove.ts).
  //
  // The 'best' and 'good' tiers are computed live server-side (no stored row
  // involved). 'best' = the played move identity-equals the stored best_move
  // (out of book, not gem/great).
  // 'good' = the mover-POV expected-score drop is below INACCURACY_DROP (out
  // of book, not best/gem/great). Precedence gem > great > best > good > null.
  // maia_prob stays null for best/good — it is a gem/great-only rarity stat.
  best_move_tier: 'gem' | 'great' | 'best' | 'good' | null;
  // Maia policy probability (0..1) of the stored mainline move at this ply's
  // pinned rating rung — set ONLY alongside a non-null gem/great
  // best_move_tier (never populated for a "neither" ply, nor for best/good).
  maia_prob: number | null;
}

/** The two "rare move" tiers (gem/great) that surface as eval-chart dots and a
 *  tooltip row. The best/good tiers are analysis-board /
 *  library-card only and MUST NOT appear on the eval chart — gate every
 *  eval-chart tier read on this guard so a widened `best_move_tier` never leaks
 *  best/good into the chart's `=== 'gem' ? … : great` fallback. */
export type RareMoveTier = 'gem' | 'great';
export function isRareMoveTier(tier: EvalPoint['best_move_tier']): tier is RareMoveTier {
  return tier === 'gem' || tier === 'great';
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
  /** Tactic allowed to flaw-maker's opponent (refutation PV). Null below confidence gate or when DB column is NULL. */
  allowed_tactic_motif: string | null;
  /** Confidence for allowed_tactic_motif (0-100). Null when no motif assigned. */
  allowed_tactic_confidence: number | null;
  /** 0-based ply depth of the allowed tactic; null when its motif chip is hidden. Display as depth+1. */
  allowed_tactic_depth: number | null;
  /** Tactic the flaw-maker missed (the "instead-of" PV). Null below confidence gate or when DB column is NULL. */
  missed_tactic_motif: string | null;
  /** Confidence for missed_tactic_motif (0-100). Null when no motif assigned. */
  missed_tactic_confidence: number | null;
  /** 0-based ply depth of the missed tactic; null when its motif chip is hidden. Display as depth+1. */
  missed_tactic_depth: number | null;
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
 * One ISO-week flaw-trend datapoint (mirrors backend FlawTrendPoint).
 *
 * `date` is the Monday of the ISO week (label for an ordinal axis, not a calendar bucket).
 * blunder/mistake/inaccuracy_rate are per-100-moves MACRO rates over a trailing
 * trend_window-game window, from the games-table oracle columns. games_in_window is the
 * window size; per_week_games is the games played that ISO week (volume bars).
 */
export interface FlawTrendPoint {
  date: string;
  blunder_rate: number;
  mistake_rate: number;
  inaccuracy_rate: number;
  games_in_window: number;
  per_week_games: number;
}

/** One time control's Flaws Timeline series (mirrors backend FlawTrendTc). */
export interface FlawTrendTc {
  tc: TimeControlBucket;
  points: FlawTrendPoint[];
}

/**
 * Response for GET /api/library/flaw-stats (mirrors backend FlawStatsResponse).
 *
 * The timeline comes per time control (`trend_by_tc`, one entry per TC that has analyzed
 * games); there is no severity band, tag distribution or overall aggregate.
 * trend_window = rolling window size (games). analyzed_n is the filter-scoped
 * analyzed-game count (FlawsTab reads it).
 */
export interface FlawStatsResponse {
  trend_by_tc: FlawTrendTc[];
  trend_window: number;
  analyzed_n: number;
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
  /** SAN of the flawed move — sourced from game_positions at ply=N. */
  move_san: string | null;
  severity: 'mistake' | 'blunder';
  tags: FlawTag[];
  /** Before/after eval from game_positions join (white-POV). */
  eval_cp_before: number | null;
  eval_mate_before: number | null;
  eval_cp_after: number | null;
  eval_mate_after: number | null;
  /** Player ratings from the games join. */
  white_rating: number | null;
  black_rating: number | null;
  // Game metadata row header
  user_result: 'win' | 'draw' | 'loss';
  played_at: string | null;
  time_control_bucket: string | null;
  /** Game-info line parity with the Games card. */
  time_control_str: string | null;
  ply_count: number | null;
  termination: string | null;
  platform: string;
  platform_url: string | null;
  white_username: string | null;
  black_username: string | null;
  user_color: string;
  /** Mover's remaining clock AFTER the flawed move; null = no %clk (chess.com). */
  clock_seconds: number | null;
  /** Time spent on the flawed move (1dp); null when prior clock unknown. */
  move_seconds: number | null;
  /** Tactic allowed to flaw-maker's opponent (refutation PV, flaw_ply+1). Null below confidence gate. */
  allowed_tactic_motif: string | null;
  /** Confidence for allowed_tactic_motif (0-100). Null when no motif assigned. */
  allowed_tactic_confidence: number | null;
  /** 0-based ply depth of the allowed tactic; null when its motif chip is hidden. Display as depth+1. */
  allowed_tactic_depth: number | null;
  /** Tactic the flaw-maker missed (the "instead-of" PV, flaw_ply). Null below confidence gate. */
  missed_tactic_motif: string | null;
  /** Confidence for missed_tactic_motif (0-100). Null when no motif assigned. */
  missed_tactic_confidence: number | null;
  /** 0-based ply depth of the missed tactic; null when its motif chip is hidden. Display as depth+1. */
  missed_tactic_depth: number | null;
  /** Engine best move FROM the pre-flaw position (UCI); null when no PV captured. */
  best_move: string | null;
}

/** Response for GET /api/library/flaws — paginated per-flaw list (mirrors LibraryFlawsResponse). */
export interface LibraryFlawsResponse {
  flaws: FlawListItem[];
  matched_count: number;
  offset: number;
  limit: number;
}

// ─── Flaw comparison (GET /api/library/flaw-comparison) ───────────────────────

/** The 12 flaw-delta metrics (mirrors backend FlawDeltaMetric). */
export type FlawDeltaMetric =
  | 'mistake'
  | 'blunder'
  | 'low_clock'
  | 'hasty'
  | 'unrushed'
  | 'opening'
  | 'middlegame'
  | 'endgame_phase'
  | 'miss'
  | 'lucky'
  | 'reversed'
  | 'squandered';

/**
 * Per-bullet data for one flaw-delta metric of one time control (mirrors backend FlawBullet).
 *
 * snake_case field names to match the JSON payload exactly. delta and CI fields are null
 * when both player_events and opp_events are zero. `significant` is the server-side 99%
 * test (CI excludes 0) that an out-of-band verdict needs; `has_zone` is always true
 * for flaw bullets.
 */
export interface FlawBullet {
  tag: FlawDeltaMetric;
  delta: number | null;
  ci_low: number | null;
  ci_high: number | null;
  /** Mean per-game player flaw rate per 100 of the user's moves (null = zero-event). */
  player_rate: number | null;
  /** Mean per-game opponent flaw rate per 100 of the user's moves (null = zero-event).
   *  player_rate - opp_rate === delta exactly (paired comparison). */
  opp_rate: number | null;
  /** Two-sided p-value vs H0: delta === 0 (null = zero-event / n < 2). */
  p_value: number | null;
  player_events: number;
  opp_events: number;
  zone_lo: number;
  zone_hi: number;
  has_zone: boolean;
  significant: boolean;
}

/** The three clock tags of a crossed cell (mirrors backend FlawTempoMetric). */
export type FlawTempoMetric = 'low_clock' | 'hasty' | 'unrushed';

/** The three game-phase tags of a crossed cell (mirrors backend FlawPhaseMetric). */
export type FlawPhaseMetric = 'opening' | 'middlegame' | 'endgame_phase';

/**
 * One crossed tempo x game-phase cell (mirrors backend TempoPhaseCell): flaws carrying
 * BOTH tags, same paired per-100-moves basis as FlawBullet. 8 of 9 cells carry the
 * backend's pooled benchmark band (TEMPO_PHASE_ZONES); low_clock x opening has none
 * (has_zone false, zones 0). Flaws with no clock data (NULL tempo) are in no cell.
 */
export interface TempoPhaseCell extends Omit<FlawBullet, 'tag'> {
  tempo: FlawTempoMetric;
  phase: FlawPhaseMetric;
}

/** One time control's flaw comparison (mirrors backend FlawComparisonTc). */
export interface FlawComparisonTc {
  tc: TimeControlBucket;
  analyzed_n: number;
  /** All games of this TC in the current filters, analyzed or not (coverage denominator). */
  total_n: number;
  below_gate: boolean;
  /** 12 bullets, also below the gate (the tile numbers stay visible). */
  bullets: FlawBullet[];
  /** 9 crossed tempo x phase cells, phase-major (opening, middlegame, endgame_phase; low_clock, hasty, unrushed inside each). */
  tempo_phase_cells: TempoPhaseCell[];
}

// ─── Tactic comparison (GET /api/library/tactic-comparison) ───────────────────

/** Which side of a tactic a cell describes (mirrors backend TacticSide). */
export type TacticSide = 'missed' | 'allowed';

/**
 * One tactic family on one side (mirrors backend TacticBullet).
 *
 * Rates and delta are per 100 games. Sign convention: positive delta = you have MORE of
 * these tactics than your opponents = bad, for both sides. Rate, delta, CI and p-value
 * are null when neither side has a flaw (then `significant` is false).
 */
export interface TacticBullet {
  family: TacticFamily;
  orientation: TacticSide;
  you_rate: number | null;     // per 100 games, player side
  opp_rate: number | null;     // per 100 games, opponent side
  delta: number | null;        // you_rate - opp_rate per 100 games
  ci_low: number | null;       // 99% CI lower bound on delta
  ci_high: number | null;      // 99% CI upper bound on delta
  p_value: number | null;      // two-sided p vs H0: delta === 0
  you_events: number;          // raw flaw count, player side
  opp_events: number;          // raw flaw count, opponent side
  zone_lo: number;             // typical-range bounds per 100 games; 0.0 when has_zone is false
  zone_hi: number;
  has_zone: boolean;           // false when this family-side has no viable benchmark band
  significant: boolean;        // 99% CI on delta excludes 0
}

/** One time control's tactic comparison (mirrors backend TacticComparisonTc). */
export interface TacticComparisonTc {
  tc: TimeControlBucket;
  analyzed_n: number;
  below_gate: boolean;
  /** 38 bullets in family order, missed before allowed; populated below the gate too. */
  bullets: TacticBullet[];
}

/**
 * Response for GET /api/library/tactic-comparison (mirrors backend TacticComparisonResponse).
 *
 * tcs: one entry per time control with analyzed games in the current filters, in
 *      LIBRARY_TC_ORDER. The TC switch is client-side over this list.
 * analyzed_gate: minimum analyzed games per TC; exposed so the frontend renders "N of 20"
 *                without hardcoding.
 */
export interface TacticComparisonResponse {
  tcs: TacticComparisonTc[];
  analyzed_gate: number;
}

/**
 * Response for GET /api/library/flaw-comparison (mirrors backend FlawComparisonResponse).
 *
 * tcs: one entry per time control with analyzed games in the current filters, in
 *      LIBRARY_TC_ORDER. The TC switch is client-side over this list.
 * analyzed_gate: minimum analyzed games per TC (constant = 20); exposed so the frontend
 *                can render "N of 20" without hardcoding.
 */
export interface FlawComparisonResponse {
  tcs: FlawComparisonTc[];
  analyzed_gate: number;
  /** All games (analyzed or not) under the current filters, across the allowed TCs. */
  total_n: number;
}

// ─── Tactic Lines (GET /api/library/flaws/{game_id}/{ply}/tactic-lines) ────────

/**
 * PV walk data for the TacticLineExplorer.
 * Mirrors backend TacticLinesResponse Pydantic model field-for-field.
 *
 * missed_moves: SAN from the decision position (flaw_ply PV). Null when PV is NULL.
 * allowed_moves: SAN starting with the flaw move (prepended) then opponent PV.
 *                Null when game_positions[ply+1].pv is NULL.
 * position_fen: full FEN (with side-to-move from ply parity) for chess.js root board.
 * flaw_ply: real game ply of the flaw (for move-number labeling in SAN ladder).
 */
export interface TacticLinesResponse {
  missed_moves: string[] | null;
  missed_depth: number | null;
  missed_tactic_ply_index: number | null;
  missed_motif: string | null;
  /** Engine eval of the missed-line root (decision position, from game_positions[ply-1] since eval is post-move), white-POV. */
  missed_eval_cp: number | null;
  missed_eval_mate: number | null;
  allowed_moves: string[] | null;
  allowed_depth: number | null;
  allowed_tactic_ply_index: number | null;
  allowed_motif: string | null;
  /** Engine eval of the allowed-line root (after the flaw move, from game_positions[ply] post-move eval), white-POV. */
  allowed_eval_cp: number | null;
  allowed_eval_mate: number | null;
  /** Full FEN (with side-to-move) for chess.js root board initialization. */
  position_fen: string;
  /** SAN of the move played (the flaw move). Null on final position. */
  flaw_move_san: string | null;
  /** Engine best move from the pre-flaw position (UCI). Null when no PV captured. */
  best_move_uci: string | null;
  /** Real game ply of the flaw (for move-number anchoring in the SAN ladder). */
  flaw_ply: number;
  /** Severity of the flaw move ("mistake" | "blunder") — drives the SAN-ladder glyph. */
  flaw_severity: FlawSeverity;
}
