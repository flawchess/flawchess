/**
 * TrainBotStepper — Phase 222: a forward-only step index for the bot
 * onboarding flows (first-session intro, first-reveal walkthrough). This is
 * a CONTROLLED component — the caller owns the step index (`step`) in its
 * own `useState`, because the parent also needs that same number to feed
 * `resolveBubbleState`'s `introStep` and the matching `introCopy`/
 * `walkthroughCopy` resolver. `TrainBotStepper` owns NO copy of its own —
 * it renders whatever `children` the caller passes for the current step.
 *
 * NOT a wrapper around `TrainLineStepper` (RESEARCH Pitfall 4): that
 * component replays SAN moves from a FEN onto the shared board — an
 * entirely different contract with its own prev/next chess-move-stepper
 * testids, which this component must never reuse (see that file for the
 * exact names).
 */
import type { ReactElement, ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';

export interface TrainBotStepperProps {
  /** Total number of steps (e.g. 3 for the intro stepper). */
  stepCount: number;
  /** The currently active step index, owned by the caller. */
  step: number;
  /** Advances the caller's own step state. Not called on the last step —
   * `lastControl` takes over instead. */
  onNext: () => void;
  /** The control(s) rendered in place of the Next button once `step` is the
   * last step (e.g. the guess buttons, or a "Got it" close control). */
  lastControl: ReactNode;
  /** The current step's copy/content. */
  children: ReactNode;
  /**
   * Phase 222 plan 06 (D-24): the Next button's testid, so a second caller
   * (the first-reveal walkthrough) can carry its own distinct testid
   * (`btn-train-bot-walkthrough-next`) instead of colliding with the intro
   * stepper's `btn-train-bot-step-next`. Defaults to the intro stepper's
   * original testid, so that call site is unaffected.
   */
  nextTestId?: string;
}

export function TrainBotStepper({
  stepCount,
  step,
  onNext,
  lastControl,
  children,
  nextTestId = 'btn-train-bot-step-next',
}: TrainBotStepperProps): ReactElement {
  const isLastStep = step >= stepCount - 1;
  return (
    <>
      {children}
      {isLastStep ? (
        lastControl
      ) : (
        <Button
          variant="default"
          className={TRAIN_BUTTON_CLASS}
          data-testid={nextTestId}
          onClick={onNext}
        >
          Next
        </Button>
      )}
    </>
  );
}
