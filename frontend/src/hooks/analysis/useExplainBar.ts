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
 * Explain does not navigate to the fork itself (unlike a chip click): the graft
 * effect hands the landing to useExplainLineEntry, which for a missed line shows
 * the fork briefly before playing the better move. The D-07 re-entry path below
 * goes through the same entry so both look identical.
 *
 * Got it deletes the line's whole subtree, so free moves the user played inside
 * the line go with it, exactly like a chip toggle-off.
 */

import { useMemo } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { useTacticLines } from '@/hooks/useLibrary';
import type { NodeId } from '@/hooks/useAnalysisBoard';
import type { FlawMarker } from '@/types/library';
import {
  flawKey,
  forkPlyForOrientation,
  type OpenLine,
  type PendingFlaw,
  type TacticRef,
} from '@/lib/analysisTactics';
import type { EnterExplainLine } from '@/hooks/analysis/useExplainLineEntry';
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
  /** The page's focusedFlaw memo (findFocusedFlaw), the single source for the got-it rule. */
  focusedFlaw: TacticRef | null;
  openLines: Map<string, OpenLine>;
  fastForwardRunning: boolean;

  // ── Board / state setters ─────────────────────────────────────────────
  mainLine: NodeId[];
  goToNode: (id: NodeId, opts?: { silent?: boolean }) => void;
  deleteSubtree: (rootId: NodeId) => void;
  enterExplainLine: EnterExplainLine;
  setPendingFlaw: (flaw: PendingFlaw | null) => void;
  setOpenLines: Dispatch<SetStateAction<Map<string, OpenLine>>>;
}

export interface UseExplainBarResult {
  state: ExplainBarState;
  onExplain: () => void;
  onGotIt: () => void;
}

export function useExplainBar(options: UseExplainBarOptions): UseExplainBarResult {
  const {
    isGameMode,
    gameId,
    flawMarkers,
    landingPly,
    pendingFlaw,
    focusedFlaw,
    openLines,
    fastForwardRunning,
    mainLine,
    goToNode,
    deleteSubtree,
    enterExplainLine,
    setPendingFlaw,
    setOpenLines,
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
        focusedFlaw,
        openLines,
        tacticLines,
      }),
    [isGameMode, fastForwardRunning, flawMarkers, landingPly, pendingFlaw, focusedFlaw, openLines, tacticLines],
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
      const forkNodeId = mainLine[forkPlyForOrientation(existing.ply, existing.orientation)];
      if (forkNodeId === undefined) goToNode(existing.rootNodeId);
      else enterExplainLine(forkNodeId, existing.rootNodeId, existing.orientation);
      return;
    }
    setPendingFlaw({ ...state.flaw, enter: true });
  };

  const onGotIt = (): void => {
    if (state.kind !== 'got-it') return;
    trackFeature('board-tool', { target: 'explain-close' });
    const key = flawKey(state.line);
    // Removes the line's subtree; recovers the cursor to the fork when it was inside.
    deleteSubtree(state.line.rootNodeId);
    setOpenLines((prev) => {
      const next = new Map(prev);
      next.delete(key);
      return next;
    });
    // D-06: back to the flaw move on the main line for both orientations. For an allowed
    // line the recovery already lands there and goToNode bails; main-line nodes are never
    // deleted.
    const flawNodeId = mainLine[state.line.ply];
    if (flawNodeId !== undefined) goToNode(flawNodeId);
  };

  return { state, onExplain, onGotIt };
}
