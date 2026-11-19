/**
 * Shared GET /train/progress fixture pieces for the Train tests (Phase 251): the per-mode rows
 * and the plan 06 fields every `TrainProgressResponse` fixture now carries.
 */
import type { TrainBlunderCheckModeProgress, TrainModeProgress, TrainProgressResponse } from '@/types/train';

const PUZZLES_PER_SESSION = 6;
const BLUNDER_CHECK_PER_SESSION = 6;

export const PUZZLES_MODE: TrainModeProgress = {
  size: PUZZLES_PER_SESSION,
  state: 'pending',
  remaining: 0,
  pending: 0,
  first_session_done: false,
};

export const BLUNDER_CHECK_MODE: TrainBlunderCheckModeProgress = {
  size: BLUNDER_CHECK_PER_SESSION,
  state: 'pending',
  remaining: BLUNDER_CHECK_PER_SESSION,
  pending: BLUNDER_CHECK_PER_SESSION,
  first_session_done: false,
  points_today: 0,
  has_rated_games: true,
  needs_level: false,
};

/** The four plan 06 `TrainProgressResponse` fields, spread into a fixture. */
export const PHASE_251_PROGRESS_FIELDS: Pick<
  TrainProgressResponse,
  'modes' | 'day_complete' | 'pending_count' | 'blunder_check_notice'
> = {
  modes: { puzzles: PUZZLES_MODE, blunder_check: BLUNDER_CHECK_MODE },
  day_complete: false,
  pending_count: PUZZLES_MODE.pending + BLUNDER_CHECK_MODE.pending,
  blunder_check_notice: false,
};
