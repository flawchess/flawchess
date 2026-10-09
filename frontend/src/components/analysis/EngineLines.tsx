/**
 * EngineLines — renders up to `maxLines` top PV lines from the Stockfish engine
 * (the count comes from the Stockfish lines setting, 1-5, Phase 228).
 *
 * Each line is a single row:
 *  - a colored eval badge (read from pvLines[i].evalCp / pvLines[i].evalMate, D-03):
 *    solid blue (BEST_MOVE_ARROW) on the best line, one translucent blue
 *    (STOCKFISH_BADGE_SECONDARY) on every later line, white text throughout (SEED-175).
 *  - up to 5 clickable PV move chips that call onMoveClick(from, to)
 *
 * The search depth is shown by the engine info line above this component, not here.
 *
 * When `isAnalyzing && pvLines.length === 0`, shows a fixed-height skeleton
 * placeholder (EngineLinesSkeleton) so the panel height is stable as lines arrive.
 * When `isAnalyzing && pvLines.length > 0`, shows the lines.
 * When `!isAnalyzing && pvLines.length === 0`, renders empty (Phase 138 handles
 * engine-loading chrome).
 *
 * All engine strings are rendered as React children (auto-escaped, T-137-03 mitigated).
 */

import { useState } from 'react';
import { Chess } from 'chess.js';
import { ChevronDown } from 'lucide-react';

import type { PvLine } from '@/hooks/uciParser';
import { moveLabel } from '@/lib/moveNumberLabel';
import { cn } from '@/lib/utils';
import {
  BEST_MOVE_ARROW,
  STOCKFISH_BADGE_SECONDARY,
  MOVE_HIGHLIGHT_GOOD,
} from '@/lib/theme';
import { MiniBoard } from '@/components/board/MiniBoard';
import { Tooltip } from '@/components/ui/tooltip';
import { trackFeature } from '@/lib/analytics';

/** Maximum number of plies shown per PV line. */
const MAX_PLIES = 5;
/** Miniboard size (px) inside the engine-move hover tooltip. */
const TOOLTIP_BOARD_SIZE = 144;

/** One replayed PV step: SAN of the move and the FEN of the resulting position. */
interface PvStep {
  /** SAN string, or null when it can't be produced (no base FEN / illegal move). */
  san: string | null;
  /** Full FEN after this move, or null when it can't be produced. */
  fen: string | null;
}

/**
 * Replay a PV's UCI moves from `baseFen`, returning per-move SAN + resulting FEN.
 * Callers fall back to raw UCI for null SAN and skip the hover preview for null FEN.
 * Replay is sequential, so once a move fails every later move returns nulls (the
 * board can no longer advance).
 *
 * Exported (Phase 155 Plan 03) so `FlawChessEngineLines.tsx` can reuse this verbatim
 * instead of duplicating it — see D-07.
 */
export function replayPvLine(baseFen: string | undefined, uciMoves: string[]): PvStep[] {
  if (!baseFen) return uciMoves.map(() => ({ san: null, fen: null }));
  let game: Chess;
  try {
    game = new Chess(baseFen);
  } catch {
    return uciMoves.map(() => ({ san: null, fen: null }));
  }
  let broken = false;
  return uciMoves.map((uci) => {
    if (broken) return { san: null, fen: null };
    try {
      const promotion = uci.length > 4 ? uci.slice(4, 5) : undefined;
      const mv = game.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion });
      if (!mv) {
        broken = true;
        return { san: null, fen: null };
      }
      return { san: mv.san, fen: game.fen() };
    } catch {
      broken = true;
      return { san: null, fen: null };
    }
  });
}

// PV chip class — matches HorizontalMoveList chip exactly (PATTERNS line 176).
// whitespace-nowrap: a chip is a flex item that may shrink to min-content, which broke
// "O-O-O+" at its hyphens and stacked the O's vertically (Phase 237 UAT).
// text-xs is the user-approved exception to the CLAUDE.md text-sm floor, scoped to this
// dense engine surface (Quick 260628-r5v UAT: shrink the desktop engine lines to match the
// already-compact mobile lines). The compact variant below keeps the same font, differing
// only in row layout (no-wrap + zero padding).
const CHIP_CLASS =
  'inline-flex items-center gap-0.5 rounded px-1 py-0.5 whitespace-nowrap font-mono text-xs cursor-pointer transition-colors hover:bg-accent';

