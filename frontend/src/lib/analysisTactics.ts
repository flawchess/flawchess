/**
 * analysisTactics — shared tactic-sideline helpers for the /analysis page
 * cluster.
 *
 * `forkPlyForOrientation`, `flawKey`, `bestSanFromPv` and the `TacticRef`/
 * `OpenLine` types (plus `findFocusedFlaw`, moved here so the Explain bar tests
 * can use the page's exact focus rule) previously existed as up to four independent copies
 * across `Analysis.tsx` and its extracted hooks/components
 * (`useAnalysisBoardArrows.ts`, `useAnalysisRouteSeeding.ts`,
 * `AnalysisTabs.tsx`, `useAnalysisEngineLines.ts`) — each justified at the
 * time as "hooks must not depend on page-level modules," but one copy
 * (`useAnalysisBoardArrows.ts`'s `forkPlyForOrientation`) had already
 * textually diverged from the other three (logically equivalent today, but
 * a silent drift risk the moment the fork rule changes again — this rule has
 * changed before), and
 * `flawKey` is the `openLines` Map key (the `PendingFlaw` type carries the
 * Explain bar's `enter` flag), so three independent copies of a
 * key-format function was a lookup-miss bug waiting to happen. This module
 * is a lib file (not a page or hook), so every reader — page, hook, or
 * component — can import it directly without breaching the "hooks must not
 * import page-level modules" rule; it matches the existing
 * `@/lib/tacticDepth`/`@/lib/tacticArrows` split.
 */

import { Chess } from 'chess.js';
import { uciToSquares } from '@/lib/sanToSquares';
import type { NodeId, MoveNode } from '@/hooks/useAnalysisBoard';

/** A currently-open or pending in-tree tactic sideline. */
export type TacticRef = { ply: number; orientation: 'missed' | 'allowed' };

/**
 * A tactic line awaiting its PV fetch. `enter: true` marks an Explain open (D-05): the
 * graft effect then lands on the first grafted move instead of parking at the fork.
 * Tactic chips and the deep-link auto-open omit it and keep parking at the fork.
 */
export type PendingFlaw = TacticRef & { enter?: boolean };

/** An open tactic PV sideline rooted at a specific mainline node. */
export type OpenLine = { rootNodeId: NodeId; ply: number; orientation: 'missed' | 'allowed' };

/**
 * Main-line ply the tactic PV sideline forks from, by orientation.
 *
 * Missed lines fork at the pre-flaw DECISION board (flawPly-1) and replay the
 * should-have-played PV. Allowed lines fork at the FLAW position itself (flawPly): the
 * sideline begins with the opponent's punishing response, not a replay of the flaw move.
 * The backend's allowed_moves prepends the flaw move at index 0, so allowed PVs grafted
 * here drop that lead-in move (allowed_moves.slice(1)).
 */
export function forkPlyForOrientation(flawPly: number, orientation: 'missed' | 'allowed'): number {
  return orientation === 'allowed' ? flawPly : flawPly - 1;
}

/**
 * Stable key for a tactic line (multi-line state): identifies which
 * flaw a chip / open line belongs to. Used as the openLines Map key and as an
 * activePvKeys entry so VariationTree can read chip "on" state by membership.
 */
export function flawKey(flaw: { ply: number; orientation: 'missed' | 'allowed' }): string {
  return `${flaw.ply}:${flaw.orientation}`;
}

/**
 * The engine's top-line first move (UCI) converted to SAN at `baseFen` — feeds
 * MovesByRatingChart's `bestSan` emphasis. Returns null for no
 * PV yet or an illegal/malformed replay (never throws).
 */
export function bestSanFromPv(baseFen: string, uci: string | null): string | null {
  const squares = uciToSquares(uci);
  if (!squares || !uci) return null;
  try {
    const chess = new Chess(baseFen);
    const move = chess.move({
      from: squares.from,
      to: squares.to,
      promotion: uci.length > 4 ? uci[4] : undefined,
    });
    return move.san;
  } catch {
    return null;
  }
}

/**
 * Find the open (or pending) tactic line the board is currently "in" — extracted to a
 * pure module-scope function (not inlined in a component useMemo) because the React
 * Compiler's memoization-preservation lint cannot analyze this control flow (nested
 * for/while loop with early returns) inline; a plain function called FROM useMemo
 * satisfies it.
 *
 * Checks pendingFlaw first (its fork node always matches BEFORE any previously-focused
 * line would, since handlePvChipClick / the auto-open effect navigate there immediately),
 * then every open line: match by fork-node equality OR subtree containment (walk parentId
 * up from currentNodeId until it reaches the line's rootNodeId).
 */
export function findFocusedFlaw(
  isGameMode: boolean,
  currentNodeId: NodeId | null,
  pendingFlaw: TacticRef | null,
  openLines: Map<string, OpenLine>,
  mainLine: NodeId[],
  nodes: Map<NodeId, MoveNode>,
): TacticRef | null {
  if (!isGameMode || currentNodeId === null) return null;
  if (pendingFlaw != null) {
    const forkNodeId = mainLine[forkPlyForOrientation(pendingFlaw.ply, pendingFlaw.orientation)];
    if (forkNodeId !== undefined && currentNodeId === forkNodeId) return pendingFlaw;
  }
  for (const line of openLines.values()) {
    const forkNodeId = mainLine[forkPlyForOrientation(line.ply, line.orientation)];
    if (forkNodeId !== undefined && currentNodeId === forkNodeId) {
      return { ply: line.ply, orientation: line.orientation };
    }
    if (isNodeInsideSubtree(nodes, currentNodeId, line.rootNodeId)) {
      return { ply: line.ply, orientation: line.orientation };
    }
  }
  return null;
}

/** True iff walking parentId up from `nodeId` reaches `rootId`. */
function isNodeInsideSubtree(
  nodes: Map<NodeId, MoveNode>,
  nodeId: NodeId,
  rootId: NodeId,
): boolean {
  let id: NodeId | null = nodeId;
  while (id !== null) {
    if (id === rootId) return true;
    id = nodes.get(id)?.parentId ?? null;
  }
  return false;
}
