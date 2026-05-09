import { BookMarked, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { InfoPopover } from '@/components/ui/info-popover';
import { OpeningStatsSection, type OpeningStatsSectionDescriptor } from '@/components/stats/OpeningStatsSection';
import { ScoreChart } from '@/components/charts/ScoreChart';
import {
  EVAL_BASELINE_PAWNS_WHITE,
  EVAL_BASELINE_PAWNS_BLACK,
} from '@/lib/openingStatsZones';
import { sanArrayToPgn } from '@/lib/pgn';
import type { OpeningWDL, MostPlayedOpeningsResponse, BookmarkPhaseEntryItem } from '@/types/stats';
import type {
  PositionBookmarkResponse,
  TimeSeriesResponse,
} from '@/types/position_bookmarks';

export type WdlStatsRow = {
  wins: number;
  draws: number;
  losses: number;
  total: number;
  last_played_at: string | null;
};

type StatsTabProps = {
  bookmarks: PositionBookmarkResponse[];
  chartBookmarks: PositionBookmarkResponse[];
  wdlStatsMap: Record<number, WdlStatsRow>;
  bookmarkPhaseEntryByHash: Map<string, BookmarkPhaseEntryItem>;
  mostPlayedData: MostPlayedOpeningsResponse | undefined;
  mostPlayedLoading: boolean;
  mostPlayedError: boolean;
  tsData: TimeSeriesResponse | undefined;
  onOpenMoves: (opening: OpeningWDL, color: 'white' | 'black') => void;
  onOpenChartBookmarkGames: (bookmark: PositionBookmarkResponse) => void;
  onOpenGames: (pgn: string, color: 'white' | 'black') => void;
  onOpenSuggestions: () => void;
};

export function StatsTab({
  bookmarks,
  chartBookmarks,
  wdlStatsMap,
  bookmarkPhaseEntryByHash,
  mostPlayedData,
  mostPlayedLoading,
  mostPlayedError,
  tsData,
  onOpenMoves,
  onOpenChartBookmarkGames,
  onOpenGames,
  onOpenSuggestions,
}: StatsTabProps) {
  // Build bookmark rows for a given color (used when bookmarks exist)
  const buildBookmarkRows = (targetColor: 'white' | 'black'): OpeningWDL[] =>
    chartBookmarks
      .filter((b) => b.color === targetColor)
      .flatMap((b) => {
        const s = wdlStatsMap[b.id];
        if (!s || s.total <= 0) return [];
        const winPct = s.total > 0 ? (s.wins / s.total) * 100 : 0;
        const drawPct = s.total > 0 ? (s.draws / s.total) * 100 : 0;
        const lossPct = s.total > 0 ? (s.losses / s.total) * 100 : 0;
        const pe = bookmarkPhaseEntryByHash.get(b.target_hash);
        const row: OpeningWDL = {
          opening_eco: '',
          opening_name: b.label,
          display_name: b.label,
          label: b.label,
          pgn: sanArrayToPgn(b.moves),
          fen: b.fen,
          full_hash: b.target_hash,
          wins: s.wins,
          draws: s.draws,
          losses: s.losses,
          total: s.total,
          win_pct: winPct,
          draw_pct: drawPct,
          loss_pct: lossPct,
          avg_eval_pawns: pe?.avg_eval_pawns ?? null,
          eval_ci_low_pawns: pe?.eval_ci_low_pawns ?? null,
          eval_ci_high_pawns: pe?.eval_ci_high_pawns ?? null,
          eval_n: pe?.eval_n ?? 0,
          eval_p_value: pe?.eval_p_value ?? null,
          eval_confidence: pe?.eval_confidence ?? 'low',
          last_played_at: s.last_played_at,
        };
        return [row];
      })
      .sort((a, b) => b.total - a.total);

  const whiteBookmarkRows = bookmarks.length > 0 ? buildBookmarkRows('white') : [];
  const blackBookmarkRows = bookmarks.length > 0 ? buildBookmarkRows('black') : [];

  const bookmarkByHash = new Map<string, PositionBookmarkResponse>(
    chartBookmarks.map((b) => [b.target_hash, b]),
  );
  const handleOpenBookmarkGames = (opening: OpeningWDL) => {
    const bookmark = bookmarkByHash.get(opening.full_hash);
    if (bookmark) onOpenChartBookmarkGames(bookmark);
  };

  const whiteBookmarksSection: OpeningStatsSectionDescriptor = {
    key: 'white-bookmarks',
    color: 'white',
    title: (
      <span className="inline-flex items-center gap-1.5">
        <BookMarked className="h-5 w-5" />
        <span className="inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground bg-white" />
        White Opening Bookmarks
      </span>
    ),
    openings: whiteBookmarkRows,
    evalBaselinePawns:
      mostPlayedData?.eval_baseline_pawns_white ?? EVAL_BASELINE_PAWNS_WHITE,
    onOpenMoves,
    onOpenGames: (opening) => handleOpenBookmarkGames(opening),
    showAll: true,
    testId: 'bookmarks-white-section',
    cardTestIdPrefix: 'bookmarks-white-card',
  };

  const blackBookmarksSection: OpeningStatsSectionDescriptor = {
    key: 'black-bookmarks',
    color: 'black',
    title: (
      <span className="inline-flex items-center gap-1.5">
        <BookMarked className="h-5 w-5" />
        <span className="inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground bg-zinc-900" />
        Black Opening Bookmarks
      </span>
    ),
    openings: blackBookmarkRows,
    evalBaselinePawns:
      mostPlayedData?.eval_baseline_pawns_black ?? EVAL_BASELINE_PAWNS_BLACK,
    onOpenMoves,
    onOpenGames: (opening) => handleOpenBookmarkGames(opening),
    showAll: true,
    testId: 'bookmarks-black-section',
    cardTestIdPrefix: 'bookmarks-black-card',
  };

  const whiteMpoSection: OpeningStatsSectionDescriptor | null =
    mostPlayedData && mostPlayedData.white.length > 0
      ? {
          key: 'mpo-white',
          color: 'white',
          title: (
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground bg-white" />
              Most Played Openings as White
            </span>
          ),
          headingExtra: (
            <InfoPopover ariaLabel="White openings info" testId="mpo-white-info" side="top">
              Your most frequently played openings as White, based on the lichess opening table. Games passing through each opening's position are counted, including games that continued into deeper variations. Openings under 3 half-moves are excluded, so trivial trunks like 1.d4 don't dominate. Rows prefixed with "vs." are openings defined by Black's move (e.g. "vs. Sicilian Defense") that you faced as White.
            </InfoPopover>
          ),
          openings: mostPlayedData.white,
          evalBaselinePawns: mostPlayedData.eval_baseline_pawns_white,
          onOpenMoves,
          onOpenGames: (opening, color) => onOpenGames(opening.pgn, color),
          testId: 'mpo-white-section',
          cardTestIdPrefix: 'mpo-white-card',
        }
      : null;

  const blackMpoSection: OpeningStatsSectionDescriptor | null =
    mostPlayedData && mostPlayedData.black.length > 0
      ? {
          key: 'mpo-black',
          color: 'black',
          title: (
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground bg-zinc-900" />
              Most Played Openings as Black
            </span>
          ),
          headingExtra: (
            <InfoPopover ariaLabel="Black openings info" testId="mpo-black-info" side="top">
              Your most frequently played openings as Black, based on the lichess opening table. Games passing through each opening's position are counted, including games that continued into deeper variations. Openings under 3 half-moves are excluded, so trivial trunks like 1.e4 don't dominate. Rows prefixed with "vs." are openings defined by White's move (e.g. "vs. Blackmar-Diemer Gambit") that you faced as Black.
            </InfoPopover>
          ),
          openings: mostPlayedData.black,
          evalBaselinePawns: mostPlayedData.eval_baseline_pawns_black,
          onOpenMoves,
          onOpenGames: (opening, color) => onOpenGames(opening.pgn, color),
          testId: 'mpo-black-section',
          cardTestIdPrefix: 'mpo-black-card',
        }
      : null;

  return (
    <div className="flex flex-col gap-6">
      {/* Empty-state hint when there are no bookmarks at all */}
      {bookmarks.length === 0 && (
        <div className="charcoal-texture rounded-md p-4">
          <h2 className="text-lg font-medium mb-3">
            <span className="inline-flex items-center gap-1">
              <BookMarked className="h-5 w-5" />
              Bookmarked Openings
            </span>
          </h2>
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

      {/* 1. White Opening Bookmarks (full width) */}
      {whiteBookmarkRows.length > 0 && (
        <OpeningStatsSection section={whiteBookmarksSection} />
      )}

      {/* 2. Black Opening Bookmarks (full width) */}
      {blackBookmarkRows.length > 0 && (
        <OpeningStatsSection section={blackBookmarksSection} />
      )}

      {/* 3. Score over Time — only when bookmarks exist with time series data */}
      {bookmarks.length > 0 && tsData && (
        <div className="charcoal-texture rounded-md p-4">
          <ScoreChart bookmarks={chartBookmarks} series={tsData.series} />
        </div>
      )}

      {/* Loading state when bookmarks exist but tsData is not ready */}
      {bookmarks.length > 0 && chartBookmarks.length > 0 && !tsData && (
        <div className="charcoal-texture rounded-md p-4 text-center text-muted-foreground">
          Loading chart data...
        </div>
      )}

      {/* Most Played Openings — error / loading branches per CLAUDE.md */}
      {mostPlayedError && (
        <div
          className="charcoal-texture rounded-md p-4 text-center text-muted-foreground"
          data-testid="mpo-error"
        >
          Failed to load most-played openings. Something went wrong. Please try again in a moment.
        </div>
      )}
      {!mostPlayedError && mostPlayedLoading && !mostPlayedData && (
        <div
          className="charcoal-texture rounded-md p-4 text-center text-muted-foreground"
          data-testid="mpo-loading"
        >
          Loading most-played openings...
        </div>
      )}

      {/* 4. Most Played Openings as White (full width) */}
      {whiteMpoSection && <OpeningStatsSection section={whiteMpoSection} />}

      {/* 5. Most Played Openings as Black (full width) */}
      {blackMpoSection && <OpeningStatsSection section={blackMpoSection} />}
    </div>
  );
}
