/**
 * trainBubbleState — resolves which state the single chat-row bubble slot
 * under the board should render. Pure, no React import (mirrors
 * `lib/trainGuessLabels.ts`'s guard-clause-returns convention).
 *
 * One chat-row slot under the board persists through the whole puzzle —
 * guess prompt with buttons -> after the guess the SAME host bubble swaps
 * copy to the move prompt -> while grading "Checking your move…" (or, while
 * the disagreement re-check runs, "Taking a closer look…": the same
 * `grading` state with `recheck: true`) -> the outcome bot's verdict row
 * replaces it when the reveal opens. On the instant (server-graded) path the
 * solve POST round trip shows `submitting`, a copy-less spinner, instead of
 * any grading copy. No layout jump, no vanishing bot. Keeping this
 * resolution out of `TrainSolveScreen` (rather than inlining sibling JSX
 * guard blocks) keeps that component's own branching down.
 *
 * Precedence (highest first): verdict > grading > submitting > move > intro
 * > drop-nudge > prompt. The `intro` state carries a step of the two-bubble
 * first-session intro (welcome, then the closing prompt).
 */

import type { IntroStep } from '@/lib/trainBotCopy';

/** The single chat-row bubble's current state (discriminated union). */
export type TrainBubbleState =
  | { kind: 'verdict' }
  | { kind: 'grading'; recheck: boolean }
  | { kind: 'submitting' }
  | { kind: 'move' }
  | { kind: 'intro'; step: IntroStep }
  | { kind: 'drop-nudge' }
  | { kind: 'prompt' };

/** Inputs `resolveBubbleState` needs — already-computed booleans/values from
 * `TrainSolveScreen`'s own state, never re-derived here. */
export interface ResolveBubbleStateInput {
  /** True once a verdict (`SolveResponse`) has landed for the puzzle on screen. */
  hasVerdict: boolean;
  /** True while the grading engine (and the follow-on solve POST) is in flight. */
  isGrading: boolean;
  /** True while the disagreement re-check runs; only ever true
   * while `isGrading`. Selects the "Taking a closer look…" copy. */
  isRechecking: boolean;
  /** True while the instant solve POST is in flight. No grading
   * copy; the bubble shows a copy-less spinner. Never set together with
   * `isGrading` (the instant path does not grade before the POST). */
  isSubmitting: boolean;
  /** True once the guess has been committed (`guess !== null`). */
  guessMade: boolean;
  /** The active first-session intro-stepper step, or `null` when the intro
   * is not showing (already seen, or a later puzzle). */
  introStep: IntroStep | null;
  /** True for the render(s) following a piece dropped before the guess. */
  nudgeActive: boolean;
}

/**
 * Resolves the bubble's state from already-computed inputs. Guard-clause
 * returns only — no `else`, no nesting — so the precedence chain reads as a
 * flat, ordered list.
 */
export function resolveBubbleState(input: ResolveBubbleStateInput): TrainBubbleState {
  if (input.hasVerdict) return { kind: 'verdict' };
  if (input.isGrading) return { kind: 'grading', recheck: input.isRechecking };
  if (input.isSubmitting) return { kind: 'submitting' };
  if (input.guessMade) return { kind: 'move' };
  if (input.introStep !== null) return { kind: 'intro', step: input.introStep };
  if (input.nudgeActive) return { kind: 'drop-nudge' };
  return { kind: 'prompt' };
}
