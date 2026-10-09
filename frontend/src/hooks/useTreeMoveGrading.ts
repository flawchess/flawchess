/**
 * useTreeMoveGrading — grades the user's own moves on the Train reveal's move
 * tree (Phase 237 plan 06, lifted from the retired free-play hook, Phase 200).
 *
 * Every sideline (free) move is graded with the SAME expected-score pipeline as
 * the solve verdict (`classifyTrainMoveQuality` over `liveFlaw`'s sigmoid): the
 * parent position's completed engine eval vs the child position's, with "was it
 * the engine's own top move" answered from the parent's rank-1 PV. ONE
 * exception (Phase 211, D-06): a non-best ROOT-ply move that matches the SERVED
 * vetted list (`TreeSeedEval.vettedMoves`, the same `SolveResponse.vetted_moves`
 * the reveal's "Also fine" row draws) is badged with that entry's own
 * server-computed quality, never re-derived from evals, so the badge can never
 * contradict the list (SEED-137 case 2). Deliberately NO Maia (Phase 200 UAT):
 * the Train loop never loads the ONNX runtime, so what the Analysis page would
 * call a gem or a great move is labelled plainly `best` here.
 *
 * The caller owns the single reveal engine and hands this hook its live reading
 * for the shown position; the hook caches every shown position's eval (known
 * lines included) so a fork off a stepped line position grades as soon as the
 * move is played.
 */

import { useEffect, useMemo, useState } from 'react';

import type { SquareMarker } from '@/components/board/ChessBoard';
import type { FlawMarkerEntry } from '@/components/analysis/VariationTree';
import type { MoveNode, NodeId } from '@/hooks/useAnalysisBoard';
import { evalToExpectedScore, sideToMoveFromFen, terminalPositionEval } from '@/lib/liveFlaw';
import {
  classifyTrainMoveQuality,
  trainQualityMarker,
  vettedMoveForSquares,
  TRAIN_STEP_HIGHLIGHT,
} from '@/lib/trainArrows';
import type { TrainFineMove, TrainMoveQuality } from '@/lib/trainArrows';

/**
 * FIFO bound on the per-FEN eval cache, mirroring the Analysis page's own
 * `LIVE_EVAL_CACHE_MAX`, so a long session can't grow it without bound. Well
 * above any realistic sideline depth.
 */
export const REVEAL_EVAL_CACHE_MAX = 200;

/** One position's completed engine verdict, cached while the board sits on it
 * so the move OUT of it can be graded once the board has moved on. */
interface TreeEval {
  cp: number | null;
  mate: number | null;
  /** The engine's rank-1 move from this position (UCI), or null when unknown:
   * the "is this the best move" input to `classifyTrainMoveQuality`. */
  bestUci: string | null;
}

/**
 * Phase 211 (D-06, replacing Phase 205's mount-rank seam): the grading engine's
 * seed for the tree, threaded through `TrainSolveScreen`'s `treeSeedEval`.
 * Extends `TreeEval`'s three fields with the SERVED vetted list
 * (`SolveResponse.vetted_moves`, the same entries the reveal's "Also fine" row
 * and green arrows draw), so a move played from the puzzle's ROOT ply that
 * matches a served entry is badged with that entry's own server-computed
 * quality instead of a fresh, independently-searched post-move eval that can
 * disagree with the list (SEED-137 case 2). See `currentQuality`'s root-only
 * branch below. `vettedMoves` is REQUIRED here (unlike the OPTIONAL wire field,
 * which a pre-211 restored verdict genuinely lacks at runtime): the one nullish
 * default that absorbs a missing/older-bundle value lives at
 * `TrainSolveScreen.tsx`'s hoisted `vettedMoves` memo, not here (D-10: a second
 * default would make that one untestable).
 */
export interface TreeSeedEval extends TreeEval {
  vettedMoves: TrainFineMove[];
}

/** The engine's reading of the SHOWN position, or null while the engine has not
 * reached it (staleness-guarded by the caller). */
export interface TreeLiveEval {
  cp: number | null;
  mate: number | null;
  bestUci: string | null;
}

/**
 * Phase 211 (D-06): frozen empty vetted-move array, for referential stability so
 * `currentQuality`'s memo does not re-run every render when no seed is present.
 * Never mutated.
 */
const NO_VETTED_MOVES = Object.freeze<TrainFineMove[]>([]);

export interface UseTreeMoveGradingOptions {
  /** The puzzle position: the root of every line, and the seed's key. */
  startFen: string;
  /**
   * Keys the per-node quality state to the tree it belongs to (the puzzle
   * position while active, else null). A change drops every stored quality,
   * because the tree restarts its node ids at 0 and a stale entry would attach
   * itself to an unrelated new node.
   */
  resetKey: string | null;
  nodes: Map<NodeId, MoveNode>;
  currentNodeId: NodeId | null;
  /** FEN of the shown position, or null while the reveal is inactive. */
  fen: string | null;
  /** True for a user-played (free) node; known-line nodes are not graded here. */
  isFreeNode: (id: NodeId) => boolean;
  live: TreeLiveEval | null;
  /** The grading engine's verdict for `startFen`. Null before the verdict. */
  seedEval: TreeSeedEval | null;
}

