import type { FilterState } from '@/components/filters/FilterPanel';
import type { OpeningInsightFinding } from '@/types/insights';
import { OpeningInsightsBlock } from '@/components/insights/OpeningInsightsBlock';
import { EvalCoverageHeader } from '@/components/EvalCoverageHeader';

type InsightsTabProps = {
  hasOpenings: boolean;
  debouncedFilters: FilterState;
  onFindingClick: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
};

export function InsightsTab({
  hasOpenings,
  debouncedFilters,
  onFindingClick,
  onOpenGames,
}: InsightsTabProps) {
  return (
    <div className="flex flex-col gap-6">
      <EvalCoverageHeader />
      {/* Phase 71: dedicated Insights subtab. */}
      {/* Hidden block + friendly empty state when user has no imported games (proxy: mostPlayedData empty). */}
      {hasOpenings ? (
        <OpeningInsightsBlock
          debouncedFilters={debouncedFilters}
          onFindingClick={onFindingClick}
          onOpenGames={onOpenGames}
        />
      ) : (
        <p className="text-sm text-muted-foreground" data-testid="opening-insights-no-games">
          Import some games to see opening insights.
        </p>
      )}
    </div>
  );
}
