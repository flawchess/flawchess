import { Cpu } from 'lucide-react';

/**
 * Inline placeholder bar shown in OpeningStatsCard when Tier 2 is not yet
 * reached (i.e. Stockfish analysis is still pending).
 *
 * Replaces both the eval bullet row and the eval-text+popover row with a
 * single pulsating-Cpu amber bar that spans the full 2-col grid. Its height
 * matches the MiniBulletChart it covers (h-5) so swapping in the placeholder
 * does not change the card's row height, and it reads as a thin "covered"
 * metric bar rather than a chunky box. Shares the EvalCoverageHeader amber
 * "Stockfish is working" semantic (amber token, animate-pulse Cpu icon).
 *
 * The WDL score row is intentionally unaffected — it is not eval-dependent.
 */
export function EvalCpuPlaceholder() {
  return (
    <div
      className="flex h-5 items-center gap-1.5 rounded-sm border border-amber-400/40 bg-amber-50/60 px-2 col-span-2"
      data-testid="eval-cpu-placeholder"
    >
      <Cpu className="h-3.5 w-3.5 shrink-0 text-amber-700 animate-pulse" aria-hidden="true" />
      <span className="text-foreground text-sm truncate">Analyzing…</span>
    </div>
  );
}
