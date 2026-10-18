/**
 * Shared "only one good move vs several" guess vocabulary.
 *
 * Single source of truth for the exact wording so `TrainSolveScreen`'s guess
 * buttons and the move prompt's echo can never drift apart. The reveal does
 * not read these: its verdict sentence (`verdictClauseParts` in
 * `trainBotCopy.ts`) states the position fact itself.
 *
 * The short button-label form is "Only one" / "Several" (`GUESS_LABELS`) —
 * the old "One critical move" / "Several fine moves" pair read as two full
 * sentences stacked in a 375px button row. `GUESS_CALL_LABELS` is a SEPARATE
 * longer map, not an overload of `GUESS_LABELS`.
 */

export type Guess = 'critical' | 'several';

/** Short guess-button labels. Read by `TrainSolveScreen`'s guess pair. */
export const GUESS_LABELS: Record<Guess, string> = {
  critical: 'Only one',
  several: 'Several',
};

/** Long call-form echoed by the move prompt after the guess ("Your call:
 * only one good move. Now play a move for white.") — "Only one" read alone
 * was unreadable out of context. */
export const GUESS_CALL_LABELS: Record<Guess, string> = {
  critical: 'only one good move',
  several: 'several good moves',
};
