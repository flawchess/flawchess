import { Cpu } from 'lucide-react';
import { useEvalCoverage } from '@/hooks/useEvalCoverage';

/** Page-level Stockfish analysis progress banner.
 *
 * Renders while Stockfish evaluation is still in progress (isPending === true).
 * Returns null at 100% so it leaves no layout gap once coverage is complete.
 *
 * Phase 91 feedback iteration:
 * - The earlier muted-text rendering was too easy to scroll past — banner now
 *   uses an amber-tinted info treatment with a pulsing Cpu icon.
 * - Percent-based progress was deceptive during a live import (the denominator
 *   grows faster than the numerator, so the bar walked backwards). The banner
 *   now leads with absolute counts ("N of M games analysed") — the analysed
 *   count grows monotonically and never regresses. The pulsing Cpu icon
 *   carries the liveness signal; no percent-driven bar.
 *
 * Mount on every page that surfaces Stockfish-dependent stats: Endgames Stats,
 * Openings Stats, Openings Explorer, Openings Insights. NOT in the global
 * topbar, NOT on the Import page (see D-02).
 */
export function EvalCoverageHeader() {
  const { pendingCount, totalCount, isPending } = useEvalCoverage();

  if (!isPending) return null;

  const analysedCount = Math.max(totalCount - pendingCount, 0);
  const gamesLabel = totalCount === 1 ? 'game' : 'games';
  return (
    <div
      role="status"
      data-testid="eval-coverage-header"
      className="flex items-center gap-2 rounded-md border border-amber-400/40 bg-amber-50/60 px-3 py-2 text-sm text-foreground mb-3"
    >
      <Cpu className="h-4 w-4 shrink-0 text-amber-700 animate-pulse" aria-hidden="true" />
      <span>
        Stockfish analysis in progress:{' '}
        <strong>{analysedCount.toLocaleString()}</strong> of{' '}
        <strong>{totalCount.toLocaleString()}</strong> {gamesLabel} analysed
        {' '}<span className="text-muted-foreground">({pendingCount.toLocaleString()} still pending)</span>
      </span>
    </div>
  );
}
