/**
 * useTrainRevealTree — the Train reveal's single move tree (Phase 237, SEED-194;
 * reworked by SEED-197 into a first-move + live-preview model).
 *
 * One `useAnalysisBoard` tree. Each chip owns only its FIRST move, grafted as a
 * ROOT node by the non-navigating `graftLine` (so a chip that arrives late never
 * yanks the user off the position they are looking at). Everything after that
 * first move is an ordinary free node. The hook's own `mainLine` stays empty:
 * which nodes belong to which chip is DERIVED each render from the chip's
 * first-move node, never stored on a node (RESEARCH Pattern 1).
 *
 * The engine continuation is NOT in the tree. `useRevealPreview` resolves a dimmed
 * preview at the end of the current leaf (seeded from the chip's graded line,
 * replaced by the live PV once it is deep enough); `goForward` / ArrowRight or
 * `commitPreview(n)` (a tap on preview token n-1) graft its moves as real nodes.
 * Committed nodes never change afterwards and are never graded.
 *
 * Chip focus (RESEARCH Pattern 3) is one stored value, `rootFocus` (the chip
 * whose arrow is lit at the puzzle position, or null once the user played a
 * move no chip owns, D-04), plus a derivation: away from the root, the active
 * chip is the owner of the current node.
 *
 * T-190-16 / T-237-04: nothing is seeded while `active` is false (the solve
 * verdict has not landed), so the answer lines never exist in the client tree
 * before the verdict.
 *
 * ONE Stockfish engine follows the shown position at MultiPV max(Stockfish
 * lines, Stockfish arrows) on every node (it feeds the eval bar, the Stockfish
 * row, the board's engine arrows, the preview and the move grader), and a move
 * played after the verdict forks a sideline in place. `useTreeMoveGrading` grades
 * the moves the user plays, not the ones committed from the preview.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { RefObject } from 'react';
import { findChildBySquares, useAnalysisBoard } from '@/hooks/useAnalysisBoard';
import type { MoveNode, NodeId } from '@/hooks/useAnalysisBoard';
import type { FlawMarkerEntry } from '@/components/analysis/VariationTree';
import type { SquareMarker } from '@/components/board/ChessBoard';
import { useBoardNavigationInput } from '@/hooks/useBoardNavigationInput';
import { useRevealPreview } from '@/hooks/useRevealPreview';
import type { RevealPreviewView } from '@/hooks/useRevealPreview';
import type { PvLine } from '@/hooks/uciParser';
import { useStockfishEngine } from '@/hooks/useStockfishEngine';
import { useTreeMoveGrading } from '@/hooks/useTreeMoveGrading';
import type { TreeSeedEval } from '@/hooks/useTreeMoveGrading';
import { useEngineDisplaySettings } from '@/lib/engineSettings';
import type { ExploreMoveSource } from '@/lib/trainTelemetry';
import {
  DEFAULT_ROOT_FOCUS,
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
import type {
  ChipGroup,
  RevealTreeSnapshot,
  RoleKey,
  TreeListView,
} from '@/lib/trainRevealLines';

/**
 * Shared empty line list for the "engine has not reached the shown position yet"
 * branch. A fresh `[]` per render would change `pvLines`' identity every render
 * and re-run the board's engine-arrows memo keyed on it. Never mutated.
 */
const NO_PV_LINES: PvLine[] = Object.freeze([] as PvLine[]) as PvLine[];

/** No MultiPV floor: the reveal engine runs the settings width. */
const NO_MULTIPV_FLOOR = 0;

/** What the tree needs from a chip: its key, its first move (the only node the
 * tree seeds) and its graded line (which seeds the preview). A `ChipGroup`
 * satisfies it. */
export type RevealChipLine = Pick<ChipGroup, 'key' | 'uci' | 'line'>;

/** One user-played move, reported for review telemetry (D-13): a hand-played
 * move that matches an existing node is a board move, not a fork. */
