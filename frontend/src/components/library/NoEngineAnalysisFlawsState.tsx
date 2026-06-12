import { Cpu } from 'lucide-react';
import { ANALYSIS_COVERAGE_PARAGRAPHS } from './analysisCoverageCopy';

/**
 * Full-width message shown on the Flaws tab when the user has imported games
 * but none have analyzed flaws (e.g. chess.com-only imports or unanalyzed
 * lichess games).
 *
 * Styled like EndgamesProcessingState: centered column, amber Cpu icon,
 * h2 heading + muted paragraphs. No CTA — users import from their platform.
 *
 * Plan 260610-vru: swaps the generic "No flaws matched" EmptyState when
 * games exist but matched_count is zero.
 */
export function NoEngineAnalysisFlawsState() {
  return (
    <div
      data-testid="flaws-no-engine-analysis"
      className="flex min-h-[40vh] flex-col items-center justify-center gap-4 px-4 py-12 text-center"
    >
      <Cpu className="h-8 w-8 text-amber-600" aria-hidden="true" />
      <h2 className="text-xl font-semibold text-foreground">Engine analysis coming soon</h2>
      {ANALYSIS_COVERAGE_PARAGRAPHS.map((para) => (
        <p key={para} className="text-sm text-muted-foreground max-w-sm">
          {para}
        </p>
      ))}
    </div>
  );
}
