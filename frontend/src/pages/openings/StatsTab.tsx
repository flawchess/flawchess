import { Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LoadError } from '@/components/ui/load-error';
import { OpeningColorSwitch } from '@/components/openings/stats/OpeningColorSwitch';
import { OpeningFindings } from '@/components/openings/stats/OpeningFindings';
import { RepertoireList } from '@/components/openings/stats/RepertoireList';
import type { FilterState } from '@/components/filters/FilterPanel';
import { useRepertoireRows } from '@/pages/openings/useRepertoireRows';
import type { Color } from '@/types/api';
import type { OpeningInsightFinding } from '@/types/insights';
import type { MostPlayedOpeningsResponse, BookmarkPhaseEntryItem } from '@/types/stats';
import type {
  PositionBookmarkResponse,
  TimeSeriesResponse,
} from '@/types/position_bookmarks';

type StatsTabProps = {
  /** The colour whose table is shown (the sticky White | Black switch, D-00). */
  color: Color;
  onColorChange: (color: Color) => void;
  bookmarks: PositionBookmarkResponse[];
  bookmarkPhaseEntryByHash: Map<string, BookmarkPhaseEntryItem>;
  mostPlayedData: MostPlayedOpeningsResponse | undefined;
  mostPlayedLoading: boolean;
  mostPlayedError: boolean;
  tsData: TimeSeriesResponse | undefined;
  onOpenSuggestions: () => void;
  /** Sidebar filters (debounced) that scope the findings request. */
  debouncedFilters: FilterState;
  /** Finding card deep links: Moves tab with the pulse highlight, and Games tab. */
  onOpenFinding: (finding: OpeningInsightFinding) => void;
  onOpenFindingGames: (finding: OpeningInsightFinding) => void;
  /** Expanded-row links: Moves tab, Games tab (most-played rows), Games tab (bookmark rows). */
  onOpenMoves: (pgn: string, color: Color) => void;
  onOpenGames: (pgn: string, color: Color) => void;
  onOpenBookmarkGames: (bookmark: PositionBookmarkResponse) => void;
};

export function StatsTab({
  color,
  onColorChange,
  bookmarks,
  bookmarkPhaseEntryByHash,
  mostPlayedData,
  mostPlayedLoading,
  mostPlayedError,
  tsData,
  onOpenSuggestions,
  debouncedFilters,
  onOpenFinding,
  onOpenFindingGames,
  onOpenMoves,
  onOpenGames,
  onOpenBookmarkGames,
}: StatsTabProps) {
  const { bookmarkRows, currentRows, pastRows } = useRepertoireRows({
    color,
    mostPlayedData,
    bookmarks,
    tsData,
    bookmarkPhaseEntryByHash,
  });
  const currentCutoff =
    (color === 'white' ? mostPlayedData?.current_cutoff_white : mostPlayedData?.current_cutoff_black) ??
    null;
  const showRepertoire = !mostPlayedError && (mostPlayedData !== undefined || bookmarkRows.length > 0);

  return (
    <div className="flex flex-col gap-6">
      {/* Desktop sticky colour bar. Phones render the same switch inside the sticky Filters
          row in Openings.tsx (one sticky row, not two). No ancestor may set overflow-*
          or the bar stops sticking. */}
      <div
        className="hidden lg:flex sticky top-0 z-20 items-center justify-end py-2 bg-background/80 backdrop-blur-sm"
        data-testid="opening-stats-color-bar"
      >
        <OpeningColorSwitch idPrefix="desktop" selected={color} onSelect={onColorChange} />
      </div>

      {/* Empty-state hint when there are no bookmarks at all */}
      {bookmarks.length === 0 && (
        <div className="charcoal-texture rounded-md p-4">
          <h2 className="font-brand text-lg font-semibold text-foreground mb-3">Bookmarked Openings</h2>
          <p
            className="text-sm italic text-muted-foreground mb-3"
            data-testid="bookmarks-tip"
          >
            <span className="font-semibold text-foreground/80">Tip:</span> Save some openings as bookmarks to see your results and win rate over time here. Each bookmark has a Piece filter setting (Mine/Opponent/Both) that controls how positions are matched. Use the Suggest button to pick from your most-played positions.
          </p>
          <Button
            size="lg"
            variant="brand-outline"
            className="w-full"
            onClick={onOpenSuggestions}
            data-testid="btn-suggest-bookmarks-empty"
          >
            <Sparkles className="h-4 w-4" />
            Suggest
          </Button>
        </div>
      )}

      {/* Most Played Openings — error / loading branches per CLAUDE.md */}
      {mostPlayedError && (
        <LoadError
          resource="most-played openings"
          className="charcoal-texture rounded-md p-4 text-center"
          data-testid="mpo-error"
        />
      )}
      {!mostPlayedError && mostPlayedLoading && !mostPlayedData && (
        <div
          className="charcoal-texture rounded-md p-4 text-center text-muted-foreground"
          data-testid="mpo-loading"
        >
          Loading most-played openings...
        </div>
      )}

      {/* Repertoire cards of the selected colour: bookmarks, most played, played before */}
      {showRepertoire && (
        <RepertoireList
          color={color}
          bookmarkRows={bookmarkRows}
          currentRows={currentRows}
          pastRows={pastRows}
          currentCutoff={currentCutoff}
          onOpenSuggestions={onOpenSuggestions}
          debouncedFilters={debouncedFilters}
          onOpenMoves={onOpenMoves}
          onOpenGames={onOpenGames}
          onOpenBookmarkGames={onOpenBookmarkGames}
        />
      )}

      {/* Findings of the selected colour (99%-gated cards, Not clear yet) below the repertoire */}
      <OpeningFindings
        color={color}
        debouncedFilters={debouncedFilters}
        onOpenMoves={onOpenFinding}
        onOpenGames={onOpenFindingGames}
      />
    </div>
  );
}
