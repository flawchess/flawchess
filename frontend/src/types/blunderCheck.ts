/**
 * Wire types of the blunder-check drill API (Phase 249).
 *
 * Hand-mirrored from `app/schemas/blunder_check.py`: field names and the string
 * literal unions match the Pydantic models exactly. The server owns every grade
 * and every point total (Pitfall 13), so the client never derives either.
 */

import type { TrainMoveTier } from '@/lib/trainScore';
import type { TimeControlBucket } from '@/types/endgames';
import type { ServerGradedMove } from '@/types/train';

export type WindowOutcome = 'cleared' | 'caught' | 'missed' | 'false_alarm';
export type WindowState = 'pending' | 'active' | 'ended';
export type AnswerKind = 'safe' | 'blunder' | 'timeout';
export type AnswerResult =
  | 'correct_safe'
  | 'false_alarm'
  | 'caught'
  | 'missed'
  | 'timeout_safe'
  | 'timeout_blunder';

/** Progress of one window: the outcome is known only once the window has ended. */
export interface WindowProgress {
  position: number;
  state: WindowState;
  outcome: WindowOutcome | null;
  points_scored: number;
}

/** Session header plus the per-window progress strip. */
export interface BlunderCheckSessionResponse {
  session_id: number;
  window_count: number;
  /** Lowest position whose outcome is still open; null when every window has ended. */
  current_position: number | null;
  session_points: number;
  windows: WindowProgress[];
}

/** The one judged move the user must rate right now; its UCI is the arrow on the board. */
export interface Prompt {
  move_index: number;
  move_uci: string;
}

/** A judged move already answered, with the opponent reply that followed it (if any). */
export interface AnsweredMove {
  move_index: number;
  move_uci: string;
  reply_uci: string | null;
  result: AnswerResult;
  points_awarded: number;
  points_forfeited: number;
}

/** Window start (or reload): the lead-in, the answered moves so far and the single open prompt. */
export interface WindowStartResponse {
  position: number;
  start_fen: string;
  orientation: 'white' | 'black';
  lead_in_ucis: string[];
  answered: AnsweredMove[];
  prompt: Prompt;
  timer_remaining_ms: number;
  move_timer_seconds: number;
  window_points: number;
  session_points: number;
  /**
   * Set only on a reload after a caught blunder whose better move is still open: `answered`
   * then ends with the caught move and `prompt` repeats it.
   */
  better_move: BetterMoveTask | null;
}

/** One answer to the open prompt; the server grades it. */
export interface AnswerRequest {
  move_index: number;
  answer: AnswerKind;
  client_elapsed_ms: number;
}

/** The better-move task, handed out only when the blunder was caught. */
export interface BetterMoveTask {
  fen: string;
  key_uci: string;
  server_graded_moves: ServerGradedMove[];
}

/** The server's grade for one answer plus what the user may see next. */
export interface AnswerResponse {
  move_index: number;
  result: AnswerResult;
  points_awarded: number;
  points_forfeited: number;
  window_points: number;
  session_points: number;
  window_ended: boolean;
  outcome: WindowOutcome | null;
  reply_uci: string | null;
  next_prompt: Prompt | null;
  timer_remaining_ms: number | null;
  better_move: BetterMoveTask | null;
}

/** One finished window in the session result. */
export interface WindowResultItem {
  position: number;
  outcome: WindowOutcome;
  points_scored: number;
  points_possible: number;
}

/** Finished session: points, points possible and Score %. */
export interface SessionResultResponse {
  session_id: number;
  session_points: number;
  points_possible: number;
  score_pct: number;
  windows: WindowResultItem[];
}

/** The better-move grade of one off-key move, the same three tiers as personalized puzzles. */
export type BetterMoveTier = TrainMoveTier;

/** The better move the user played; `client_tier` is the phone's reading for an off-key move. */
export interface BetterMoveRequest {
  played_uci: string;
  client_tier: BetterMoveTier;
}

/** The server's grade of the better move: the tier decides the points (+2 / +1 / +0). */
export interface BetterMoveResponse {
  tier: BetterMoveTier;
  points_awarded: number;
  window_points: number;
  session_points: number;
}

/** Neutral facts of a stranger's game (D-09): no usernames, emails or user ids. */
export interface GameInfo {
  time_control_str: string | null;
  time_control_bucket: TimeControlBucket | null;
  played_at: string | null;
  mover_rating: number | null;
}

export type BlunderWindowCase = 'allowed' | 'pure_miss' | 'mixed';

/** Solution of a caught or missed blunder window. */
export interface BlunderSolution {
  kind: 'blunder';
  outcome: 'caught' | 'missed';
  is_own: boolean;
  window_case: BlunderWindowCase;
  game_id: number | null;
  analysis_ply: number;
  fen: string;
  blunder_uci: string;
  key_uci: string;
  better_move_uci: string | null;
  better_move_tier: BetterMoveTier | null;
  /** The server-graded moves at the blunder position (the key included), best first. */
  server_graded_moves: ServerGradedMove[];
  game_info: GameInfo | null;
  window_points: number;
  /** The breakdown of `window_points`: the safe calls before the blunder. */
  safe_points: number;
  /** The points for calling the blunder (0 when it was missed). */
  blunder_points: number;
  /** The points of the better move, null when none was played. */
  better_move_points: number | null;
}

/** Solution of a cleared herring window: every judged move was fine. */
export interface HerringSolution {
  kind: 'herring';
  outcome: 'cleared';
  is_own: boolean;
  game_id: number | null;
  analysis_ply: number;
  fen: string;
  /** Every ply from `fen` on, the judged moves and the replies between them, in order. */
  sequence_ucis: string[];
  game_info: GameInfo | null;
  window_points: number;
}

/**
 * Solution of a false alarm: the flagged move, its game and the best move at its position.
 * Never the window's case or the blunder the user did not reach (D-10).
 */
export interface FalseAlarmSolution {
  kind: 'false_alarm';
  outcome: 'false_alarm';
  is_own: boolean;
  game_id: number | null;
  analysis_ply: number;
  flagged_uci: string;
  fen: string;
  /** Stockfish's stored best move at the flagged position, null when there is none. */
  key_uci: string | null;
  game_info: GameInfo | null;
  window_points: number;
}

/** A solution that shows lines: a caught or missed blunder, or a false alarm. */
export type LinesSolution = BlunderSolution | FalseAlarmSolution;

export type WindowSolution = BlunderSolution | HerringSolution | FalseAlarmSolution;
