/**
 * useExplainLineEntry — how an Explain click lands in its tactic line (SEED-208, Phase 245 UAT).
 *
 * A MISSED line forks at the pre-flaw position (ply-1), so jumping straight from the flaw
 * move to the line's first move swaps two moves at once and the board reads as a teleport.
 * Instead the board steps back to the fork, pauses EXPLAIN_FORK_PREVIEW_MS so the user sees
 * the position before the mistake, then plays the better move.
 *
 * An ALLOWED line forks at the flaw position itself (the board is already there), so it
 * lands on the refutation immediately.
 *
 * The pending advance is cancelled when the board leaves the fork before it fires (a
 * move-list click, Got it, a Jump run, a new game) and on unmount, so it never yanks the
 * user back into the line.
 */

import { useCallback, useEffect, useRef } from 'react';
import type { NodeId } from '@/hooks/useAnalysisBoard';

/** How long the pre-flaw position stays on the board before the better move plays. */
export const EXPLAIN_FORK_PREVIEW_MS = 800;

export type EnterExplainLine = (
  forkNodeId: NodeId,
  rootNodeId: NodeId,
  orientation: 'missed' | 'allowed',
) => void;

type PendingAdvance = { timerId: ReturnType<typeof setTimeout>; forkNodeId: NodeId };

export function useExplainLineEntry(
  currentNodeId: NodeId | null,
  goToNode: (id: NodeId) => void,
): EnterExplainLine {
  const pending = useRef<PendingAdvance | null>(null);

  const cancel = useCallback((): void => {
    if (pending.current === null) return;
    clearTimeout(pending.current.timerId);
    pending.current = null;
  }, []);

  useEffect(() => cancel, [cancel]);

  useEffect(() => {
    if (pending.current !== null && currentNodeId !== pending.current.forkNodeId) cancel();
  }, [currentNodeId, cancel]);

  return useCallback<EnterExplainLine>(
    (forkNodeId, rootNodeId, orientation) => {
      cancel();
      if (orientation === 'allowed') {
        goToNode(rootNodeId);
        return;
      }
      goToNode(forkNodeId);
      const timerId = setTimeout(() => {
        pending.current = null;
        goToNode(rootNodeId);
      }, EXPLAIN_FORK_PREVIEW_MS);
      pending.current = { timerId, forkNodeId };
    },
    [goToNode, cancel],
  );
}
