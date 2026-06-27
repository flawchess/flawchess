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
 *   TacticModeOverlay — conditional tactic chrome (Phase 139)
 *
 * Security:
 *   T-138-01: FEN-guard on ?fen= param — malformed FEN degrades to STARTING_FEN.
 *   T-139-01: NaN-guard on ?game_id= / ?flaw_ply= params — malformed values → null.
 *   T-139-02: ?orientation= cast + resolveVisibleTactic fallback for unknown values.
 * Engine: on by default (D-06); "Loading engine…" shown in eval area while WASM inits;
 *   board stays interactive throughout (SC#3).
 */

import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Chess } from 'chess.js';
import { Cpu, Loader2 } from 'lucide-react';
import { useAnalysisBoard } from '@/hooks/useAnalysisBoard';
import { useStockfishEngine } from '@/hooks/useStockfishEngine';
import { useTacticLines } from '@/hooks/useLibrary';
import { useFlawFilterStore } from '@/hooks/useFlawFilterStore';
import { resolveVisibleTactic } from '@/lib/tacticComparisonMeta';
import { toDisplayDepthForOrientation } from '@/lib/tacticDepth';
import type { TacticDepthOrientation } from '@/lib/tacticDepth';
import { EvalBar } from '@/components/analysis/EvalBar';
import { EngineLines } from '@/components/analysis/EngineLines';
import { VariationTree } from '@/components/analysis/VariationTree';
import {
  TacticModeOverlay,
  buildRootArrows,
  buildPvArrow,
  isBlackToMove,
} from '@/components/analysis/TacticModeOverlay';
import { ChessBoard } from '@/components/board/ChessBoard';
import type { BoardArrow } from '@/components/board/ChessBoard';
import { BoardControls } from '@/components/board/BoardControls';
import { Button } from '@/components/ui/button';
import { uciToSquares } from '@/lib/sanToSquares';
import { BEST_MOVE_ARROW, ARROW_NEUTRAL, TAC_MISSED, TAC_ALLOWED } from '@/lib/theme';
import type { NodeId } from '@/hooks/useAnalysisBoard';

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

// ─── Page ────────────────────────────────────────────────────────────────────

