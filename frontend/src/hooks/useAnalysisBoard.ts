/**
 * useAnalysisBoard — Branching move-tree hook for the /analysis page (Phase 137).
 *
 * Divergences from the existing board hooks:
 * - No session-storage persistence (D-01: ephemeral; analysis state lives in URL).
 * - No URL write-back (D-01: read-only entry-point only; URL reading is Analysis.tsx, Phase 138).
 * - No Zobrist hashing or opening lookup.
 * - Mid-line moves fork a new child node rather than truncating the main line (BOARD-01).
 * - Stores full FEN per node for O(1) goToNode — no root replay (BOARD-02).
 * - Container-scoped keyboard handler (same pattern as useTacticLine, not window-level).
 */

import { useRef, useState, useCallback, useEffect } from 'react';
import type { RefObject } from 'react';
import { Chess } from 'chess.js';

// ─── Types ───────────────────────────────────────────────────────────────────

/** Auto-incrementing integer node identifier. */
export type NodeId = number;

/** A single node in the branching move tree. */
export interface MoveNode {
  id: NodeId;
  san: string;          // SAN of the move that reached this position
  fen: string;          // Full FEN of this position (stored, not replayed — O(1) navigation)
  from: string;         // Source square (for board highlighting)
  to: string;           // Target square
  parentId: NodeId | null; // null means the parent is rootFen
}

/** Internal tree state — exported for consumers (e.g. VariationTree). */
export interface AnalysisBoardState {
  nodes: Map<NodeId, MoveNode>;
  currentNodeId: NodeId | null;
  mainLine: NodeId[];
  rootFen: string;
  nextId: number;
}

/** Public return contract of the hook. */
export interface AnalysisBoardReturn {
  position: string;
  currentNodeId: NodeId | null;
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
  rootFen: string;
  lastMove: { from: string; to: string } | null;
  makeMove: (from: string, to: string) => boolean;
  goBack: () => void;
  goForward: () => void;
  goToNode: (id: NodeId) => void;
  loadMainLine: (sans: string[], newRootFen: string) => void;
  isOnMainLine: (nodeId: NodeId) => boolean;
  containerRef: RefObject<HTMLDivElement | null>;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function buildNode(
  id: NodeId,
  san: string,
  fen: string,
  from: string,
  to: string,
  parentId: NodeId | null,
): MoveNode {
  return { id, san, fen, from, to, parentId };
}

function getPosition(s: AnalysisBoardState): string {
  if (s.currentNodeId === null) return s.rootFen;
  const node = s.nodes.get(s.currentNodeId);
  return node ? node.fen : s.rootFen;
}

function getLastMove(s: AnalysisBoardState): { from: string; to: string } | null {
  if (s.currentNodeId === null) return null;
  const node = s.nodes.get(s.currentNodeId);
  return node ? { from: node.from, to: node.to } : null;
}

/**
 * Scan the node map for the first child of `parentId` by insertion order
 * (lowest id wins — ids are auto-incremented at creation time).
 */
function findFirstChild(
  nodes: Map<NodeId, MoveNode>,
  parentId: NodeId | null,
): MoveNode | undefined {
  let firstChild: MoveNode | undefined;
  for (const node of nodes.values()) {
    if (node.parentId === parentId) {
      if (!firstChild || node.id < firstChild.id) {
        firstChild = node;
      }
    }
  }
  return firstChild;
}

function makeInitialState(rootFen: string): AnalysisBoardState {
  return {
    nodes: new Map<NodeId, MoveNode>(),
    currentNodeId: null,
    mainLine: [],
    rootFen,
    nextId: 0,
  };
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useAnalysisBoard(
  initialRootFen: string = STARTING_FEN,
): AnalysisBoardReturn {
  const [state, setState] = useState<AnalysisBoardState>(() =>
    makeInitialState(initialRootFen),
  );

  // Mutable ref synced each render — lets makeMove/isOnMainLine read the latest
  // state synchronously from callbacks without closing over stale values.
  // (Same stale-closure-safe pattern as useTacticLine lines 99-110.)
  const stateRef = useRef(state);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    stateRef.current = state;
  });

