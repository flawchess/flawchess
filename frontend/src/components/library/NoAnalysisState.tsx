import { Cpu } from 'lucide-react';
import { InfoPopover } from '@/components/ui/info-popover';
import { ANALYSIS_COVERAGE_COPY } from './analysisCoverageCopy';

interface NoAnalysisStateProps {
  gameId: number;
}

/**
 * "No Analysis" pill rendered when a game has no engine analysis (chess.com games
 * or lichess games without computer analysis). Replaces the entire severity row +
 * chips section. Per UI-SPEC §'"No engine analysis" state': never shows count text
 * — the schema enforces severity_counts=null for these games.
 *
 * Styled to match the FlawDenominatorPill coverage badge (Cpu icon + label + info
 * popover) so the analyzed-coverage badge and the per-game no-analysis pill read as
 * the same family.
 */
export function NoAnalysisState({ gameId }: NoAnalysisStateProps) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-sm font-bold text-muted-foreground"
      style={{ background: 'oklch(1 0 0 / 4%)' }}
      aria-label="No engine analysis available for this game"
      data-testid={`no-analysis-${gameId}`}
    >
      <Cpu className="h-4 w-4 shrink-0" aria-hidden="true" />
      No Analysis
      <InfoPopover
        ariaLabel="About missing game analysis"
        testId={`no-analysis-info-${gameId}`}
      >
        {ANALYSIS_COVERAGE_COPY}
      </InfoPopover>
    </span>
  );
}
