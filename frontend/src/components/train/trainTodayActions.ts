/**
 * The Today card's start actions, provided by the Train page.
 *
 * The page owns the session loop and the blunder-check host, so the card (and the
 * launcher rows built on it) only call these two actions instead of receiving a prop
 * chain through `TrainStartScreen`. `useTrainTodayActions()` throws outside a provider so a
 * card rendered without the page fails loudly in tests rather than doing nothing.
 */

import { createContext, useContext } from 'react';

export interface TrainTodayActions {
  /** Enter the puzzle solve loop (Start or Resume). */
  startPuzzles: () => void;
  /** Start or resume a blunder-check drill under Today. */
  startBlunderCheck: () => void;
}

export const TrainTodayActionsContext = createContext<TrainTodayActions | null>(null);

export function useTrainTodayActions(): TrainTodayActions {
  const actions = useContext(TrainTodayActionsContext);
  if (actions === null) {
    throw new Error('useTrainTodayActions must be used inside a TrainTodayActionsContext provider');
  }
  return actions;
}
