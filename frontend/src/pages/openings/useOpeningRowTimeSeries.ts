import { useMemo } from 'react';
import { useTimeSeries } from '@/hooks/usePositionBookmarks';
import type { FilterState } from '@/components/filters/FilterPanel';
import { timeSeriesFilterParams } from '@/pages/openings/useOpeningsChartData';
import type { RepertoireRowModel } from '@/pages/openings/useRepertoireRows';
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
 * The score-over-time series of one repertoire row. Bookmark rows already carry theirs from the
 * table-wide request, so they issue nothing. A most-played row requests its own series on the
 * full-position hash (match side "full"). Callers mount the hook only while the card's chart is
 * open, so mounting is the lazy trigger.
 */
export function useOpeningRowTimeSeries({
  row,
  debouncedFilters,
}: UseOpeningRowTimeSeriesParams): UseOpeningRowTimeSeriesResult {
  const needsRequest = row.series === null;
  const request: TimeSeriesRequest | null = useMemo(() => {
    if (!needsRequest) return null;
    return {
      bookmarks: [
        {
          bookmark_id: MOST_PLAYED_ROW_SERIES_ID,
          target_hash: row.fullHash,
          match_side: 'full',
          color: row.color,
        },
      ],
      ...timeSeriesFilterParams(debouncedFilters),
    };
  }, [needsRequest, row.fullHash, row.color, debouncedFilters]);

  const query = useTimeSeries(request);
  if (row.series !== null) return { series: row.series, isLoading: false, isError: false };
  return {
    series: query.data?.series.find((s) => s.bookmark_id === MOST_PLAYED_ROW_SERIES_ID) ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
