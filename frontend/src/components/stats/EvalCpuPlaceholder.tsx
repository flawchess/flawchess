import { Cpu } from 'lucide-react';
import { ANALYSIS_PENDING_ICON_CLASS, ANALYSIS_PENDING_TINT_CLASS } from '@/lib/theme';
import { cn } from '@/lib/utils';

/**
 * Inline placeholder shown in the repertoire card's eval bar (and FindingCard) when
 * Tier 2 is not yet reached (i.e. Stockfish analysis is still pending).
 *
 * A thin pulsating-Cpu amber bar (h-5, matching the cell's content height) replaces the eval
 * value so swapping it in does not change the row height. Shares the EvalCoverageHeader amber
 * "Stockfish is working" semantic (amber token, animate-pulse Cpu icon).
 *
 * The score cell is intentionally unaffected: it is not eval-dependent.
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
