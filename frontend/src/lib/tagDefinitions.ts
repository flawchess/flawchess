/**
 * Human-readable definitions for each FlawTag, with thresholds interpolated
 * from flawThresholds.ts (never hardcoded in the sentence literals).
 */

import type { FlawTag } from '@/types/library';
import {
  TIME_PRESSURE_CLOCK_FRACTION,
  TIME_PRESSURE_CLOCK_ABS_SECONDS,
  HASTY_MOVE_FRACTION,
  HASTY_MOVE_ABS_SECONDS,
  RESULT_WIN_THRESHOLD,
  RESULT_DRAW_THRESHOLD,
} from '@/lib/flawThresholds';

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
const WIN_PCT = pct(RESULT_WIN_THRESHOLD);
const DRAW_PCT = pct(RESULT_DRAW_THRESHOLD);

// ─── Tag definitions ──────────────────────────────────────────────────────────

/**
 * One-sentence definitions for each FlawTag.
 * Record type ensures exhaustiveness — all 10 tags must be covered.
 */
export const TAG_DEFINITIONS: Record<FlawTag, string> = {
  'low-clock': `Played when your clock was under ${LOW_CLOCK_PCT} of your starting time (or under ${LOW_CLOCK_ABS}).`,
  'impatient': `Played in under ${HASTY_PCT} of your starting time (or under ${HASTY_ABS}) while you still had a comfortable clock.`,
  'considered': 'A flaw you spent real time on, so not caused by haste or time pressure.',
  'miss': 'You had a strong move available and chose a worse one.',
  'lucky-escape': 'Your opponent let you off the hook right after your slip.',
  'while-ahead': 'A flaw made from a winning position, throwing away part of your lead.',
  'result-changing': `A flaw that flipped your game from winning (over ${WIN_PCT}) or at least drawing (over ${DRAW_PCT}) down to losing.`,
  'opening': 'A flaw in the opening phase of the game.',
  'middlegame': 'A flaw in the middlegame phase.',
  'endgame': 'A flaw in the endgame phase.',
};

// ─── Tag display labels ───────────────────────────────────────────────────────

/**
 * Human-readable bold label for each FlawTag (title-cased, hyphen as space).
 * Used in the popover heading.
 */
export const TAG_LABELS: Record<FlawTag, string> = {
  'low-clock': 'Low clock',
  'impatient': 'Impatient',
  'considered': 'Considered',
  'miss': 'Miss',
  'lucky-escape': 'Lucky escape',
  'while-ahead': 'While ahead',
  'result-changing': 'Result changing',
  'opening': 'Opening',
  'middlegame': 'Middlegame',
  'endgame': 'Endgame',
};