  /**
   * makeMove(from, to) — input-agnostic move entry point (BOARD-03).
   * Both drag-drop and click-to-click board input call this.
   * Board wiring is Phase 138; this hook exposes the entry point only.
   *
   * Mid-line fork: the new node is parented to currentNodeId regardless of
   * whether that node already has children. This is the inverse of
   * The opening board hook truncates on mid-line moves — this hook forks instead.
   */
  const makeMove = useCallback((from: string, to: string): boolean => {
    const { currentNodeId, nodes, rootFen, nextId } = stateRef.current;
    const parentFen =
      currentNodeId !== null ? (nodes.get(currentNodeId)?.fen ?? rootFen) : rootFen;

    const chess = new Chess(parentFen);
    let result: ReturnType<typeof chess.move>;
    try {
      result = chess.move({ from, to, promotion: 'q' });
    } catch {
      return false;
    }
    if (!result) return false;

    const newNode = buildNode(
      nextId,
      result.san,
      chess.fen(),
      result.from,
      result.to,
      currentNodeId,
    );

    setState((prev) => {
      const newNodes = new Map(prev.nodes);
      newNodes.set(newNode.id, newNode);
      return { ...prev, nodes: newNodes, currentNodeId: newNode.id, nextId: prev.nextId + 1 };
    });

    return true;
  }, []);

  /**
   * goBack() — retreat to parent; null parent returns to rootFen (BOARD-02).
   * Uses a functional setState updater to always act on the latest state.
   */
  const goBack = useCallback((): void => {
    setState((prev) => {
      if (prev.currentNodeId === null) return prev; // already at root — no-op
      const node = prev.nodes.get(prev.currentNodeId);
      if (!node) return prev;
      return { ...prev, currentNodeId: node.parentId };
    });
  }, []);

  /**
   * goForward() — advance to the first child of currentNodeId in insertion
   * order (lowest id). No-op when the node has no children (BOARD-02).
   */
  const goForward = useCallback((): void => {
    setState((prev) => {
      const child = findFirstChild(prev.nodes, prev.currentNodeId);
      if (!child) return prev;
      return { ...prev, currentNodeId: child.id };
    });
  }, []);

  /**
   * goToNode(id) — O(1) jump: reads nodes.get(id).fen directly, no replay loop.
   * (BOARD-02 / ARCHITECTURE Pattern 3 lines 208-209.)
   */
  const goToNode = useCallback((id: NodeId): void => {
    setState((prev) => {
      if (!prev.nodes.has(id)) return prev;
      return { ...prev, currentNodeId: id };
    });
  }, []);

  /**
   * loadMainLine(sans, newRootFen) — BOARD-04 / D-01 entry-point seeding.
   * Replays each SAN onto a fresh Chess(newRootFen), creates one MoveNode per
   * SAN in sequence, and records their IDs into mainLine. Resets the whole tree.
   * Mirrors useTacticLine's rootFen-start replay (lines 117-136) but builds
   * a branching tree rather than a flat history array.
   */
  const loadMainLine = useCallback((sans: string[], newRootFen: string): void => {
    const newNodes = new Map<NodeId, MoveNode>();
    const newMainLine: NodeId[] = [];
    const chess = new Chess(newRootFen);
    let prevId: NodeId | null = null;
    let id = 0;

    for (const san of sans) {
      // safe: for-of iterates defined SAN strings from the caller
      const move = chess.move(san);
      if (!move) break; // stop on illegal SAN rather than throwing
      const node = buildNode(id, move.san, chess.fen(), move.from, move.to, prevId);
      newNodes.set(id, node);
      newMainLine.push(id);
      prevId = id;
      id++;
    }

    const lastId = newMainLine[newMainLine.length - 1];
    setState({
      nodes: newNodes,
      currentNodeId: lastId !== undefined ? lastId : null,
      mainLine: newMainLine,
      rootFen: newRootFen,
      nextId: id,
    });
  }, []);

  /**
   * isOnMainLine(nodeId) — true iff the node was seeded by loadMainLine.
   * Reads from stateRef to avoid stale-closure issues when called from events.
   */
  const isOnMainLine = useCallback((nodeId: NodeId): boolean => {
    return stateRef.current.mainLine.includes(nodeId);
  }, []);

  // Container-scoped keyboard handler (ArrowLeft = goBack, ArrowRight = goForward).
  // Scoped to containerRef — NOT window — to avoid clashing with page shortcuts.
  // (Mirrors useTacticLine lines 181-197; goBack/goForward are stable callbacks
  // with [] deps, so no stale closure on the handler.)
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const handleKeyDown = (e: KeyboardEvent): void => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        goBack();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        goForward();
      }
    };
    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [goBack, goForward]);

  const position = getPosition(state);
  const lastMove = getLastMove(state);

  return {
    position,
    currentNodeId: state.currentNodeId,
    nodes: state.nodes,
    mainLine: state.mainLine,
    rootFen: state.rootFen,
    lastMove,
    makeMove,
    goBack,
    goForward,
    goToNode,
    loadMainLine,
    isOnMainLine,
    containerRef,
  };
}
