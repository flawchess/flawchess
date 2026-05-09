import { useState } from 'react';

export type TabResetApi = {
  gamesOffset: number;
  setGamesOffset: (offset: number) => void;
};

/**
 * Tracks tab transitions to reset cross-tab state (currently: Games tab
 * pagination offset). Behavior preserved from OpeningsPage:
 *  - On tab switch, gamesOffset resets to 0.
 *  - The "set state during render" pattern uses prevTab tracking, matching
 *    the original implementation.
 */
export function useTabReset(
  activeTab: 'explorer' | 'games' | 'stats' | 'insights',
): TabResetApi {
  const [gamesOffset, setGamesOffset] = useState(0);

  // Reset pagination on tab switch (mirrors the prevTab pattern from OpeningsPage)
  const [prevTab, setPrevTab] = useState(activeTab);
  if (activeTab !== prevTab) {
    setPrevTab(activeTab);
    setGamesOffset(0);
  }

  return { gamesOffset, setGamesOffset };
}
