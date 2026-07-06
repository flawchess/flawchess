/**
 * treeCommon — pure, strategy-agnostic tree primitives shared by BOTH
 * `SearchRunner` implementations (`mctsSearch.ts` and
 * `fallbackExpectimax.ts`).
 *
 * Extracted from the two orchestrators (WR-06): these helpers were
 * previously copy-pasted near-verbatim in both files, including the
 * correctness-critical root-relative mate/draw frame (`terminalValue`) —
 * exactly the class of subtle sign logic a future one-sided fix would have
 * silently diverged. The guardrail's ENGINE-06 independence story is the two
 * SEARCH STRATEGIES being distinct (PUCT budget allocation vs. full-width
 * depth-limited walk), not each file owning its own copy of the shared
 * value-frame math. `practicalScore` semantics therefore cannot drift
 * between the runners (D-06): both consume this single implementation.
 *
 * Everything here is pure with respect to the search: no provider calls, no
 * budget or concurrency bookkeeping, no timers.
 */

import { Chess } from 'chess.js';
import type { MoverColor } from '@/lib/liveFlaw';
import { uciToSquares } from '@/lib/sanToSquares';
import type { EngineSnapshot, RankedLine, Side } from './types';
import { type BackupChild, backupExpectation, backupRootMax } from './backup';

/**
 * Neutral expected score (0-1 midpoint): the initial value of an ungraded
 * node and the fallback for a candidate the batched grade() call omitted
 * (should not occur with a well-formed provider).
 */
export const NEUTRAL_EXPECTED_SCORE = 0.5;

/** Root-relative expected score of a drawn terminal (stalemate/insufficient material/threefold/50-move). */
const DRAW_EXPECTED_SCORE = 0.5;

/**
 * The minimal node shape the shared helpers operate over. Each runner's
 * concrete node type extends this with its own strategy-specific fields
 * (e.g. `mctsSearch`'s pending/closure bookkeeping) — the recursive type
 * parameter keeps `children` values typed as the CONCRETE node type.
 */
export interface SearchTreeNode<N extends SearchTreeNode<N>> {
  readonly fen: string;
  readonly side: Side;
  readonly depth: number;
  readonly isRoot: boolean;
  /** The UCI move that produced this node from its parent; null for the root. */
  readonly uci: string | null;
  /** Renormalized Maia prior for this child at its parent (D-02) — root's own value is unused. */
  prior: number;
  /** Root-relative expected score (0-1): leaf estimate until expanded, then the backed-up value. */
  value: number;
  visits: number;
  /** True once fixed as a checkmate/stalemate/draw leaf (Pitfall 6) — never expanded. */
  isTerminal: boolean;
  /** True once this node's children are populated OR it has been permanently closed (terminal/depth-capped). */
  isExpanded: boolean;
  /** White-POV Stockfish eval (cp) at grading time, if available — surfaced on RankedLine. */
  objectiveEvalCp: number | null;
  readonly children: Map<string, N>;
}

/** Side-to-move literal from a FEN's own second field (D-08) — never depth/ply parity (Pitfall 3/4). */
export function fenSide(fen: string): Side {
  return fen.split(' ')[1] === 'b' ? 'b' : 'w';
}

/**
 * Fixed root-relative terminal value (Pitfall 6): checkmate is 1.0 when the
 * checkmated side is NOT `rootMover` (the root player delivered mate), 0.0
 * when it IS; stalemate/insufficient-material/threefold/draw is
 * DRAW_EXPECTED_SCORE. Returns null when `fen` is not a game-over position.
 */
export function terminalValue(fen: string, rootMover: MoverColor): number | null {
  const chess = new Chess(fen);
  if (!chess.isGameOver()) return null;
  if (chess.isCheckmate()) {
    // The side to move in a mated position IS the checkmated side —
    // chess.turn() already knows it; no second FEN parse needed (IN-02).
    const checkmatedSide: MoverColor = chess.turn() === 'w' ? 'white' : 'black';
    return checkmatedSide === rootMover ? 0 : 1;
  }
  return DRAW_EXPECTED_SCORE;
}

/**
 * Applies a UCI move to `fen` and returns the resulting FEN, or null when
 * chess.js rejects the move (illegal in this position, or malformed UCI).
 *
 * WR-07: candidate UCIs come from `policy()` output and
 * `budget.extraRootMoves` — in Phase 154 these are real Maia/Stockfish
 * results crossing a worker boundary, exactly where a stale-FEN race or
 * protocol hiccup can produce a move that is legal in a DIFFERENT position.
 * chess.js's `.move()` THROWS on such input; without this containment one
 * bad candidate rejected the entire SearchRunner promise after budget was
 * partially consumed. Callers skip null (a deterministic drop, not a crash).
 */
export function applyUciMoveFen(fen: string, uci: string): string | null {
  const squares = uciToSquares(uci);
  const chess = new Chess(fen);
  try {
    chess.move({
      from: squares?.from ?? uci.slice(0, 2),
      to: squares?.to ?? uci.slice(2, 4),
      promotion: uci.length > 4 ? uci[4] : undefined,
    });
  } catch {
    return null;
  }
  return chess.fen();
}

/** Recomputes `node.value` from its CURRENT children set (D-01/D-02): max at root, prior-weighted expectation otherwise. */
export function recomputeValue<N extends SearchTreeNode<N>>(node: N): void {
  if (node.children.size === 0) return;
  const backupChildren: BackupChild[] = Array.from(node.children.values()).map((c) => ({
    prior: c.prior,
    value: c.value,
  }));
  node.value = node.isRoot ? backupRootMax(backupChildren) : backupExpectation(backupChildren);
}

/** Most-visited continuation from a root candidate's own subtree (canonical UCI tie-break). */
function buildModalPath<N extends SearchTreeNode<N>>(rootChild: N): string[] {
  const path: string[] = [];
  let node: N | null = rootChild;
  while (node !== null) {
    if (node.uci !== null) path.push(node.uci);
    if (!node.isExpanded || node.children.size === 0) break;
    let best: N | null = null;
    for (const child of node.children.values()) {
      const isBetter =
        best === null ||
        child.visits > best.visits ||
        (child.visits === best.visits && (child.uci ?? '') < (best.uci ?? ''));
      if (isBetter) best = child;
    }
    node = best;
  }
  return path;
}

/** Ranked root candidates by practicalScore descending, canonical-UCI tie-break (ENGINE-01/ENGINE-07). */
function buildRankedLines<N extends SearchTreeNode<N>>(root: N): RankedLine[] {
  const lines: RankedLine[] = [];
  for (const child of root.children.values()) {
    if (child.uci === null) continue; // defensive; every root child has a uci
    lines.push({
      rootMove: child.uci,
      practicalScore: child.value,
      objectiveEvalCp: child.objectiveEvalCp,
      modalPath: buildModalPath(child),
      visits: child.visits,
    });
  }
  lines.sort((a, b) => {
    if (b.practicalScore !== a.practicalScore) return b.practicalScore - a.practicalScore;
    return a.rootMove < b.rootMove ? -1 : a.rootMove > b.rootMove ? 1 : 0;
  });
  return lines;
}

export function buildSnapshot<N extends SearchTreeNode<N>>(
  root: N,
  nodesEvaluated: number,
  budgetExhausted: boolean,
): EngineSnapshot {
  return { rankedLines: buildRankedLines(root), nodesEvaluated, budgetExhausted };
}
