/**
 * useExplainBar — state and handlers for the contextual Explain bar (SEED-208).
 *
 * WHY a hook: keeps `Analysis()` from growing (its complexity is an accepted
 * residual); the page makes one call and mounts the presentational
 * `ExplainBar` with the result.
 *
 * WHY a second tactic-lines observer instead of folding the landing ply into
 * the page's `fetchFlaw`: `contextualPending` drives VariationTree's chip
 * spinner, so a prefetch on another ply would spin an unrelated active chip.
 * The second observer shares the `['tactic-lines', gameId, ply]` query key, so
 * the Explain click is a synchronous cache hit (D-11).
 *
 * Explain does NOT navigate to the fork first (unlike a chip click): with the
 * cached data the graft lands in one commit, while a fork navigation would add
 * a second commit, a one-frame back-step and a second move sound.
 */

import { useMemo } from 'react';
import { useTacticLines } from '@/hooks/useLibrary';
import type { NodeId } from '@/hooks/useAnalysisBoard';
import type { FlawMarker } from '@/types/library';
import { flawKey, type OpenLine, type PendingFlaw } from '@/lib/analysisTactics';
import {
  eligibleExplainMarker,
  resolveExplainBarState,
  type ExplainBarState,
} from '@/lib/explainBar';
import { trackFeature } from '@/lib/analytics';
import { unlockAudio } from '@/lib/sounds';

export interface UseExplainBarOptions {
  // ── Route / game data ─────────────────────────────────────────────────
  isGameMode: boolean;
  gameId: number | null;
  flawMarkers: FlawMarker[] | null | undefined;
  /** The page's currentMainlinePly (-1 off the main line). */
  landingPly: number;

  // ── Tactic line state ─────────────────────────────────────────────────
  pendingFlaw: PendingFlaw | null;
  openLines: Map<string, OpenLine>;
  fastForwardRunning: boolean;

  // ── Board / state setters ─────────────────────────────────────────────
  goToNode: (id: NodeId, opts?: { silent?: boolean }) => void;
  setPendingFlaw: (flaw: PendingFlaw | null) => void;
}

export interface UseExplainBarResult {
  state: ExplainBarState;
  onExplain: () => void;
}

export function useExplainBar(options: UseExplainBarOptions): UseExplainBarResult {
  const {
    isGameMode,
    gameId,
    flawMarkers,
    landingPly,
    pendingFlaw,
    openLines,
    fastForwardRunning,
    goToNode,
    setPendingFlaw,
  } = options;

  const eligiblePly = eligibleExplainMarker(flawMarkers, landingPly) !== null ? landingPly : null;
  const { data: tacticLines } = useTacticLines(gameId, eligiblePly, isGameMode && eligiblePly !== null);

  const state = useMemo(
    () =>
      resolveExplainBarState({
        isGameMode,
        fastForwardRunning,
        flawMarkers,
        landingPly,
        pendingFlaw,
        tacticLines,
      }),
    [isGameMode, fastForwardRunning, flawMarkers, landingPly, pendingFlaw, tacticLines],
  );

  const onExplain = (): void => {
    if (state.kind !== 'explain' || state.pending) return;
    // The graft effect's goToNode runs outside the user gesture, so iOS/WebKit
    // needs the audio unlock here.
    unlockAudio();
    trackFeature('board-tool', { target: 'explain-open' });
    // D-07 re-entry: a line with this key is already open (Explain- or chip-opened).
    // Navigate into it instead of grafting a duplicate; without this branch the graft
    // effect's openLines.has early return would leave pendingFlaw stuck.
    const existing = openLines.get(flawKey(state.flaw));
    if (existing !== undefined) {
      goToNode(existing.rootNodeId);
      return;
    }
    setPendingFlaw({ ...state.flaw, enter: true });
  };

  return { state, onExplain };
}