export interface TreeMoveGrading {
  /** The move list half of the quality highlighting: one entry per graded node. */
  moveListMarkers: Map<NodeId, FlawMarkerEntry>;
  /** The quality badge for the move that reached the shown position (free nodes only). */
  boardMarkers: SquareMarker[];
  /** Quality-colored last-move highlight, or undefined while ungraded. */
  lastMoveColor: string | undefined;
}

/**
 * The `VariationTree` marker entry for one graded move. Maps the Train quality
 * taxonomy onto the move list's icon slots. An inaccuracy is passed through as
 * `severity: 'inaccuracy'`, but the shared move list draws no glyph for it
 * (D-03, same as the Analysis page); only the board badge shows "?!" (quick
 * 261008-opg). Never sets `gem`/`great`: no Maia runs in the Train loop.
 */
function markerEntryForQuality(quality: TrainMoveQuality): FlawMarkerEntry {
  const base: FlawMarkerEntry = {
    missedMotif: null,
    allowedMotif: null,
    missedDepth: null,
    allowedDepth: null,
    ply: 0,
  };
  if (quality === 'best') return { ...base, best: true };
  if (quality === 'good') return { ...base, good: true };
  return { ...base, severity: quality };
}

/** Insert into a FEN-keyed cache under the shared FIFO bound (Map preserves
 * insertion order, so the first key is the oldest). */
function withCapped<V>(prev: Map<string, V>, key: string, value: V): Map<string, V> {
  const next = new Map(prev);
  next.set(key, value);
  if (next.size > REVEAL_EVAL_CACHE_MAX) {
    const oldest = next.keys().next().value;
    if (oldest !== undefined) next.delete(oldest);
  }
  return next;
}

