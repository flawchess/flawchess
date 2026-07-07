/**
 * FlawChessEngineLines — renders the top 2 ranked practical lines from the
 * FlawChess Engine (the Phase 153-155 client-side MCTS search core).
 *
 * Structurally a sibling of `EngineLines.tsx`: same row skeleton, same
 * chip/badge/hover-preview pattern, same expand chevron — with three deltas
 * (D-08/D-06/D-07):
 *  - top 2 lines (`MAX_LINES = 2`, D-08).
 *  - a filled gold practical-score badge (white font, one of three
 *    `FLAWCHESS_ENGINE_BADGE_SHADES` by rank — the gold analog of the blue
 *    Stockfish best/2nd badges), followed by the objective Stockfish eval of the
 *    same move in Stockfish blue (155 UAT). Both numbers are white-POV
 *    pawn-scale (D-06, DISPLAY-03). The badge NEVER renders the bare phrase "best
 *    move" unqualified (ARROW-04 principle) — the aria-label frames it as
 *    "practically Y for you, objectively X".
 *  - modal-path chips walked from `RankedLine.modalPath` (already root-relative)
 *    instead of a raw PV move array (D-07, DISPLAY-02).
 *
 * This is body-only (like `EngineLines`) — the `Card`/`CardHeader`/`Switch`
 * wrapper and placement inside `/analysis` are Plan 04's job.
 *
 * All engine strings are rendered as React children (auto-escaped, T-155-04
 * mitigated — inherited by construction from `EngineLines.tsx`'s T-137-03
 * mitigation).
 */

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

import type { RankedLine } from '@/lib/engine/types';
import { expectedScoreToWhitePovCp, sideToMoveFromFen, type MoverColor } from '@/lib/liveFlaw';
import { moveLabel } from '@/lib/moveNumberLabel';
import { cn } from '@/lib/utils';
import {
  FLAWCHESS_ENGINE_BADGE_SHADES,
  STOCKFISH_ACCENT,
  MOVE_HIGHLIGHT_GOOD,
} from '@/lib/theme';
import { MiniBoard } from '@/components/board/MiniBoard';
import { Tooltip } from '@/components/ui/tooltip';
import { replayPvLine, formatScore, EngineLinesSkeleton, LINES_MIN_HEIGHT } from './EngineLines';

/** Maximum number of ranked lines displayed (D-08) — a LOCAL constant, distinct
 * from EngineLines.tsx's own MAX_LINES; do not mutate the shared one. */
const MAX_LINES = 2;
/** Maximum number of plies shown per modal path (D-07, mirrors EngineLines.tsx). */
const MAX_PLIES = 5;
/** Miniboard size (px) inside the move-chip hover tooltip (mirrors EngineLines.tsx). */
const TOOLTIP_BOARD_SIZE = 144;

// Chip class — identical to EngineLines.tsx's desktop (non-compact) CHIP_CLASS,
// so the two engine cards read as one visual family. No compact variant here:
// card placement/mobile-tab wiring is Plan 04's job, not this body component's.
const CHIP_CLASS =
  'inline-flex items-center gap-0.5 rounded px-1 py-0.5 font-mono text-xs transition-colors hover:bg-accent';
// Filled gold practical-score badge — the same pill shell as EngineLines'
// BADGE_CLASS (white font), so the two engine cards read as one visual family;
// only the fill color differs (gold-by-rank vs SF blue). shrink-0 lives on the
// wrapper so the badge + "SF <eval>" aside stay together on one line.
const BADGE_CLASS = 'rounded px-1.5 py-0.5 text-xs font-semibold text-white';

