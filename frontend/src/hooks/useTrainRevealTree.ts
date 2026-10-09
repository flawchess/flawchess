/**
 * useTrainRevealTree — the Train reveal's single move tree (Phase 237, SEED-194).
 *
 * One `useAnalysisBoard` tree holds every chip's line as a pre-loaded ROOT
 * branch (grafted by the non-navigating `graftLine`, so a line that arrives
 * late never yanks the user off the position they are looking at). The hook's
 * own `mainLine` stays empty: which nodes belong to which chip is DERIVED each
 * render by walking each chip's UCI list through the tree, never stored on a
 * node (RESEARCH Pattern 1). That is what lets child reuse, late lines and a
 * hand-played move that matches a line all agree.
 *
 * Chip focus (RESEARCH Pattern 3) is one stored value, `rootFocus` (the chip
 * whose arrow is lit at the puzzle position, or null once the user played a
 * move no chip owns, D-04), plus a derivation: away from the root, the active
 * chip is the owner of the current node.
 *
 * Divergent late lines: in practice lines only ever EXTEND (the best line is
 * the key line, the played line grows from the played move). If a line ever did
 * diverge, the stale continuation simply stays as a free branch; no pruning.
 *
 * T-190-16 / T-237-04: nothing is seeded while `active` is false (the solve
 * verdict has not landed), so the answer lines never exist in the client tree
 * before the verdict.
 *
 * Plan 06 folds the old free-play mode in: ONE Stockfish engine follows the
 * shown position (it feeds the eval bar on every node, the Stockfish row and the
 * board's engine arrows off the known lines, and the move grader), and a move
 * played after the verdict forks a sideline in place. `useTreeMoveGrading` grades
 * those sideline moves.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { RefObject } from 'react';
import { findChildBySquares, useAnalysisBoard } from '@/hooks/useAnalysisBoard';
import type { MoveNode, NodeId } from '@/hooks/useAnalysisBoard';
import type { FlawMarkerEntry } from '@/components/analysis/VariationTree';
import type { SquareMarker } from '@/components/board/ChessBoard';
import { useBoardNavigationInput } from '@/hooks/useBoardNavigationInput';
import type { PvLine } from '@/hooks/uciParser';
import { useStockfishEngine } from '@/hooks/useStockfishEngine';
import { useTreeMoveGrading } from '@/hooks/useTreeMoveGrading';
import type { TreeSeedEval } from '@/hooks/useTreeMoveGrading';
import { useEngineDisplaySettings } from '@/lib/engineSettings';
import type { ExploreMoveSource } from '@/lib/trainTelemetry';
import {
  DEFAULT_ROOT_FOCUS,
  MAX_LINE_PLIES,
  REVEAL_TREE_SNAPSHOT_MAX_PATHS,
  REVEAL_TREE_SNAPSHOT_MAX_PLIES,
  buildRevealTreeSnapshot,
  buildTreeListView,
  classifyTreeNodes,
  nodeUci,
  pathToNode,
  resolveForwardTarget,
  walkLinePath,
} from '@/lib/trainRevealLines';
import type { RevealTreeSnapshot, RoleKey, TreeListView } from '@/lib/trainRevealLines';

/** The eval bar needs only the top line, so the engine runs MultiPV 1 on the
 * known lines (the deepest eval for the same movetime). */
const TRAIN_REVEAL_ONLINE_MULTIPV = 1;

/**
 * Shared empty line list for the "engine has not reached the shown position yet"
 * branch. A fresh `[]` per render would change `pvLines`' identity every render
 * and re-run the board's engine-arrows memo keyed on it. Never mutated.
 */
const NO_PV_LINES: PvLine[] = Object.freeze([] as PvLine[]) as PvLine[];

/** What the tree needs from a chip: its key and the UCI line to pre-load. A
 * `ChipGroup` satisfies it. */
export interface RevealChipLine {
  key: RoleKey;
  lineUcis: readonly string[];
}

/** One user-played move, reported for review telemetry (D-13): a hand-played
 * move that matches an existing node is a board move, not a fork. */
export interface RevealUserMove {
  source: ExploreMoveSource;
  forked: boolean;
}

/** The current position's place on a known line, for the board overlay (the
 * quality highlight on the last move and the blue next-move pointer). Null at
 * the puzzle position and on free (user-played) nodes. */
