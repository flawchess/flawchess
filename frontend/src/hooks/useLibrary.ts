import { useQuery } from '@tanstack/react-query';
import { libraryApi } from '@/api/client';
import { resolveDateRange, dateRangeToWireParams } from '@/lib/recency';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { FlawTag, TacticLinesResponse } from '@/types/library';
import { isFlawFilterNonDefault } from '@/hooks/useFlawFilterStore';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';
import type { GameFlawCard } from '@/types/library';
import type { TacticFamily } from '@/lib/tacticComparisonMeta';
import { depthToQueryParams } from '@/lib/tacticDepth';

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
 *
 * @param refetchIntervalMs - when > 0, re-polls at this interval so per-game
 *   analysis_state transitions (no_engine_analysis → analyzed) are picked up
 *   automatically without a page reload. Pass 0 or omit when idle.
 */
export function useLibraryGames(
  filters: FilterState,
  flawFilter: FlawFilterState,
  offset: number,
  limit: number,
  refetchIntervalMs: number = 0,
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
  // Quick 260620-pza / 260621-sm8: tactic filters on the Games tab (mirrors
  // useLibraryFlaws). Depth + orientation are now independently meaningful, so they
  // are ALWAYS sent — gating them behind a selected family meant a depth-only or
  // orientation-only filter never reached the backend (the bug being fixed). The
  // family group is sent only when ≥1 is selected. The backend treats the
  // all-inclusive default (no family, either, full range) as a no-op.
  // Optional-chained: defensive against partial filter objects (older persisted/mocked
  // state predating the tacticFamilies field), matching isFlawFilterNonDefault.
  const tacticFamily =
    (flawFilter.tacticFamilies?.length ?? 0) > 0 ? flawFilter.tacticFamilies : undefined;
  const tacticOrientation = flawFilter.tacticOrientation ?? 'either';
  const depthParam = depthToQueryParams(flawFilter.tacticDepthMin, flawFilter.tacticDepthMax);
  return useQuery({
    queryKey: ['library-games', params, tacticFamily, tacticOrientation, depthParam, offset, limit],
    queryFn: () =>
      libraryApi.getGames({
        ...params,
        tactic_family: tacticFamily,
        tactic_orientation: tacticOrientation,
        ...depthParam,
        offset,
        limit,
      }),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
    refetchInterval: refetchIntervalMs > 0 ? refetchIntervalMs : false,
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
 * Fetch the 15-bullet flaw comparison for the current filter + flaw filter.
 *
 * Query key: ['library-flaw-comparison', params]
 * Independent of ['library-flaw-stats', params] — separate endpoint, separate type.
 * Same buildLibraryParams + LIBRARY_STALE_TIME + refetchOnWindowFocus:false as
 * useLibraryFlawStats (exact analog).
 */
export function useLibraryFlawComparison(
  filters: FilterState,
  flawFilter: FlawFilterState,
) {
  const params = buildLibraryParams(filters, flawFilter.severity, flawFilter.tags);
  return useQuery({
    queryKey: ['library-flaw-comparison', params],
    queryFn: () => libraryApi.getFlawComparison(params),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}

/**
 * Fetch the 6-family tactic-motif comparison for the current filter + flaw filter.
 *
 * Self-fetch for TacticComparisonGrid (Phase 126). Mirrors useLibraryFlawComparison
 * exactly but adds the tactic_families dimension to the query key so filter changes
 * trigger a re-fetch.
 *
 * Query key: ['library-tactic-comparison', params, tacticFamilies]
 * Do NOT add a manual Sentry.captureException — TanStack Query errors are captured
 * globally (CLAUDE.md).
 */
export function useTacticComparison(
  filters: FilterState,
  flawFilter: FlawFilterState,
  tacticFamilies: TacticFamily[],
) {
  const params = buildLibraryParams(filters, flawFilter.severity, flawFilter.tags);
  return useQuery({
    queryKey: ['library-tactic-comparison', params, tacticFamilies],
    queryFn: () =>
      libraryApi.getTacticComparison({
        ...params,
        tactic_families: tacticFamilies.length > 0 ? tacticFamilies : undefined,
      }),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}

/**
 * Fetch a single game by id for the "View game" modal.
 *
 * Query key: ['library-game', gameId, tacticFamily, tacticOrientation, depthParam]
 * Disabled when gameId is null — no fetch fires until the modal opens.
 * Returns the full GameFlawCard for rendering in LibraryGameCard.
 *
 * Quick 260621-sm8: when a flawFilter is supplied, the active tactic filter is
 * forwarded so the modal nulls non-matching tactic slots per-slot, matching the
 * Flaws/Games lists. orientation + depth are always sent (like useLibraryFlaws),
 * family only when ≥1 is selected; the backend treats the all-inclusive default
 * as a no-op, so a direct/unfiltered open is unchanged. The tactic params join
 * the query key so changing the filter refetches the open modal.
 *
 * Severity tactic-leak fix: severity is forwarded only when it narrows (exactly one
 * tier selected — matching isFlawFilterNonDefault), so opening a game under
 * "blunders only" / "mistakes only" gates the modal's tactic chips by severity too.
 * Empty or both-selected = no narrowing, so it is omitted (a direct open is unchanged).
 */
export function useLibraryGame(
  gameId: number | null,
  flawFilter?: FlawFilterState,
): ReturnType<typeof useQuery<GameFlawCard>> {
  const severity =
    flawFilter && flawFilter.severity.length === 1 ? flawFilter.severity : undefined;
  const tacticFamily =
    flawFilter && flawFilter.tacticFamilies.length > 0 ? flawFilter.tacticFamilies : undefined;
  const tacticOrientation = flawFilter ? (flawFilter.tacticOrientation ?? 'either') : undefined;
  const depthParam = flawFilter
    ? depthToQueryParams(flawFilter.tacticDepthMin, flawFilter.tacticDepthMax)
    : undefined;
  return useQuery<GameFlawCard>({
    queryKey: ['library-game', gameId, severity, tacticFamily, tacticOrientation, depthParam],
    queryFn: () =>
      libraryApi.getGame(gameId!, {
        severity,
        tactic_family: tacticFamily,
        tactic_orientation: tacticOrientation,
        ...depthParam,
      }),
    enabled: gameId !== null,
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}

/**
 * Lazy-fetch the tactic PV walk for a specific flaw (game_id + ply).
 *
 * Query key: ['tactic-lines', gameId, ply]
 * Enabled only when `enabled` is true AND gameId/ply are non-null — gates the
 * network request until the TacticLineExplorer opens (lazy fetch on open).
 * Phase 135, Plan 03 — consumed by TacticLineExplorer.
 */
export function useTacticLines(
  gameId: number | null,
  ply: number | null,
  enabled: boolean,
): ReturnType<typeof useQuery<TacticLinesResponse>> {
  return useQuery<TacticLinesResponse>({
    queryKey: ['tactic-lines', gameId, ply],
    queryFn: () => libraryApi.getTacticLines(gameId!, ply!),
    enabled: enabled && gameId != null && ply != null,
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}

/**
 * Fetch the paginated per-flaw list for the current filter + flaw filter.
 *
 * Query key: ['library-flaws', params, tacticFamily, tacticOrientation, depthParam, offset, limit]
 * Both offset and limit are part of the key so page changes trigger a new fetch.
 * Phase 129: tactic_orientation + max_tactic_depth appended to key so changing either
 * triggers a refetch (pitfall 4 prevention).
 */
export function useLibraryFlaws(
  filters: FilterState,
  flawFilter: FlawFilterState,
  offset: number,
  limit: number,
) {
  const params = buildLibraryParams(filters, flawFilter.severity, flawFilter.tags);
  // Phase 126: tactic-motif family filter is a flaw-level Tags-panel filter (off by
  // default; applied only when ≥1 family is selected), so it lives on flawFilter, not
  // the game-metadata FilterState. Sent to /library/flaws as repeated tactic_family.
  const tacticFamily = flawFilter.tacticFamilies.length > 0 ? flawFilter.tacticFamilies : undefined;
  // Phase 129: orientation (omit when 'either'). Quick 260620-l5k: depth is a
  // [min, max] range in depth units — both bounds always sent.
  const tacticOrientation = flawFilter.tacticOrientation ?? 'either';
  const depthParam = depthToQueryParams(flawFilter.tacticDepthMin, flawFilter.tacticDepthMax);
  return useQuery({
    queryKey: ['library-flaws', params, tacticFamily, tacticOrientation, depthParam, offset, limit],
    queryFn: () =>
      libraryApi.getFlaws({
        ...params,
        tactic_family: tacticFamily,
        tactic_orientation: tacticOrientation,
        ...depthParam,
        offset,
        limit,
      }),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
