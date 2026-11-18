/**
 * The Today card's start actions, provided by the Train page.
 *
 * The page owns the session loop and the blunder-check host, so the card (and the
 * launcher rows built on it) only call these two actions instead of receiving a prop
 * chain through `TrainStartScreen`. `useTrainTodayActions()` throws outside a provider so a
 * card rendered without the page fails loudly in tests rather than doing nothing.
 */

import { createContext, useContext } from 'react';
import { useTrainProgress } from '@/hooks/useTrainProgress';
import type { TrainModeState } from '@/types/train';

export interface TrainTodayActions {
  /** Enter the puzzle solve loop (Start or Resume). */
  startPuzzles: () => void;
  /** Start or resume a blunder-check drill under Today. */
  startBlunderCheck: () => void;
  /** Puts the feature-discovery dot on the Blunder Check Start (D-21). Absent reads as false. */
  showBlunderCheckRouteDot?: boolean;
}

export const TrainTodayActionsContext = createContext<TrainTodayActions | null>(null);

export function useTrainTodayActions(): TrainTodayActions {
  const actions = useContext(TrainTodayActionsContext);
  if (actions === null) {
    throw new Error('useTrainTodayActions must be used inside a TrainTodayActionsContext provider');
  }
  return actions;
}

/** The primary button on a score screen that hands off to the other mode (D-12). */
export interface ContinueAction {
  label: string;
  testId: string;
  onClick: () => void;
}

type TrainModeKey = 'puzzles' | 'blunder_check';

/** The other mode is still owed today when it is pending or in progress (D-12). */
const OWED_STATES: readonly TrainModeState[] = ['pending', 'in_progress'];

const CONTINUE_COPY: Record<TrainModeKey, { label: string; testId: string }> = {
  puzzles: { label: 'Continue with Puzzles', testId: 'btn-train-continue-puzzles' },
  blunder_check: { label: 'Continue with Blunder Check', testId: 'btn-train-continue-blunder-check' },
};

/**
 * The score screen's "Continue with <other mode>" action, or undefined when there is nothing to
 * hand off to: the other mode is done or off, the progress has not loaded, or the screen is
 * rendered outside the Train page (no actions provider). Read fresh from the progress cache,
 * which both modes invalidate when a session finishes.
 */
export function useContinueAction(other: TrainModeKey): ContinueAction | undefined {
  const actions = useContext(TrainTodayActionsContext);
  const { data: progress } = useTrainProgress();
  if (actions === null || progress === undefined) return undefined;
  if (!OWED_STATES.includes(progress.modes[other].state)) return undefined;
  const copy = CONTINUE_COPY[other];
  return {
    ...copy,
    onClick: other === 'puzzles' ? actions.startPuzzles : actions.startBlunderCheck,
  };
}
