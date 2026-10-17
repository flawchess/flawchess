import { EmptyState } from '@/components/ui/empty-state';
import { DEFAULT_FILTERS, FILTER_DOT_FIELDS, areFiltersEqual } from '@/components/filters/FilterPanel';
import type { FilterState } from '@/components/filters/FilterPanel';

// Named empty state for a user whose imported games exist but whose analytics
// population is emptied by the Human + Rated defaults. One-directional import
// from FilterPanel — FilterPanel must not import this module.

/**
 * True only when the CURRENT filters are exactly the analytics defaults (no
 * other filter is also narrowing the population) AND the user has at least
 * one imported game.
 *
 * The second condition matters because the copy asserts a cause ("none are
 * rated games against humans") — it may only be shown when the Human+Rated
 * defaults are the ONLY thing narrowing the population. If the user has also
 * set a time control, platform, or date filter, the existing generic "try
 * adjusting your filters" state stays correct and this one must not claim
 * a cause it can't back up.
 */
export function shouldShowNoHumanRatedGames(
  filters: FilterState,
  totalGames: number | null,
): boolean {
  return (
    totalGames !== null
    && totalGames > 0
    && areFiltersEqual(filters, DEFAULT_FILTERS, FILTER_DOT_FIELDS)
  );
}

interface NoHumanRatedGamesStateProps {
  /**
   * Accepts `number | null` so callers need no `?? 0`;
   * shouldShowNoHumanRatedGames already guarantees a positive count whenever
   * this is shown.
   */
  totalGames: number | null;
}

export function NoHumanRatedGamesState({ totalGames }: NoHumanRatedGamesStateProps) {
  const count = totalGames ?? 0;
  return (
    <EmptyState
      layout="page"
      data-testid="empty-no-human-rated-games"
      title="No rated games against humans"
      subtitle={`You have ${count} games, but none are rated games against humans. Change the Opponent or Rated filter to include them.`}
    />
  );
}
