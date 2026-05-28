import { Cpu } from 'lucide-react';

interface EndgamesProcessingStateProps {
  pendingCount: number;
  totalCount: number;
}

/**
 * Whole-page locked state for Endgames while Stockfish eval is still in
 * progress. Used for both first-import and incremental import (D-01/D-02) —
 * one component, one message. No CTA button; unlock is via the Tier-2 toast
 * from App.tsx or reactive reveal when tier2 flips to true on this page.
 */
export function EndgamesProcessingState({ pendingCount, totalCount }: EndgamesProcessingStateProps) {
  const analysedCount = Math.max(totalCount - pendingCount, 0);

  return (
    <div
      data-testid="endgames-processing-state"
      className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 py-12 text-center"
    >
      <Cpu className="h-8 w-8 text-amber-600 animate-pulse" aria-hidden="true" />
      <h2 className="text-xl font-semibold text-foreground">Analyzing endgames</h2>
      <p className="text-sm text-muted-foreground">
        Stockfish:{' '}
        <strong>{analysedCount.toLocaleString()}</strong>
        {' / '}
        <strong>{totalCount.toLocaleString()}</strong>
        {' '}games
      </p>
      <p className="text-sm text-muted-foreground max-w-sm">
        Endgame analysis will be available once Stockfish finishes evaluating your games.
      </p>
    </div>
  );
}
