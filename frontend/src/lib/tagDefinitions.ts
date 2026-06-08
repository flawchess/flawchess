/**
 * Human-readable definitions for FlawTags.
 *
 * TAG_DEFINITIONS is rebuilt (Phase 110 Plan 05 D-07) for the TagChip and
 * FlawFilterControl definition popovers: each entry is a one-sentence definition with all
 * numeric thresholds interpolated from @/generated/flawThresholds — no hard-coded
 * percentages anywhere in this file.
 *
 * Every tag surface (chips, Flaw-Stats panel, filter control) renders the raw
 * lowercase-with-dash tag string; there is no title-cased label map (D-07 amendment,
 * Phase 110 UAT).
 */

import type { FlawTag } from '@/types/library';
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

// ─── Precomputed display values ───────────────────────────────────────────────

const LOW_CLOCK_PCT = pct(TIME_PRESSURE_CLOCK_FRACTION);
const LOW_CLOCK_ABS = secs(TIME_PRESSURE_CLOCK_ABS_SECONDS);
const HASTY_PCT = pct(HASTY_MOVE_FRACTION);
const HASTY_ABS = secs(HASTY_MOVE_ABS_SECONDS);
const WIN_PCT = pct(WINNING_LINE_ES);
const LOSING_PCT = pct(LOSING_LINE_ES);
const FROM_WIN_PCT = pct(FROM_WINNING_ES);
const SQUANDERED_EXIT_PCT = pct(SQUANDERED_EXIT_ES);

// ─── Tag definitions ──────────────────────────────────────────────────────────

/**
 * One-sentence definitions for each FlawTag.
 * Record type ensures exhaustiveness — all tags must be covered.
 * All thresholds are interpolated from @/generated/flawThresholds; no literals.
 */
export const TAG_DEFINITIONS: Record<FlawTag, string> = {
  'low-clock': `Played when your clock was under ${LOW_CLOCK_PCT} of your starting time (or under ${LOW_CLOCK_ABS}). A forced time problem.`,
  'hasty': `Played in under ${HASTY_PCT} of your starting time (or under ${HASTY_ABS}) while you still had a comfortable clock. Self-inflicted haste.`,
  'unrushed': 'You had time and did not rush, yet the move was still a blunder or mistake. No time excuse — purely a matter of judgement.',
  'miss': 'Your blunder or mistake came immediately after the opponent\'s own mistake or blunder: they handed you something and you missed it on the very next move.',
  'lucky': 'A blunder the opponent failed to punish: their immediate reply was itself a mistake or blunder, so your Expected Score recovered. The one good-news tag.',
  'reversed': `You turned a winning game into a losing one: your Expected Score before the move was at least ${WIN_PCT} (clearly winning) and dropped to ${LOSING_PCT} or below (clearly losing). A full reversal across equality.`,
  'squandered': `You erased an overwhelming advantage back to roughly even: your Expected Score before the move was at least ${FROM_WIN_PCT} and dropped to ${SQUANDERED_EXIT_PCT} or below, but not far enough to be reversed. The win is gone, the game is still playable.`,
  'opening': 'The blunder or mistake occurred in the opening phase of the game.',
  'middlegame': 'The blunder or mistake occurred in the middlegame (also the default when the phase cannot be determined).',
  'endgame': 'The blunder or mistake occurred in the endgame phase of the game.',
};