export interface RevealTreeStepInfo {
  line: RoleKey;
  /** Zero-based index of the shown position's move within the line. */
  index: number;
  lastMoveUci: string;
  nextMoveUci: string | null;
  /** True one move into the line (the quality badge shows for the FIRST move only). */
  isFirstMove: boolean;
}

export interface UseTrainRevealTreeOptions {
  /** The puzzle position: the tree's root. A change re-seeds a fresh tree. */
  startFen: string;
  /** True once the solve verdict has landed. While false nothing is seeded. */
  active: boolean;
  chips: readonly RevealChipLine[];
  /** Fired for every legal user-played move (board drop or engine-line click). */
  onUserMove?: (move: RevealUserMove) => void;
  /** Fired for a deliberate step through the tree (‹ ›, ← →, a list tap). */
  onUserStep?: () => void;
  /** Fired when a chip becomes the focus by a tap or a line-matching move. */
  onChipSelect?: (key: RoleKey) => void;
  /** The board wrapper: arrow keys, Home and the wheel act only while it is
   * mounted and the hook is active, so they never fire before the verdict. */
  navContainerRef?: RefObject<HTMLDivElement | null> | null;
  /**
   * A snapshot to rebuild on top of the seeded lines (the Analyze -> Back
   * restore). Applied once per puzzle position, only while active.
   */
  restored?: RevealTreeSnapshot | null;
  /**
   * The grading engine's verdict for the puzzle position (plus the served vetted
   * list), so a fork from the puzzle position is graded immediately. Null before
   * the verdict or while an instant grade is still pending.
   */
  seedEval?: TreeSeedEval | null;
  /**
   * False keeps the reveal engine off (the Phase 236 instant grade is still
   * pending, so nothing may compete with the phone-accuracy background search).
   */
  engineEnabled?: boolean;
}

/** The reveal engine's reading of the shown position (the eval bar's input). */
export interface RevealEvalReading {
  evalCp: number | null;
  evalMate: number | null;
  depth: number;
}

export interface TrainRevealTree {
  /** FEN of the position the board shows. */
  fen: string;
  nodes: Map<NodeId, MoveNode>;
  currentNodeId: NodeId | null;
  /** The chip lit at the puzzle position; null = no chip (D-04). */
  rootFocus: RoleKey | null;
  /** The chip owning the shown position, or null (no chip / a root fork). */
  activeChip: RoleKey | null;
  /** Node ids along each chip's line, derived from the tree (not stored). */
  linePaths: Partial<Record<RoleKey, NodeId[]>>;
  isAtRoot: boolean;
  /** True away from the known lines (a user-played position). */
  isOffLine: boolean;
  canGoBack: boolean;
  canGoForward: boolean;
  /** The slice of the tree the move list renders. */
  listView: TreeListView;
  stepInfo: RevealTreeStepInfo | null;
  lastMove: { from: string; to: string } | null;
  /** UCIs from the puzzle position to the shown position. */
  currentPathUcis: string[];
  /** Ply offset of the puzzle position (for move numbering). */
  rootPly: number;
  selectChip: (key: RoleKey) => void;
  playMove: (from: string, to: string) => boolean;
  playLine: (uciMoves: readonly string[]) => void;
  goBack: () => void;
  goForward: () => void;
  goToNode: (id: NodeId) => void;
  goToRoot: () => void;
  deleteLine: (rootId: NodeId) => void;
  /** The tree as UCI paths (focus, shown position, free sidelines), for the
   * restored-reveal cache. Read it from an event handler, not during render. */
  snapshot: () => RevealTreeSnapshot;
  /** Staleness-guarded: empty unless the lines belong to the shown position. */
  pvLines: PvLine[];
  isAnalyzing: boolean;
  /** Staleness-guarded engine reading of the shown position (nulls and depth 0
   * until the engine reaches it). */
  evalReading: RevealEvalReading;
  /** Quality marks on the user's own sideline moves, per node. */
  moveListMarkers: Map<NodeId, FlawMarkerEntry>;
  /** Quality badge for the sideline move on the board (empty on the known lines). */
  boardMarkers: SquareMarker[];
  /** Quality-colored last-move highlight for a graded sideline move. */
  lastMoveColor: string | undefined;
}

