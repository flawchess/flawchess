/**
 * EngineLines — renders up to 2 top PV lines from the Stockfish engine.
 *
 * Each line shows:
 *  - a per-line score (read from pvLines[i].evalCp / pvLines[i].evalMate, D-03)
 *  - a depth badge on line 0 only
 *  - up to 5 clickable PV move chips that call onMoveClick(from, to)
 *
 * When `isAnalyzing && pvLines.length === 0`, shows a spinner ("Analyzing…").
 * When `isAnalyzing && pvLines.length > 0`, shows the lines (depth badge is the
 * progress signal — no spinner overlay).
 * When `!isAnalyzing && pvLines.length === 0`, renders empty (Phase 138 handles
 * engine-loading chrome).
 *
 * All engine strings are rendered as React children (auto-escaped, T-137-03 mitigated).
 */

import { Loader2 } from 'lucide-react';

import type { PvLine } from '@/hooks/uciParser';
import { moveLabel } from '@/lib/moveNumberLabel';

/** Maximum number of PV lines displayed. */
const MAX_LINES = 2;
/** Maximum number of plies shown per PV line. */
const MAX_PLIES = 5;

// PV chip class — matches HorizontalMoveList chip exactly (PATTERNS line 176).
// text-sm added to meet the CLAUDE.md text-sm floor.
const CHIP_CLASS =
  'inline-flex items-center gap-0.5 rounded px-1 py-0.5 font-mono text-sm transition-colors hover:bg-accent';

/** Format a per-line score from evalCp / evalMate per the UI-SPEC table. */
function formatScore(
  evalCp: number | null,
  evalMate: number | null,
): string {
  if (evalMate !== null) {
    if (evalMate > 0) return `#+${evalMate}`;
    if (evalMate < 0) return `#-${Math.abs(evalMate)}`;
    return '#0';
  }
  if (evalCp !== null) {
    if (evalCp >= 0) return `+${(evalCp / 100).toFixed(2)}`;
    return (evalCp / 100).toFixed(2);
  }
  return '…';
}

export interface EngineLinesProps {
  /** PV lines from useStockfishEngine. */
  pvLines: PvLine[];
  /** Current search depth (shared across all lines). */
  depth: number;
  /** True while the engine is running (used only for the spinner gate). */
  isAnalyzing: boolean;
  /** Game ply at engine invocation — used for move-number labels. Default 0. */
  startPly?: number;
  /** Called when the user clicks a PV move chip. */
  onMoveClick: (from: string, to: string) => void;
}

interface PvLineRowProps {
  line: PvLine;
  lineIndex: number;
  depth: number;
  startPly: number;
  onMoveClick: (from: string, to: string) => void;
  showDepthBadge: boolean;
  addSeparator: boolean;
}

/** Renders a single PV line (score header + move chips). */
function PvLineRow({
  line,
  lineIndex,
  depth,
  startPly,
  onMoveClick,
  showDepthBadge,
  addSeparator,
}: PvLineRowProps) {
  const scoreText = formatScore(line.evalCp, line.evalMate);
  // Build the moves list — aria uses UCI notation since we lack SAN here.
  const moves = line.moves.slice(0, MAX_PLIES);

  return (
    <div className={addSeparator ? 'border-t border-border' : undefined}>
      {/* Line header: score + depth badge (line 0 only) */}
      <div className="flex items-center gap-2 px-2 pt-1">
        <span
          className="text-sm font-semibold text-foreground"
          aria-label={`Line ${lineIndex + 1}: ${scoreText}`}
        >
          {scoreText}
        </span>
        {showDepthBadge && (
          <span className="text-sm text-muted-foreground">d{depth}</span>
        )}
      </div>

      {/* PV move chips */}
      <div className="flex flex-wrap items-center gap-0.5 px-2 pb-1">
        {moves.map((uciMove, moveIndex) => {
          // Safe: moveIndex is within moves.slice(0, MAX_PLIES) bounds.
          const from = uciMove.slice(0, 2);
          const to = uciMove.slice(2, 4);
          const label = moveLabel(startPly, lineIndex === 0 ? moveIndex : moveIndex);
          const isWhiteMove = (startPly + moveIndex) % 2 === 0;

          return (
            <span key={moveIndex} className="inline-flex items-center gap-0.5">
              {isWhiteMove && (
                <span className="text-sm text-muted-foreground select-none">
                  {label}
                </span>
              )}
              <button
                className={CHIP_CLASS}
                data-testid={`engine-line-${lineIndex}-move-${moveIndex}`}
                aria-label={`Play ${uciMove}`}
                onClick={() => onMoveClick(from, to)}
              >
                {uciMove}
              </button>
            </span>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Renders up to 2 top engine PV lines with scores, depth badge, and clickable
 * move chips.
 */
export function EngineLines({
  pvLines,
  depth,
  isAnalyzing,
  startPly = 0,
  onMoveClick,
}: EngineLinesProps) {
  const visibleLines = pvLines.slice(0, MAX_LINES);

  return (
    <div
      data-testid="analysis-engine-lines"
      aria-label="Engine lines"
      aria-live="polite"
    >
      {/* Analyzing spinner — only when engine is running AND no lines yet */}
      {isAnalyzing && pvLines.length === 0 && (
        <div
          data-testid="engine-lines-analyzing"
          className="flex items-center gap-2 text-sm text-muted-foreground p-2"
        >
          <span aria-label="Analyzing" aria-busy="true">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </span>
          Analyzing…
        </div>
      )}

      {/* PV lines — rendered when lines are available */}
      {visibleLines.map((_, lineIndex) => {
        // noUncheckedIndexedAccess: narrow before use.
        const line = visibleLines[lineIndex];
        if (!line) return null;
        return (
          <PvLineRow
            key={lineIndex}
            line={line}
            lineIndex={lineIndex}
            depth={depth}
            startPly={startPly}
            onMoveClick={onMoveClick}
            showDepthBadge={lineIndex === 0}
            addSeparator={lineIndex > 0}
          />
        );
      })}
    </div>
  );
}
