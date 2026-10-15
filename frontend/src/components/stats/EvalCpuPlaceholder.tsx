import { Cpu } from 'lucide-react';
import { ANALYSIS_PENDING_ICON_CLASS, ANALYSIS_PENDING_TINT_CLASS } from '@/lib/theme';
import { cn } from '@/lib/utils';

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
      className={cn('flex h-5 items-center gap-1.5 rounded-sm px-2 col-span-2', ANALYSIS_PENDING_TINT_CLASS)}
      data-testid="eval-cpu-placeholder"
    >
      <Cpu className={cn('h-3.5 w-3.5 shrink-0 animate-pulse', ANALYSIS_PENDING_ICON_CLASS)} aria-hidden="true" />
      <span className="text-foreground text-sm truncate">Analyzing…</span>
    </div>
  );
}