/** A chip's pre-load line in the value-comparable form the seeding keys on. */
type ChipLineSpec = [key: RoleKey, lineUcis: string[]];

/** Never consulted: `canGoForward` only asks whether a target exists. */
const NO_LAST_CHILDREN: ReadonlyMap<NodeId | null, NodeId> = new Map();

/** Ply offset of a FEN (mirrors Analysis.tsx's `fenToPly`). */
function fenToPly(fen: string): number {
  const parts = fen.split(' ');
  const side = parts[1];
  const fullmove = parts[5];
  if (side === undefined || fullmove === undefined) return 0;
  const ply = (Number(fullmove) - 1) * 2 + (side === 'b' ? 1 : 0);
  return Number.isNaN(ply) ? 0 : ply;
}

/** The chip that owns the shown position (see module docs). */
function deriveActiveChip(
  currentNodeId: NodeId | null,
  rootFocus: RoleKey | null,
  owners: Map<NodeId, RoleKey | null>,
  specs: readonly ChipLineSpec[],
): RoleKey | null {
  if (currentNodeId !== null) return owners.get(currentNodeId) ?? null;
  if (rootFocus === null) return null;
  return specs.some(([key]) => key === rootFocus) ? rootFocus : null;
}

/** Where the shown node sits on its known line, or null at the root / off-line. */
function deriveStepInfo(
  nodes: Map<NodeId, MoveNode>,
  currentNodeId: NodeId | null,
  owners: Map<NodeId, RoleKey | null>,
  linePaths: Partial<Record<RoleKey, NodeId[]>>,
): RevealTreeStepInfo | null {
  if (currentNodeId === null) return null;
  const line = owners.get(currentNodeId) ?? null;
  const node = nodes.get(currentNodeId);
  if (line === null || node === undefined) return null;
  const path = linePaths[line] ?? [];
  const index = path.indexOf(currentNodeId);
  if (index < 0) return null; // a free sideline node hanging off the line
  const nextId = path[index + 1];
  const next = nextId !== undefined ? nodes.get(nextId) : undefined;
  return {
    line,
    index,
    lastMoveUci: nodeUci(node),
    nextMoveUci: next !== undefined ? nodeUci(next) : null,
    isFirstMove: index === 0,
  };
}

