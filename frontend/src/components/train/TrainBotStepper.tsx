/**
 * TrainBotStepper — a forward-only step index for the bot first-session
 * intro (two bubbles; the reveal tour uses the board overlay instead). This
 * is a CONTROLLED component — the caller owns the step index (`step`) in its
 * own `useState`, because the parent also needs that same number to feed
 * `resolveBubbleState`'s `introStep` and the matching `introCopy` resolver.
 * `TrainBotStepper` owns NO copy of its own — it renders whatever `children`
 * the caller passes for the current step.
 */
import type { ReactElement, ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';

export interface TrainBotStepperProps {
  /** Total number of steps. */
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
  /** The Next button's testid; defaults to `btn-train-bot-step-next`. */
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
