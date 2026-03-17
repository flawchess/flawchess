import { useMemo } from 'react';
import { Chess } from 'chess.js';
import { ArrowLeftRight } from 'lucide-react';
import { WDL_WIN, WDL_DRAW, WDL_LOSS } from '@/components/results/WDLBar';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';
import type { NextMoveEntry } from '@/types/api';

interface MoveExplorerProps {
  moves: NextMoveEntry[];
  isLoading: boolean;
  isError: boolean;
  position: string;
  onMoveClick: (from: string, to: string) => void;
  onMoveHover?: (moveSan: string | null) => void;
}

export function MoveExplorer({ moves, isLoading, isError, position, onMoveClick, onMoveHover }: MoveExplorerProps) {
  const moveMap = useMemo(() => {
    const chess = new Chess(position);
    const legalMoves = chess.moves({ verbose: true });
    return new Map(legalMoves.map(m => [m.san, { from: m.from, to: m.to }]));
  }, [position]);

  const handleRowClick = (entry: NextMoveEntry) => {
    const squares = moveMap.get(entry.move_san);
    if (squares) {
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
              <th className="w-[3rem] text-left text-xs text-muted-foreground font-normal pb-1">Move</th>
              <th className="w-[4rem] text-right text-xs text-muted-foreground font-normal pb-1">Games</th>
              <th className="text-left text-xs text-muted-foreground font-normal pb-1 pl-2">Results</th>
            </tr>
          </thead>
          <tbody>
            {moves.map(entry => (
              <tr
                key={entry.move_san}
                data-testid={`move-explorer-row-${entry.move_san}`}
                className="cursor-pointer hover:bg-accent min-h-[44px]"
                role="button"
                tabIndex={0}
                onClick={() => handleRowClick(entry)}
                onKeyDown={(e) => handleRowKeyDown(e, entry)}
                onMouseEnter={() => onMoveHover?.(entry.move_san)}
                onMouseLeave={() => onMoveHover?.(null)}
              >
                <td className="py-1 text-sm text-foreground font-normal truncate">
                  {entry.move_san}
                </td>
                <td className="py-1 text-right tabular-nums">
                  <span className="inline-flex items-center justify-end gap-0.5">
                    {entry.transposition_count > entry.game_count && (
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span data-testid={`move-explorer-transpose-${entry.move_san}`}>
                              <ArrowLeftRight className="inline h-4 w-4 text-muted-foreground mr-1" />
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            Position reached in {entry.transposition_count} total games ({entry.transposition_count - entry.game_count} via other move orders)
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    )}
                    {entry.game_count}
                  </span>
                </td>
                <td className="py-1 pl-2">
                  {entry.win_pct === 0 && entry.draw_pct === 0 && entry.loss_pct === 0 ? (
                    <div className="flex h-3 w-full overflow-hidden rounded bg-muted" />
                  ) : (
                    <div
                      className="flex h-3 w-full overflow-hidden rounded"
                      title={`W: ${entry.win_pct.toFixed(0)}% D: ${entry.draw_pct.toFixed(0)}% L: ${entry.loss_pct.toFixed(0)}%`}
                    >
                      {entry.win_pct > 0 && (
                        <div style={{ width: `${entry.win_pct}%`, backgroundColor: WDL_WIN }} />
                      )}
                      {entry.draw_pct > 0 && (
                        <div style={{ width: `${entry.draw_pct}%`, backgroundColor: WDL_DRAW }} />
                      )}
                      {entry.loss_pct > 0 && (
                        <div style={{ width: `${entry.loss_pct}%`, backgroundColor: WDL_LOSS }} />
                      )}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