// Eval badge — filled pill in the line's arrow color (solid blue best / translucent blue rest).
const BADGE_CLASS = 'shrink-0 rounded px-1.5 py-0.5 text-xs font-semibold text-white';

// Compact variants (Quick 260628-dgv — mobile /analysis takeover): same text-xs font as the
// desktop chips, but with zero vertical padding and no-wrap so each PV line is one
// deterministic ~16px row. (Desktop now uses text-xs too — Quick 260628-r5v — so the compact
// split is purely about row layout, not font size.)
const CHIP_CLASS_COMPACT =
  'inline-flex items-center gap-0.5 rounded px-1 whitespace-nowrap font-mono text-xs leading-4 cursor-pointer transition-colors hover:bg-accent';
const BADGE_CLASS_COMPACT = 'shrink-0 rounded px-1 text-xs font-semibold leading-4 text-white';

// Fixed-height container for the engine-lines region — keeps the panel from
// jumping as the engine transitions analyzing → N lines (Quick 260627-mt8 item 5).
// Height is rows × a per-row pixel budget, applied as an inline style (Tailwind only
// ships literal class strings, so an interpolated `min-h-[${n}px]` would never be
// generated — Phase 228 RESEARCH Pitfall 4).
//
// Desktop: ~30px per row (2 rows = 60px, the pre-Phase-228 `min-h-[60px]`).
export const ENGINE_LINE_ROW_PX = 30;
// Compact (mobile takeover) rows: 25px each, so 2 rows = 50px. Quick 260628-cjp: bumped
// 44→50px. Below 640px the unlayered `.text-xs` override in index.css forces line-height
// 1.25rem (20px), beating the chips' `leading-4` (16px), so two real PV rows measure 49px —
// but the skeleton's fixed h-4/h-3 bars stay at 40px. 50px clears the measured 49px with a
// 1px margin so every state (loading skeleton, analyzing skeleton, rendered rows) is the
// same height (no vertical jump on the mobile takeover — Quick 260628-dgv).
const ENGINE_LINE_ROW_PX_COMPACT = 25;

/** Fixed min-height (px) of an engine-lines region holding `rows` PV rows. */
export function engineLinesMinHeightPx(rows: number, compact = false): number {
  return rows * (compact ? ENGINE_LINE_ROW_PX_COMPACT : ENGINE_LINE_ROW_PX);
}

/**
 * Pulsing placeholder rows shaped like PV lines (eval badge + move chips) — the
 * card-content loading animation that replaces the "Analyzing…" / "Loading
 * engine…" text while the engine spins up or searches (Quick 260627-r9g item 3).
 *
 * G-213-34 (supersedes D-12): download progress lives EXCLUSIVELY in the
 * `EngineReadyGate` modal now — this skeleton never renders a download
 * readout of any kind, on any surface. Do not reintroduce one here; the one
 * aggregate bar in the gate is the only progress surface in the app.
 */
export function EngineLinesSkeleton({
  testId,
  compact = false,
  rows,
}: {
  testId?: string;
  /** Mobile takeover: shorter rows matching the compact text-xs PV lines. */
  compact?: boolean;
  /**
   * Number of placeholder rows — the engine's lines setting (1-5, Phase 228 D-16).
   * Also sets the container's fixed min-height via `engineLinesMinHeightPx`.
   */
  rows: number;
}) {
  return (
    <div
      data-testid={testId}
      className="flex flex-col justify-center gap-2 px-2"
      style={{ minHeight: engineLinesMinHeightPx(rows, compact) }}
      aria-busy="true"
      aria-label="Loading engine lines"
    >
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-2">
          <span
            className={cn(
              'shrink-0 animate-pulse rounded bg-muted/40',
              compact ? 'h-4 w-8' : 'h-5 w-10',
            )}
          />
          <span
            className={cn(
              'w-[60%] animate-pulse rounded bg-muted/30',
              compact ? 'h-3' : 'h-4',
            )}
          />
        </div>
      ))}
    </div>
  );
}

/**
 * Format a per-line score from evalCp / evalMate per the UI-SPEC table.
 * Exported (Phase 155 Plan 03) so `FlawChessEngineLines.tsx` can reuse this
 * verbatim for both the objective and practical score-pair numbers (D-06).
 */
