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
  /**
   * IDs of nodes grafted by insertPvLine, ordered from the fork node's first
   * PV move to the last. Empty when no PV is expanded. Cleared by clearPvLine.
   * Ephemeral — not URL-encoded (D-01).
   */
  pvLine: NodeId[];
  rootFen: string;
  nextId: number;
}

/** Public return contract of the hook. */
export interface AnalysisBoardReturn {
  position: string;
  currentNodeId: NodeId | null;
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
  /** Currently expanded PV nodes, ordered from fork's first move to end. */
  pvLine: NodeId[];
  rootFen: string;
  lastMove: { from: string; to: string } | null;
  makeMove: (from: string, to: string) => boolean;
  goBack: () => void;
  goForward: () => void;
  goToNode: (id: NodeId) => void;
  /**
   * goToRoot() — jump to the root position (currentNodeId = null) without
   * altering nodes, mainLine, or rootFen. Used by tactic mode to land the
   * board at the decision position after loadMainLine seeds the stored PV
   * (Phase 139, D-5).
   */
  goToRoot: () => void;
  loadMainLine: (sans: string[], newRootFen: string) => void;
  isOnMainLine: (nodeId: NodeId) => boolean;
  /**
   * insertPvLine(pvSans, forkNodeId) — graft a PV sideline onto the existing
   * node map in a single setState call (L-1/L-7: stateRef only syncs after
   * render; calling makeMove in a loop would graft every PV node onto the same
   * stale parent). Sets pvLine to the new node IDs, leaves mainLine untouched,
   * and parks currentNodeId at forkNodeId (not the first PV move).
   */
  insertPvLine: (pvSans: string[], forkNodeId: NodeId) => void;
  /**
   * playUciLine(uciMoves) — graft a UCI move sequence from currentNodeId as a
   * branch (reusing matching children) and navigate to the last move. Used by the
   * engine-line chips to play the whole line up to the clicked move.
   */
  playUciLine: (uciMoves: string[]) => void;
  /**
   * clearPvLine() — delete all pvLine nodes from the map, empty pvLine, and
   * recover currentNodeId to the nearest ancestor on mainLine.
   */
  clearPvLine: () => void;
  /** isOnPvLine(nodeId) — true iff nodeId was grafted by the last insertPvLine. */
  isOnPvLine: (nodeId: NodeId) => boolean;
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
    pvLine: [],
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
      // When a flaw PV sideline is grafted and the board is parked at its fork node,
      // step INTO the sideline rather than continuing down the main line. The main-line
      // continuation has a lower id (created by loadMainLine) than the grafted PV node
      // (created later by insertPvLine), so findFirstChild would otherwise pick the main
      // line and the open flaw line would feel un-enterable (UAT thl item 4).
      if (prev.pvLine.length > 0) {
        const firstPvId = prev.pvLine[0];
        const firstPvNode = firstPvId !== undefined ? prev.nodes.get(firstPvId) : undefined;
        if (firstPvNode && firstPvNode.parentId === prev.currentNodeId) {
          return { ...prev, currentNodeId: firstPvNode.id };
        }
      }
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
      // Bail when already on this node: returning a fresh state object for a no-op
      // navigation triggers a needless re-render, which can feed render-loop cascades
      // (e.g. the eval-chart syncPly round-trip, FLAWCHESS-7B).
      if (prev.currentNodeId === id) return prev;
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
      pvLine: [],
      rootFen: newRootFen,
      nextId: id,
    });
  }, []);

  /**
   * goToRoot() — jump to the root position (currentNodeId = null) without
   * altering nodes, mainLine, or rootFen. Used by tactic mode (Phase 139,
   * D-5) to land the board at the decision position after loadMainLine seeds
   * the stored PV so the user steps forward toward the punchline.
   */
  const goToRoot = useCallback((): void => {
    setState((prev) => ({ ...prev, currentNodeId: null }));
  }, []);

  /**
   * isOnMainLine(nodeId) — true iff the node was seeded by loadMainLine.
   * Reads from stateRef to avoid stale-closure issues when called from events.
   */
  const isOnMainLine = useCallback((nodeId: NodeId): boolean => {
    return stateRef.current.mainLine.includes(nodeId);
  }, []);

  /**
   * insertPvLine(pvSans, forkNodeId) — graft a PV sideline in ONE setState call.
   *
   * Sequential makeMove calls are forbidden here (L-1/L-7): stateRef.current
   * only syncs to state after the next render, so every makeMove in a loop would
   * read the same stale parent and chain all PV nodes onto forkNodeId. Instead
   * we replicate the loadMainLine batch-build loop but graft onto the existing
   * node map rather than replacing it.
   *
   * After the call: pvLine holds the new PV node IDs, mainLine is untouched,
   * and currentNodeId is parked at forkNodeId (not the first PV move).
   */
  const insertPvLine = useCallback((pvSans: string[], forkNodeId: NodeId): void => {
    setState((prev) => {
      const forkNode = prev.nodes.get(forkNodeId);
      if (!forkNode) return prev; // guard: forkNodeId missing → no-op (T-140-01a)

      const newNodes = new Map(prev.nodes);
      const newPvLine: NodeId[] = [];
      const chess = new Chess(forkNode.fen);
      let prevId: NodeId | null = forkNodeId;
      let id = prev.nextId;

      for (const san of pvSans) {
        const move = chess.move(san);
        if (!move) break; // break on illegal SAN rather than crashing (T-140-01a)
        const node = buildNode(id, move.san, chess.fen(), move.from, move.to, prevId);
        newNodes.set(id, node);
        newPvLine.push(id);
        prevId = id;
        id++;
      }

      return {
        ...prev,
        nodes: newNodes,
        pvLine: newPvLine,
        currentNodeId: forkNodeId, // park at fork, not first PV move
        nextId: id,
      };
    });
  }, []);

  /**
   * clearPvLine() — delete all pvLine nodes from the map, empty pvLine, and
   * recover currentNodeId to the nearest ancestor on mainLine.
   *
   * Uses a functional setState updater matching the goBack() idiom to always
   * act on the latest state. Walks parentId up from currentNodeId until it
   * reaches a mainLine node; falls back to null (root) if none is found.
   */
  const clearPvLine = useCallback((): void => {
    setState((prev) => {
      if (prev.pvLine.length === 0) return prev; // already clear — no-op

      // Recover currentNodeId BEFORE deleting pvLine nodes: walk parentId up
      // through prev.nodes (which still has the pvLine entries) until we reach
      // a mainLine node or root. Using newNodes here would cause dangling
      // lookups since pvLine ids are about to be deleted.
      const mainLineSet = new Set(prev.mainLine);
      let recoveredId: NodeId | null = prev.currentNodeId;
      while (recoveredId !== null && !mainLineSet.has(recoveredId)) {
        const node = prev.nodes.get(recoveredId);
        recoveredId = node?.parentId ?? null;
      }

      const newNodes = new Map(prev.nodes);
      for (const id of prev.pvLine) {
        newNodes.delete(id);
      }

      return {
        ...prev,
        nodes: newNodes,
        pvLine: [],
        currentNodeId: recoveredId,
      };
    });
  }, []);

  /**
   * playUciLine(uciMoves) — graft a sequence of UCI moves from currentNodeId as a
   * branch in ONE setState and navigate to the LAST move.
   *
   * Used by the engine-line move chips: clicking move N in a Stockfish line plays
   * the WHOLE line up to that move from the current anchor, not just the single
   * clicked move (Quick 260628-shc UAT — the old wiring called makeMove(from, to)
   * with just the clicked move, skipping all moves before it).
   *
   * Differences from insertPvLine: it lands on the line's end (not the fork),
   * reuses an existing child when its from/to already matches (so re-clicking the
   * same line doesn't spawn duplicate branches), and does NOT touch pvLine /
   * tactic-overlay state. Like insertPvLine it batch-builds in one setState because
   * stateRef only syncs after render (L-1/L-7).
   */
  const playUciLine = useCallback((uciMoves: string[]): void => {
    if (uciMoves.length === 0) return;
    setState((prev) => {
      const newNodes = new Map(prev.nodes);
      let parentId: NodeId | null = prev.currentNodeId;
      const parentFen =
        parentId !== null ? (newNodes.get(parentId)?.fen ?? prev.rootFen) : prev.rootFen;
      const chess = new Chess(parentFen);
      let id = prev.nextId;
      let landingId: NodeId | null = parentId;

      for (const uci of uciMoves) {
        const from = uci.slice(0, 2);
        const to = uci.slice(2, 4);
        // Engine UCI carries the promotion char (e.g. e7e8q); 'q' is a harmless
        // default for non-promotion moves (chess.js ignores it).
        const promotion = uci.length > 4 ? uci.slice(4, 5) : 'q';
        let move: ReturnType<typeof chess.move>;
        try {
          move = chess.move({ from, to, promotion });
        } catch {
          break; // illegal move → stop grafting (land on what we reached)
        }
        if (!move) break;

        // Reuse an existing child with the same from/to to avoid duplicate branches.
        let child: MoveNode | undefined;
        for (const node of newNodes.values()) {
          if (node.parentId === parentId && node.from === move.from && node.to === move.to) {
            child = node;
            break;
          }
        }
        if (!child) {
          child = buildNode(id, move.san, chess.fen(), move.from, move.to, parentId);
          newNodes.set(id, child);
          id++;
        }
        parentId = child.id;
        landingId = child.id;
      }

      if (landingId === prev.currentNodeId) return prev; // nothing grafted — no-op
      return { ...prev, nodes: newNodes, currentNodeId: landingId, nextId: id };
    });
  }, []);

  /**
   * isOnPvLine(nodeId) — true iff the node was grafted by the last insertPvLine.
   * Reads from stateRef to avoid stale-closure issues (mirrors isOnMainLine).
   */
  const isOnPvLine = useCallback((nodeId: NodeId): boolean => {
    return stateRef.current.pvLine.includes(nodeId);
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
    pvLine: state.pvLine,
    rootFen: state.rootFen,
    lastMove,
    makeMove,
    goBack,
    goForward,
    goToNode,
    goToRoot,
    loadMainLine,
    isOnMainLine,
    insertPvLine,
    playUciLine,
    clearPvLine,
    isOnPvLine,
    containerRef,
  };
}
