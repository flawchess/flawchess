/**
 * Facepalm score units, the stats cut and the shared copy.
 *
 * UNIT: the facepalm score is a 0..1 probability; the UI shows it as a whole percent,
 * rounded DOWN (toFacepalmPct), clamped to FACEPALM_PCT_MIN..FACEPALM_PCT_MAX.
 *
 * The facepalm dimension is a cut (FACEPALM_HIGH_CUTOFF), not a range: a blunder at or
 * above it is a facepalm blunder (isFacepalmBlunder). The former range filter, its
 * presets and its summary are gone (Phase 260 D-10).
 */

import type { FacepalmType } from '@/types/library';

// ─── Named constants (no magic numbers) ─────────────────────────────────────

/** Lower bound of the whole-percent scale toFacepalmPct clamps to. */
export const FACEPALM_PCT_MIN = 0;

/** Upper bound of the whole-percent scale toFacepalmPct clamps to. */
export const FACEPALM_PCT_MAX = 100;

/**
 * The facepalm cut (whole percent, UI cutoff): a blunder scoring at or above it is a facepalm
 * blunder, the Facepalm tag. It is also the stats cut: the Flaws Timeline facepalm band and the
 * Facepalm rows name it. The backend FACEPALM_STATS_MIN is pinned to the same 70% by test.
 */
export const FACEPALM_HIGH_CUTOFF = 70;

/**
 * Below this whole percent a blunder is "hard to spot" in the avatar's game-move line (264
 * D-23). The backend HARD_TO_CATCH_SCORE_BELOW (blunder check's "hard to catch" line) is pinned
 * to the same 50% by test, so the two never disagree in one bubble.
 */
export const FACEPALM_HARD_TO_SPOT_BELOW = 50;

/**
 * 257 D-20: the info popovers of the Facepalm blunders card and the Flaws Timeline facepalm
 * band. What a facepalm blunder is, plus the training pointer ("trains you to spot them", not a
 * promise to reduce them: no training effect is measured). No link, since a hover popover cannot
 * be pinned to click it.
 */
const FACEPALM_DEFINITION = `blunders that should have been easy to see for a player at your level`;
const FACEPALM_TRAINING = 'Blunder Check trains you to spot them before you move.';
export const FACEPALM_CARD_INFO = `Facepalm blunders are ${FACEPALM_DEFINITION}: our model gives them a facepalm score of ${FACEPALM_HIGH_CUTOFF}% or more. ${FACEPALM_TRAINING}`;
/** Shown in place of the comparison when too few of either side's blunders are scored. */
export const FACEPALM_LOW_COVERAGE_NOTE =
  'Not enough blunders in these games have a facepalm score yet to compare you with your opponents.';
export const FACEPALM_TIMELINE_INFO = `The darker band shows facepalm blunders: ${FACEPALM_DEFINITION} (facepalm score of ${FACEPALM_HIGH_CUTOFF}% or more). ${FACEPALM_TRAINING}`;

/** Whose blunder the score is explained for; picks the level word. */
export type FacepalmAudience = 'self' | 'opponent';

const FACEPALM_AUDIENCE_LEVEL: Record<FacepalmAudience, string> = {
  self: 'your',
  opponent: 'their',
};

/**
 * What the facepalm score means, in one sentence. Shared by the score popover
 * (FacepalmExplanation) and any other copy that explains the score, so they never drift.
 * `audience` picks the level word: 'self' (your blunder) or 'opponent' (their blunder).
 */
export function facepalmScoreMeaning(audience: FacepalmAudience = 'self'): string {
  const level = FACEPALM_AUDIENCE_LEVEL[audience];
  return `A high facepalm score tells you the blunder should have been easy to see for a player at ${level} level, a low one that it was probably hard to see.`;
}

/** Multiplier turning a 0..1 score into a percent. */
const FACEPALM_PCT_SCALE = 100;

/**
 * Whole percent shown in the facepalm popover, the eval chart tooltip and the Explain bar for a
 * raw 0..1 score. Rounded DOWN so the shown percent never reads above the score (0.697 shows 69%, below
 * the 70% cut). The backend compares the unrounded score to FACEPALM_STATS_MIN, which
 * agrees with this floor at the cut. Clamped to 0..100.
 */
export function toFacepalmPct(score: number): number {
  const pct = Math.floor(score * FACEPALM_PCT_SCALE);
  return Math.max(FACEPALM_PCT_MIN, Math.min(FACEPALM_PCT_MAX, pct));
}

/**
 * True when a blunder's score makes it a facepalm blunder (the "???" badge): the floored chip
 * percent reaches FACEPALM_HIGH_CUTOFF, the same cut the KPI tile, card and timeline band count.
 */
export function isFacepalmBlunder(score: number | null | undefined): boolean {
  return score != null && toFacepalmPct(score) >= FACEPALM_HIGH_CUTOFF;
}

// ─── Facepalm type copy (257 D-10) ───────────────────────────────────────────

/** 257 D-10: short type name, shown lower-cased in aria-labels and the eval-chart tooltip. */
export const FACEPALM_TYPE_LABEL: Record<FacepalmType, string> = {
  missed_win: 'Missed win',
  allowed_loss: 'Allowed loss',
};

/**
 * The accessible name of a facepalm popover trigger: "Facepalm blunder, facepalm score N%, type" on a facepalm blunder and
 * "Blunder, facepalm score N%, type" on any other scored blunder, so a screen reader never calls an
 * ordinary blunder a facepalm. Shared by the Flaws card chip and the analysis move-list glyph
 * (plan 260-09) so the two never drift.
 */
export function facepalmScoreLabel(score: number, type: FacepalmType): string {
  const pct = toFacepalmPct(score);
  const typeName = FACEPALM_TYPE_LABEL[type].toLowerCase();
  return isFacepalmBlunder(score)
    ? `Facepalm blunder, facepalm score ${pct}%, ${typeName}`
    : `Blunder, facepalm score ${pct}%, ${typeName}`;
}

/**
 * 257 D-10: what the type means, in one mover-neutral sentence (so the opponent variant needs no
 * second wording). No probability words (D-05). Read as `${LABEL}: ${SENTENCE}`.
 */
export const FACEPALM_TYPE_SENTENCE: Record<FacepalmType, string> = {
  missed_win: 'the best move won material or led to checkmate, and was not played.',
  allowed_loss: 'the move gave away material or allowed checkmate.',
};