export function formatScore(
  evalCp: number | null,
  evalMate: number | null,
): string {
  if (evalMate !== null) {
    if (evalMate > 0) return `#+${evalMate}`;
    if (evalMate < 0) return `#-${Math.abs(evalMate)}`;
    return '#0';
  }
  if (evalCp !== null) {
    if (evalCp >= 0) return `+${(evalCp / 100).toFixed(1)}`;
    return (evalCp / 100).toFixed(1);
  }
  return '…';
}

export interface EngineLinesProps {
  /** PV lines from useStockfishEngine. */
  pvLines: PvLine[];
  /**
   * How many PV rows to render (and how many skeleton rows to show). Comes from the
   * Stockfish lines setting via the parent; this component never reads the store.
   */
  maxLines: number;
  /** True while the engine is running (used only for the analyzing-gate). */
  isAnalyzing: boolean;
  /** Game ply at engine invocation — used for move-number labels. Default 0. */
  startPly?: number;
  /**
   * FEN of the position the engine is analyzing. When provided, PV moves render
   * as SAN (replayed from this FEN) instead of raw UCI. Falls back to UCI per
   * move when SAN can't be produced.
   */
  baseFen?: string;
  /** Board orientation for the hover-preview miniboards (matches the main board). */
  flipped?: boolean;
  /**
   * Called when the user clicks a PV move chip with the UCI moves from the start
   * of the line up to (and including) the clicked move. The board grafts the whole
   * prefix as a sideline from the current anchor and lands on the clicked move —
   * clicking move N no longer skips moves 1..N-1 (Quick 260628-shc UAT).
   */
  onMoveClick: (uciMoves: string[]) => void;
  /**
   * Compact mobile rendering (Quick 260628-dgv): single-row PV lines with a shorter
   * container, so the mobile takeover region holds a constant height through
   * loading → analyzing → 2 lines. Desktop leaves this false (same text-xs font, but
   * wrapping rows). Font size no longer differs between the two (Quick 260628-r5v).
   */
  compact?: boolean;
}

interface PvLineRowProps {
  line: PvLine;
  lineIndex: number;
  startPly: number;
  baseFen: string | undefined;
  flipped: boolean;
  onMoveClick: (uciMoves: string[]) => void;
  addSeparator: boolean;
  compact: boolean;
}

