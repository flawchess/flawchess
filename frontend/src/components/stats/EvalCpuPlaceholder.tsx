import { Cpu } from 'lucide-react';

/**
 * Inline placeholder bar shown in OpeningStatsCard when Tier 2 is not yet
 * reached (i.e. Stockfish analysis is still pending).
 *
 * Replaces both the eval bullet row and the eval-text+popover row with a
 * single pulsating-Cpu amber bar that spans the full 2-col grid — matching
 * EvalCoverageHeader styling exactly so both surfaces share the same
 * "Stockfish is working" semantic (amber token, animate-pulse Cpu icon).
 *
 * The WDL score row is intentionally unaffected — it is not eval-dependent.
 */
export function EvalCpuPlaceholder() {
  return (
    <div
      className="flex items-center gap-2 rounded-md border border-amber-400/40 bg-amber-50/60 px-3 py-2 text-sm col-span-2"
      data-testid="eval-cpu-placeholder"
    >
      <Cpu className="h-4 w-4 shrink-0 text-amber-700 animate-pulse" aria-hidden="true" />
      <span className="text-muted-foreground text-sm truncate">Analyzing…</span>
    </div>
  );
}
