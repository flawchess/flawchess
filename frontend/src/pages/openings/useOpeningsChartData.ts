import { useMemo } from 'react';
import { Chess } from 'chess.js';
import { useBookmarkPhaseEntryMetrics } from '@/hooks/useStats';
import { useTimeSeries } from '@/hooks/usePositionBookmarks';
import { getArrowColor } from '@/lib/arrowColor';
import { rangeToQueryParams } from '@/lib/opponentStrength';
import { resolveDateRange, dateRangeToWireParams } from '@/lib/recency';
import { resolveMatchSide } from '@/types/api';
import type { BoardArrow } from '@/components/board/ChessBoard';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { Color, NextMovesResponse } from '@/types/api';
import type {
  PositionBookmarkResponse,
  TimeSeriesRequest,
  TimeSeriesResponse,
} from '@/types/position_bookmarks';
import type { BookmarkPhaseEntryItem } from '@/types/stats';
import type { HighlightedMove } from './useDeepLinkHighlight';

export type UseOpeningsChartDataParams = {
  bookmarks: PositionBookmarkResponse[];
  nextMovesData: NextMovesResponse | undefined;
  position: string;
  hoveredMove: string | null;
  highlightedMove: HighlightedMove | null;
  pulseActive: boolean;
  debouncedFilters: FilterState;
};

/** The sidebar filters as /openings/time-series request params (shared with the per-row series). */
export function timeSeriesFilterParams(
  filters: FilterState,
): Omit<TimeSeriesRequest, 'bookmarks'> {
  return {
    time_control: filters.timeControls,
    platform: filters.platforms,
    rated: filters.rated,
    opponent_type: filters.opponentType,
    ...rangeToQueryParams(filters.opponentStrength),
    // Recency flows as resolved date bounds (from_date/to_date)
    // so the bookmark card WDL bar, game count, and Score % respond to the filter.
    ...dateRangeToWireParams(resolveDateRange(filters)),
  };
}

export type OpeningsChartData = {
  boardArrows: BoardArrow[];
  bookmarkPhaseEntryByHash: Map<string, BookmarkPhaseEntryItem>;
  tsData: TimeSeriesResponse | undefined;
};

/**
 * Query-derivation cluster for the Openings page: board arrows from next-move
 * frequencies, per-bookmark phase-entry metrics, and the per-bookmark time series
 * (every bookmark feeds both requests). Matches useOpeningsHandlers.ts's shape (one typed
 * params object in, one named data interface out).
 */
export function useOpeningsChartData(params: UseOpeningsChartDataParams): OpeningsChartData {
  const {
    bookmarks,
    nextMovesData,
    position,
    hoveredMove,
    highlightedMove,
    pulseActive,
    debouncedFilters,
  } = params;

  // Board arrows derived from next move frequencies. The matching arrow on a
  // deep-link gets isHighlightPulse=true so its <path> pulses briefly. The
  // arrow's COLOR stays whatever getArrowColor returned (score zone) — pulse
  // only modulates opacity. Row tint comes from the score zone too, so a
  // highlighted row pulses through grey alpha levels and lands on the row's
  // natural score-zone color.
  const boardArrows = useMemo(() => {
    if (!nextMovesData?.moves.length) return [];

    const chessInstance = new Chess(position);
    const legalMoves = chessInstance.moves({ verbose: true });
    const moveMap = new Map(legalMoves.map(m => [m.san, { from: m.from, to: m.to }]));

    const moves = nextMovesData.moves;
    const maxCount = Math.max(...moves.map(m => m.game_count), 1);

    return moves
      .map(entry => {
        const squares = moveMap.get(entry.move_san);
        if (!squares) return null;
        const isHovered = entry.move_san === hoveredMove;
        const isHighlightPulse = pulseActive && highlightedMove !== null && entry.move_san === highlightedMove.san;
        return {
          startSquare: squares.from,
          endSquare: squares.to,
          color: getArrowColor(entry.score, entry.game_count, entry.confidence),
          width: entry.game_count / maxCount,
          isHovered,
          isHighlightPulse,
        };
      })
      .filter((a): a is NonNullable<typeof a> => a !== null);
  }, [nextMovesData, position, hoveredMove, highlightedMove, pulseActive]);

  // Per-bookmark MG/EG entry eval metrics.
  // Without this, bookmark rows in the Stats subtab tables permanently render with
  // eval_n=0 / "low" / "0 games" because buildBookmarkRows hardcoded those fields.
  const bookmarkMetricsRequest = useMemo(
    () =>
      bookmarks.map((b) => ({
        target_hash: b.target_hash,
        match_side: resolveMatchSide(b.match_side, (b.color ?? 'white') as Color),
        color: b.color,
      })),
    [bookmarks],
  );
  const { data: bookmarkPhaseEntryData } = useBookmarkPhaseEntryMetrics(
    bookmarkMetricsRequest,
    {
      recency: debouncedFilters.recency,
      customRange: debouncedFilters.customRange,
      timeControls: debouncedFilters.timeControls,
      platforms: debouncedFilters.platforms,
      rated: debouncedFilters.rated,
      opponentType: debouncedFilters.opponentType,
      opponentStrength: debouncedFilters.opponentStrength,
    },
  );
  const bookmarkPhaseEntryByHash = useMemo(() => {
    const map = new Map<string, NonNullable<typeof bookmarkPhaseEntryData>['items'][number]>();
    for (const item of bookmarkPhaseEntryData?.items ?? []) {
      map.set(item.target_hash, item);
    }
    return map;
  }, [bookmarkPhaseEntryData]);

  const timeSeriesRequest: TimeSeriesRequest | null = useMemo(() => {
    if (bookmarks.length === 0) return null;
    return {
      bookmarks: bookmarks.map((b) => ({
        bookmark_id: b.id,
        target_hash: b.target_hash,
        match_side: resolveMatchSide(b.match_side, (b.color ?? 'white') as Color),
        color: b.color,
      })),
      ...timeSeriesFilterParams(debouncedFilters),
    };
  }, [bookmarks, debouncedFilters]);

  const { data: tsData } = useTimeSeries(timeSeriesRequest);

  return {
    boardArrows,
    bookmarkPhaseEntryByHash,
    tsData,
  };
}
