/**
 * Analysis — standalone /analysis page.
 *
 * Default export (required by React.lazy — every other page uses a named export;
 * this is the intentional divergence, see RESEARCH.md Pitfall 1).
 *
 * Composes:
 *   useAnalysisBoard  — branching move-tree board state
 *   useStockfishEngine — UCI WASM engine state
 *   EvalBar / EngineLines / VariationTree — analysis display components
 *   ChessBoard / BoardControls — board interaction
 *   EvalChart — below-board eval chart with slider (Phase 140 game mode)
 *
 * Security:
 *   T-138-01: FEN-guard on ?fen= param — malformed FEN degrades to STARTING_FEN.
 *   T-140-02a: NaN-guard on ?game_id= / ?ply= params — malformed → null → isGameMode false.
 *   T-140-02b: L-8 guard on mainLine[ply] accesses — out-of-bounds → undefined → no-op.
 *
 * Engine: on by default (D-06); "Loading engine…" shown in eval area while WASM inits;
 *   board stays interactive throughout (SC#3).
 *
 * Modes: ?fen= seeds free play; ?game_id=X&ply=Y loads the full game at ply Y (game mode).
 *   The legacy tactic mode (?flaw_ply=) was removed in Quick 260627-l2z; clicking a
 *   move-list tactic chip grafts the PV as an in-tree sideline with a depth overlay.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Chess } from 'chess.js';
import { Cpu } from 'lucide-react';
import { useAnalysisBoard } from '@/hooks/useAnalysisBoard';
import { useStockfishEngine } from '@/hooks/useStockfishEngine';
import { useGameOverlay } from '@/hooks/useGameOverlay';
import { useLiveMoveFlaw } from '@/hooks/useLiveMoveFlaw';
import { useTacticLines, useLibraryGame } from '@/hooks/useLibrary';
import { toDisplayDepthForOrientation } from '@/lib/tacticDepth';
import { buildPvArrow } from '@/lib/tacticArrows';
import { EvalBar } from '@/components/analysis/EvalBar';
import { EngineLines, EngineLinesSkeleton } from '@/components/analysis/EngineLines';
import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { VariationTree } from '@/components/analysis/VariationTree';
import type { FlawMarkerEntry } from '@/components/analysis/VariationTree';
import type { FlawSeverity } from '@/types/library';
import { EvalChart } from '@/components/library/EvalChart';
import { ChessBoard } from '@/components/board/ChessBoard';
import type { BoardArrow } from '@/components/board/ChessBoard';
import { BoardControls } from '@/components/board/BoardControls';
import { PlayerBar } from '@/components/board/PlayerBar';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { uciToSquares } from '@/lib/sanToSquares';
import { ARROW_NEUTRAL, TAC_MISSED, TAC_ALLOWED, MOVE_HIGHLIGHT_GOOD } from '@/lib/theme';
import type { NodeId } from '@/hooks/useAnalysisBoard';

// ─── Constants ────────────────────────────────────────────────────────────────

const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

/** Engine label shown in the engine info line — the bundled Stockfish 18 WASM. */
const ENGINE_NAME = 'SF 18';

/** Cap on the per-session live engine-eval cache (FEN → completed eval), item 4. */
const LIVE_EVAL_CACHE_MAX = 256;

/** Below this width the page renders its mobile takeover layout (matches the shell's
 *  `sm` breakpoint where the app swaps to mobile chrome). */
const MOBILE_BREAKPOINT_PX = 640;

/**
 * True while the viewport is below the mobile breakpoint. Drives a single-tree render
 * (mobile OR desktop, never both) so the board / eval-chart / variation-tree mount once —
 * a CSS `hidden` split would duplicate their stable `id`/`data-testid`s and the engine board.
 */
function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    () =>
      typeof window !== 'undefined' &&
      window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}

// ─── Root-ply helper ──────────────────────────────────────────────────────────

/**
 * Derive the ply offset of a position from its FEN.
 * rootPly = (fullmoveNumber - 1) * 2 + (sideToMove === 'b' ? 1 : 0)
 * Used by EngineLines (startPly) and VariationTree (rootPly) to produce
 * correct move-number labels for opening-position entries.
 */
function fenToRootPly(fen: string | undefined): number {
  if (!fen) return 0;
  const parts = fen.split(' ');
  const side = parts[1];
  const fullmove = parts[5];
  if (side === undefined || fullmove === undefined) return 0;
  const ply = (Number(fullmove) - 1) * 2 + (side === 'b' ? 1 : 0);
  return Number.isNaN(ply) ? 0 : ply;
}

/**
 * Main-line ply the tactic PV sideline forks from, by orientation (Quick 260628-pu2 UAT).
 *
 * Missed lines fork at the pre-flaw DECISION board (flawPly-1) and replay the
 * should-have-played PV. Allowed lines fork at the FLAW position itself (flawPly): the
 * sideline begins with the opponent's punishing response, not a replay of the flaw move.
 * The backend's allowed_moves prepends the flaw move at index 0, so allowed PVs grafted
 * here drop that lead-in move (allowed_moves.slice(1)).
 */
function forkPlyForOrientation(flawPly: number, orientation: 'missed' | 'allowed'): number {
  return orientation === 'allowed' ? flawPly : flawPly - 1;
}

// ─── Page ────────────────────────────────────────────────────────────────────

