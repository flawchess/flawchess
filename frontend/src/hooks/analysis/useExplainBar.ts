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
 * Two buttons (Phase 245 UAT, replacing the single Explain button and its D-04
 * direction rule): Best opens the MISSED line (undo the mistake, play the
 * better move from ply-1), Punish opens the ALLOWED line (the refutation from the
 * flaw position). Neither navigates to the fork itself (unlike a chip click): the
 * graft effect hands the landing to useExplainLineEntry, which for a missed line
 * shows the fork briefly before playing the better move. The D-07 re-entry path
 * below goes through the same entry so both look identical.
 *
 * Inside a line the bar shows a line stepper (Back/Forward clamped to the line)
 * and Got it; the other line's button is hidden there (no Best/Punish switch).
 * Got it deletes the line's whole subtree, so free moves the user played inside
 * the line go with it, exactly like a chip toggle-off.
 */

import { useMemo } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { useTacticLines } from '@/hooks/useLibrary';
import type { MoveNode, NodeId } from '@/hooks/useAnalysisBoard';
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
  type ExplainOrientation,
} from '@/lib/explainBar';
import { trackFeature } from '@/lib/analytics';
import { unlockAudio } from '@/lib/sounds';

const OPEN_TARGET = { missed: 'explain-best', allowed: 'explain-punish' } as const;

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
  nodes: Map<NodeId, MoveNode>;
  currentNodeId: NodeId | null;
  mainLine: NodeId[];
  goToNode: (id: NodeId) => void;
  goForward: () => void;
  goBack: () => void;
  deleteSubtree: (rootId: NodeId) => void;
  enterExplainLine: EnterExplainLine;
  setPendingFlaw: (flaw: PendingFlaw | null) => void;
  setOpenLines: Dispatch<SetStateAction<Map<string, OpenLine>>>;
}

/** Back/Forward clamped to the open line: Back stops at the fork, Forward starts into the line. */
export interface ExplainLineStepper {
  canBack: boolean;
  canForward: boolean;
  onBack: () => void;
  onForward: () => void;
}

export interface UseExplainBarResult {
  state: ExplainBarState;
  onOpenLine: (orientation: ExplainOrientation) => void;
  onGotIt: () => void;
  stepper: ExplainLineStepper;
}

function hasChild(nodes: Map<NodeId, MoveNode>, id: NodeId | null): boolean {
  for (const node of nodes.values()) if (node.parentId === id) return true;
  return false;
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
    nodes,
    currentNodeId,
    mainLine,
    goToNode,
    goForward,
    goBack,
    deleteSubtree,
    enterExplainLine,
    setPendingFlaw,
    setOpenLines,
  } = options;

  // Only the explain state reads the lines (Best/Punish usability), and only for the
  // landing ply; the got-it state needs none. Same query key as the page's fetchFlaw
  // observer, so the Best/Punish click is a cache hit.
  const linesPly = eligibleExplainMarker(flawMarkers, landingPly) !== null ? landingPly : null;
  const { data: tacticLines } = useTacticLines(gameId, linesPly, isGameMode && linesPly !== null);

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
        tacticLinesPly: linesPly,
      }),
    [isGameMode, fastForwardRunning, flawMarkers, landingPly, pendingFlaw, focusedFlaw, openLines, tacticLines, linesPly],
  );

  /** Open (or re-enter, D-07) the `orientation` line of the flaw at `ply`. */
  const openLine = (ply: number, orientation: ExplainOrientation): void => {
    const existing = openLines.get(flawKey({ ply, orientation }));
    if (existing !== undefined) {
      const forkNodeId = mainLine[forkPlyForOrientation(existing.ply, existing.orientation)];
      if (forkNodeId === undefined) goToNode(existing.rootNodeId);
      else enterExplainLine(forkNodeId, existing.rootNodeId, existing.orientation);
      return;
    }
    // Without the re-entry branch above the graft effect's openLines.has early return
    // would release pendingFlaw without landing in the line.
    setPendingFlaw({ ply, orientation, enter: true });
  };

  /** Delete the line's subtree and forget it; the cursor recovers to the fork when it was inside. */
  const closeLine = (line: OpenLine): void => {
    deleteSubtree(line.rootNodeId);
    setOpenLines((prev) => {
      const next = new Map(prev);
      next.delete(flawKey(line));
      return next;
    });
  };

  const onOpenLine = (orientation: ExplainOrientation): void => {
    // The graft effect's goToNode runs outside the user gesture, so iOS/WebKit
    // needs the audio unlock here.
    unlockAudio();
    // Only the explain state offers line buttons; inside a line (got-it) the other
    // line's button is hidden (Phase 245 UAT).
    if (state.kind !== 'explain' || state.pending !== null || !state.usable[orientation]) return;
    trackFeature('board-tool', { target: OPEN_TARGET[orientation] });
    openLine(state.ply, orientation);
  };

  const onGotIt = (): void => {
    if (state.kind !== 'got-it') return;
    trackFeature('board-tool', { target: 'explain-close' });
    closeLine(state.line);
    // D-06: back to the flaw move on the main line for both orientations. For an allowed
    // line the recovery already lands there and goToNode bails; main-line nodes are never
    // deleted.
    const flawNodeId = mainLine[state.line.ply];
    if (flawNodeId !== undefined) goToNode(flawNodeId);
  };

  // Line stepper (UAT): only meaningful in the got-it state. Move stepping is
  // high-frequency, so it sends no Umami event (frontend CLAUDE.md, D-06).
  const line = state.kind === 'got-it' ? state.line : null;
  const forkNodeId = line !== null ? mainLine[forkPlyForOrientation(line.ply, line.orientation)] : undefined;
  const atFork = forkNodeId !== undefined && currentNodeId === forkNodeId;
  const canForward = useMemo(
    () => line !== null && (atFork || hasChild(nodes, currentNodeId)),
    [line, atFork, nodes, currentNodeId],
  );
  const stepper: ExplainLineStepper = {
    canBack: line !== null && !atFork,
    canForward,
    onBack: () => {
      if (line !== null && !atFork) goBack();
    },
    onForward: () => {
      if (line === null) return;
      // At the fork, goForward would pick the lowest-id PV child, which can belong to
      // another line forking at the same node (missed of P and allowed of P-1 share
      // mainLine[P-1]). Step into THIS line explicitly.
      if (atFork) goToNode(line.rootNodeId);
      else goForward();
    },
  };

  return { state, onOpenLine, onGotIt, stepper };
}