/** Renders a single PV line as one row: eval badge + move chips. */
function PvLineRow({
  line,
  lineIndex,
  startPly,
  baseFen,
  flipped,
  onMoveClick,
  addSeparator,
  compact,
}: PvLineRowProps) {
  // Per-line expand toggle: collapsed shows the first MAX_PLIES moves; the chevron
  // reveals the whole PV (Quick 260628-shc UAT). State persists across the engine's
  // streaming depth updates because the row's key (lineIndex) is stable.
  const [expanded, setExpanded] = useState(false);
  const scoreText = formatScore(line.evalCp, line.evalMate);
  const hasMore = line.moves.length > MAX_PLIES;
  const moves = expanded ? line.moves : line.moves.slice(0, MAX_PLIES);
  // SAN labels + per-step FENs (replayed from baseFen). Null SAN falls back to raw
  // UCI; null FEN skips the hover preview for that (and every later) chip.
  const steps = replayPvLine(baseFen, moves);
  // Badge matches the board arrow: solid blue best move, one translucent blue for
  // every later line. White text (BADGE_CLASS) stays legible on both fills.
  const badgeColor = lineIndex === 0 ? BEST_MOVE_ARROW : STOCKFISH_BADGE_SECONDARY;

  return (
    <div
      className={cn(
        'flex gap-1 mx-2',
        // Expanded desktop lines wrap to several rows; top-align so the badge and
        // chevron pin to the first row instead of floating in the vertical center.
        compact ? 'items-center py-0.5' : 'items-start py-1',
        addSeparator && 'border-t border-border',
      )}
    >
      {/* Eval badge — solid blue (best) / translucent blue (later lines), matching the arrows. */}
      <span
        className={compact ? BADGE_CLASS_COMPACT : BADGE_CLASS}
        style={{ backgroundColor: badgeColor }}
        aria-label={`Line ${lineIndex + 1}: ${scoreText}`}
      >
        {scoreText}
      </span>

      {/* Move chips, in a flex-1 container so the chevron can pin right. Compact:
          never wrap (deterministic single-row height) — horizontal scroll if too
          wide. Desktop: wrap. */}
      <div
        className={cn(
          'flex min-w-0 flex-1 items-center gap-1',
          compact ? 'flex-nowrap overflow-x-auto thin-scrollbar' : 'flex-wrap',
        )}
      >
      {/* PV move chips — inline on the same row as the badge. */}
      {moves.map((uciMove, moveIndex) => {
          // Safe: moveIndex is within moves.slice(0, MAX_PLIES) bounds.
          const from = uciMove.slice(0, 2);
          const to = uciMove.slice(2, 4);
          const label = moveLabel(startPly, lineIndex === 0 ? moveIndex : moveIndex);
          const isWhiteMove = (startPly + moveIndex) % 2 === 0;
          // SAN when available, raw UCI as fallback.
          const step = steps[moveIndex];
          const displayMove = step?.san ?? uciMove;
          const previewFen = step?.fen ?? null;

          const chip = (
            <button
              className={compact ? CHIP_CLASS_COMPACT : CHIP_CLASS}
              data-testid={`engine-line-${lineIndex}-move-${moveIndex}`}
              aria-label={`Play ${displayMove}`}
              // Play the WHOLE line up to (and including) this move, not just this
              // move — moves is a prefix of line.moves, so slice gives the UCI path.
              onClick={() => onMoveClick(moves.slice(0, moveIndex + 1))}
            >
              {displayMove}
            </button>
          );

          return (
            <span key={moveIndex} className="inline-flex items-center gap-0.5">
              {isWhiteMove && (
                <span className="text-muted-foreground select-none text-xs">
                  {label}
                </span>
              )}
              {/* Hover preview: a miniboard of the position after this PV move
                  (desktop only — Tooltip suppresses on touch). */}
              {previewFen ? (
                <Tooltip
                  side="top"
                  delayDuration={150}
                  // p-0 + overflow-hidden drops the dark padding frame and clips the
                  // board to the tooltip's rounded corners (Quick w8k item 1).
                  contentClassName="overflow-hidden p-0"
                  content={
                    <MiniBoard
                      fen={previewFen}
                      size={TOOLTIP_BOARD_SIZE}
                      flipped={flipped}
                      // Green overlay on the move played to reach this preview (item 1).
                      lastMove={{ from, to }}
                      lastMoveColor={MOVE_HIGHLIGHT_GOOD}
                    />
                  }
                >
                  {chip}
                </Tooltip>
              ) : (
                chip
              )}
            </span>
          );
        })}
      </div>

      {/* Chevron — reveals the rest of the PV (only when the line is longer than
          MAX_PLIES). Pinned right, outside the scrolling move container. */}
      {hasMore && (
        <button
          type="button"
          className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          data-testid={`engine-line-${lineIndex}-expand`}
          aria-label={expanded ? 'Collapse line' : 'Expand line'}
          aria-expanded={expanded}
          onClick={() => {
            setExpanded(!expanded);
            // Expand only: collapsing is not a feature use.
            if (!expanded) trackFeature('board-tool', { target: 'line-expand' });
          }}
        >
          <ChevronDown
            className={cn('h-4 w-4 transition-transform', expanded && 'rotate-180')}
          />
        </button>
      )}
    </div>
  );
}

/**
 * Renders up to `maxLines` top engine PV lines as single rows (eval badge + clickable move
 * chips) inside a fixed-height container, with a non-jumping "Analyzing…"
 * placeholder before any lines arrive. The search depth lives in the engine info
 * line above this component.
 */
export function EngineLines({
  pvLines,
  maxLines,
  isAnalyzing,
  startPly = 0,
  baseFen,
  flipped = false,
  onMoveClick,
  compact = false,
}: EngineLinesProps) {
  const visibleLines = pvLines.slice(0, maxLines);

  return (
    <div
      data-testid="analysis-engine-lines"
      aria-label="Engine lines"
      aria-live="polite"
      style={{ minHeight: engineLinesMinHeightPx(maxLines, compact) }}
    >
      {/* Analyzing placeholder — fixed-height skeleton (avoids layout jump). */}
      {isAnalyzing && pvLines.length === 0 && (
        <EngineLinesSkeleton testId="engine-lines-analyzing" rows={maxLines} compact={compact} />
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
            startPly={startPly}
            baseFen={baseFen}
            flipped={flipped}
            onMoveClick={onMoveClick}
            addSeparator={lineIndex > 0}
            compact={compact}
          />
        );
      })}
    </div>
  );
}