/**
 * Default-exported Analysis page (required by React.lazy in App.tsx).
 * ROUTE-01: reachable by authenticated users inside ProtectedLayout.
 * ROUTE-02: ?fen= seeds the board; empty/malformed → standard start.
 * ROUTE-04 (Phase 140): ?game_id=&ply= enters game mode (full game at initial ply).
 */
export default function Analysis() {
  const [searchParams] = useSearchParams();
  const fenParam = searchParams.get('fen') ?? undefined;

  // Security FEN-guard (T-138-01): attempt chess.js parse; fall back to
  // undefined (STARTING_FEN) so a hand-typed bad URL renders the start
  // position instead of crashing react-chessboard at render.
  let guardedFen: string | undefined;
  if (fenParam !== undefined) {
    try {
      new Chess(fenParam);
      guardedFen = fenParam;
    } catch {
      // Malformed FEN: degrade to STARTING_FEN (guardedFen stays undefined).
    }
  }

  // ── URL params — game mode (T-140-02a) ──────────────────────────────────────
  // Security: NaN-guard on numeric params — malformed → null → mode disabled.
  const gameIdRaw = searchParams.get('game_id');
  const plyRaw = searchParams.get('ply');

  const gameId: number | null =
    gameIdRaw != null && !Number.isNaN(Number(gameIdRaw)) ? Number(gameIdRaw) : null;
  // Game mode initial ply (T-140-02a: NaN-guard). null when the ply param is absent
  // or malformed; game mode still loads (gameId drives it) and opens at ply 0
  // (Quick 260628-qta UAT: game_id without ply loads the game at ply 0).
  const initialPly: number | null =
    plyRaw != null && !Number.isNaN(Number(plyRaw)) ? Number(plyRaw) : null;

  // Game mode is keyed on game_id alone — the ply param is optional (defaults to 0
  // via the `?? 0` guards on every mainLine[initialPly] access below).
  const isGameMode = gameId != null;

  const isMobile = useIsMobile();

  // D-06: engine on by default; toggle available via infoSlot button.
  const [engineEnabled, setEngineEnabled] = useState(true);
  const [boardFlipped, setBoardFlipped] = useState(false);
  // Once we have auto-oriented the board to the player's color, manual flips win.
  const hasAutoFlipped = useRef(false);

  // Phase 140: active PV flaw state (move-list tactic-chip expansion → in-tree sideline).
  // Ephemeral in-memory — D-01: not URL-encoded.
  const [activePvFlaw, setActivePvFlaw] = useState<{
    ply: number;
    orientation: 'missed' | 'allowed';
  } | null>(null);

  // ── All hooks (unconditional, React rules) ────────────────────────────────────

  const {
    position,
    currentNodeId,
    nodes,
    mainLine,
    pvLine,
    rootFen,
    lastMove,
    makeMove,
    goBack,
    goForward,
    goToNode,
    loadMainLine,
    isOnMainLine,
    insertPvLine,
    playUciLine,
    clearPvLine,
    isOnPvLine,
    containerRef,
  } = useAnalysisBoard(guardedFen);

  // Engine hook must run unconditionally (React rules).
  const engine = useStockfishEngine({
    fen: engineEnabled ? position : null,
    enabled: engineEnabled,
  });

  // Contextual PV fetch: lazy-fetch for inline chip expansion (L-3: unconditional).
  // Enabled only when a move-list tactic chip is expanded in game mode.
  const {
    data: contextualTacticData,
    isFetching: contextualPending,
    isError: contextualError,
  } = useTacticLines(gameId, activePvFlaw?.ply ?? null, activePvFlaw != null && isGameMode);

  // Game-by-id fetch for full-game mode (D-4: existing endpoint, no new backend).
  // Unconditional hook call; enabled only when isGameMode (gameId is null otherwise).
  const { data: gameData, isError: gameError } = useLibraryGame(
    isGameMode ? gameId : null,
  );

  // Seeding guard refs: prevent re-running effects after the first game load.
  const hasLoadedMainLine = useRef(false);
  const hasNavigatedToInitialPly = useRef(false);

  // ── Effects (game seeding, board flip, contextual PV insert) ──────────────────

  // Game mode: orient the board to the player's color once (item 5). Black games open
  // flipped; manual flips afterward win (hasAutoFlipped guard). Free play stays white.
  useEffect(() => {
    if (!isGameMode || gameData?.user_color == null || hasAutoFlipped.current) return;
    hasAutoFlipped.current = true;
    setBoardFlipped(gameData.user_color === 'black');
  }, [isGameMode, gameData?.user_color]);

  // Game mode: seed the board once when game data arrives (L-1: never call from chip click).
  useEffect(() => {
    if (!isGameMode || gameData?.moves == null || hasLoadedMainLine.current) return;
    hasLoadedMainLine.current = true;
    loadMainLine(gameData.moves, STARTING_FEN);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameData?.moves, isGameMode]);

  // Navigate to initialPly AFTER loadMainLine state lands (separate effect — RESEARCH.md Hardest Part 3).
  // Watches mainLine.length so it fires after the batch-reset from loadMainLine.
  useEffect(() => {
    if (!isGameMode || mainLine.length === 0 || hasNavigatedToInitialPly.current) return;
    hasNavigatedToInitialPly.current = true;
    // T-140-02b: L-8 guard — out-of-bounds ply is a no-op, not a crash.
    const nodeId = mainLine[initialPly ?? 0];
    if (nodeId !== undefined) goToNode(nodeId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mainLine.length, isGameMode]);

  // Insert contextual PV sideline when the fetch arrives (L-1: insertPvLine, not loadMainLine).
  useEffect(() => {
    if (!isGameMode || activePvFlaw == null || contextualTacticData == null) return;
    // Allowed lines start AT the flaw position and drop the prepended flaw move (index 0),
    // so the sideline begins with the opponent's response (Quick 260628-pu2 UAT). Missed
    // lines start at the decision board and use the full PV.
    const pvMoves =
      activePvFlaw.orientation === 'missed'
        ? (contextualTacticData.missed_moves ?? [])
        : (contextualTacticData.allowed_moves ?? []).slice(1);
    // T-140-02b: L-8 guard on the fork node lookup.
    const forkNodeId = mainLine[forkPlyForOrientation(activePvFlaw.ply, activePvFlaw.orientation)];
    if (forkNodeId !== undefined) insertPvLine(pvMoves, forkNodeId);
    // mainLine intentionally omitted — stable after game load; including it causes
    // spurious re-runs when the user navigates the variation tree.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contextualTacticData, activePvFlaw?.ply, activePvFlaw?.orientation, isGameMode]);

  // ── Derived values ────────────────────────────────────────────────────────────

  const engineLoading = engineEnabled && !engine.isReady;

  const rootPly = fenToRootPly(rootFen);
  const currentPly = fenToRootPly(position);

  const canGoForward = useMemo(() => {
    for (const node of nodes.values()) {
      if (node.parentId === currentNodeId) return true;
    }
    return false;
  }, [nodes, currentNodeId]);

  // ── Derived values (game mode — new) ─────────────────────────────────────────

  // Slider parked when not on the main line (D-05): disabled + opacity-40 + tooltip.
  const isOnMainLineForSlider = currentNodeId === null || isOnMainLine(currentNodeId);

  // Eval-chart sync ply (Quick 260627-mt8): the board's current main-line ply, or the
  // fork point (nearest main-line ancestor) when off the main line. Drives the eval-
  // chart slider so navigating the move list / board keeps the chart in sync; on a
  // sideline it parks the (disabled) slider at the position the sideline branches from.
  const evalChartPly = useMemo<number | null>(() => {
    if (!isGameMode || currentNodeId === null) return null;
    if (isOnMainLine(currentNodeId)) {
      const idx = mainLine.indexOf(currentNodeId);
      return idx >= 0 ? idx : null;
    }
    let id: NodeId | null = nodes.get(currentNodeId)?.parentId ?? null;
    while (id !== null) {
      if (isOnMainLine(id)) {
        const idx = mainLine.indexOf(id);
        return idx >= 0 ? idx : null;
      }
      id = nodes.get(id)?.parentId ?? null;
    }
    return null;
  }, [isGameMode, currentNodeId, mainLine, nodes, isOnMainLine]);

  // Per-side remaining clock at the current position (Quick 260628-pcb). eval_series
  // carries the mover's remaining clock per ply (even ply = White, odd = Black,
  // 0-based on moves — same convention as game_positions.ply and mainLine indexing).
  // Walk up to the current ply, keeping the latest clock seen for each side.
  // clock_seconds is null for imports without %clk (e.g. some chess.com games), so
  // that side simply shows no clock.
  const playerClocks = useMemo<{ white: number | null; black: number | null }>(() => {
    const series = gameData?.eval_series;
    if (!isGameMode || series == null) return { white: null, black: null };
    const ply = evalChartPly ?? -1;
    let white: number | null = null;
    let black: number | null = null;
    for (const point of series) {
      if (point.ply > ply) break; // eval_series is ply-ascending
      if (point.clock_seconds == null) continue;
      if (point.ply % 2 === 0) white = point.clock_seconds;
      else black = point.clock_seconds;
    }
    return { white, black };
  }, [isGameMode, gameData?.eval_series, evalChartPly]);

  // Flaw marker map for VariationTree: keyed by mainLine nodeId.
  // Only entries with a tactic chip or blunder/mistake severity are included (D-02, D-03).
  const flawMarkerByNodeId = useMemo<Map<NodeId, FlawMarkerEntry>>(() => {
    const map = new Map<NodeId, FlawMarkerEntry>();
    if (!isGameMode || gameData?.flaw_markers == null) return map;
    // Quick 260628-1t5 (reverting e116912c item 5): the missed chip goes back onto the
    // flaw node mainLine[ply], together with the allowed chip + severity glyph — a single
    // entry per flaw node, no decision-node (ply-1) split.
    for (const fm of gameData.flaw_markers) {
      // noUncheckedIndexedAccess guard (T-140-02b): skip out-of-range plies.
      const nodeId = mainLine[fm.ply];
      if (nodeId === undefined) continue;
      // Quick 260628-u7d follow-up: opponent tactic tags are surfaced in the eval-chart
      // tooltip (built separately in EvalChart) but NOT in the move list — suppress the
      // opponent's motifs here. Severity glyphs stay both-color (pre-existing behavior).
      const missedMotif = fm.is_user ? fm.missed_tactic_motif : null;
      const allowedMotif = fm.is_user ? fm.allowed_tactic_motif : null;
      const sev = fm.severity;
      if (missedMotif !== null || allowedMotif !== null || sev === 'blunder' || sev === 'mistake') {
        map.set(nodeId, {
          missedMotif,
          allowedMotif,
          missedDepth: fm.is_user ? fm.missed_tactic_depth : null,
          allowedDepth: fm.is_user ? fm.allowed_tactic_depth : null,
          severity: sev,
          ply: fm.ply,
        });
      }
    }
    return map;
  }, [isGameMode, gameData, mainLine]);

  // The mainLine node whose chip is currently expanded (for ring highlight + aria). Both
  // the missed and allowed chips for a flaw now live on the same flaw node mainLine[ply]
  // (Quick 260628-1t5); activePvOrientation disambiguates which of the two is active.
  const activePvNodeId: NodeId | null = useMemo(() => {
    if (!isGameMode || activePvFlaw == null) return null;
    // Chip is on mainLine[ply] — the node AFTER the flaw move (noUncheckedIndexedAccess guard).
    const nodeId = mainLine[activePvFlaw.ply];
    return nodeId ?? null;
  }, [isGameMode, activePvFlaw, mainLine]);

  // Contextual overlay PV ply (0 = fork position, 1+ = steps into the PV).
  const contextualCurrentPly =
    currentNodeId !== null ? pvLine.indexOf(currentNodeId) + 1 : 0;

  // onStoredLine for contextual overlay: true only when on the PV sideline itself.
  const contextualOnStoredLine = currentNodeId !== null && isOnPvLine(currentNodeId);

  // Game-mode overlay (Quick 260627): precomputed blue best-move arrow + tactic depth
  // overlay + eval bar, with the live engine supplying only the grey 2nd-best line.
  const gameOverlay = useGameOverlay({
    enabled: isGameMode,
    evalSeries: gameData?.eval_series,
    flawMarkers: gameData?.flaw_markers,
    mainLine,
    currentNodeId,
    isOnMainLine,
    lastMove,
    enginePvLines: engine.pvLines,
    engineEvalCp: engine.evalCp,
    engineEvalMate: engine.evalMate,
    engineDepth: engine.depth,
  });

  // ── Live free-move classification (item 4) ────────────────────────────────────
  // Cache each position's COMPLETED engine eval (white POV) keyed by FEN. The engine
  // only sets evalCp/evalMate once a search finishes (null while analyzing), so a
  // non-null value here is a depth-complete eval for the current position. Held in
  // state (not a ref) so reading it during render is legitimate; updates are
  // low-frequency (one per completed ~1.5s search) and no-op when unchanged.
  const [engineEvalByFen, setEngineEvalByFen] = useState<
    Map<string, { cp: number | null; mate: number | null }>
  >(() => new Map());
  useEffect(() => {
    if (!engineEnabled) return;
    if (engine.evalCp == null && engine.evalMate == null) return;
    setEngineEvalByFen((prev) => {
      const existing = prev.get(position);
      if (existing && existing.cp === engine.evalCp && existing.mate === engine.evalMate) {
        return prev; // unchanged — skip the re-render
      }
      const next = new Map(prev);
      next.set(position, { cp: engine.evalCp, mate: engine.evalMate });
      // Rough FIFO cap (Map preserves insertion order) so a long session can't grow it
      // without bound.
      if (next.size > LIVE_EVAL_CACHE_MAX) {
        const oldest = next.keys().next().value;
        if (oldest !== undefined) next.delete(oldest);
      }
      return next;
    });
  }, [position, engine.evalCp, engine.evalMate, engineEnabled]);

  // FEN of the position BEFORE the current move — the live classifier's "best before".
  const parentFen = useMemo<string | null>(() => {
    if (currentNodeId === null) return null;
    const node = nodes.get(currentNodeId);
    if (!node) return null;
    if (node.parentId === null) return rootFen;
    return nodes.get(node.parentId)?.fen ?? rootFen;
  }, [currentNodeId, nodes, rootFen]);

  // Live classification applies only to freely-played moves off the precomputed line:
  // any node that is NOT a game main-line node (game mode) and NOT a grafted PV node
  // (those are best-play lines). In free-play mode every played node qualifies.
  const liveFlawActive =
    currentNodeId !== null &&
    !(isGameMode && isOnMainLine(currentNodeId)) &&
    !isOnPvLine(currentNodeId);

  const parentEval = parentFen != null ? engineEvalByFen.get(parentFen) ?? null : null;

  const liveFlaw = useLiveMoveFlaw({
    active: liveFlawActive,
    parentFen,
    parentEval,
    childEvalCp: engine.evalCp,
    childEvalMate: engine.evalMate,
    lastMove,
  });

  // Persist each freely-played node's live blunder/mistake classification, keyed by node id
  // (Quick 260628-r5v UAT). Two purposes: (1) the move-list glyph stays on EVERY sideline move
  // the user has stepped through, not just the current one; (2) it caches the per-node
  // classification so returning to an earlier sideline move re-shows its icon without waiting
  // on the live engine to re-grade it. (The eval VALUE is already cached by FEN in
  // engineEvalByFen above; this caches the derived classification per node.)
  const [liveFlawByNode, setLiveFlawByNode] = useState<Map<NodeId, FlawSeverity>>(
    () => new Map(),
  );
  useEffect(() => {
    if (!liveFlawActive || currentNodeId === null) return;
    const severity = liveFlaw.squareMarkers[0]?.severity;
    // Only blunder/mistake paint a glyph; skip while still pending (squareMarkers is empty
    // until both parent and child evals complete) or when the move grades clean/inaccuracy.
    if (severity !== 'blunder' && severity !== 'mistake') return;
    setLiveFlawByNode((prev) => {
      if (prev.get(currentNodeId) === severity) return prev; // unchanged — skip re-render
      const next = new Map(prev);
      next.set(currentNodeId, severity);
      // FIFO cap (Map preserves insertion order) mirrors the eval-cache bound.
      if (next.size > LIVE_EVAL_CACHE_MAX) {
        const oldest = next.keys().next().value;
        if (oldest !== undefined) next.delete(oldest);
      }
      return next;
    });
  }, [liveFlawActive, currentNodeId, liveFlaw]);

  // Move-list marker map (item 1, Quick 260628-1t5): merge the game-mode flaw markers with
  // the live free-move severity for the CURRENT node, so a freely-played blunder/mistake
  // paints the same glyph in the move list as on the board (single source — liveFlaw's own
  // squareMarker severity — so list and board can never disagree). Only blunder/mistake get
  // a glyph (inaccuracy/clean show none, matching the main-line behavior). The live entry is
  // NOT gated by game mode — it must also surface in free-play mode (where flawMarkerByNodeId
  // is empty). When there is no live flaw the original map is returned unchanged (stable ref).
  const moveListMarkers = useMemo<Map<NodeId, FlawMarkerEntry>>(() => {
    const liveSeverity = liveFlaw.squareMarkers[0]?.severity;
    const showCurrentLive =
      currentNodeId !== null && (liveSeverity === 'blunder' || liveSeverity === 'mistake');
    if (liveFlawByNode.size === 0 && !showCurrentLive) return flawMarkerByNodeId;

    const mainLineSet = new Set(mainLine);
    const merged = new Map(flawMarkerByNodeId);
    const addLive = (nodeId: NodeId, severity: FlawSeverity): void => {
      if (merged.has(nodeId)) return; // game/PV flaw entry wins (keeps its tactic chips)
      if (mainLineSet.has(nodeId)) return; // stale id reused as a main-line node after reload
      if (!nodes.has(nodeId)) return; // node deleted (e.g. a collapsed PV fork)
      merged.set(nodeId, {
        missedMotif: null,
        allowedMotif: null,
        missedDepth: null,
        allowedDepth: null,
        severity,
        ply: -1, // placeholder — free-move entries carry no game ply
      });
    };
    // Persisted sideline classifications first, then the current node's in-flight one.
    for (const [nodeId, severity] of liveFlawByNode) addLive(nodeId, severity);
    if (currentNodeId !== null && (liveSeverity === 'blunder' || liveSeverity === 'mistake')) {
      addLive(currentNodeId, liveSeverity);
    }
    return merged;
  }, [flawMarkerByNodeId, liveFlaw, currentNodeId, liveFlawByNode, mainLine, nodes]);

  // Move-list coloring inside the PV sideline (Quick 260628-ojq UAT, extends item 4):
  // teal (TAC_MISSED) for a missed tactic, crimson (TAC_ALLOWED) for an allowed one. Every
  // sideline move from the fork up to and including the depth-0 resolving move is colored,
  // so the whole tactic line reads in its orientation color (not just the punchline move).
  // The *_tactic_ply_index indexes the PV moves, which line up 1:1 with the grafted pvLine.
  const sidelineNodeColors = useMemo(() => {
    const colors = new Map<NodeId, string>();
    if (!isGameMode || activePvFlaw == null || contextualTacticData == null) return colors;
    const isMissed = activePvFlaw.orientation === 'missed';
    // allowed_tactic_ply_index indexes the API allowed_moves (flaw move at index 0); the
    // grafted pvLine drops that lead-in, so shift -1 to align with pvLine (Quick 260628-pu2).
    const resolveIdx = isMissed
      ? (contextualTacticData.missed_tactic_ply_index ?? 0)
      : (contextualTacticData.allowed_tactic_ply_index ?? 1) - 1;
    const color = isMissed ? TAC_MISSED : TAC_ALLOWED;
    for (let i = 0; i <= resolveIdx; i++) {
      const node = pvLine[i];
      if (node !== undefined) colors.set(node, color);
    }
    return colors;
  }, [isGameMode, activePvFlaw, contextualTacticData, pvLine]);

  // Board "tactic overlay" while navigating a PV sideline (item 3): the depth-countdown
  // arrow on the next stored PV move, mirroring the old tactic-mode overlay. Anchored to
  // the contextual line's depth/orientation; the live engine still supplies the grey 2nd.
  const pvSidelineArrows = useMemo<BoardArrow[] | null>(() => {
    if (!isGameMode || activePvFlaw == null || contextualTacticData == null) return null;
    const orientation = activePvFlaw.orientation;
    const forkNodeId = mainLine[forkPlyForOrientation(activePvFlaw.ply, orientation)];
    const onPvPath = contextualOnStoredLine || (forkNodeId !== undefined && currentNodeId === forkNodeId);
    if (!onPvPath) return null;

    const depthRaw =
      orientation === 'missed'
        ? (contextualTacticData.missed_depth ?? 0)
        : (contextualTacticData.allowed_depth ?? 0);
    // anchored=false (Quick 260628-1t5 DECISION 2): the analysis board is a navigable
    // surface, so the allowed +1 decision-anchor offset is dropped (allowed reads like missed).
    const rootDisplayDepth = toDisplayDepthForOrientation(depthRaw, orientation, false);

    // Steps into the PV from the current node (0 at the fork position).
    const stepIntoPv = contextualCurrentPly;
    const nextPvNodeId = pvLine[stepIntoPv];
    const nextPvNode = nextPvNodeId !== undefined ? nodes.get(nextPvNodeId) : undefined;
    const nextMove = nextPvNode ? { from: nextPvNode.from, to: nextPvNode.to } : null;
    if (!nextMove) return null;

    const displayDepth = Math.max(0, rootDisplayDepth - stepIntoPv);
    // Depth 0 is the move after the tactic resolves: treat it as payoff so it shows no
    // number and drops the orientation color — the tactic is over by then (Quick 260628-pu2
    // UAT). The countdown therefore runs ...2, 1 (punchline), then payoff.
    const isPayoff = stepIntoPv >= rootDisplayDepth;
    const arrows = buildPvArrow(nextMove, displayDepth, isPayoff, orientation);

    // Grey 2nd-best from the live engine (skip if it duplicates the overlay arrow).
    const grey = uciToSquares(engine.pvLines[1]?.moves[0] ?? null);
    if (grey && !(grey.from === nextMove.from && grey.to === nextMove.to)) {
      arrows.push({
        startSquare: grey.from,
        endSquare: grey.to,
        color: ARROW_NEUTRAL,
        width: 0.5,
      });
    }
    return arrows.length > 0 ? arrows : null;
  }, [
    isGameMode,
    activePvFlaw,
    contextualTacticData,
    contextualOnStoredLine,
    contextualCurrentPly,
    currentNodeId,
    mainLine,
    pvLine,
    nodes,
    engine.pvLines,
  ]);

  // Game-mode board arrows: PV-sideline overlay takes precedence; otherwise the
  // precomputed/engine overlay from useGameOverlay.
  const boardArrows: BoardArrow[] | undefined = isGameMode
    ? (pvSidelineArrows ?? gameOverlay.boardArrows)
    : undefined;

  // ── Handlers ──────────────────────────────────────────────────────────────────

  // L-5: game mode Reset → clear PV, reset activePvFlaw, navigate to entry ply.
  const handleReset = isGameMode
    ? () => {
        clearPvLine();
        setActivePvFlaw(null);
        setLiveFlawByNode(new Map()); // drop persisted sideline glyphs on reset
        // T-140-02b: L-8 guard on initialPly — out-of-bounds is a no-op.
        const nodeId = mainLine[initialPly ?? 0];
        if (nodeId !== undefined) goToNode(nodeId);
      }
    : () => {
        setLiveFlawByNode(new Map());
        loadMainLine([], rootFen);
      };

  const canReset = currentNodeId !== null;

  // Inline chip click: toggle off (same chip) or set new active flaw.
  const handlePvChipClick = (
    nodeId: NodeId,
    flaw: { ply: number; orientation: 'missed' | 'allowed' },
  ): void => {
    if (activePvFlaw?.ply === flaw.ply && activePvFlaw.orientation === flaw.orientation) {
      // Same chip clicked again: collapse PV.
      clearPvLine();
      setActivePvFlaw(null);
      return;
    }
    // Different chip: clear any existing PV, set new active flaw.
    // insertPvLine is called by the useEffect when contextualTacticData arrives.
    if (activePvFlaw != null) clearPvLine();
    setActivePvFlaw(flaw);
    // Navigate to the fork node — decision board (ply-1) for missed, flaw position (ply) for
    // allowed (Quick 260628-pu2 UAT). T-140-02b guard.
    const forkNodeId = mainLine[forkPlyForOrientation(flaw.ply, flaw.orientation)];
    if (forkNodeId !== undefined) goToNode(forkNodeId);
    void nodeId; // nodeId passed for API symmetry with VariationTree; ply identifies the flaw
  };

  // EvalChart scrub callback: navigate board on main line only (slider disabled off-line).
  const handleEvalChartPlyChange = (ply: number | null): void => {
    if (ply === null || !isOnMainLineForSlider) return;
    // T-140-02b: L-8 guard — ply from eval chart may not align exactly with mainLine.
    const nodeId = mainLine[ply];
    if (nodeId !== undefined) goToNode(nodeId);
  };

  // ── Render ────────────────────────────────────────────────────────────────────

  // Board + EvalBar row — the single source of the `analysis-board` ref/testid and the
  // react-chessboard instance. Shared by the desktop and mobile trees (only one renders
  // at a time via isMobile), so the board mounts exactly once either way.
  const boardRow = (
    <div className="flex flex-row items-stretch gap-2">
      <div ref={containerRef} data-testid="analysis-board" tabIndex={0} className="flex-1">
        <ChessBoard
          id="analysis-board"
          position={position}
          onPieceDrop={makeMove}
          lastMove={lastMove}
          // Precomputed overlay (main line) wins; else the live free-move
          // classification (item 4), which also covers free-play mode. Default green
          // (MOVE_HIGHLIGHT_GOOD): a played move is assumed OK until the engine proves
          // otherwise, so engine-line (PV) moves and not-yet-graded moves read green
          // instead of the shared yellow fallback. The engine still overrides to
          // red/orange on a blunder/mistake (and yellow on an inaccuracy).
          lastMoveColor={
            gameOverlay.lastMoveHighlightColor ??
            liveFlaw.lastMoveHighlightColor ??
            MOVE_HIGHLIGHT_GOOD
          }
          flipped={boardFlipped}
          arrows={boardArrows}
          squareMarkers={
            gameOverlay.squareMarkers.length > 0
              ? gameOverlay.squareMarkers
              : liveFlaw.squareMarkers
          }
          maxWidth={600}
        />
      </div>

      {/* Eval bar: precomputed eval in game mode (immediate), live engine
          otherwise — useGameOverlay passes the engine through when disabled. */}
      <EvalBar
        evalCp={gameOverlay.evalCp}
        evalMate={gameOverlay.evalMate}
        depth={gameOverlay.evalDepth}
        flipped={boardFlipped}
      />
    </div>
  );

  // Player info row (desktop, game mode): name + ELO left, remaining clock right.
  // Rendered above and below the board, ordered by orientation (Quick 260628-pcb).
  const playerBar = (color: 'white' | 'black') => (
    <PlayerBar
      isWhite={color === 'white'}
      name={(color === 'white' ? gameData?.white_username : gameData?.black_username) ?? null}
      rating={(color === 'white' ? gameData?.white_rating : gameData?.black_rating) ?? null}
      clockSeconds={color === 'white' ? playerClocks.white : playerClocks.black}
      testId={`analysis-player-${color}`}
    />
  );

  // VariationTree props — shared between the desktop side panel and the mobile Moves tab.
  // The mobile tab passes variant="vertical" to fill the space; props are otherwise identical.
  const variationTree = (variant: 'responsive' | 'vertical') => (
    <VariationTree
      variant={variant}
      nodes={nodes}
      mainLine={mainLine}
      currentNodeId={currentNodeId}
      rootPly={rootPly}
      initialPly={isGameMode ? initialPly : undefined}
      onNodeClick={goToNode}
      decorations={sidelineNodeColors}
      pvLine={isGameMode ? pvLine : undefined}
      flawMarkerByNodeId={moveListMarkers}
      onPvChipClick={isGameMode ? handlePvChipClick : undefined}
      activePvNodeId={isGameMode ? activePvNodeId : undefined}
      activePvOrientation={isGameMode ? (activePvFlaw?.orientation ?? null) : undefined}
      pvFetchPending={isGameMode ? contextualPending : undefined}
      pvFetchError={isGameMode ? contextualError : undefined}
    />
  );

  // Board controls — shared; the desktop panel keeps the charcoal pill, the mobile
  // footer passes flat so the buttons read like the main nav (Quick 260628-dgv).
  const boardControls = (flat = false) => (
    <BoardControls
      onBack={goBack}
      onForward={goForward}
      onReset={handleReset}
      onFlip={() => setBoardFlipped((f) => !f)}
      canGoBack={currentNodeId !== null}
      canReset={canReset}
      canGoForward={canGoForward}
      flat={flat}
    />
  );

  // The eval-chart element (game mode only) — placed below the board on desktop, inside the
  // Eval tab on mobile. Single instance; rendered in whichever tree is active.
  const evalChartReady =
    isGameMode &&
    gameId != null &&
    gameData?.eval_series != null &&
    gameData.flaw_markers != null &&
    gameData.phase_transitions != null &&
    gameData.moves != null;
  const evalChart = (heightClass: string) =>
    evalChartReady && gameId != null && gameData?.eval_series != null && gameData.flaw_markers != null && gameData.phase_transitions != null && gameData.moves != null ? (
      <EvalChart
        gameId={gameId}
        evalSeries={gameData.eval_series}
        flawMarkers={gameData.flaw_markers}
        phaseTransitions={gameData.phase_transitions}
        moves={gameData.moves}
        heightClass={heightClass}
        initialPly={initialPly}
        flipped={gameData.user_color === 'black'}
        sliderTestId="analysis-eval-chart-slider"
        sliderDisabled={!isOnMainLineForSlider}
        onHoverPlyChange={handleEvalChartPlyChange}
        syncPly={evalChartPly}
      />
    ) : null;

  // ── Mobile takeover layout (< 640px) ──────────────────────────────────────────
  // Engine PV lines above the board (no info card), board + eval bar, then a 2-tab view
  // (Moves | Eval) that fills the space down to the in-flow board-controls footer. Free
  // play has no eval chart, so it shows only the move list (no tab bar). The shell's
  // back-button header + suppressed bottom nav (ProtectedLayout) complete the takeover.
  if (isMobile) {
    return (
      <div
        data-testid="analysis-page"
        className="flex min-h-0 flex-1 flex-col bg-background"
      >
        {/* Engine PV lines on top, without the info-card header. */}
        <div className="shrink-0 px-2 pt-2" data-testid="analysis-engine-lines-mobile">
          {engineLoading ? (
            <EngineLinesSkeleton testId="analysis-engine-loading" compact />
          ) : (
            <EngineLines
              pvLines={engine.pvLines}
              isAnalyzing={engine.isAnalyzing}
              startPly={currentPly}
              baseFen={position}
              flipped={boardFlipped}
              onMoveClick={playUciLine}
              compact
            />
          )}
        </div>

        {/* Board + eval bar. */}
        <div className="shrink-0 px-2 pt-2">{boardRow}</div>

        {/* Game load error (CLAUDE.md isError branch). */}
        {isGameMode && gameError && (
          <p className="shrink-0 px-3 py-2 text-sm text-muted-foreground">
            Failed to load game. Something went wrong. Please try again in a moment.
          </p>
        )}

        {/* Tab view — fills all vertical space between the board and the footer. */}
        {isGameMode && evalChartReady ? (
          <Tabs
            defaultValue="moves"
            className="flex min-h-0 flex-1 flex-col gap-2 px-2 pt-2"
          >
            <TabsList variant="underline" className="w-full shrink-0">
              <TabsTrigger value="moves" data-testid="analysis-tab-moves">
                Moves
              </TabsTrigger>
              <TabsTrigger value="eval" data-testid="analysis-tab-eval">
                Eval chart
              </TabsTrigger>
            </TabsList>
            <TabsContent value="moves" className="flex min-h-0 flex-1 flex-col">
              {variationTree('vertical')}
            </TabsContent>
            {/* Bounded chart height (not h-full): the board already dominates the
                viewport, so a greedy chart pushed the board-controls footer off-screen
                when the mobile browser's URL bar shrank the height. h-[120px] (the
                established mobile chart height) keeps the footer visible.
                px-3 wrapper: the scrub slider is rendered 16px wider than the chart
                (±8px thumb overhang) and normally lands in the desktop card's padding;
                here it needs that horizontal room or it triggers a horizontal scrollbar
                (overflow-y-auto coerces overflow-x to auto). overflow-x-hidden is the
                belt-and-suspenders. */}
            <TabsContent value="eval" className="min-h-0 overflow-x-hidden overflow-y-auto thin-scrollbar">
              <div className="px-3">{evalChart('h-[120px]')}</div>
            </TabsContent>
          </Tabs>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col px-2 pt-2">
            {variationTree('vertical')}
          </div>
        )}

        {/* In-flow board-controls footer — replaces the suppressed mobile nav bar. */}
        <div
          data-testid="analysis-mobile-footer"
          className="shrink-0 border-t border-border bg-background px-2 py-2 pb-safe"
        >
          {boardControls(true)}
        </div>
      </div>
    );
  }

  return (
    <div data-testid="analysis-page" className="flex min-h-0 flex-1 flex-col bg-background">
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 pb-20 md:py-6 md:pb-6 md:px-6">
        <div className="flex flex-col lg:flex-row lg:items-stretch gap-4">

          {/* Board column ──────────────────────────────────────────────────── */}
          <div className="flex flex-col gap-2 w-full lg:w-[628px] shrink-0">
            {/* Top player (opponent at top of board, by orientation) */}
            {isGameMode && gameData && playerBar(boardFlipped ? 'white' : 'black')}

            {/* Board + EvalBar row */}
            {boardRow}

            {/* Bottom player */}
            {isGameMode && gameData && playerBar(boardFlipped ? 'black' : 'white')}

            {/* EvalChart with slider — game mode only, below board (UI-SPEC Layout Contract). */}
            {evalChartReady && (
              <div data-testid="analysis-eval-chart">{evalChart('h-[120px]')}</div>
            )}
          </div>

          {/* Side panel: engine + variation tree + controls. Narrower than the board
              column (UAT 260627-mt8 item 1) and stretched to the board column's
              height so the controls bottom-align with the eval-chart slider. */}
          <div className="flex w-full lg:w-[360px] shrink-0 flex-col gap-4 min-w-0">

            {/* Spacer mirroring the board column's top player bar so the engine card
                top aligns with the board top (not the player-bar top). Desktop only
                (lg) where the columns sit side by side; invisible keeps its height.
                -mb-2 trims this column's gap-4 down to the board column's gap-2 so the
                spacer→card gap equals the bar→board gap. (Quick 260628-pcb) */}
            {isGameMode && gameData && (
              <div aria-hidden="true" className="hidden lg:block lg:invisible lg:-mb-2">
                {playerBar(boardFlipped ? 'white' : 'black')}
              </div>
            )}

            {/* Game load error (CLAUDE.md isError branch). */}
            {isGameMode && gameError && (
              <p className="text-sm text-muted-foreground p-2">
                Failed to load game. Something went wrong. Please try again in a moment.
              </p>
            )}

            {/* Engine info + lines in a fixed-height charcoal Card (Quick 260627-r9g
                item 3). The info line is the card header; the body never jumps as the
                engine transitions loading → analyzing → 2 lines. */}
            <Card data-testid="analysis-engine-card">
              {/* Info line in the header: engine toggle + "SF 18, Depth d". */}
              <CardHeader
                size="compact"
                data-testid="analysis-engine-info"
                className="font-normal text-muted-foreground"
              >
                <Button
                  variant="ghost"
                  size="icon"
                  className="-ml-1 h-7 w-7 hover:bg-accent"
                  onClick={() => setEngineEnabled((v) => !v)}
                  aria-label="Toggle engine"
                  aria-pressed={engineEnabled}
                  data-testid="btn-analysis-engine-toggle"
                >
                  <Cpu className={`h-4 w-4 ${engineEnabled ? '' : 'text-muted-foreground'}`} />
                </Button>
                <span className="text-sm">
                  {ENGINE_NAME}
                  {engineEnabled && engine.depth > 0 ? `, Depth ${engine.depth}` : ''}
                </span>
              </CardHeader>

              {/* min-height (not fixed) — holds a stable floor through the
                  loading → analyzing → 2-lines transition, but grows to fit a line
                  the user expands via its chevron (Quick 260628-shc UAT). */}
              <CardBody className="min-h-[78px] p-2">
                {engineLoading ? (
                  <EngineLinesSkeleton testId="analysis-engine-loading" />
                ) : !engineEnabled ? (
                  <div className="flex h-full items-center px-2 text-sm text-muted-foreground">
                    Engine off
                  </div>
                ) : (
                  <EngineLines
                    pvLines={engine.pvLines}
                    isAnalyzing={engine.isAnalyzing}
                    startPly={currentPly}
                    baseFen={position}
                    flipped={boardFlipped}
                    onMoveClick={playUciLine}
                  />
                )}
              </CardBody>
            </Card>

            {variationTree('responsive')}

            {/* BoardControls relocated to bottom of right column (chess.com pattern — UI-SPEC). */}
            {boardControls()}
          </div>

        </div>
      </main>
    </div>
  );
}