/**
 * Default-exported Analysis page (required by React.lazy in App.tsx).
 * ROUTE-01: reachable by authenticated users inside ProtectedLayout.
 * ROUTE-02: ?fen= seeds the board; empty/malformed → standard start.
 * ROUTE-03 (Phase 139): ?game_id=&flaw_ply= enters tactic mode; ?orientation= optional.
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

  // ── Tactic-mode URL params (T-139-01 / T-139-02) ────────────────────────────
  // Security: NaN-guard on numeric params (T-139-01) — malformed → null → no tactic mode.
  const gameIdRaw = searchParams.get('game_id');
  const flawPlyRaw = searchParams.get('flaw_ply');
  const gameId: number | null =
    gameIdRaw != null && !Number.isNaN(Number(gameIdRaw)) ? Number(gameIdRaw) : null;
  const flawPly: number | null =
    flawPlyRaw != null && !Number.isNaN(Number(flawPlyRaw)) ? Number(flawPlyRaw) : null;
  const isTacticMode = gameId != null && flawPly != null;

  // Orientation state seeded from URL param (T-139-02: unknown value falls back to 'missed').
  const orientationParam = searchParams.get('orientation');
  const [orientation, setOrientation] = useState<TacticDepthOrientation>(
    orientationParam === 'allowed' ? 'allowed' : 'missed',
  );

  // D-06: engine on by default; toggle available via infoSlot button.
  const [engineEnabled, setEngineEnabled] = useState(true);
  const [boardFlipped, setBoardFlipped] = useState(false);

  // ── All hooks (unconditional, React rules) ────────────────────────────────────

  // Destructure board return value so each property is a plain variable.
  // This avoids eslint-plugin-react-hooks/refs v7 false-positive that fires
  // when hook-return properties (including containerRef) are accessed inline
  // inside JSX — see TacticLineExplorer.tsx:289-291 for the same pattern.
  const {
    position,
    currentNodeId,
    nodes,
    mainLine,
    rootFen,
    lastMove,
    makeMove,
    goBack,
    goForward,
    goToNode,
    goToRoot,
    loadMainLine,
    isOnMainLine,
    containerRef,
  } = useAnalysisBoard(guardedFen);

  // Engine hook must run unconditionally (React rules).
  // Idled via fen=null / enabled=false when toggled off.
  const engine = useStockfishEngine({
    fen: engineEnabled ? position : null,
    enabled: engineEnabled,
  });

  // Tactic data: lazy-fetch enabled only in tactic mode.
  const { data: tacticData } = useTacticLines(gameId, flawPly, isTacticMode);

  // Flaw filter for resolveVisibleTactic gating (mirrors TacticLineExplorer).
  const [flawFilter] = useFlawFilterStore();

  // ── Tactic-mode filter-gated visibility ────────────────────────────────────────

  const missedVisible = resolveVisibleTactic(
    'missed',
    tacticData?.missed_motif ?? null,
    tacticData?.missed_depth ?? null,
    flawFilter,
  );
  const allowedVisible = resolveVisibleTactic(
    'allowed',
    tacticData?.allowed_motif ?? null,
    tacticData?.allowed_depth ?? null,
    flawFilter,
  );
  const hasMissed = missedVisible != null && (tacticData?.missed_moves ?? null) != null;
  const hasAllowed = allowedVisible != null && (tacticData?.allowed_moves ?? null) != null;

  // Resolve to the visible orientation; fall back when user choice is filtered out.
  // T-139-02: unknown/malformed orientation falls back to the available one.
  const resolvedOrientation: TacticDepthOrientation =
    orientation === 'allowed'
      ? hasAllowed
        ? 'allowed'
        : 'missed'
      : hasMissed
        ? 'missed'
        : 'allowed';

  // ── Effects (re-seed, board flip, arrow-source reset) ─────────────────────────

  const positionFen = tacticData?.position_fen;

  // D-5 re-seed: fires when flaw data or resolved orientation changes (Behavior D).
  // Seeds loadMainLine with stored PV, then goToRoot to land at the decision position.
  useEffect(() => {
    if (!isTacticMode || positionFen == null) return;
    const moves =
      resolvedOrientation === 'missed'
        ? hasMissed
          ? (tacticData?.missed_moves ?? [])
          : []
        : hasAllowed
          ? (tacticData?.allowed_moves ?? [])
          : [];
    loadMainLine(moves, positionFen);
    goToRoot();
    // loadMainLine/goToRoot are stable callbacks ([] deps). hasMissed/hasAllowed
    // derive from tacticData which is captured via the positionFen dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [positionFen, resolvedOrientation, isTacticMode]);

  // Board flip default (Phase 135 parity): orient so the side to move at the
  // decision position sits at the bottom. Re-runs per flaw but preserves manual
  // flips within the same flaw.
  useEffect(() => {
    if (positionFen != null) setBoardFlipped(isBlackToMove(positionFen));
  }, [positionFen]);

  // ── Derived values ────────────────────────────────────────────────────────────

  // tacticPly: 0 = decision position (root), 1+ = steps into the stored PV.
  const tacticPly =
    currentNodeId === null ? 0 : mainLine.indexOf(currentNodeId) + 1;

  const activeDepthRaw =
    resolvedOrientation === 'missed'
      ? (tacticData?.missed_depth ?? 0)
      : (tacticData?.allowed_depth ?? 0);

  const rootDisplayDepth = toDisplayDepthForOrientation(activeDepthRaw, resolvedOrientation);
  const displayDepth = Math.max(0, rootDisplayDepth - tacticPly);
  const isPayoff = tacticPly > rootDisplayDepth;

  // On main line: at root OR on a seeded mainLine node.
  const onMainLine = currentNodeId === null || isOnMainLine(currentNodeId);

  // Desktop move-list (VariationTree) tactic coloring (UAT): the depth-0 target
  // (punchline) is marked blue and the blunder (the allowed line's prepended
  // flaw move) red — matching the board's blue best-move / red flaw arrows.
  const tacticNodeColors = useMemo(() => {
    const colors = new Map<NodeId, string>();
    if (!isTacticMode || tacticData == null) return colors;
    const punchlineIdx =
      resolvedOrientation === 'missed'
        ? (tacticData.missed_tactic_ply_index ?? 0)
        : (tacticData.allowed_tactic_ply_index ?? 0);
    const punchlineNode = mainLine[punchlineIdx];
    if (punchlineNode !== undefined) colors.set(punchlineNode, TAC_MISSED);
    // Allowed line: index 0 is the prepended flaw move (the blunder) → red.
    if (resolvedOrientation === 'allowed') {
      const blunderNode = mainLine[0];
      if (blunderNode !== undefined) colors.set(blunderNode, TAC_ALLOWED);
    }
    return colors;
  }, [isTacticMode, tacticData, resolvedOrientation, mainLine]);

  // Depth labels for root arrows (used by buildRootArrows).
  const missedDepthLabel = hasMissed ? (missedVisible?.depthLabel ?? undefined) : undefined;
  const allowedDepthLabel = hasAllowed ? (allowedVisible?.depthLabel ?? undefined) : undefined;

  // SC#3 / D-06: "Loading engine…" only in the eval area; board stays live.
  const engineLoading = engineEnabled && !engine.isReady;

  // VariationTree + EngineLines labels anchor to the FEN-derived ply. In tactic
  // mode the seeded position_fen carries a fullmove of 1 — it is rebuilt from
  // board_fen() (piece-placement only), so python-chess defaults the counter — so
  // the raw FEN ply would number the tree/engine lines from move 1 while the tactic
  // move-list numbers from the real game ply (flaw_ply). Shift both by the same
  // offset so all three displays agree. Frontend-only (D-4: endpoint unchanged).
  const rootPlyBase = fenToRootPly(rootFen);
  const plyShift = isTacticMode && flawPly != null ? flawPly - rootPlyBase : 0;
  const rootPly = rootPlyBase + plyShift;
  // EngineLines tracks the current ply (not root) so move numbers stay correct
  // as the user navigates. Bug fix (CR-01): passing rootPly desynced labels on navigation.
  const currentPly = fenToRootPly(position) + plyShift;

  // canGoForward: true when the current node has at least one child. Mirrors
  // findFirstChild() in useAnalysisBoard. Bug fix (WR-01): was hardcoded true,
  // so the forward button never disabled at a leaf node.
  const canGoForward = useMemo(() => {
    for (const node of nodes.values()) {
      if (node.parentId === currentNodeId) return true;
    }
    return false;
  }, [nodes, currentNodeId]);

  // ── Board arrows ─────────────────────────────────────────────────────────────
  // Always-on engine (Quick 260627). The blue best-move arrow is the precomputed
  // stored-PV move while on the stored line, and the live engine best move once
  // forked off-line; the grey second-best arrow always comes from the live engine.
  let boardArrows: BoardArrow[] | undefined;

  // Next move in the stored PV from the current position: the move that leads to
  // the next main-line node (current node sits at index tacticPly-1, so the next
  // node is mainLine[tacticPly]). Used for the blue arrow at ply 1+ (UAT below).
  const nextStoredNodeId = mainLine[tacticPly];
  const nextStoredNode = nextStoredNodeId !== undefined ? nodes.get(nextStoredNodeId) : undefined;
  const nextStoredMove = nextStoredNode
    ? { from: nextStoredNode.from, to: nextStoredNode.to }
    : null;

  if (isTacticMode && tacticData != null) {
    const arrows: BoardArrow[] = [];
    // Blue best-move squares for the grey second-best dedup below. Every branch
    // assigns this before it is read.
    let bestSquares: { from: string; to: string } | null;

    if (onMainLine && tacticPly === 0) {
      // Decision position: stored-PV blue arrow + red flaw arrow. The grey
      // second-best is layered on from the live engine below.
      arrows.push(
        ...buildRootArrows(
          tacticData.position_fen,
          tacticData.best_move_uci,
          tacticData.flaw_move_san,
          missedDepthLabel,
          allowedDepthLabel,
        ),
      );
      bestSquares = uciToSquares(tacticData.best_move_uci);
    } else if (onMainLine && nextStoredMove) {
      // Within the stored PV: the blue arrow + depth describe the NEXT ply to play
      // (the move leading to the next main-line node), matching the grey engine
      // arrow. UAT: previously this drew lastMove (the move already played to reach
      // the current ply), so the blue arrow + depth lagged one ply behind the grey.
      arrows.push(...buildPvArrow(nextStoredMove, displayDepth, isPayoff, resolvedOrientation, false));
      bestSquares = nextStoredMove;
    } else {
      // Off the stored line (forked) or at its leaf: blue best move from the live engine.
      bestSquares = uciToSquares(engine.pvLines[0]?.moves[0] ?? null);
      if (bestSquares) {
        arrows.push({
          startSquare: bestSquares.from,
          endSquare: bestSquares.to,
          color: BEST_MOVE_ARROW,
          width: 0.5,
        });
      }
    }

    // Grey second-best arrow from the live engine. Skipped when it duplicates the
    // blue best move (same from→to would collide on the arrow's React key).
    const second = uciToSquares(engine.pvLines[1]?.moves[0] ?? null);
    if (
      second &&
      !(bestSquares && second.from === bestSquares.from && second.to === bestSquares.to)
    ) {
      arrows.push({
        startSquare: second.from,
        endSquare: second.to,
        color: ARROW_NEUTRAL,
        width: 0.5,
      });
    }

    if (arrows.length > 0) boardArrows = arrows;
  }

  // ── Handlers ──────────────────────────────────────────────────────────────────

  // Orientation toggle: update state; re-seed effect handles board seeding.
  const handleOrientationChange = (next: TacticDepthOrientation): void => {
    if (next === resolvedOrientation) return;
    setOrientation(next);
  };

  // In tactic mode Reset returns to the decision position (beginning of the PV line).
  const handleReset = isTacticMode
    ? () => goToRoot()
    : () => loadMainLine([], rootFen);

  // Reset stays enabled when there is somewhere to return to.
  const canReset = currentNodeId !== null;

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div data-testid="analysis-page" className="flex min-h-0 flex-1 flex-col bg-background">
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 pb-20 md:py-6 md:pb-6 md:px-6">
        <div className="flex flex-col lg:flex-row lg:items-start gap-4">

          {/* Board column ──────────────────────────────────────────────────── */}
          {/* Fixed desktop width so the board does not collapse to min-content
              inside the lg:flex-row (the side panel is flex-1 and would otherwise
              eat all the width). Width = 480px board + 20px EvalBar + 8px gap.
              Full width on mobile. shrink-0 keeps it from being squeezed. */}
          <div className="flex flex-col gap-2 w-full lg:w-[508px] shrink-0">
            {/* Eval bar to the right of the board, following its perspective
                (Quick 260627). Single EvalBar rendered once. */}
            <div className="flex flex-row items-stretch gap-2">
              {/* Board wrapper: containerRef enables container-scoped ←/→ keys
                  (Pitfall 5). tabIndex={0} ensures focus is reachable before a
                  square button receives it. data-testid="analysis-board" is the
                  Wave-0 test anchor; id="analysis-board" drives square testids. */}
              <div
                ref={containerRef}
                data-testid="analysis-board"
                tabIndex={0}
                className="flex-1"
              >
                <ChessBoard
                  id="analysis-board"
                  position={position}
                  onPieceDrop={makeMove}
                  lastMove={lastMove}
                  flipped={boardFlipped}
                  arrows={boardArrows}
                  maxWidth={480}
                />
              </div>

              <EvalBar
                evalCp={engine.evalCp}
                evalMate={engine.evalMate}
                depth={engine.depth}
                flipped={boardFlipped}
              />
            </div>

            {/* Board controls with engine toggle in infoSlot */}
            <BoardControls
              onBack={goBack}
              onForward={goForward}
              onReset={handleReset}
              onFlip={() => setBoardFlipped((f) => !f)}
              canGoBack={currentNodeId !== null}
              canReset={canReset}
              canGoForward={canGoForward}
              infoSlot={
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 hover:bg-accent"
                  onClick={() => setEngineEnabled((v) => !v)}
                  aria-label="Toggle engine"
                  aria-pressed={engineEnabled}
                  data-testid="btn-analysis-engine-toggle"
                >
                  <Cpu className="h-4 w-4" />
                </Button>
              }
            />
          </div>

          {/* Side panel: tactic overlay + engine lines + variation tree ────── */}
          <div className="flex flex-1 flex-col gap-4 min-w-0">

            {/* Tactic chrome: shown in tactic mode when data is loaded. */}
            {isTacticMode && tacticData != null && (
              <TacticModeOverlay
                data={tacticData}
                resolvedOrientation={resolvedOrientation}
                currentPly={tacticPly}
                onStoredLine={onMainLine}
                onOrientationChange={handleOrientationChange}
                onMoveClick={(ply) => {
                  const nodeId = mainLine[ply - 1];
                  if (nodeId !== undefined) goToNode(nodeId);
                }}
              />
            )}

            {/* Engine area state machine:
                - engineLoading: "Loading engine…" (page's job, not EngineLines)
                - !engineEnabled: "Engine off" rest text
                - otherwise: EngineLines (shows its own "Analyzing…" spinner or lines)
                EvalBar + EngineLines stay LIVE throughout tactic mode (D-03). */}
            {engineLoading ? (
              <div
                data-testid="analysis-engine-loading"
                className="flex items-center gap-2 text-sm text-muted-foreground p-2"
              >
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading engine…
              </div>
            ) : !engineEnabled ? (
              <div className="text-sm text-muted-foreground p-2">Engine off</div>
            ) : (
              <EngineLines
                pvLines={engine.pvLines}
                depth={engine.depth}
                isAnalyzing={engine.isAnalyzing}
                startPly={currentPly}
                baseFen={position}
                onMoveClick={makeMove}
              />
            )}

            <VariationTree
              nodes={nodes}
              mainLine={mainLine}
              currentNodeId={currentNodeId}
              rootPly={rootPly}
              onNodeClick={goToNode}
              decorations={tacticNodeColors}
            />
          </div>

        </div>
      </main>
    </div>
  );
}
