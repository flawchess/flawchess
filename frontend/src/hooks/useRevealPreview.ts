/**
 * useRevealPreview — the Train reveal's ephemeral engine preview state
 * (SEED-197). A sub-hook of `useTrainRevealTree` so that hook stays small.
 *
 * It owns three things, none of which ever live in the move tree:
 *  - the RESOLVED preview for the shown branch (`preview`): the dimmed engine
 *    continuation at the end of the current leaf (see `lib/trainRevealPreview`);
 *  - the STORED live PVs, one per leaf the engine has reached at
 *    TRAIN_LIVE_ALT_MIN_DEPTH, so stepping away and back shows the refined line
 *    at once;
 *  - the ids of nodes COMMITTED from the preview (`committedIds`), which the
 *    reveal tree excludes from move grading (the user did not play them).
 *
 * Chip seeds are derived each render from the chips and are never stored, so a
 * Move or Game line that arrives late refreshes the preview without touching
 * committed nodes. Nothing is previewed while `active` is false (T-261011-lwy-01).
 */

import { useCallback, useEffect, useMemo, useState } from 'react';

import type { MoveNode, NodeId } from '@/hooks/useAnalysisBoard';
import type { PvLine } from '@/hooks/uciParser';
import {
  buildPreviewSeeds,
  liveCandidate,
  resolvePreview,
  resolvePreviewAnchor,
} from '@/lib/trainRevealPreview';
import type { PreviewLine, RevealPreviewStep } from '@/lib/trainRevealPreview';
import type { ChipGroup, RoleKey } from '@/lib/trainRevealLines';

/** The preview as the UI consumes it. */
export interface RevealPreviewView {
  /** The leaf the preview hangs off (the current node, or the active chip's
   * first-move node at the puzzle position). */
  anchorId: NodeId;
  /** Legal moves to show, at most TRAIN_PREVIEW_MAX_PLIES. The preview carries
   * no eval: the Stockfish row's line 1 shows it (SEED-197 UAT). */
  steps: RevealPreviewStep[];
}

export interface UseRevealPreviewOptions {
  active: boolean;
  /** Resets the keyed state (the tree's focus key: puzzle FEN, null while inactive). */
  resetKey: string | null;
  nodes: Map<NodeId, MoveNode>;
  currentNodeId: NodeId | null;
  activeChip: RoleKey | null;
  linePaths: Partial<Record<RoleKey, NodeId[]>>;
  chips: readonly Pick<ChipGroup, 'key' | 'uci' | 'line'>[];
  /** Staleness-guarded: empty unless the lines belong to the shown position. */
  pvLines: readonly PvLine[];
}

export interface UseRevealPreview {
  preview: RevealPreviewView | null;
  /** Nodes committed from the preview (never graded). */
  committedIds: ReadonlySet<NodeId>;
  /** Mark freshly grafted node ids as committed from the preview. Call in the same
   * event as the board update that grafts them. */
  markCommitted: (ids: readonly NodeId[]) => void;
}

const NO_COMMITTED: ReadonlySet<NodeId> = new Set();
const NO_STORED: ReadonlyMap<NodeId, PreviewLine> = new Map();

interface StoredState {
  key: string | null;
  map: Map<NodeId, PreviewLine>;
}

interface CommittedState {
  key: string | null;
  ids: Set<NodeId>;
}

function samePreviewLine(a: PreviewLine | undefined, b: PreviewLine): boolean {
  return (
    a !== undefined &&
    a.evalCp === b.evalCp &&
    a.evalMate === b.evalMate &&
    a.ucis.join(' ') === b.ucis.join(' ')
  );
}

export function useRevealPreview({
  active,
  resetKey,
  nodes,
  currentNodeId,
  activeChip,
  linePaths,
  chips,
  pvLines,
}: UseRevealPreviewOptions): UseRevealPreview {
  const [storedState, setStoredState] = useState<StoredState>({ key: resetKey, map: new Map() });
  const stored = storedState.key === resetKey ? storedState.map : NO_STORED;

  const seeds = useMemo(() => buildPreviewSeeds(chips, linePaths), [chips, linePaths]);

  const activeChipFirstId = activeChip !== null ? (linePaths[activeChip]?.[0] ?? null) : null;
  const resolved = useMemo(() => {
    if (!active) return null;
    const anchorId = resolvePreviewAnchor({ nodes, currentNodeId, activeChipFirstId });
    if (anchorId === null) return null;
    // Live applies only to the node the engine is actually on; at the puzzle
    // position the anchor is the chip's node, which the engine is not searching.
    const live = anchorId === currentNodeId ? liveCandidate(pvLines) : null;
    return resolvePreview({ nodes, anchorId, live, stored, seeds });
  }, [active, nodes, currentNodeId, activeChipFirstId, pvLines, stored, seeds]);

  // Remember each leaf's refined live line (equality-guarded so a repeat of the
  // same PV does not churn state).
  const storeAnchorId = resolved?.source === 'live' ? resolved.anchorId : null;
  const storeLine = resolved?.source === 'live' ? resolved.line : null;
  useEffect(() => {
    if (storeAnchorId === null || storeLine === null) return;
    setStoredState((prev) => {
      const base = prev.key === resetKey ? prev.map : new Map<NodeId, PreviewLine>();
      if (samePreviewLine(base.get(storeAnchorId), storeLine)) return prev;
      const map = new Map(base);
      map.set(storeAnchorId, storeLine);
      return { key: resetKey, map };
    });
  }, [storeAnchorId, storeLine, resetKey]);

  const preview = useMemo<RevealPreviewView | null>(
    () => (resolved === null ? null : { anchorId: resolved.anchorId, steps: resolved.steps }),
    [resolved],
  );

  // ── Preview-committed nodes ──────────────────────────────────────────────
  // The ids are known when the commit happens (a leaf's preview always grafts
  // brand-new nodes, numbered from the board's `nextId`), so they are recorded in
  // the SAME batch as the board update. Resolving them in a later effect would
  // leave one render where the new node counts as hand-played and the grader
  // persists a badge on it. Ids are monotonic and never reused, so a node deleted
  // and re-played gets a fresh id and is graded again.
  const [committedState, setCommittedState] = useState<CommittedState>({
    key: resetKey,
    ids: new Set(),
  });
  const committedIds = committedState.key === resetKey ? committedState.ids : NO_COMMITTED;

  // WR-03 fix: the keyed state above only hides a previous key's data lazily. When
  // `resetKey` goes fen -> null -> fen (a deactivate/reactivate of the SAME puzzle FEN
  // in one mounted screen) the old key matched again and the previous reveal's
  // committed ids and stored lines came back, while the tree restarted its node ids at
  // 0. Node ids are reused, so a stale committed id silently suppressed grading of an
  // unrelated hand-played node. Replace both states with empty ones as soon as the key
  // changes (including to null), so no state keyed to an older reveal can ever match.
  useEffect(() => {
    setStoredState((prev) =>
      prev.key === resetKey && prev.map.size === 0 ? prev : { key: resetKey, map: new Map() },
    );
    setCommittedState((prev) =>
      prev.key === resetKey && prev.ids.size === 0 ? prev : { key: resetKey, ids: new Set() },
    );
  }, [resetKey]);

  const markCommitted = useCallback(
    (ids: readonly NodeId[]): void => {
      setCommittedState((prev) => {
        const base = prev.key === resetKey ? prev.ids : new Set<NodeId>();
        return { key: resetKey, ids: new Set([...base, ...ids]) };
      });
    },
    [resetKey],
  );

  return { preview, committedIds, markCommitted };
}