export interface FlawChessEngineLinesProps {
  /** Ranked practical lines from useFlawChessEngine's latest EngineSnapshot. */
  rankedLines: RankedLine[];
  /** True while the search is running — gates the pre-first-snapshot skeleton. */
  isSearching: boolean;
  /** Game ply at search invocation — used for move-number labels. Default 0. */
  startPly?: number;
  /**
   * FEN of the position the search is analyzing. When provided, modal-path
   * moves render as SAN (replayed from this FEN) instead of raw UCI, and —
   * unless `rootMover` is passed explicitly — the root side-to-move is derived
   * from it.
   */
  baseFen?: string;
  /**
   * Root side-to-move, used to convert each line's root-side-to-move
   * `practicalScore` (0-1) to a white-POV cp value for the practical badge
   * number (D-06). Derived from `baseFen` via `sideToMoveFromFen` when omitted;
   * defaults to 'white' if neither is available.
   */
  rootMover?: MoverColor;
  /** Board orientation for the hover-preview miniboards (matches the main board). */
  flipped?: boolean;
  /**
   * Called when the user clicks a modal-path chip with the UCI moves from the
   * start of the line up to (and including) the clicked move. The board grafts
   * the whole prefix as a sideline (D-10) — identical semantics to EngineLines.
   */
  onMoveClick: (uciMoves: string[]) => void;
}

interface RankedLineRowProps {
  line: RankedLine;
  lineIndex: number;
  startPly: number;
  baseFen: string | undefined;
  rootMover: MoverColor;
  flipped: boolean;
  onMoveClick: (uciMoves: string[]) => void;
  addSeparator: boolean;
}

