import { useQuery } from '@tanstack/react-query';
import { libraryApi } from '@/api/client';
import { resolveDateRange, dateRangeToWireParams } from '@/lib/recency';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { FlawTag } from '@/types/library';
import { isFlawFilterNonDefault } from '@/hooks/useFlawFilterStore';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';
import type { GameFlawCard } from '@/types/library';

// Library queries are similar in cost to endgame queries (GROUP BY on FlawRecords).
// 5 minutes staleTime + no refetch-on-focus prevents redundant DB load
// from alt-tabbing or component re-mounts. Data only changes on new imports.
const LIBRARY_STALE_TIME = 5 * 60 * 1000;

/**
 * Build shared query params for library endpoints from a FilterState.
 *
 * Mirrors buildEndgameParams from useEndgames.ts but drops color/matchSide
 * (the Games subtab shows all colors) and adds optional severity + tag filters.
 * severity and tag are omitted from the params object entirely when empty.
 */
function buildLibraryParams(
  filters: FilterState,
  severity: ('blunder' | 'mistake')[],
  tags: FlawTag[] = [],
) {
  const dateParams = dateRangeToWireParams(resolveDateRange(filters));
  return {
    time_control: filters.timeControls,
    platform: filters.platforms,
    ...dateParams,
    rated: filters.rated,
    opponent_type: filters.opponentType,
    opponent_strength: filters.opponentStrength,
    severity: severity.length > 0 ? severity : undefined,
    tag: tags.length > 0 ? tags : undefined,
    color: filters.playedAs === 'either' ? undefined : filters.playedAs,
  };
}

/**
 * Fetch the paginated library game archive for the current filter + flaw filter.
 *
 * Accepts a full FlawFilterState (severity + tags) so both filter dimensions are
 * included in the query key and passed to the endpoint (D-04).
 *
 * Query key: ['library-games', params, offset, limit]
 * Both offset and limit are part of the key so page changes trigger a new fetch.
 */
export function useLibraryGames(
  filters: FilterState,
  flawFilter: FlawFilterState,
  offset: number,
  limit: number,
) {
  // Bug fix: the default flaw filter (severity = blunder+mistake, no tags) used
  // to be sent to GET /library/games, where the backend's severity EXISTS
  // excludes every game without engine analysis — users with only unanalyzed
  // games saw "0 games matched" with no filters set. The default state means
  // "no flaw filtering" on the Games tab (matching the modified-dot logic), so
  // only send severity/tags when the user actively changed the flaw filter.
  const isFiltering = isFlawFilterNonDefault(flawFilter);
  const params = buildLibraryParams(
    filters,
    isFiltering ? flawFilter.severity : [],
    isFiltering ? flawFilter.tags : [],
  );
  return useQuery({
    queryKey: ['library-games', params, offset, limit],
    queryFn: () => libraryApi.getGames({ ...params, offset, limit }),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}

/**
 * Fetch the Flaw-Stats panel data for the current filter + flaw filter.
 *
 * Query key: ['library-flaw-stats', params]
 * No offset — the stats panel aggregates over all matching games, not just
 * the current page.
 */
export function useLibraryFlawStats(
  filters: FilterState,
  flawFilter: FlawFilterState,
) {
  const params = buildLibraryParams(filters, flawFilter.severity, flawFilter.tags);
  return useQuery({
    queryKey: ['library-flaw-stats', params],
    queryFn: () => libraryApi.getFlawStats(params),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}

/**
 * Fetch a single game by id for the "View game" modal.
 *
 * Query key: ['library-game', gameId]
 * Disabled when gameId is null — no fetch fires until the modal opens.
 * Returns the full GameFlawCard for rendering in LibraryGameCard.
 */
export function useLibraryGame(gameId: number | null): ReturnType<typeof useQuery<GameFlawCard>> {
  return useQuery<GameFlawCard>({
    queryKey: ['library-game', gameId],
    queryFn: () => libraryApi.getGame(gameId!),
    enabled: gameId !== null,
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}

/**
 * Fetch the paginated per-flaw list for the current filter + flaw filter.
 *
 * Query key: ['library-flaws', params, offset, limit]
 * Both offset and limit are part of the key so page changes trigger a new fetch.
 */
export function useLibraryFlaws(
  filters: FilterState,
  flawFilter: FlawFilterState,
  offset: number,
  limit: number,
) {
  const params = buildLibraryParams(filters, flawFilter.severity, flawFilter.tags);
  return useQuery({
    queryKey: ['library-flaws', params, offset, limit],
    queryFn: () => libraryApi.getFlaws({ ...params, offset, limit }),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
