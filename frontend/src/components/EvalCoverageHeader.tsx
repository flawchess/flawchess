import { Cpu } from 'lucide-react';
import { useEvalCoverage } from '@/hooks/useEvalCoverage';

/** Global Stockfish analysis progress banner.
 *
 * Renders while Stockfish evaluation is still in progress (isPending === true).
 * Returns null at 100% so it leaves no layout gap once coverage is complete.
 * Mounted once in ProtectedLayout so it sits above the per-page subtab nav on
 * every protected page.
 */
export function EvalCoverageHeader() {
  const { pendingCount, totalCount, isPending } = useEvalCoverage();

  if (!isPending) return null;

  const analysedCount = Math.max(totalCount - pendingCount, 0);
  return (
    <div
      role="status"
      data-testid="eval-coverage-header"
      className="flex items-center gap-2 rounded-md border border-amber-400/40 bg-amber-50/60 px-3 py-2 text-sm text-foreground mb-3 whitespace-nowrap overflow-hidden"
    >
      <Cpu className="h-4 w-4 shrink-0 text-amber-700 animate-pulse" aria-hidden="true" />
      <span className="truncate">
        Stockfish: <strong>{analysedCount.toLocaleString()}</strong>
        {' / '}
        <strong>{totalCount.toLocaleString()}</strong> games
      </span>
    </div>
  );
}