/** Renders a single ranked line as one row: score-pair badge + modal-path chips. */
function RankedLineRow({
  line,
  lineIndex,
  startPly,
  baseFen,
  rootMover,
  flipped,
  onMoveClick,
  addSeparator,
}: RankedLineRowProps) {
  // Per-line expand toggle, mirrors EngineLines.tsx: collapsed shows the first
  // MAX_PLIES moves; the chevron reveals the whole modal path. State persists
  // across live-refine snapshot updates because the row's key (lineIndex) is
  // stable while the search is running (a fresh search remounts the list).
  const [expanded, setExpanded] = useState(false);

  // Objective is already white-POV cp (RankedLine.objectiveEvalCp) — pass
  // straight to formatScore. Practical is a 0-1 root-STM expected score —
  // convert via the Plan 01 inverse-sigmoid before formatting (D-06).
  const objectiveText = formatScore(line.objectiveEvalCp, null);
  const practicalCp = expectedScoreToWhitePovCp(line.practicalScore, rootMover);
  const practicalText = formatScore(practicalCp, null);
  // Gold badge shade by practical rank (best/2nd/3rd). noUncheckedIndexedAccess:
  // lineIndex is 0..MAX_LINES-1 and SHADES has MAX_LINES entries, but narrow anyway.
  const badgeShade =
    FLAWCHESS_ENGINE_BADGE_SHADES[lineIndex] ??
    FLAWCHESS_ENGINE_BADGE_SHADES[FLAWCHESS_ENGINE_BADGE_SHADES.length - 1];

  const hasMore = line.modalPath.length > MAX_PLIES;
  const moves = expanded ? line.modalPath : line.modalPath.slice(0, MAX_PLIES);
  // SAN labels + per-step FENs (replayed from baseFen). Null SAN falls back to
  // raw UCI; null FEN skips the hover preview for that (and every later) chip.
  const steps = replayPvLine(baseFen, moves);

  return (
    <div
      className={cn('flex items-start gap-1 px-2 py-1', addSeparator && 'border-t border-border')}
    >
      {/* Gold practical-score badge (white font, shade by rank) + the objective
          Stockfish eval of this same move in Stockfish blue. Never the bare phrase
          "best move" (D-06). */}
      <span
        className="flex shrink-0 items-center gap-1"
        aria-label={`Line ${lineIndex + 1}: practically ${practicalText} for you, objectively ${objectiveText}`}
      >
        <span className={BADGE_CLASS} style={{ backgroundColor: badgeShade }}>
          {practicalText}
        </span>
        <span className="font-mono text-xs" style={{ color: STOCKFISH_ACCENT }}>
          {objectiveText}
        </span>
      </span>

      {/* Modal-path chips, in a flex-1 wrapping container so the chevron pins right. */}
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1">
        {moves.map((uciMove, moveIndex) => {
          // Safe: moveIndex is within moves.slice(0, MAX_PLIES) bounds (noUncheckedIndexedAccess).
          const from = uciMove.slice(0, 2);
          const to = uciMove.slice(2, 4);
          const label = moveLabel(startPly, moveIndex);
          const isWhiteMove = (startPly + moveIndex) % 2 === 0;
          // SAN when available, raw UCI as fallback.
          const step = steps[moveIndex];
          const displayMove = step?.san ?? uciMove;
          const previewFen = step?.fen ?? null;

          const chip = (
            <button
              className={CHIP_CLASS}
              data-testid={`flawchess-line-${lineIndex}-move-${moveIndex}`}
              aria-label={`Play ${displayMove}`}
              // Grafts the WHOLE line up to (and including) this move — moves is
              // a prefix of line.modalPath, so slice gives the UCI path (D-10).
              onClick={() => onMoveClick(moves.slice(0, moveIndex + 1))}
            >
              {displayMove}
            </button>
          );

          return (
            <span key={moveIndex} className="inline-flex items-center gap-0.5">
              {isWhiteMove && (
                <span className="text-muted-foreground select-none text-xs">{label}</span>
              )}
              {/* Hover preview: a miniboard of the position after this modal-path
                  move (desktop only — Tooltip suppresses on touch). */}
              {previewFen ? (
                <Tooltip
                  side="top"
                  delayDuration={150}
                  contentClassName="overflow-hidden p-0"
                  content={
                    <MiniBoard
                      fen={previewFen}
                      size={TOOLTIP_BOARD_SIZE}
                      flipped={flipped}
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

      {/* Chevron — reveals the rest of the modal path (only when longer than
          MAX_PLIES). Pinned right, outside the wrapping move container. */}
      {hasMore && (
        <button
          type="button"
          className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          data-testid={`flawchess-line-${lineIndex}-expand`}
          aria-label={expanded ? 'Collapse line' : 'Expand line'}
          aria-expanded={expanded}
          onClick={() => setExpanded((v) => !v)}
        >
          <ChevronDown className={cn('h-4 w-4 transition-transform', expanded && 'rotate-180')} />
        </button>
      )}
    </div>
  );
}

/**
 * Renders up to 2 top FlawChess Engine ranked lines as single rows (score-pair
 * badge + clickable modal-path chips) inside a fixed-height container, with a
 * non-jumping skeleton before the first snapshot arrives (D-09). Card
 * chrome/placement inside `/analysis` is Plan 04's job — this component is
 * body-only.
 */
export function FlawChessEngineLines({
  rankedLines,
  isSearching,
  startPly = 0,
  baseFen,
  rootMover,
  flipped = false,
  onMoveClick,
}: FlawChessEngineLinesProps) {
  const resolvedRootMover: MoverColor =
    rootMover ?? (baseFen ? sideToMoveFromFen(baseFen) : 'white');
  const visibleLines = rankedLines.slice(0, MAX_LINES);

  return (
    <div
      data-testid="analysis-flawchess-card"
      aria-label="FlawChess Engine lines"
      aria-live="polite"
      className={LINES_MIN_HEIGHT}
    >
      {/* Pre-first-snapshot placeholder — fixed-height skeleton sized for 2 rows
          (D-09), avoids layout jump as lines arrive. */}
      {isSearching && rankedLines.length === 0 && (
        <EngineLinesSkeleton testId="analysis-flawchess-loading" rows={MAX_LINES} />
      )}

      {/* Ranked lines — rendered when at least one snapshot has arrived. */}
      {visibleLines.map((_, lineIndex) => {
        // noUncheckedIndexedAccess: narrow before use.
        const line = visibleLines[lineIndex];
        if (!line) return null;
        return (
          <RankedLineRow
            key={lineIndex}
            line={line}
            lineIndex={lineIndex}
            startPly={startPly}
            baseFen={baseFen}
            rootMover={resolvedRootMover}
            flipped={flipped}
            onMoveClick={onMoveClick}
            addSeparator={lineIndex > 0}
          />
        );
      })}
    </div>
  );
}