export function useTreeMoveGrading({
  startFen,
  resetKey,
  nodes,
  currentNodeId,
  fen,
  isFreeNode,
  live,
  seedEval,
}: UseTreeMoveGradingOptions): TreeMoveGrading {
  // ── Per-FEN eval cache ────────────────────────────────────────────────────
  // Every position's completed eval, captured while the board sits on it, so the
  // move OUT of it can be graded once the board has moved on. Held in state (not
  // a ref) so reading it during render is legitimate: same shape and rationale
  // as the Analysis page's `engineEvalByFen`.
  const [evalByFen, setEvalByFen] = useState<Map<string, TreeEval>>(() => new Map());

  const seedCp = seedEval?.cp ?? null;
  const seedMate = seedEval?.mate ?? null;
  const seedBestUci = seedEval?.bestUci ?? null;
  // Phase 211 (D-06): the SERVED vetted list, or the shared frozen empty array
  // when no seed is present yet. Deliberately NOT
  // `seedEval?.vettedMoves ?? NO_VETTED_MOVES` here: `seedEval.vettedMoves` is a
  // REQUIRED field on `TreeSeedEval` (the one nullish default for a missing
  // value lives at the hoisted `vettedMoves` memo in `TrainSolveScreen.tsx`, per
  // D-10; a second default here would make that one untestable).
  const seedVettedMoves = seedEval === null ? NO_VETTED_MOVES : seedEval.vettedMoves;
  useEffect(() => {
    if (seedCp === null && seedMate === null) return;
    setEvalByFen((prev) => {
      const existing = prev.get(startFen);
      if (existing?.cp === seedCp && existing.mate === seedMate && existing.bestUci === seedBestUci) {
        return prev; // unchanged: skip the re-render
      }
      return withCapped(prev, startFen, { cp: seedCp, mate: seedMate, bestUci: seedBestUci });
    });
  }, [startFen, seedCp, seedMate, seedBestUci]);

  const liveCp = live?.cp ?? null;
  const liveMate = live?.mate ?? null;
  const liveBestUci = live?.bestUci ?? null;
  const hasSeed = seedCp !== null || seedMate !== null;
  useEffect(() => {
    if (fen === null) return;
    if (liveCp === null && liveMate === null) return;
    // The reveal engine now also searches the puzzle position (the eval bar needs
    // it on the known lines), but the seed is the grading engine's own deeper
    // verdict for that position: keep it as the parent eval of a root fork, as
    // when the old free-play engine only ever started AFTER the first move.
    if (fen === startFen && hasSeed) return;
    setEvalByFen((prev) => {
      const existing = prev.get(fen);
      if (existing?.cp === liveCp && existing.mate === liveMate && existing.bestUci === liveBestUci) {
        return prev;
      }
      return withCapped(prev, fen, { cp: liveCp, mate: liveMate, bestUci: liveBestUci });
    });
  }, [fen, startFen, hasSeed, liveCp, liveMate, liveBestUci]);

  // ── Live grading of the move that reached the current node ────────────────
  const currentNode = currentNodeId !== null ? (nodes.get(currentNodeId) ?? null) : null;
  const isFree = currentNodeId !== null && isFreeNode(currentNodeId);
  const parentFen = useMemo<string | null>(() => {
    if (currentNode === null) return null;
    if (currentNode.parentId === null) return startFen;
    return nodes.get(currentNode.parentId)?.fen ?? startFen;
  }, [currentNode, nodes, startFen]);

  const currentQuality = useMemo<TrainMoveQuality | null>(() => {
    if (!isFree || currentNode === null || parentFen === null || fen === null) return null;
    const parent = evalByFen.get(parentFen);
    if (parent === undefined || (parent.cp === null && parent.mate === null)) return null;
    // A checkmate/stalemate position makes the engine report an ambiguous
    // `mate 0`; the rules already know the answer, so prefer them (same fix the
    // Analysis page applies: otherwise a mating move grades as a blunder).
    const terminal = terminalPositionEval(fen);
    // Compare on from/to only: the engine's UCI carries a promotion suffix that
    // `MoveNode` does not store, so a full-string compare would call an
    // engine-best promotion a non-best move.
    const isBest =
      parent.bestUci !== null &&
      parent.bestUci.slice(0, 4) === `${currentNode.from}${currentNode.to}`;
    // Phase 211 (D-06, replacing Phase 205's mount-rank lookup): when the played
    // move is the puzzle's ROOT ply (no parent move: `currentNode.parentId ===
    // null`) and it matches a SERVED vetted move, return that entry's own
    // server-computed quality directly. The reveal's "Also fine" row and this
    // badge read the SAME key, so a move the row calls fine can never be badged
    // worse when played (SEED-137 case 2). The badge is deliberately NOT
    // re-derived from evals here: mixing this client engine's parent eval with
    // the server key's deep child eval would create a THIRD grader that agrees
    // with neither side, the trap the retired rank-line mechanism would have
    // become at width 1. Precedence: a terminal position (the rules) wins over
    // the key, and the engine's own top move still reads best, not good: both
    // checked above. Root-only on purpose: below the root, the parent and child
    // evals already come from ONE engine (the reveal engine itself), which is
    // already self-consistent; the key describes the PUZZLE position, not any
    // deeper one.
    if (terminal === null && !isBest && currentNode.parentId === null) {
      const vetted = vettedMoveForSquares(seedVettedMoves, currentNode.from, currentNode.to);
      if (vetted !== null) return vetted.quality;
    }
    const childCp = terminal !== null ? terminal.cp : liveCp;
    const childMate = terminal !== null ? terminal.mate : liveMate;
    if (childCp === null && childMate === null) return null;
    const mover = sideToMoveFromFen(parentFen);
    const esBefore = evalToExpectedScore(parent.cp, parent.mate, mover);
    const esAfter = evalToExpectedScore(childCp, childMate, mover);
    return classifyTrainMoveQuality(esBefore, esAfter, isBest);
  }, [isFree, currentNode, parentFen, fen, evalByFen, liveCp, liveMate, seedVettedMoves]);

  // Persist each graded node's quality so the move-list badge stays on EVERY
  // explored move (not just the current one) and re-showing an earlier move
  // doesn't wait on the engine to re-grade it. Keyed to the tree (`resetKey`).
  const [qualityState, setQualityState] = useState<{
    key: string | null;
    byNode: Map<NodeId, TrainMoveQuality>;
  }>(() => ({ key: resetKey, byNode: new Map() }));
  useEffect(() => {
    if (currentQuality === null || currentNodeId === null) return;
    setQualityState((prev) => {
      const base = prev.key === resetKey ? prev.byNode : new Map<NodeId, TrainMoveQuality>();
      if (prev.key === resetKey && base.get(currentNodeId) === currentQuality) return prev;
      const byNode = new Map(base);
      byNode.set(currentNodeId, currentQuality);
      return { key: resetKey, byNode };
    });
  }, [currentQuality, currentNodeId, resetKey]);
  const qualityByNode = useMemo(
    () => (qualityState.key === resetKey ? qualityState.byNode : new Map<NodeId, TrainMoveQuality>()),
    [qualityState, resetKey],
  );

  const moveListMarkers = useMemo(() => {
    const markers = new Map<NodeId, FlawMarkerEntry>();
    for (const [nodeId, quality] of qualityByNode) {
      if (!nodes.has(nodeId)) continue; // a deleted sideline keeps no badges
      markers.set(nodeId, markerEntryForQuality(quality));
    }
    return markers;
  }, [qualityByNode, nodes]);

  const shownQuality =
    isFree && currentNodeId !== null ? (qualityByNode.get(currentNodeId) ?? currentQuality) : null;
  const boardMarkers = useMemo<SquareMarker[]>(
    () =>
      currentNode !== null && shownQuality !== null
        ? [trainQualityMarker(currentNode.to, shownQuality)]
        : [],
    [currentNode, shownQuality],
  );
  const lastMoveColor = shownQuality !== null ? TRAIN_STEP_HIGHLIGHT[shownQuality] : undefined;

  return { moveListMarkers, boardMarkers, lastMoveColor };
}
