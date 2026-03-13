import { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';

interface MoveListProps {
  moveHistory: string[];
  currentPly: number;
  onMoveClick: (ply: number) => void;
}

export function MoveList({ moveHistory, currentPly, onMoveClick }: MoveListProps) {
  const activeRef = useRef<HTMLButtonElement>(null);

  // Auto-scroll to keep current move visible
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [currentPly]);

  if (moveHistory.length === 0) {
    return (
      <div className="h-24 overflow-y-auto rounded border border-border bg-muted/30 p-2 text-sm text-muted-foreground">
        No moves yet
      </div>
    );
  }

  // Build pairs: [[white_move, black_move?], ...]
  const movePairs: Array<[string, string | null]> = [];
  for (let i = 0; i < moveHistory.length; i += 2) {
    movePairs.push([moveHistory[i], moveHistory[i + 1] ?? null]);
  }

  return (
    <div className="h-24 overflow-y-auto rounded border border-border bg-muted/30 p-2 text-sm">
      <div className="flex flex-wrap gap-x-1 gap-y-0.5">
        {movePairs.map((pair, pairIdx) => {
          const whitePly = pairIdx * 2 + 1;
          const blackPly = pairIdx * 2 + 2;
          return (
            <span key={pairIdx} className="flex items-center gap-0.5">
              <span className="text-muted-foreground select-none">{pairIdx + 1}.</span>
              <button
                ref={currentPly === whitePly ? activeRef : undefined}
                onClick={() => onMoveClick(whitePly)}
                data-testid={`move-${whitePly}`}
                aria-label={`Move ${pairIdx + 1}. ${pair[0]} (white)`}
                className={cn(
                  'rounded px-1 py-0.5 font-mono hover:bg-accent transition-colors',
                  currentPly === whitePly && 'bg-primary text-primary-foreground hover:bg-primary/90',
                )}
              >
                {pair[0]}
              </button>
              {pair[1] !== null && (
                <button
                  ref={currentPly === blackPly ? activeRef : undefined}
                  onClick={() => onMoveClick(blackPly)}
                  data-testid={`move-${blackPly}`}
                  aria-label={`Move ${pairIdx + 1}. ${pair[1]} (black)`}
                  className={cn(
                    'rounded px-1 py-0.5 font-mono hover:bg-accent transition-colors',
                    currentPly === blackPly && 'bg-primary text-primary-foreground hover:bg-primary/90',
                  )}
                >
                  {pair[1]}
                </button>
              )}
            </span>
          );
        })}
      </div>
    </div>
  );
}
