import { useMemo, useState } from 'react';
import { ArrowRightLeft, Bookmark, BookmarkMinus, BookmarkPlus, ChevronDown, Swords } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { ScoreChart } from '@/components/charts/ScoreChart';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { LoadError } from '@/components/ui/load-error';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { ScoreLine } from '@/components/openings/stats/ScoreLine';
import {
  CardVerdictGrid,
  EvalVerdictLine,
  LastPlayedIndicator,
  VerdictSentence,
} from '@/components/openings/stats/CardParts';
import { CARD_BOARD_SIZE, CARD_LINK_BUTTON_CLASS } from '@/components/openings/stats/cardLayout';
import { useCreatePositionBookmark, useDeletePositionBookmark } from '@/hooks/usePositionBookmarks';
import type { FilterState } from '@/components/filters/FilterPanel';
import { trackFeature } from '@/lib/analytics';
import {
  isFadedRow,
  scoreAccentColor,
  scoreVerdictInput,
  type EvalSample,
} from '@/lib/openingVerdict';
import { pgnToSanArray } from '@/lib/pgn';
import { lastMoveSquares } from '@/lib/sanToSquares';
import { UNRELIABLE_OPACITY } from '@/lib/theme';
import { cn } from '@/lib/utils';
import { useOpeningRowTimeSeries } from '@/pages/openings/useOpeningRowTimeSeries';
import type { RepertoireRowModel } from '@/pages/openings/useRepertoireRows';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';

interface RepertoireCardProps {
  row: RepertoireRowModel;
  /** Position in the list; builds the testids (names repeat once ECO codes are dropped). */
  index: number;
  /** Sidebar filters (debounced) that scope the lazily fetched score series. */
  debouncedFilters: FilterState;
  onOpenMoves: (pgn: string, color: 'white' | 'black') => void;
  onOpenGames: (pgn: string, color: 'white' | 'black') => void;
  onOpenBookmarkGames: (bookmark: PositionBookmarkResponse) => void;
}

function evalSample(row: RepertoireRowModel): EvalSample {
  return {
    avgEvalPawns: row.avgEvalPawns,
    evalN: row.evalN,
    confidence: row.evalConfidence,
    color: row.color,
  };
}

/**
 * Bookmark / Remove bookmark link. Both mutations invalidate the bookmark and most-played
 * queries, so the card moves between the groups once the lists refetch. No Umami event: the
 * bookmark row is DB-known.
 */
function BookmarkLink({ row, testId }: { row: RepertoireRowModel; testId: string }) {
  const create = useCreatePositionBookmark();
  const remove = useDeletePositionBookmark();
  const bookmark = row.bookmark;
  const handleClick = () => {
    if (bookmark) {
      remove.mutate(bookmark.id);
      return;
    }
    create.mutate({
      label: row.name,
      target_hash: row.fullHash,
      fen: row.fen,
      moves: pgnToSanArray(row.moveLine),
      color: row.color,
      match_side: 'both',
      is_flipped: row.color === 'black',
    });
  };
  const Icon = bookmark ? BookmarkMinus : BookmarkPlus;
  return (
    <button
      type="button"
      className={CARD_LINK_BUTTON_CLASS}
      disabled={create.isPending || remove.isPending}
      onClick={handleClick}
      data-testid={`${testId}-btn-bookmark`}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" />
      <span>{bookmark ? 'Remove bookmark' : 'Bookmark'}</span>
    </button>
  );
}

/** Score over time: the rolling score line plus grey weekly game bars (D-00). */
function ScoreOverTime({
  row,
  testId,
  debouncedFilters,
}: {
  row: RepertoireRowModel;
  testId: string;
  debouncedFilters: FilterState;
}) {
  // The block only mounts while the chart is open, so mounting is the lazy trigger.
  const { series, isLoading, isError } = useOpeningRowTimeSeries({ row, debouncedFilters });
  return (
    <div className="min-w-0 border-t border-card-edge pt-3" data-testid={`${testId}-chart`}>
      {isError ? (
        <LoadError resource="the score chart" data-testid={`${testId}-chart-error`} />
      ) : isLoading || !series ? (
        <p className="text-sm text-muted-foreground" data-testid={`${testId}-chart-loading`}>
          Loading score chart...
        </p>
      ) : (
        <ScoreChart series={series} showVolume testId={`${testId}-score-chart`} />
      )}
    </div>
  );
}

