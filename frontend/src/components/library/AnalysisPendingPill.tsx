import { Cpu } from 'lucide-react';

interface AnalysisPendingPillProps {
  gameId: number;
  /** true → "Analyzing…" (worker actively running); false → "Pending…" (queued/optimistic). */
  leased: boolean;
}

/**
 * The pulsing "Pending…"/"Analyzing…" pill shown while a game's eval job is
 * in flight. Shared by NoAnalysisState and the analysis board (where the eval
 * chart would go while an unanalyzed game's analysis is pending or leased).
 * Presentational only; callers decide when to show it.
 */
export function AnalysisPendingPill({ gameId, leased }: AnalysisPendingPillProps) {
  const label = leased ? 'Analyzing…' : 'Pending…';
  const ariaLabel = leased
    ? 'Analysis is actively running for this game'
    : 'Analysis is pending for this game';

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-sm font-bold text-muted-foreground animate-pulse"
      style={{ background: 'oklch(1 0 0 / 4%)' }}
      data-testid={`analyzing-${gameId}`}
      aria-label={ariaLabel}
    >
      <Cpu className="h-4 w-4 shrink-0" aria-hidden="true" />
      {label}
    </span>
  );
}
