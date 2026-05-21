import { Cpu } from 'lucide-react';
import { useEvalCoverage } from '@/hooks/useEvalCoverage';

/** Page-level Stockfish analysis progress banner.
 *
 * Renders when Stockfish evaluation is still in progress (isPending === true).
 * Returns null at 100% so it leaves no layout gap once coverage is complete.
 *
 * Visual treatment: amber-tinted info banner with progress bar so users notice
 * that engine-dependent metrics are still filling in. Phase 91 feedback: the
 * earlier muted-text rendering was too easy to scroll past.
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
      className="flex flex-col gap-1.5 rounded-md border border-amber-400/40 bg-amber-50/60 px-3 py-2 text-sm text-foreground mb-3"
    >
      <div className="flex items-center gap-2">
        <Cpu className="h-4 w-4 text-amber-700 animate-pulse" aria-hidden="true" />
        <span>
          Stockfish analysis in progress: <strong>{pct}%</strong> complete
          {' '}<span className="text-muted-foreground">({pendingCount.toLocaleString()} {gamesLabel} still pending)</span>
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-amber-200/60 overflow-hidden" aria-hidden="true">
        <div
          className="h-full bg-amber-600 transition-[width] duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
