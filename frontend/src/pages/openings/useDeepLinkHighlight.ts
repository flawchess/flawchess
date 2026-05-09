import { useState, useEffect, useRef } from 'react';
import { HIGHLIGHT_PULSE_DURATION_MS, HIGHLIGHT_PULSE_ITERATIONS } from '@/lib/highlightPulse';
import type { FilterState } from '@/components/filters/FilterPanel';

export type HighlightedMove = { san: string };

export type DeepLinkHighlight = {
  highlightedMove: HighlightedMove | null;
  setHighlightedMove: (m: HighlightedMove | null) => void;
  pulseActive: boolean;
};

/**
 * Owns the deep-link highlight state for the Move Explorer subtab and the
 * pulse-timing state.
 *
 * Behavior preserved from OpeningsPage:
 *  - When `highlightedMove` is set, pulse starts and auto-flips off after the
 *    HIGHLIGHT_PULSE_ITERATIONS * HIGHLIGHT_PULSE_DURATION_MS window.
 *  - Decoupling pulse-active from highlight-active prevents any later React
 *    re-render from re-attaching .animate-arrow-pulse and restarting the CSS
 *    animation.
 *  - Cross-tab nav (leaving explorer subtab) clears the highlight.
 *  - Filter changes AFTER the highlight was set clear it (snapshot pattern).
 */
export function useDeepLinkHighlight(
  activeTab: 'explorer' | 'games' | 'stats' | 'insights',
  filters: FilterState,
): DeepLinkHighlight {
  const [highlightedMove, setHighlightedMove] = useState<HighlightedMove | null>(null);
  const [pulseActive, setPulseActive] = useState(false);

  useEffect(() => {
    if (highlightedMove == null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- behavior preserved from original OpeningsPage; the setState here is the off-edge of the pulse-timer sync, not a render-derived value
      setPulseActive(false);
      return;
    }
    setPulseActive(true);
    const timeoutId = window.setTimeout(
      () => setPulseActive(false),
      HIGHLIGHT_PULSE_ITERATIONS * HIGHLIGHT_PULSE_DURATION_MS,
    );
    return () => window.clearTimeout(timeoutId);
  }, [highlightedMove]);

  // Clear the deep-link highlight when leaving the explorer subtab — the
  // highlighted row only makes sense inside MoveExplorer, so don't carry it
  // across tab navigations. Mirrors the prevTab pattern in useTabReset.
  const [prevTabForHighlight, setPrevTabForHighlight] = useState(activeTab);
  if (activeTab !== prevTabForHighlight) {
    setPrevTabForHighlight(activeTab);
    if (activeTab !== 'explorer' && highlightedMove !== null) {
      setHighlightedMove(null);
    }
  }

  // Clear the deep-link highlight when filters change AFTER the highlight was
  // set. Snapshot the filter identity at the moment the highlight transitions
  // to non-null; later filter changes (with the same highlight active) clear it.
  // Living here (not in MoveExplorer) avoids a false-trigger from the moves-array
  // reference change when the useNextMoves query first resolves on tab mount.
  const filtersAtHighlightRef = useRef<FilterState | null>(null);
  const prevHighlightForFilterClearRef = useRef(highlightedMove);
  useEffect(() => {
    const highlightChanged = prevHighlightForFilterClearRef.current !== highlightedMove;
    prevHighlightForFilterClearRef.current = highlightedMove;
    if (highlightedMove == null) {
      filtersAtHighlightRef.current = null;
      return;
    }
    if (highlightChanged) {
      filtersAtHighlightRef.current = filters;
      return;
    }
    if (filtersAtHighlightRef.current !== null && filtersAtHighlightRef.current !== filters) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- behavior preserved from original OpeningsPage; cross-render filter-change-after-highlight clear depends on a snapshot ref, cannot be derived during render
      setHighlightedMove(null);
    }
  }, [filters, highlightedMove]);

  return { highlightedMove, setHighlightedMove, pulseActive };
}