export interface RevealUserMove {
  source: ExploreMoveSource;
  forked: boolean;
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
  /**
   * A MultiPV floor applied only while the shown node is the puzzle position
   * (quick 261010-e5l). The Train screen passes 4 for a soft puzzle so the root
   * can offer live good-move alternatives; default none.
   */
  rootMinMultiPv?: number;
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
  canGoBack: boolean;
  canGoForward: boolean;
  /** The slice of the tree the move list renders. */
  listView: TreeListView;
  /**
   * The dimmed engine preview at the end of the shown branch (null when the shown
   * node has children, at a finished game, or before the verdict). Anchored at the
   * shown node, or at the active chip's first-move node at the puzzle position.
   */
  preview: RevealPreviewView | null;
  /**
   * The chip whose first move the shown node is (and that move's UCI), else null.
   * Only a chip's first move carries the chip quality badge and highlight.
   */
  chipMove: { line: RoleKey; uci: string } | null;
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
  /**
   * Commit the first `plies` moves of the shown preview as real tree nodes and land
   * on the last one (a tap on preview token `plies - 1`). At the puzzle position the
   * chip's first move is played first. Not graded, not a fork.
   */
  commitPreview: (plies: number) => void;
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

/** A chip's first move in the value-comparable form the seeding keys on. The
 * graded line is deliberately not part of it: a late line must not re-run the
 * graft (it only refreshes the preview). */
type ChipLineSpec = [key: RoleKey, uci: string];

/** Never consulted: `canGoForward` only asks whether a target exists. */
const NO_LAST_CHILDREN: ReadonlyMap<NodeId | null, NodeId> = new Map();

/** Ply offset of a FEN (mirrors Analysis.tsx's `fenToPly`). */
export function fenToPly(fen: string): number {
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

/** The chip whose first-move node `currentNodeId` is, or null. */
function deriveChipMove(
  nodes: Map<NodeId, MoveNode>,
  currentNodeId: NodeId | null,
  linePaths: Partial<Record<RoleKey, NodeId[]>>,
): { line: RoleKey; uci: string } | null {
  const node = currentNodeId !== null ? nodes.get(currentNodeId) : undefined;
  if (currentNodeId === null || node === undefined) return null;
  for (const [key, path] of Object.entries(linePaths) as [RoleKey, NodeId[] | undefined][]) {
    if (path?.[0] === currentNodeId) return { line: key, uci: nodeUci(node) };
  }
  return null;
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
  rootMinMultiPv = NO_MULTIPV_FLOOR,
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

  // The chips' first moves as a primitive signature: a new array identity carrying
  // the same moves must not re-run the seeding effect, and a line that arrives or
  // grows (a late search result) must not either (it only changes the preview).
  const chipsSignature = JSON.stringify(chips.map((chip): ChipLineSpec => [chip.key, chip.uci]));
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

  // Seed every chip's FIRST move as a root node. graftLine is a functional update
  // that never moves the board, so a chip arriving late lands in place.
  useEffect(() => {
    if (!active) return;
    for (const [, uci] of specs) graftLine([uci], null);
  }, [active, specs, startFen, graftLine]);

  // Restore (Analyze -> Back): graft the saved sidelines and the shown path from the
  // root with the same child-reusing graft as the chip lines, so a game line that
  // arrives later lands on the restored nodes instead of duplicating them. Applied
  // once per puzzle position; the capped, chess.js-guarded replay never throws on
  // a tampered snapshot (T-237-05). Declared AFTER the seeding effect.
  const restoredFenRef = useRef<string | null>(null);
  const [restoreTarget, setRestoreTarget] = useState<string[] | null>(null);
  // WR-02: the paths of the preview-committed nodes, resolved to ids (and re-marked
  // never-graded) once the grafted nodes exist, in the effect after useRevealPreview.
  const [restoreCommitted, setRestoreCommitted] = useState<string[][] | null>(null);
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
    setRestoreCommitted(restored.committedPaths ?? null);
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
    for (const [key, uci] of specs) paths[key] = walkLinePath(nodes, [uci]);
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
  const chipMove = useMemo(
    () => deriveChipMove(nodes, currentNodeId, linePaths),
    [nodes, currentNodeId, linePaths],
  );
  const currentPathUcis = useMemo(
    () =>
      pathToNode(nodes, currentNodeId).flatMap((id) => {
        const node = nodes.get(id);
        return node !== undefined ? [nodeUci(node)] : [];
      }),
    [nodes, currentNodeId],
  );
  // ── The one reveal engine ────────────────────────────────────────────────
  // It follows the shown position and runs max(Stockfish lines, Stockfish
  // arrows) everywhere: the row shows that many lines, the board draws that many
  // arrows and the preview takes its live PV from the top line. At a soft
  // puzzle's root the caller's `rootMinMultiPv` floor widens the search to best
  // + 3 so the board can offer live good-move alternatives; the accepted cost
  // is a slightly shallower root top line within the same movetime. Not started
  // lazily: the eval bar and the preview need a search on every shown node, and
  // searching it also fills the eval cache, so a fork from it grades. Off while
  // the Phase 236 background grade is pending (`engineEnabled`).
  const { sfLines, sfArrows } = useEngineDisplaySettings();
  const shownFen = active ? board.position : null;
  const multiPvFloor = currentNodeId === null ? rootMinMultiPv : NO_MULTIPV_FLOOR;
  const engine = useStockfishEngine({
    fen: shownFen,
    enabled: active && engineEnabled,
    multiPv: Math.max(sfLines, sfArrows, multiPvFloor),
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
  const { preview, committedIds, markCommitted } = useRevealPreview({
    active,
    resetKey: focusKey,
    nodes,
    currentNodeId,
    activeChip,
    linePaths,
    chips,
    pvLines,
  });
  // WR-02 fix: a restore regrafts the committed continuations as plain nodes with
  // fresh ids, so the node-id based committed set was lost across Analyze -> Back and
  // every engine move became "free" (graded, badged) as soon as the user stepped onto
  // it. Re-resolve the saved paths against the regrafted tree and mark them again.
  // Same render as the landing effect above: the nodes already hold the grafts. A
  // path cut short by an illegal move, or over the ply cap, marks nothing.
  useEffect(() => {
    if (restoreCommitted === null) return;
    setRestoreCommitted(null);
    const ids: NodeId[] = [];
    for (const path of restoreCommitted.slice(0, REVEAL_TREE_SNAPSHOT_MAX_PATHS)) {
      if (path.length > REVEAL_TREE_SNAPSHOT_MAX_PLIES) continue;
      const walked = walkLinePath(nodes, path);
      const id = walked.at(-1);
      if (id !== undefined && walked.length === path.length) ids.push(id);
    }
    if (ids.length > 0) markCommitted(ids);
  }, [restoreCommitted, nodes, markCommitted]);
  // The user's own moves are graded; a chip's first move keeps its served quality
  // and a node committed from the preview is the engine's move, never graded
  // (SEED-197, CONTEXT "Grading of preview-committed moves").
  const isFreeNode = useCallback(
    (id: NodeId): boolean => !knownIds.has(id) && !committedIds.has(id),
    [knownIds, committedIds],
  );
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

  // Forward is possible through an existing node, or by committing the preview
  // that hangs off the shown node.
  const canGoForward =
    resolveForwardTarget({
      nodes,
      currentNodeId,
      activeChip,
      linePaths,
      lastChildByParent: NO_LAST_CHILDREN,
    }) !== null ||
    (preview !== null && preview.anchorId === currentNodeId && preview.steps.length > 0);

  // Commands read the latest derived values through a ref synced after commit; they
  // only ever run from event handlers, which fire after the commit.
  const latestRef = useRef({
    nodes,
    currentNodeId,
    rootFocus,
    activeChip,
    linePaths,
    owners,
    knownIds,
    preview,
    committedIds,
    nextId: board.nextId,
  });
  useEffect(() => {
    latestRef.current = {
      nodes,
      currentNodeId,
      rootFocus,
      activeChip,
      linePaths,
      owners,
      knownIds,
      preview,
      committedIds,
      nextId: board.nextId,
    };
  });

  const snapshot = useCallback((): RevealTreeSnapshot => {
    const live = latestRef.current;
    return buildRevealTreeSnapshot(
      live.nodes,
      live.currentNodeId,
      live.linePaths,
      live.rootFocus,
      live.committedIds,
    );
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
      const {
        nodes: liveNodes,
        currentNodeId: liveCurrent,
        owners: liveOwners,
        preview: livePreview,
      } = latestRef.current;
      // Decided BEFORE the move: an existing child is a hand-played line move
      // (a board move, D-13), and so is the engine preview's own next move (what
      // the forward button would commit); anything else forks a new node.
      const existing = findChildBySquares(liveNodes, liveCurrent, from, to);
      const nextStep = livePreview?.anchorId === liveCurrent ? livePreview?.steps[0] : undefined;
      const followsPreview = nextStep !== undefined && nextStep.uci.slice(0, 4) === from + to;
      if (!boardMakeMove(from, to)) return false;
      if (liveCurrent === null) {
        // D-04: a root move onto a chip's first move focuses that chip; any other
        // root move (a new fork, or an earlier free fork) deselects every chip.
        const owner = existing !== undefined ? (liveOwners.get(existing.id) ?? null) : null;
        setRootFocus(owner);
        if (owner !== null) onChipSelectRef.current?.(owner);
      }
      onUserMoveRef.current?.({ source: 'board', forked: existing === undefined && !followsPreview });
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

  // WR-01: the first id NOT yet consumed once the commit(s) queued in the current
  // event have been applied. `latestRef` only syncs after a render, so a second
  // commit in the same event reads the SAME nextId / preview / nodes as the first.
  // Its stale steps replay from the new current node, where the mover's from-square
  // is already vacated, so the board grafts nothing, but the predicted ids
  // (liveNextId + i) would still have been marked committed: ids that the NEXT
  // hand-played node gets, silently exempting it from grading. 0 = no commit pending.
  const pendingNextIdRef = useRef(0);

  const commitPreview = useCallback(
    (plies: number): void => {
      const {
        preview: shown,
        nodes: liveNodes,
        currentNodeId: liveCurrent,
        nextId: liveNextId,
      } = latestRef.current;
      if (shown === null || plies < 1) return;
      // WR-01 guard: the ref has not seen the previous commit of this event yet, so
      // everything read from it is stale. Ignore the repeat; the first one stands.
      if (liveNextId < pendingNextIdRef.current) return;
      const anchor = liveNodes.get(shown.anchorId);
      if (anchor === undefined) return;
      // A preview is only committable from where it hangs: the shown node, or at
      // the puzzle position the chip's root-level first move (played first).
      const atAnchor = liveCurrent === shown.anchorId;
      const fromRoot = liveCurrent === null && anchor.parentId === null;
      if (!atAnchor && !fromRoot) return;
      const stepUcis = shown.steps.slice(0, plies).map((step) => step.uci);
      boardPlayUciLine(fromRoot ? [nodeUci(anchor), ...stepUcis] : stepUcis);
      // A leaf's preview grafts brand-new nodes, numbered from the board's next id.
      markCommitted(stepUcis.map((_, i) => liveNextId + i));
      pendingNextIdRef.current = liveNextId + stepUcis.length;
      // The board update is applied by the end of the current event (a discrete
      // event flushes synchronously), so the next event always reads a fresh ref.
      queueMicrotask(() => {
        pendingNextIdRef.current = 0;
      });
      onUserStepRef.current?.(); // stepping, not a move: no onUserMove, no fork (A4)
    },
    [boardPlayUciLine, markCommitted],
  );

  const goForward = useCallback((): void => {
    const live = latestRef.current;
    const target = resolveForwardTarget({
      nodes: live.nodes,
      currentNodeId: live.currentNodeId,
      activeChip: live.activeChip,
      linePaths: live.linePaths,
      lastChildByParent: lastChildRef.current,
    });
    if (target === null) {
      commitPreview(1); // a leaf: the preview's next move becomes a real node
      return;
    }
    boardGoToNode(target);
    onUserStepRef.current?.();
  }, [boardGoToNode, commitPreview]);

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
    canGoBack: currentNodeId !== null,
    canGoForward,
    listView,
    preview,
    chipMove,
    lastMove: board.lastMove,
    currentPathUcis,
    rootPly: fenToPly(startFen),
    selectChip,
    playMove,
    playLine,
    goBack,
    goForward,
    commitPreview,
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
