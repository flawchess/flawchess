import { useEffect, useMemo, useRef, useState } from 'react';
import { Chess } from 'chess.js';
import { ArrowLeftRight } from 'lucide-react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY } from '@/lib/theme';
import { getArrowColor, GREY, MINOR_EFFECT_SCORE, SCORE_PIVOT } from '@/lib/arrowColor';
import { OPENING_INSIGHTS_CONFIDENCE_COPY } from '@/components/insights/OpeningInsightsBlock';
import {
  HIGHLIGHT_PULSE_DURATION_MS,
  HIGHLIGHT_PULSE_ITERATIONS,
  HIGHLIGHT_BG_LOW_ALPHA,
  HIGHLIGHT_BG_HIGH_ALPHA,
  HIGHLIGHT_BG_REST_ALPHA,
} from '@/lib/highlightPulse';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { InfoPopover } from '@/components/ui/info-popover';
import { Tooltip } from '@/components/ui/tooltip';
import { ConfidenceTooltipContent } from '@/components/insights/ConfidenceTooltipContent';
import { cn } from '@/lib/utils';
import { isTrollPosition } from '@/lib/trollOpenings';
import type { NextMoveEntry, Color } from '@/types/api';

interface MoveExplorerProps {
  moves: NextMoveEntry[];
  isLoading: boolean;
  isError: boolean;
  position: string;
  onMoveClick: (from: string, to: string) => void;
  onMoveHover?: (moveSan: string | null) => void;
  /**
   * When non-null, the row whose move_san matches `san` renders a sticky
   * severity-tinted background in `color` and is auto-scrolled into view once.
   * When `pulse` is true, the row tint also runs the synced pulse animation.
   * The parent flips `pulse` false after the pulse window so a later React
   * re-render can't re-attach the animation class and restart it.
   * (Quick-task 260427-j41.)
   */
  highlightedMove?: { san: string; color: string; pulse: boolean } | null;
  /**
   * Fired when the highlight should clear:
   *   1. Position changes (board move played, navigation, etc.).
   *   2. Any move row is clicked.
   * Filter-change clears live in the parent (Openings).
   * The parent owns the actual highlight state — MoveExplorer just signals.
   */
  onHighlightConsumed?: () => void;
}

const IS_TOUCH = typeof window !== 'undefined' && 'ontouchstart' in window;

// Background-tint pulse for the highlighted row. The keyframe lives in
// index.css (`@keyframes row-highlight-pulse`); MoveRow supplies the three
// color stops via inline CSS variables and the duration/iteration count
// inline so the pulse stays in sync with the chessboard arrow pulse.

