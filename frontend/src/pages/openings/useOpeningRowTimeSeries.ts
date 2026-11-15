import { useMemo } from 'react';
import { useTimeSeries } from '@/hooks/usePositionBookmarks';
import type { FilterState } from '@/components/filters/FilterPanel';
import { timeSeriesFilterParams } from '@/pages/openings/useOpeningsChartData';
import type { RepertoireRowModel } from '@/pages/openings/useRepertoireRows';
import { resolveMatchSide } from '@/types/api';
import type { BookmarkTimeSeries, TimeSeriesRequest } from '@/types/position_bookmarks';

/** A most-played row has no bookmark; the endpoint just echoes this id back on its one series. */
export const MOST_PLAYED_ROW_SERIES_ID = 0;

interface UseOpeningRowTimeSeriesParams {
  row: RepertoireRowModel;
  debouncedFilters: FilterState;
}

interface UseOpeningRowTimeSeriesResult {
  series: BookmarkTimeSeries | null;
  isLoading: boolean;
  isError: boolean;
}

/**
 * The score-over-time series of one repertoire row, fetched on demand with the eval-expected
 * series. Every card requests its own one-opening series, bookmark and most-played alike, because
 * the middlegame-entry eval join is too costly to front-load for all bookmarks on page load (it
 * added 1.3 to 1.8 s for the heaviest dev user). A bookmark row keeps the table-wide series only
 * for its totals and verdict fields. Callers mount the hook only while the card's chart is open,
 * so mounting is the lazy trigger.
 */
export function useOpeningRowTimeSeries({
  row,
  debouncedFilters,
}: UseOpeningRowTimeSeriesParams): UseOpeningRowTimeSeriesResult {
  const { bookmark, color, fullHash } = row;
  const seriesId = bookmark?.id ?? MOST_PLAYED_ROW_SERIES_ID;
  const request: TimeSeriesRequest = useMemo(
    () => ({
      bookmarks: [
        {
          bookmark_id: seriesId,
          target_hash: bookmark?.target_hash ?? fullHash,
          match_side: bookmark ? resolveMatchSide(bookmark.match_side, color) : 'full',
          color,
        },
      ],
      ...timeSeriesFilterParams(debouncedFilters),
      include_expected_score: true,
    }),
    [seriesId, bookmark, fullHash, color, debouncedFilters],
  );

  const query = useTimeSeries(request);
  return {
    series: query.data?.series.find((s) => s.bookmark_id === seriesId) ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
