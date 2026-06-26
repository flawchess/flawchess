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
 *
 * Security: FEN-guard on ?fen= param (T-138-01) — malformed FEN degrades to
 *   STARTING_FEN instead of throwing at render.
 * Engine: on by default (D-06); "Loading engine…" shown in eval area while
 *   WASM inits; board stays interactive throughout (SC#3).
 */

import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Chess } from 'chess.js';
import { Cpu, Loader2 } from 'lucide-react';
import { useAnalysisBoard } from '@/hooks/useAnalysisBoard';
import { useStockfishEngine } from '@/hooks/useStockfishEngine';
import { EvalBar } from '@/components/analysis/EvalBar';
import { EngineLines } from '@/components/analysis/EngineLines';
import { VariationTree } from '@/components/analysis/VariationTree';
import { ChessBoard } from '@/components/board/ChessBoard';
import { BoardControls } from '@/components/board/BoardControls';
import { Button } from '@/components/ui/button';

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
    loadMainLine,
    containerRef,
  } = useAnalysisBoard(guardedFen);

  // D-06: engine on by default; toggle available via infoSlot button.
  const [engineEnabled, setEngineEnabled] = useState(true);
  const [boardFlipped, setBoardFlipped] = useState(false);

  // Hooks must be called unconditionally (React rules).
  // Engine idled via fen=null / enabled=false when toggled off.
  const engine = useStockfishEngine({
    fen: engineEnabled ? position : null,
    enabled: engineEnabled,
  });

  // SC#3 / D-06: "Loading engine…" only in the eval area; board stays live.
  const engineLoading = engineEnabled && !engine.isReady;

  // VariationTree walks rootPly + idx from the root node, so its labels anchor
  // to the tree's root FEN ply.
  const rootPly = fenToRootPly(rootFen);
  // EngineLines renders the PV from the CURRENT position, so its move numbers and
  // side-to-move parity must track the current ply, not the static entry FEN.
  // Bug fix (CR-01): passing rootPly here desynced labels (wrong move numbers,
  // flipped side coloring on odd deltas) the moment the user navigated into a move.
  const currentPly = fenToRootPly(position);
  // canGoForward: true when the current node has at least one child. Mirrors
  // findFirstChild() in useAnalysisBoard. Bug fix (WR-01): this was hardcoded
  // true, so the forward button never disabled at a leaf node.
  const canGoForward = useMemo(() => {
    for (const node of nodes.values()) {
      if (node.parentId === currentNodeId) return true;
    }
    return false;
  }, [nodes, currentNodeId]);

  return (
    <div data-testid="analysis-page" className="flex min-h-0 flex-1 flex-col bg-background">
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 pb-20 md:py-6 md:pb-6 md:px-6">
        <div className="flex flex-col lg:flex-row lg:items-start gap-4">

          {/* Board column ──────────────────────────────────────────────────── */}
          <div className="flex flex-col gap-2">
            {/* Desktop: eval bar beside board; Mobile: bar above board.
                Single EvalBar rendered once — positioning via flex-row container. */}
            <div className="flex flex-row items-stretch gap-2">
              <EvalBar
                evalCp={engine.evalCp}
                evalMate={engine.evalMate}
                depth={engine.depth}
              />

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
                />
              </div>
            </div>

            {/* Board controls with engine toggle in infoSlot */}
            <BoardControls
              onBack={goBack}
              onForward={goForward}
              onReset={() => loadMainLine([], rootFen)}
              onFlip={() => setBoardFlipped((f) => !f)}
              canGoBack={currentNodeId !== null}
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

          {/* Side panel: engine lines / loading state + variation tree ────── */}
          <div className="flex flex-1 flex-col gap-4 min-w-0">

            {/* Engine area state machine:
                - engineLoading: "Loading engine…" (page's job, not EngineLines)
                - !engineEnabled: "Engine off" rest text
                - otherwise: EngineLines (shows its own "Analyzing…" spinner or lines) */}
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
                onMoveClick={makeMove}
              />
            )}

            <VariationTree
              nodes={nodes}
              mainLine={mainLine}
              currentNodeId={currentNodeId}
              rootPly={rootPly}
              onNodeClick={goToNode}
            />
          </div>

        </div>
      </main>
    </div>
  );
}