export function useTrainRevealTree({
  startFen,
  active,
  chips,
  onUserMove,
  onUserStep,
  onChipSelect,
  navContainerRef = null,
  restored = null,
  seedEval = null,
  engineEnabled = true,
}: UseTrainRevealTreeOptions): TrainRevealTree {
  const board = useAnalysisBoard(startFen);
  const {
    loadMainLine,
    graftLine,
    makeMove: boardMakeMove,
    playUciLine: boardPlayUciLine,
    goBack: boardGoBack,
    goToNode: boardGoToNode,
    goToRoot: boardGoToRoot,
    deleteSubtree: boardDeleteSubtree,
  } = board;
  const { nodes, currentNodeId } = board;

  // The callbacks live in refs synced after commit so every command keeps a
  // stable identity.
  const onUserMoveRef = useRef(onUserMove);
  const onUserStepRef = useRef(onUserStep);
  const onChipSelectRef = useRef(onChipSelect);
  useEffect(() => {
    onUserMoveRef.current = onUserMove;
    onUserStepRef.current = onUserStep;
    onChipSelectRef.current = onChipSelect;
  });

  // The chips' lines as a primitive signature: a new array identity carrying the
  // same lines must not re-run the seeding effect, and a line that grows (a late
  // search result) must.
  const chipsSignature = JSON.stringify(
    chips.map((chip): ChipLineSpec => [chip.key, chip.lineUcis.slice(0, MAX_LINE_PLIES)]),
  );
  const specs = useMemo(() => JSON.parse(chipsSignature) as ChipLineSpec[], [chipsSignature]);

  // The focus is keyed to the puzzle it belongs to (and to being active), so a
  // new puzzle or a deactivation falls back to the default without a reset effect.
  const focusKey = active ? startFen : null;
  const [focusState, setFocusState] = useState<{ key: string | null; focus: RoleKey | null }>({
    key: focusKey,
    focus: DEFAULT_ROOT_FOCUS,
  });
  const rootFocus = focusState.key === focusKey ? focusState.focus : DEFAULT_ROOT_FOCUS;
  const setRootFocus = useCallback(
    (focus: RoleKey | null): void => setFocusState({ key: focusKey, focus }),
    [focusKey],
  );

  // Remember which child was visited last under each parent (null = the root), so
  // › re-enters the branch the user came from. Declared BEFORE the reset effect:
  // both can run in one commit and the reset must clear last.
  const lastChildRef = useRef(new Map<NodeId | null, NodeId>());
  useEffect(() => {
    if (currentNodeId === null) return;
    const node = nodes.get(currentNodeId);
    if (node !== undefined) lastChildRef.current.set(node.parentId, currentNodeId);
  }, [currentNodeId, nodes]);

  // A fresh tree per puzzle, and an empty one while inactive (nothing may linger
  // from a previous reveal). Declared BEFORE the seeding effect: both run in one
  // commit and React applies their setStates in order.
  useEffect(() => {
    lastChildRef.current.clear();
    loadMainLine([], startFen);
  }, [loadMainLine, startFen, active]);

  // Seed every chip's line as a root branch. graftLine is a functional update that
  // never moves the board, so re-running on a grown line only adds the new tail.
  useEffect(() => {
    if (!active) return;
    for (const [, lineUcis] of specs) graftLine(lineUcis, null);
  }, [active, specs, startFen, graftLine]);

  // Restore (Analyze -> Back): graft the saved sidelines and the shown path from the
  // root with the same child-reusing graft as the chip lines, so a game line that
  // arrives later lands on the restored nodes instead of duplicating them. Applied
  // once per puzzle position; the capped, chess.js-guarded replay never throws on
  // a tampered snapshot (T-237-05). Declared AFTER the seeding effect.
  const restoredFenRef = useRef<string | null>(null);
  const [restoreTarget, setRestoreTarget] = useState<string[] | null>(null);
  useEffect(() => {
    if (!active) {
      restoredFenRef.current = null;
      return;
    }
    if (restored === null || restoredFenRef.current === startFen) return;
    restoredFenRef.current = startFen;
    for (const path of restored.sidelinePaths.slice(0, REVEAL_TREE_SNAPSHOT_MAX_PATHS)) {
      graftLine(path.slice(0, REVEAL_TREE_SNAPSHOT_MAX_PLIES), null);
    }
    const target = restored.currentPath.slice(0, REVEAL_TREE_SNAPSHOT_MAX_PLIES);
    graftLine(target, null);
    setRootFocus(restored.rootFocus);
    setRestoreTarget(target);
  }, [active, restored, startFen, graftLine, setRootFocus]);

  // The grafts above and this target land in ONE render (batched effect updates),
  // so the nodes already hold the whole legal path: walk it and park there. A path
  // cut short by an illegal move lands on its longest legal prefix. Silent: a
  // restore is not a user move and must not sound.
  useEffect(() => {
    if (restoreTarget === null) return;
    setRestoreTarget(null);
    const landing = walkLinePath(nodes, restoreTarget).at(-1);
    if (landing !== undefined) boardGoToNode(landing, { silent: true });
  }, [restoreTarget, nodes, boardGoToNode]);

  const linePaths = useMemo(() => {
    const paths: Partial<Record<RoleKey, NodeId[]>> = {};
    for (const [key, lineUcis] of specs) paths[key] = walkLinePath(nodes, lineUcis);
    return paths;
  }, [nodes, specs]);
  const owners = useMemo(() => classifyTreeNodes(nodes, linePaths), [nodes, linePaths]);
  const knownIds = useMemo(
    () => new Set(Object.values(linePaths).flatMap((path) => path ?? [])),
    [linePaths],
  );
  const activeChip = deriveActiveChip(currentNodeId, rootFocus, owners, specs);
  const listView = useMemo(
    () => buildTreeListView(nodes, linePaths, owners, activeChip),
    [nodes, linePaths, owners, activeChip],
  );
  const stepInfo = useMemo(
    () => deriveStepInfo(nodes, currentNodeId, owners, linePaths),
    [nodes, currentNodeId, owners, linePaths],
  );
  const currentPathUcis = useMemo(
    () =>
      pathToNode(nodes, currentNodeId).flatMap((id) => {
        const node = nodes.get(id);
        return node !== undefined ? [nodeUci(node)] : [];
      }),
    [nodes, currentNodeId],
  );
  const canGoForward =
    resolveForwardTarget({
      nodes,
      currentNodeId,
      activeChip,
      linePaths,
      lastChildByParent: NO_LAST_CHILDREN,
    }) !== null;

  // Commands read the latest derived values through a ref synced after commit; they
  // only ever run from event handlers, which fire after the commit.
  const latestRef = useRef({ nodes, currentNodeId, rootFocus, activeChip, linePaths, owners, knownIds });
  useEffect(() => {
    latestRef.current = { nodes, currentNodeId, rootFocus, activeChip, linePaths, owners, knownIds };
  });

  const snapshot = useCallback((): RevealTreeSnapshot => {
    const live = latestRef.current;
    return buildRevealTreeSnapshot(live.nodes, live.currentNodeId, live.linePaths, live.rootFocus);
  }, []);

  const selectChip = useCallback(
    (key: RoleKey): void => {
      // D-01: a chip tap jumps to the puzzle position unless the board is already
      // on that chip's line or a sideline hanging off it (RESEARCH Open Question 2).
      if (latestRef.current.activeChip !== key) boardGoToRoot();
      setRootFocus(key);
      onChipSelectRef.current?.(key);
    },
    [boardGoToRoot, setRootFocus],
  );

  const playMove = useCallback(
    (from: string, to: string): boolean => {
      const { nodes: liveNodes, currentNodeId: liveCurrent, owners: liveOwners } = latestRef.current;
      // Decided BEFORE the move: an existing child is a hand-played line move
      // (a board move, D-13), anything else forks a new node.
      const existing = findChildBySquares(liveNodes, liveCurrent, from, to);
      if (!boardMakeMove(from, to)) return false;
      if (liveCurrent === null) {
        // D-04: a root move onto a chip's first move focuses that chip; any other
        // root move (a new fork, or an earlier free fork) deselects every chip.
        const owner = existing !== undefined ? (liveOwners.get(existing.id) ?? null) : null;
        setRootFocus(owner);
        if (owner !== null) onChipSelectRef.current?.(owner);
      }
      onUserMoveRef.current?.({ source: 'board', forked: existing === undefined });
      return true;
    },
    [boardMakeMove, setRootFocus],
  );

  const playLine = useCallback(
    (uciMoves: readonly string[]): void => {
      if (uciMoves.length === 0) return;
      const { nodes: liveNodes, currentNodeId: liveCurrent } = latestRef.current;
      const known = walkLinePath(liveNodes, uciMoves, liveCurrent).length === uciMoves.length;
      boardPlayUciLine([...uciMoves]);
      onUserMoveRef.current?.({ source: 'engine-line', forked: !known });
    },
    [boardPlayUciLine],
  );

  const goToRoot = useCallback((): void => {
    boardGoToRoot();
    // Rewinding with no chip focused restores the default focus so the puzzle
    // position always shows a lit arrow (RESEARCH A1; one line to flip).
    if (latestRef.current.rootFocus === null) setRootFocus(DEFAULT_ROOT_FOCUS);
  }, [boardGoToRoot, setRootFocus]);

  const goBack = useCallback((): void => {
    const { nodes: liveNodes, currentNodeId: liveCurrent, rootFocus: liveFocus } = latestRef.current;
    if (liveCurrent === null) return;
    boardGoBack();
    if (liveNodes.get(liveCurrent)?.parentId === null && liveFocus === null) {
      setRootFocus(DEFAULT_ROOT_FOCUS); // stepped back onto the puzzle position
    }
    onUserStepRef.current?.();
  }, [boardGoBack, setRootFocus]);

  const goForward = useCallback((): void => {
    const live = latestRef.current;
    const target = resolveForwardTarget({
      nodes: live.nodes,
      currentNodeId: live.currentNodeId,
      activeChip: live.activeChip,
      linePaths: live.linePaths,
      lastChildByParent: lastChildRef.current,
    });
    if (target === null) return;
    boardGoToNode(target);
    onUserStepRef.current?.();
  }, [boardGoToNode]);

  const goToNode = useCallback(
    (id: NodeId): void => {
      const live = latestRef.current;
      // WR-04: tapping the node the board is already on moves nothing, so it must
      // not report a user step either (it inflated review_line_steps and
      // auto-advanced the tour's "stepping" step). goBack/goForward already guard this.
      if (!live.nodes.has(id) || live.currentNodeId === id) return;
      boardGoToNode(id);
      onUserStepRef.current?.();
    },
    [boardGoToNode],
  );

  const deleteLine = useCallback(
    (rootId: NodeId): void => {
      const live = latestRef.current;
      const node = live.nodes.get(rootId);
      if (node === undefined || live.knownIds.has(rootId)) return; // known lines are not closable
      const insideDeleted = pathToNode(live.nodes, live.currentNodeId).includes(rootId);
      boardDeleteSubtree(rootId);
      // Closing the root fork the board sits in lands on the puzzle position with
      // no chip focused; restore the default so an arrow is lit there.
      if (live.rootFocus === null && node.parentId === null && insideDeleted) {
        setRootFocus(DEFAULT_ROOT_FOCUS);
      }
    },
    [boardDeleteSubtree, setRootFocus],
  );

  // ── The one reveal engine ────────────────────────────────────────────────
  // It follows the shown position. MultiPV 1 on the known lines (the eval bar
  // needs one line); off them max(Stockfish lines, Stockfish arrows) so the row
  // shows as many lines and the board draws as many arrows as the settings ask for. Not
  // started lazily: the eval bar needs a search on the known lines anyway, and
  // searching every shown node also fills the eval cache, so a fork from a
  // stepped line position grades. Off while the Phase 236 background grade is
  // pending (`engineEnabled`).
  const isOffLine = currentNodeId !== null && !knownIds.has(currentNodeId);
  const { sfLines, sfArrows } = useEngineDisplaySettings();
  const shownFen = active ? board.position : null;
  const engine = useStockfishEngine({
    fen: shownFen,
    enabled: active && engineEnabled,
    multiPv: isOffLine
      ? Math.max(sfLines, sfArrows)
      : TRAIN_REVEAL_ONLINE_MULTIPV,
  });
  // The hook's `currentFen` lags `fen` by exactly one render (its own documented
  // contract), so an unguarded read would paint the PREVIOUS position's lines
  // and, worse here, grade a move against them.
  const engineIsCurrent = shownFen !== null && engine.currentFen === shownFen;
  const pvLines = engineIsCurrent ? engine.pvLines : NO_PV_LINES;
  const live = useMemo(
    () =>
      engineIsCurrent
        ? { cp: engine.evalCp, mate: engine.evalMate, bestUci: engine.pvLines[0]?.moves[0] ?? null }
        : null,
    [engineIsCurrent, engine.evalCp, engine.evalMate, engine.pvLines],
  );
  const evalReading: RevealEvalReading = {
    evalCp: engineIsCurrent ? engine.evalCp : null,
    evalMate: engineIsCurrent ? engine.evalMate : null,
    depth: engineIsCurrent ? engine.depth : 0,
  };
  const isFreeNode = useCallback((id: NodeId): boolean => !knownIds.has(id), [knownIds]);
  const grading = useTreeMoveGrading({
    startFen,
    resetKey: focusKey,
    nodes,
    currentNodeId,
    fen: shownFen,
    isFreeNode,
    live,
    seedEval,
  });

  // Arrow keys, Home and the wheel act only while active and a board wrapper is
  // mounted, so they never fire before the verdict.
  useBoardNavigationInput({
    containerRefs: active && navContainerRef !== null ? [navContainerRef] : [],
    goBack,
    goForward,
    goHome: goToRoot,
  });

  return {
    fen: board.position,
    nodes,
    currentNodeId,
    rootFocus,
    activeChip,
    linePaths,
    isAtRoot: currentNodeId === null,
    isOffLine,
    canGoBack: currentNodeId !== null,
    canGoForward,
    listView,
    stepInfo,
    lastMove: board.lastMove,
    currentPathUcis,
    rootPly: fenToPly(startFen),
    selectChip,
    playMove,
    playLine,
    goBack,
    goForward,
    goToNode,
    goToRoot,
    deleteLine,
    snapshot,
    pvLines,
    isAnalyzing: engine.isAnalyzing,
    evalReading,
    moveListMarkers: grading.moveListMarkers,
    boardMarkers: grading.boardMarkers,
    lastMoveColor: grading.lastMoveColor,
  };
}
