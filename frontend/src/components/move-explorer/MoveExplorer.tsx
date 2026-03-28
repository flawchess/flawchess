import { useState, useMemo, useRef } from 'react';
import { Chess } from 'chess.js';
import { ArrowLeftRight } from 'lucide-react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY } from '@/lib/theme';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { InfoPopover } from '@/components/ui/info-popover';
import { cn } from '@/lib/utils';
import type { NextMoveEntry } from '@/types/api';

interface MoveExplorerProps {
  moves: NextMoveEntry[];
  isLoading: boolean;
  isError: boolean;
  position: string;
  onMoveClick: (from: string, to: string) => void;
  onMoveHover?: (moveSan: string | null) => void;
}

const IS_TOUCH = typeof window !== 'undefined' && 'ontouchstart' in window;

export function MoveExplorer({ moves, isLoading, isError, position, onMoveClick, onMoveHover }: MoveExplorerProps) {
  // Mobile: first tap highlights a row (shows arrow on board), second tap plays the move
  const [selectedMove, setSelectedMove] = useState<string | null>(null);

  const moveMap = useMemo(() => {
    const chess = new Chess(position);
    const legalMoves = chess.moves({ verbose: true });
    return new Map(legalMoves.map(m => [m.san, { from: m.from, to: m.to }]));
  }, [position]);

  // Clear selection when position changes (move was played via board or other source)
  const [prevPosition, setPrevPosition] = useState(position);
  if (prevPosition !== position) {
    setPrevPosition(position);
    if (selectedMove !== null) setSelectedMove(null);
  }

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
        <table data-testid="move-explorer-table" className="w-full text-sm">
          <thead>
            <tr>
              <th className="w-[3rem] text-left text-xs text-muted-foreground font-normal pb-1">
                <span className="inline-flex items-center gap-1">
                  Move
                  <InfoPopover ariaLabel="Move arrows info" testId="move-arrows-info" side="top">
                    <div className="space-y-2">
                      <p>
                        These are the moves that occurred next in the position shown on the board, over all the games that match the current filter settings. Moves with fewer than 10 games have unreliable statistics and are shown as muted.
                      </p>
                      <p>
                        On desktop, click a move to play it. On mobile, tap to highlight (shows the arrow on the board), then tap again to play.
                      </p>
                    </div>
                  </InfoPopover>
                </span>
              </th>
              <th className="w-[4rem] text-right text-xs text-muted-foreground font-normal pb-1">Games</th>
              <th className="text-left text-xs text-muted-foreground font-normal pb-1 pl-2">Results</th>
            </tr>
          </thead>
          <tbody>
            {moves.map(entry => (
              <MoveRow
                key={entry.move_san}
                entry={entry}
                selectedMove={selectedMove}
                onRowClick={handleRowClick}
                onRowKeyDown={handleRowKeyDown}
                onMoveHover={onMoveHover}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

/** Move row with inline MiniWDLBar showing percentages */
function MoveRow({ entry, selectedMove, onRowClick, onRowKeyDown, onMoveHover }: {
  entry: NextMoveEntry;
  selectedMove: string | null;
  onRowClick: (entry: NextMoveEntry) => void;
  onRowKeyDown: (e: React.KeyboardEvent, entry: NextMoveEntry) => void;
  onMoveHover?: (moveSan: string | null) => void;
}) {
  const hasWdl = entry.win_pct > 0 || entry.draw_pct > 0 || entry.loss_pct > 0;
  const isBelowThreshold = entry.game_count < MIN_GAMES_FOR_RELIABLE_STATS;

  return (
    <tr
      data-testid={`move-explorer-row-${entry.move_san}`}
      className={cn(
        'cursor-pointer hover:bg-accent min-h-[44px]',
        selectedMove === entry.move_san && 'bg-accent',
      )}
      style={isBelowThreshold ? { opacity: UNRELIABLE_OPACITY } : undefined}
      role="button"
      tabIndex={0}
      onClick={() => onRowClick(entry)}
      onKeyDown={(e) => onRowKeyDown(e, entry)}
      onMouseEnter={() => onMoveHover?.(entry.move_san)}
      onMouseLeave={() => onMoveHover?.(null)}
    >
      <td className="py-1 text-sm text-foreground font-normal truncate">
        {entry.move_san}
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
      <td className="py-1 pl-2">
        {!hasWdl ? (
          <div className="flex h-4 w-full overflow-hidden rounded-sm bg-muted" />
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
