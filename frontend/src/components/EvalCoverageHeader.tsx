import { Cpu } from 'lucide-react';
import { useEvalCoverage } from '@/hooks/useEvalCoverage';

/** Page-level Stockfish analysis progress bar.
 *
 * Renders when Stockfish evaluation is still in progress (isPending === true).
 * Returns null at 100% so it leaves no layout gap once coverage is complete.
 *
 * Mount on: Endgames page, Openings → Stats subtab. NOT in the global topbar,
 * NOT on the Import page (see D-02).
 */
export function EvalCoverageHeader() {
  const { pendingCount, pct, isPending } = useEvalCoverage();

  if (!isPending) return null;

  const gamesLabel = pendingCount === 1 ? 'game' : 'games';
  return (
    <div
      role="status"
      data-testid="eval-coverage-header"
      className="flex items-center gap-1.5 text-sm text-muted-foreground mb-3"
    >
      <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
      Stockfish analysis: {pct}% complete ({pendingCount.toLocaleString()} {gamesLabel} pending)
    </div>
  );
}