function CardLinks({
  row,
  testId,
  chartOpen,
  onToggleChart,
  onOpenMoves,
  onOpenGames,
}: {
  row: RepertoireRowModel;
  testId: string;
  chartOpen: boolean;
  onToggleChart: () => void;
  onOpenMoves: () => void;
  onOpenGames: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <button
        type="button"
        className={CARD_LINK_BUTTON_CLASS}
        aria-label="Open this line in the Move Explorer"
        data-testid={`${testId}-btn-moves`}
        onClick={onOpenMoves}
      >
        <ArrowRightLeft className="h-3.5 w-3.5 shrink-0" />
        <span>Moves</span>
      </button>
      <button
        type="button"
        className={CARD_LINK_BUTTON_CLASS}
        aria-label={`View ${row.games} games for this line`}
        data-testid={`${testId}-btn-games`}
        onClick={onOpenGames}
      >
        <Swords className="h-3.5 w-3.5 shrink-0" />
        <span className="tabular-nums">{row.games.toLocaleString('en-US')}</span>
        <span>Games</span>
      </button>
      <BookmarkLink row={row} testId={testId} />
      <button
        type="button"
        className={cn(CARD_LINK_BUTTON_CLASS, 'ml-auto')}
        aria-expanded={chartOpen}
        onClick={onToggleChart}
        data-testid={`${testId}-toggle`}
      >
        <span>Score over time</span>
        <ChevronDown
          className={cn('h-4 w-4 transition-transform', chartOpen && 'rotate-180')}
          aria-hidden="true"
        />
      </button>
    </div>
  );
}

/**
 * One repertoire opening as a card: name header with the last-played date, a 128 px board beside the score line, the WDL
 * bar and the Eval after opening verdict bar, the Moves / Games / Bookmark links and a toggle that
 * opens the score-over-time chart under them. A sentence under the eval bar reads the two verdicts together.
 * Cards with fewer than 20 games are faded.
 */
export function RepertoireCard({
  row,
  index,
  debouncedFilters,
  onOpenMoves,
  onOpenGames,
  onOpenBookmarkGames,
}: RepertoireCardProps) {
  const [chartOpen, setChartOpen] = useState(false);
  const testId = `repertoire-card-${index}`;
  const lastMove = useMemo(
    () => lastMoveSquares(pgnToSanArray(row.moveLine)) ?? undefined,
    [row.moveLine],
  );

  const handleToggleChart = () => {
    // Discovery only: track the expand, never the collapse.
    if (!chartOpen) trackFeature('panel-open', { target: 'opening-row-expand' });
    setChartOpen((prev) => !prev);
  };
  const handleGames = () => {
    if (row.bookmark) onOpenBookmarkGames(row.bookmark);
    else onOpenGames(row.moveLine, row.color);
  };

  const scoreInput = scoreVerdictInput(row.score, row.scoreConfidence, row.games);
  const sample = evalSample(row);

  return (
    <Card
      data-testid={testId}
      accentColor={scoreAccentColor(scoreInput)}
      style={isFadedRow(row.games) ? { opacity: UNRELIABLE_OPACITY } : undefined}
    >
      <CardHeader as="h4" size="compact" className="items-start text-base">
        {row.kind === 'bookmark' && (
          <Bookmark className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" aria-label="Bookmarked" />
        )}
        <span className="min-w-0 break-words" data-testid={`${testId}-name`}>
          {row.name}
        </span>
        {/* Stale = outside the current repertoire window: stale bookmarks and Played before rows. */}
        <LastPlayedIndicator lastPlayedAt={row.lastPlayedAt} stale={!row.isCurrent} testId={testId} />
      </CardHeader>
      <CardBody className="flex flex-col gap-3">
        <CardVerdictGrid
          board={
            <LazyMiniBoard
              fen={row.fen}
              flipped={row.color === 'black'}
              size={CARD_BOARD_SIZE}
              lastMove={lastMove}
            />
          }
          metrics={
            <>
              <div className="space-y-1.5">
                <ScoreLine
                  score={row.score}
                  games={row.games}
                  wins={row.wins}
                  draws={row.draws}
                  losses={row.losses}
                  input={scoreInput}
                  ciLow={row.scoreCiLow}
                  ciHigh={row.scoreCiHigh}
                  pValue={row.scorePValue}
                  testId={testId}
                />
                <MiniWDLBar win_pct={row.winPct} draw_pct={row.drawPct} loss_pct={row.lossPct} />
              </div>
              <EvalVerdictLine
                sample={sample}
                ciLow={row.evalCiLow}
                ciHigh={row.evalCiHigh}
                pValue={row.evalPValue}
                testId={testId}
              />
            </>
          }
          sentence={<VerdictSentence scoreInput={scoreInput} evalSample={sample} testId={testId} />}
        />
        <CardLinks
          row={row}
          testId={testId}
          chartOpen={chartOpen}
          onToggleChart={handleToggleChart}
          onOpenMoves={() => onOpenMoves(row.moveLine, row.color)}
          onOpenGames={handleGames}
        />
        {chartOpen && (
          <ScoreOverTime row={row} testId={testId} debouncedFilters={debouncedFilters} />
        )}
      </CardBody>
    </Card>
  );
}
