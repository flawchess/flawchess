import { Cpu } from 'lucide-react';
import { useEvalCoverage } from '@/hooks/useEvalCoverage';
import { ANALYSIS_PENDING_ICON_CLASS, ANALYSIS_PENDING_TINT_CLASS } from '@/lib/theme';
import { cn } from '@/lib/utils';

/** Global Stockfish analysis progress banner.
 *
 * Renders while Stockfish evaluation is still in progress (hasPendingEvals === true).
 * Returns null at 100% so it leaves no layout gap once coverage is complete.
 * Mounted per page (Import, Library Stats, Openings, Endgames) above the page content.
 */
export function EvalCoverageHeader() {
  const { pendingCount, totalCount, hasPendingEvals } = useEvalCoverage();

  if (!hasPendingEvals) return null;

  const analysedCount = Math.max(totalCount - pendingCount, 0);
  return (
    <div
      role="status"
      data-testid="eval-coverage-header"
      className={cn('flex items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground mb-3 whitespace-nowrap overflow-hidden', ANALYSIS_PENDING_TINT_CLASS)}
    >
      <Cpu className={cn('h-4 w-4 shrink-0 animate-pulse', ANALYSIS_PENDING_ICON_CLASS)} aria-hidden="true" />
      <span className="truncate">
        Quick Scan: <strong>{analysedCount.toLocaleString()}</strong>
        {' / '}
        <strong>{totalCount.toLocaleString()}</strong> games
      </span>
    </div>
  );
}