export function MoveExplorer({
  moves,
  isLoading,
  isError,
  position,
  onMoveClick,
  onMoveHover,
  highlightedMove,
  onHighlightConsumed,
}: MoveExplorerProps) {
  // Mobile: first tap highlights a row (shows arrow on board), second tap plays the move
  const [selectedMove, setSelectedMove] = useState<string | null>(null);

  // Derive side-just-moved once from the parent FEN's side-to-move token.
  // The parent's side TO MOVE is the side that plays each candidate move in
  // `moves`, so it's also the side that just moved on the resulting position
  // (D-10). Defensive throw: callers must pass a full FEN — a board-only
  // placement string has no side-to-move token and would silently produce
  // wrong results (RESEARCH.md Pitfall 7). This check runs BEFORE the
  // `moveMap` useMemo so its friendly error message wins over chess.js's
  // generic "must contain six space-delimited fields" complaint.
  const sideJustMoved: Color = useMemo(() => {
    const tokens = position.split(' ');
    const sideToken = tokens[1];
    if (sideToken !== 'w' && sideToken !== 'b') {
      throw new Error(
        `MoveExplorer: position must be a full FEN with side-to-move, got: ${position}`,
      );
    }
    return sideToken === 'w' ? 'white' : 'black';
  }, [position]);

  const moveMap = useMemo(() => {
    const chess = new Chess(position);
    const legalMoves = chess.moves({ verbose: true });
    return new Map(legalMoves.map(m => [m.san, { from: m.from, to: m.to }]));
  }, [position]);

  // Ref placed on the row matching highlightedMove.san — used to scrollIntoView.
  // We only attach the ref to the matching row to avoid managing a Map of refs.
  const highlightedRowRef = useRef<HTMLTableRowElement | null>(null);

  // Clear selection when position changes (move was played via board or other source).
  // Derived-state pattern: setState during render is React-recommended for derived
  // resets and is idempotent (the second pass sees prevPosition === position).
  const [prevPosition, setPrevPosition] = useState(position);
  if (prevPosition !== position) {
    setPrevPosition(position);
    if (selectedMove !== null) setSelectedMove(null);
  }

  // Highlight consumption signals: position change OR row click. We fire
  // onHighlightConsumed in an effect (NOT in render) so the callback runs
  // exactly once per transition — calling parent setState during render would
  // cause React 19's double-invocation in dev/strict mode to double-fire the
  // signal. Filter-change clears live in the parent (where filter identity is
  // owned) — using the moves-array reference here was a false proxy: TanStack
  // Query resolution creates a new moves reference on first fetch, which would
  // wrongly clear deep-link highlights mid-pulse.
  const prevPositionForHighlightRef = useRef(position);
  useEffect(() => {
    const positionChanged = prevPositionForHighlightRef.current !== position;
    prevPositionForHighlightRef.current = position;
    if (positionChanged && highlightedMove != null) {
      onHighlightConsumed?.();
    }
  }, [position, highlightedMove, onHighlightConsumed]);

  const handleRowClick = (entry: NextMoveEntry) => {
    const squares = moveMap.get(entry.move_san);
    if (!squares) return;

    if (IS_TOUCH) {
      // Mobile: first tap highlights, second tap on same row plays the move
      if (selectedMove === entry.move_san) {
        onMoveClick(squares.from, squares.to);
        setSelectedMove(null);
        onMoveHover?.(null);
      } else {
        setSelectedMove(entry.move_san);
        onMoveHover?.(entry.move_san);
      }
    } else {
      // Desktop: single click plays the move
      onMoveClick(squares.from, squares.to);
    }

    // Any row click clears the deep-link highlight. We signal AFTER the
    // existing logic so the next position-change effect doesn't double-clear.
    if (highlightedMove != null) {
      onHighlightConsumed?.();
    }
  };

  const handleRowKeyDown = (e: React.KeyboardEvent, entry: NextMoveEntry) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      const squares = moveMap.get(entry.move_san);
      if (squares) {
        onMoveClick(squares.from, squares.to);
      }
    }
  };

  return (
    <div data-testid="move-explorer">
      {isLoading ? (
        <div data-testid="move-explorer-loading" className="flex flex-col gap-2">
          <div className="h-8 bg-muted animate-pulse rounded" />
          <div className="h-8 bg-muted animate-pulse rounded" />
          <div className="h-8 bg-muted animate-pulse rounded" />
        </div>
      ) : isError ? (
        <div data-testid="move-explorer-empty" className="py-4">
          <p className="text-sm font-semibold text-foreground">Could not load moves</p>
          <p className="text-xs text-muted-foreground mt-1">
            There was a problem fetching next moves. Try adjusting filters or refreshing.
          </p>
        </div>
      ) : moves.length === 0 ? (
        <div data-testid="move-explorer-empty" className="py-4">
          <p className="text-sm font-semibold text-foreground">No moves found</p>
          <p className="text-xs text-muted-foreground mt-1">
            No recorded games continue from this position with the current filters.
          </p>
        </div>
      ) : (
        <table data-testid="move-explorer-table" className="w-full text-sm table-fixed">
          <thead>
            <tr>
              <th className="w-8 sm:w-12 text-left text-xs text-muted-foreground font-normal pb-1">
                <span className="inline-flex items-center gap-1">
                  <span className="sr-only sm:not-sr-only">Move</span>
                  <InfoPopover ariaLabel="Move arrows info" testId="move-arrows-info" side="top">
                    <div className="space-y-2">
                      <p>
                        These are the moves that occurred next in the position shown on the board, over all the games that match the current filter settings. Moves with fewer than 10 games or low confidence are always grey. Rows with fewer than 10 games are also dimmed since their statistics are unreliable.
                      </p>
                      <p>
                        On desktop, click a move to play it. On mobile, tap to highlight (shows the arrow on the board), then tap again to play.
                      </p>
                      <p>
                        <strong>Score</strong> is your win rate plus half your draw rate.
                        When your score is below 45% or above 55% over at
                        least 10 games, a statistical test is conducted to determine how
                        likely the difference occurred by chance.
                      </p>
                      {OPENING_INSIGHTS_CONFIDENCE_COPY}
                    </div>
                  </InfoPopover>
                </span>
              </th>
              <th className="w-[5.5rem] text-right text-xs text-muted-foreground font-normal pb-1">Games</th>
              <th
                className="w-[2.5rem] text-center text-xs text-muted-foreground font-normal pb-1"
                data-testid="move-explorer-th-conf"
              >
                Conf
              </th>
              <th className="text-left text-xs text-muted-foreground font-normal pb-1 pl-2">Results</th>
            </tr>
          </thead>
          <tbody>
            {moves.map(entry => {
              const isHighlighted = highlightedMove != null && entry.move_san === highlightedMove.san;
              return (
                <MoveRow
                  key={entry.move_san}
                  entry={entry}
                  selectedMove={selectedMove}
                  onRowClick={handleRowClick}
                  onRowKeyDown={handleRowKeyDown}
                  onMoveHover={onMoveHover}
                  highlightColor={isHighlighted ? highlightedMove.color : null}
                  highlightPulse={isHighlighted ? highlightedMove.pulse : false}
                  // Only attach the ref to the matching row — we don't need a Map of refs.
                  rowRef={isHighlighted ? highlightedRowRef : undefined}
                  sideJustMoved={sideJustMoved}
                />
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

/** Move row with inline MiniWDLBar showing percentages */
function MoveRow({ entry, selectedMove, onRowClick, onRowKeyDown, onMoveHover, highlightColor, highlightPulse, rowRef, sideJustMoved }: {
  entry: NextMoveEntry;
  selectedMove: string | null;
  onRowClick: (entry: NextMoveEntry) => void;
  onRowKeyDown: (e: React.KeyboardEvent, entry: NextMoveEntry) => void;
  onMoveHover?: (moveSan: string | null) => void;
  /** Hex color for the row background tint when this row matches highlightedMove. Null otherwise. */
  highlightColor: string | null;
  /** Whether the row should run the pulse animation. Sticky tint is independent (always on when highlightColor !== null). */
  highlightPulse: boolean;
  /** Ref attached only to the highlighted row so the parent can scrollIntoView once. */
  rowRef?: React.Ref<HTMLTableRowElement>;
  /** Side that just moved (i.e. the side TO MOVE in the parent position). Used to route the troll-set lookup. */
  sideJustMoved: Color;
}) {
  const hasWdl = entry.win_pct > 0 || entry.draw_pct > 0 || entry.loss_pct > 0;
  // Mute the row only on small samples — confidence is now its own column and
  // is hidden (not muted) when the effect is too small to be interesting.
  const isUnreliable = entry.game_count < MIN_GAMES_FOR_RELIABLE_STATS;
  // Phase 77 D-06: inline troll-face icon when the resulting position is in
  // the curated set for the side that just moved. Pure synchronous lookup —
  // no useMemo (RESEARCH.md anti-pattern note).
  const showTroll = isTrollPosition(entry.result_fen, sideJustMoved);
  // Hide the per-row confidence indicator for moves below the effect-of-
  // interest threshold (|score - 0.5| < 0.05) and for samples too small to
  // ground a significance test (game_count < 10). The column header stays.
  const hasEffectOfInterest = Math.abs(entry.score - SCORE_PIVOT) >= MINOR_EFFECT_SCORE;
  const showConfidence = hasEffectOfInterest && entry.game_count >= MIN_GAMES_FOR_RELIABLE_STATS;

  // Strength/weakness row tint: every qualifying row gets the same color the
  // chessboard arrow uses (green for strengths, red for weaknesses). Grey
  // (neutral or below the color threshold) means no tint. The deep-link
  // highlight reuses the same color and adds the pulse animation on top.
  const arrowColor = getArrowColor(entry.score, entry.game_count, entry.confidence, false);
  const severityColor = arrowColor === GREY ? null : arrowColor;
  const tintColor = highlightColor ?? severityColor;

  // Merge the unreliable-row opacity with the severity tint + pulse. The
  // sticky background tint stays whenever tintColor is set; the pulse
  // animation properties are only attached while highlightPulse is true so
  // the parent can drop it after the pulse window — preventing later React
  // re-renders (e.g. arrow re-sort on hover) from re-attaching the animation
  // class and restarting the CSS keyframe.
  const rowStyle: React.CSSProperties = {};
  if (isUnreliable) rowStyle.opacity = UNRELIABLE_OPACITY;
  if (tintColor !== null) {
    rowStyle.backgroundColor = `${tintColor}${HIGHLIGHT_BG_REST_ALPHA}`;
    if (highlightPulse) {
      rowStyle.animationDuration = `${HIGHLIGHT_PULSE_DURATION_MS}ms`;
      rowStyle.animationIterationCount = HIGHLIGHT_PULSE_ITERATIONS;
      // CSS custom properties for the keyframe stops; resolved by index.css.
      (rowStyle as React.CSSProperties & Record<`--${string}`, string>)['--row-highlight-low'] =
        `${tintColor}${HIGHLIGHT_BG_LOW_ALPHA}`;
      (rowStyle as React.CSSProperties & Record<`--${string}`, string>)['--row-highlight-high'] =
        `${tintColor}${HIGHLIGHT_BG_HIGH_ALPHA}`;
      (rowStyle as React.CSSProperties & Record<`--${string}`, string>)['--row-highlight-rest'] =
        `${tintColor}${HIGHLIGHT_BG_REST_ALPHA}`;
    }
  }

  // The highlighted row reuses the existing data-testid (`move-explorer-row-${san}`) —
  // no NEW interactive element is added (the row remains the same <tr>), so per
  // CLAUDE.md "data-testid on every interactive element" is already satisfied.

  return (
    <tr
      ref={rowRef}
      data-testid={`move-explorer-row-${entry.move_san}`}
      className={cn(
        'cursor-pointer min-h-[44px]',
        // `!` (Tailwind v4 important suffix) is needed so the hover background
        // beats the inline severity tint set via `style.backgroundColor`.
        // hover:bg-blue-500/15 sticks on mobile after tap, causing two highlighted rows
        !IS_TOUCH && 'hover:bg-blue-500/15!',
        selectedMove === entry.move_san && 'bg-blue-500/15',
        tintColor !== null && highlightPulse && 'animate-row-highlight-pulse',
      )}
      style={Object.keys(rowStyle).length > 0 ? rowStyle : undefined}
      role="button"
      tabIndex={0}
      onClick={() => onRowClick(entry)}
      onKeyDown={(e) => onRowKeyDown(e, entry)}
      onMouseEnter={() => onMoveHover?.(entry.move_san)}
      onMouseLeave={() => onMoveHover?.(null)}
    >
      <td className="py-1 text-sm text-foreground font-normal whitespace-nowrap">
        <span className="inline-flex items-center gap-1">
          <span>{entry.move_san}</span>
          {showTroll && (
            <Tooltip content="Considered a troll opening">
            <span className="inline-flex">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 64 64"
              aria-label="Considered a troll opening"
              role="img"
              data-testid={`move-list-row-${entry.move_san}-troll-icon`}
              className="inline-block h-4 w-4 text-muted-foreground"
            >
              <g fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="32" cy="32" r="27" />
                <path d="M22 43.5c2.9 3 6.3 4.5 10 4.5s7.1-1.5 10-4.5" />
              </g>
              <g fill="currentColor">
                <path d="M11.5 24.5c.5-2.3 2.4-3.5 5.1-3.5h10.1c2.4 0 3.9 1.4 3.5 3.7l-.9 5.8c-.5 3.4-2.7 5.5-6.1 5.5H19c-2.8 0-4.6-1.4-5.4-4.2l-2.1-7.3z" />
                <path d="M52.5 24.5c-.5-2.3-2.4-3.5-5.1-3.5H37.3c-2.4 0-3.9 1.4-3.5 3.7l.9 5.8c.5 3.4 2.7 5.5 6.1 5.5H45c2.8 0 4.6-1.4 5.4-4.2l2.1-7.3z" />
                <path d="M29.3 24h5.4v4h-5.4z" />
              </g>
            </svg>
            </span>
            </Tooltip>
          )}
        </span>
      </td>
      <td className="py-1 text-right tabular-nums">
        <span className="inline-flex items-center justify-end gap-0.5">
          {entry.transposition_count > entry.game_count && (
            <TranspositionInfo
              moveSan={entry.move_san}
              transpositionCount={entry.transposition_count}
              gameCount={entry.game_count}
            />
          )}
          {entry.game_count}
        </span>
      </td>
      <td className="py-1 text-center text-muted-foreground tabular-nums">
        {showConfidence && (
          <Tooltip
            content={
              <ConfidenceTooltipContent
                level={entry.confidence}
                pValue={entry.p_value}
                score={entry.score}
                gameCount={entry.game_count}
              />
            }
          >
            <span>{entry.confidence === 'medium' ? 'med' : entry.confidence}</span>
          </Tooltip>
        )}
      </td>
      <td className="py-1 pl-2">
        {!hasWdl ? (
          <div className="flex h-5 w-full overflow-hidden rounded-sm bg-muted" />
        ) : (
          <MiniWDLBar win_pct={entry.win_pct} draw_pct={entry.draw_pct} loss_pct={entry.loss_pct} />
        )}
      </td>
    </tr>
  );
}

/** Tap/hover-friendly transposition info using Popover instead of Tooltip */
function TranspositionInfo({ moveSan, transpositionCount, gameCount }: {
  moveSan: string;
  transpositionCount: number;
  gameCount: number;
}) {
  const [open, setOpen] = useState(false);
  const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <button
          type="button"
          data-testid={`move-explorer-transpose-${moveSan}`}
          aria-label={`Transposition info for ${moveSan}`}
          className="text-muted-foreground hover:text-foreground focus:outline-none"
          onClick={(e) => e.stopPropagation()}
          onMouseEnter={() => {
            hoverTimeout.current = setTimeout(() => setOpen(true), 100);
          }}
          onMouseLeave={() => {
            if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
            setOpen(false);
          }}
        >
          <ArrowLeftRight className="inline h-4 w-4 mr-1" />
        </button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="top"
          sideOffset={4}
          onMouseEnter={() => { if (hoverTimeout.current) clearTimeout(hoverTimeout.current); }}
          onMouseLeave={() => {
            if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
            setOpen(false);
          }}
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          Position reached in {transpositionCount} total games ({transpositionCount - gameCount} via other move orders)
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
