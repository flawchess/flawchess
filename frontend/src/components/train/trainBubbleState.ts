/**
 * trainBubbleState — Phase 222 (D-07): resolves which state the single
 * chat-row bubble slot under the board should render. Pure, no React import
 * (mirrors `lib/trainGuessLabels.ts`'s guard-clause-returns convention).
 *
 * D-07 (LOCKED): one chat-row slot under the board persists through the
 * whole puzzle — guess prompt with buttons -> after the guess the SAME host
 * bubble swaps copy to the move prompt -> while grading "Checking your
 * move…" -> the outcome bot's verdict row replaces it when the reveal
 * opens. No layout jump, no vanishing bot. Extracting this resolution OUT of
 * `TrainSolveScreen` (rather than inlining five sibling JSX guard blocks) is
 * the mechanism that LOWERS the component's own cyclomatic complexity while
 * adding the intro/nudge states — see 222-01-PLAN.md task 1, RESEARCH
 * Finding B / Pattern 2.
 *
 * Precedence (highest first): verdict > grading > move > intro > drop-nudge
 * > prompt. Only `prompt`, `move` and `grading` are reachable from
 * `TrainSolveScreen` after plan 01 — `intro` and `drop-nudge` are wired in
 * plan 04 (their inputs default to `introStep: null` / `nudgeActive: false`
 * until then, which structurally can never win the precedence chain).
 */

import type { IntroStep } from '@/lib/trainBotCopy';

/** The single chat-row bubble's current state (D-07 discriminated union). */
export type TrainBubbleState =
  | { kind: 'verdict' }
  | { kind: 'grading' }
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
  /** True once the guess has been committed (`guess !== null`). */
  guessMade: boolean;
  /** The active first-session intro-stepper step, or `null` when the intro
   * is not showing (already seen, later puzzle, or not yet wired — plan 04). */
  introStep: IntroStep | null;
  /** True for the render(s) following a piece dropped before the guess
   * (not yet wired — plan 04, always `false` until then). */
  nudgeActive: boolean;
}

/**
 * Resolves the bubble's state from already-computed inputs. Guard-clause
 * returns only — no `else`, no nesting — so the precedence chain reads as a
 * flat, ordered list.
 */
export function resolveBubbleState(input: ResolveBubbleStateInput): TrainBubbleState {
  if (input.hasVerdict) return { kind: 'verdict' };
  if (input.isGrading) return { kind: 'grading' };
  if (input.guessMade) return { kind: 'move' };
  if (input.introStep !== null) return { kind: 'intro', step: input.introStep };
  if (input.nudgeActive) return { kind: 'drop-nudge' };
  return { kind: 'prompt' };
}
