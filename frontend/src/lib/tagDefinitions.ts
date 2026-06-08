/**
 * Human-readable definitions for FlawTags.
 *
 * TAG_DEFINITIONS is rebuilt (Phase 110 Plan 05 D-07) for the TagChip and
 * FlawFilterControl definition popovers: each entry is a one-sentence definition with all
 * numeric thresholds interpolated from @/generated/flawThresholds — no hard-coded
 * percentages or evals anywhere in this file. Expected-score thresholds are shown as
 * Stockfish eval (pawns), which most players reason in more readily than win probability.
 *
 * Every tag surface (chips, Flaw-Stats panel, filter control) renders the raw
 * lowercase-with-dash tag string; there is no title-cased label map (D-07 amendment,
 * Phase 110 UAT).
 */

import type { FlawTag } from '@/types/library';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import {
  TIME_PRESSURE_CLOCK_FRACTION,
  TIME_PRESSURE_CLOCK_ABS_SECONDS,
  HASTY_MOVE_FRACTION,
  HASTY_MOVE_ABS_SECONDS,
  WINNING_LINE_ES,
  LOSING_LINE_ES,
  FROM_WINNING_ES,
  SQUANDERED_EXIT_ES,
} from '@/generated/flawThresholds';

// ─── Format helpers ───────────────────────────────────────────────────────────

/** Convert a fraction (e.g. 0.05) to a percent string (e.g. "5%"). */
function pct(fraction: number): string {
  return `${Math.round(fraction * 100)}%`;
}

/** Convert seconds to a duration string (e.g. 30 -> "30s"). */
function secs(s: number): string {
  return `${s}s`;
}

/**
 * Lichess winning-chances sigmoid coefficient — the canonical value lives in
 * app/services/eval_utils.py (LICHESS_K). The flaw thresholds are stored as
 * expected scores in (0, 1), but most players reason in Stockfish eval, so we
 * invert the sigmoid for display: ES = 1 / (1 + exp(-K·cp)) ⇒ cp = ln(ES/(1-ES)) / K.
 */
const LICHESS_K = 0.00368208;
const CP_PER_PAWN = 100;

/** Convert an expected score in (0, 1) to a signed pawn-eval string (e.g. 0.70 -> "+2.3"). */
function evalStr(expectedScore: number): string {
  const cp = Math.log(expectedScore / (1 - expectedScore)) / LICHESS_K;
  return formatSignedEvalPawns(cp / CP_PER_PAWN);
}

// ─── Precomputed display values ───────────────────────────────────────────────

const LOW_CLOCK_PCT = pct(TIME_PRESSURE_CLOCK_FRACTION);
const LOW_CLOCK_ABS = secs(TIME_PRESSURE_CLOCK_ABS_SECONDS);
const HASTY_PCT = pct(HASTY_MOVE_FRACTION);
const HASTY_ABS = secs(HASTY_MOVE_ABS_SECONDS);
const WIN_EVAL = evalStr(WINNING_LINE_ES);
const LOSING_EVAL = evalStr(LOSING_LINE_ES);
const FROM_WIN_EVAL = evalStr(FROM_WINNING_ES);
const SQUANDERED_EXIT_EVAL = evalStr(SQUANDERED_EXIT_ES);

// ─── Tag definitions ──────────────────────────────────────────────────────────

/**
 * One-sentence definitions for each FlawTag.
 * Record type ensures exhaustiveness — all tags must be covered.
 * All thresholds are interpolated from @/generated/flawThresholds; no literals.
 */
export const TAG_DEFINITIONS: Record<FlawTag, string> = {
  'low-clock': `Played when your clock was under ${LOW_CLOCK_PCT} of your starting time (or under ${LOW_CLOCK_ABS}).`,
  'hasty': `Played in under ${HASTY_PCT} of your starting time (or under ${HASTY_ABS}) while you still had a comfortable clock.`,
  'unrushed': 'You had time and did not rush, yet the move was still a blunder or mistake.',
  'miss': 'Your blunder or mistake came immediately after the opponent\'s own mistake or blunder: they handed you something and you missed it on the very next move.',
  'lucky': 'A blunder the opponent failed to punish: their immediate reply was itself a mistake or blunder, so your eval recovered.',
  'reversed': `You turned a winning game into a losing one: your eval before the move was at least ${WIN_EVAL} (clearly winning) and dropped to ${LOSING_EVAL} or below (clearly losing).`,
  'squandered': `You erased an overwhelming advantage back to roughly even: your eval before the move was at least ${FROM_WIN_EVAL} and dropped to ${SQUANDERED_EXIT_EVAL} or below, but not far enough to be reversed.`,
  'opening': 'The blunder or mistake occurred in the opening phase of the game.',
  'middlegame': 'The blunder or mistake occurred in the middlegame.',
  'endgame': 'The blunder or mistake occurred in the endgame phase of the game.',
};
