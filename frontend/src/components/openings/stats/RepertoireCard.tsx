import { useMemo, useState } from 'react';
import { Archive, ArrowRightLeft, Bookmark, BookmarkMinus, BookmarkPlus, ChevronDown, Swords } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { ScoreChart } from '@/components/charts/ScoreChart';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { LoadError } from '@/components/ui/load-error';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { EvalCpuPlaceholder } from '@/components/stats/EvalCpuPlaceholder';
import { VerdictBar } from '@/components/openings/stats/VerdictBar';
import {
  EvalVerdictPopover,
  ScoreVerdictPopover,
} from '@/components/openings/stats/VerdictPopover';
import { useCreatePositionBookmark, useDeletePositionBookmark } from '@/hooks/usePositionBookmarks';
import { useReadiness } from '@/hooks/useReadiness';
import type { FilterState } from '@/components/filters/FilterPanel';
import { trackFeature } from '@/lib/analytics';
import { formatSignedGap } from '@/lib/gapBar';
import {
  EVAL_VERDICT_BAND,
  SCORE_VERDICT_BAND,
  evalBaselinePawns,
  formatEvalCompact,
  formatScorePercent,
  isFadedRow,
  openingVerdict,
  openingVerdictReason,
  openingVerdictSentence,
  scoreDelta,
  type OpeningVerdictInput,
} from '@/lib/openingVerdict';
import { pgnToSanArray } from '@/lib/pgn';
import { lastMoveSquares } from '@/lib/sanToSquares';
import { formatRelativeDate } from '@/lib/relativeDate';
import { UNRELIABLE_OPACITY } from '@/lib/theme';
import { cn } from '@/lib/utils';
import { useOpeningRowTimeSeries } from '@/pages/openings/useOpeningRowTimeSeries';
import type { RepertoireRowModel } from '@/pages/openings/useRepertoireRows';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';

const BOARD_SIZE = 128;
const NO_VALUE = '—';
const EVAL_LABEL = 'Eval after opening';
const EVAL_LABEL_SHORT = 'Eval';
const NOT_PLAYED_RECENTLY = 'Not played recently';
const LINK_BUTTON_CLASS =
  'flex items-center gap-1 text-sm text-brand-brown-light transition-colors hover:text-brand-brown-highlight disabled:opacity-50';

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

function scoreInput(row: RepertoireRowModel): OpeningVerdictInput {
  return {
    delta: scoreDelta(row.score),
    band: SCORE_VERDICT_BAND,
    confidence: row.scoreConfidence,
    games: row.games,
  };
}

/** Null when the row has no eval to judge. */
function evalInput(row: RepertoireRowModel): OpeningVerdictInput | null {
  if (row.avgEvalPawns === null || row.evalN <= 0) return null;
  return {
    delta: row.avgEvalPawns - evalBaselinePawns(row.color),
    band: EVAL_VERDICT_BAND,
    confidence: row.evalConfidence,
    // WR-02: the 20-game verdict floor applies to the eval sample (eval_n), not the game count:
    // the mean excludes mate/NULL evals and trims outliers, so a 40-game opening can rest on 11 evals.
    games: row.evalN,
  };
}

function ScoreBar({ row, testId }: { row: RepertoireRowModel; testId: string }) {
  const input = scoreInput(row);
  return (
    <VerdictBar
      delta={input.delta}
      band={SCORE_VERDICT_BAND}
      verdict={openingVerdict(input)}
      valueText={formatScorePercent(row.score)}
      testId={`${testId}-score-bar`}
      ariaLabel={`Score ${formatScorePercent(row.score)}, centred on 50%`}
      leading={<span className="text-muted-foreground">Score</span>}
      trailing={
        <ScoreVerdictPopover
          testId={`${testId}-score-info`}
          score={row.score}
          games={row.games}
          wins={row.wins}
          draws={row.draws}
          losses={row.losses}
          reason={openingVerdictReason(input)}
          ci99Low={row.scoreCi99Low}
          ci99High={row.scoreCi99High}
          pValue={row.scorePValue}
        />
      }
    />
  );
}

function EvalBar({ row, testId }: { row: RepertoireRowModel; testId: string }) {
  const { tier2 } = useReadiness();
  // Eval needs Stockfish analysis: show the pending placeholder until tier 2 is reached.
  if (!tier2) return <EvalCpuPlaceholder />;
  const input = evalInput(row);
  if (row.avgEvalPawns === null || input === null) {
    return (
      <div
        className="flex items-center justify-between text-sm text-muted-foreground"
        data-testid={`${testId}-eval-none`}
      >
        <span>{EVAL_LABEL}</span>
        <span>{NO_VALUE}</span>
      </div>
    );
  }
  const baseline = evalBaselinePawns(row.color);
  return (
    <VerdictBar
      delta={input.delta}
      band={EVAL_VERDICT_BAND}
      verdict={openingVerdict(input)}
      valueText={formatEvalCompact(row.avgEvalPawns)}
      zeroTickDelta={-baseline}
      centreSwatch={row.color}
      testId={`${testId}-eval-bar`}
      ariaLabel={`${EVAL_LABEL} ${formatSignedGap(row.avgEvalPawns)}, centred on an average ${row.color} game at ${formatSignedGap(baseline)}`}
      leading={
        // Phones shorten the label so it fits beside the value on one line.
        <span className="text-muted-foreground">
          <span className="sm:hidden">{EVAL_LABEL_SHORT}</span>
          <span className="max-sm:hidden">{EVAL_LABEL}</span>
        </span>
      }
      trailing={
        <EvalVerdictPopover
          testId={`${testId}-eval-info`}
          label={EVAL_LABEL}
          avgEvalPawns={row.avgEvalPawns}
          evalN={row.evalN}
          color={row.color}
          reason={openingVerdictReason(input)}
          ci99Low={row.evalCi99Low}
          ci99High={row.evalCi99High}
          pValue={row.evalPValue}
        />
      }
    />
  );
}

/** The Score and Eval verdicts read together in one muted line; nothing when neither stands out. */
function VerdictSentence({ row, testId }: { row: RepertoireRowModel; testId: string }) {
  const { tier2 } = useReadiness();
  const evalIn = tier2 ? evalInput(row) : null;
  const sentence = openingVerdictSentence(
    openingVerdictReason(scoreInput(row)),
    evalIn ? openingVerdictReason(evalIn) : null,
  );
  if (!sentence) return null;
  return (
    <p className="text-sm text-muted-foreground" data-testid={`${testId}-sentence`}>
      {sentence}
    </p>
  );
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
      className={LINK_BUTTON_CLASS}
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
  const { series, isLoading, isError } = useOpeningRowTimeSeries({
    row,
    debouncedFilters,
    enabled: true,
  });
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
        className={LINK_BUTTON_CLASS}
        aria-label="Open this line in the Move Explorer"
        data-testid={`${testId}-btn-moves`}
        onClick={onOpenMoves}
      >
        <ArrowRightLeft className="h-3.5 w-3.5 shrink-0" />
        <span>Moves</span>
      </button>
      <button
        type="button"
        className={LINK_BUTTON_CLASS}
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
        className={cn(LINK_BUTTON_CLASS, 'ml-auto')}
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
 * One repertoire opening as a card: name header with the last-played date, a 128 px board beside the WDL bar, the Score
 * and Eval after opening verdict bars, the Moves / Games / Bookmark links and a toggle that
 * opens the score-over-time chart under them. A one-line sentence reads the two verdicts together.
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
  // Any card outside the current repertoire window: stale bookmarks and Played before rows.
  const stale = !row.isCurrent;
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

  return (
    <Card
      data-testid={testId}
      style={isFadedRow(row.games) ? { opacity: UNRELIABLE_OPACITY } : undefined}
    >
      <CardHeader as="h4" size="compact" className="items-start text-base">
        {row.kind === 'bookmark' && (
          <Bookmark className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" aria-label="Bookmarked" />
        )}
        <span className="min-w-0 break-words" data-testid={`${testId}-name`}>
          {row.name}
        </span>
        {(row.lastPlayedAt || stale) && (
          <span
            className="ml-auto flex shrink-0 items-center gap-1.5 text-sm font-normal whitespace-nowrap text-muted-foreground"
            data-testid={`${testId}-last-played`}
          >
            {row.lastPlayedAt && formatRelativeDate(row.lastPlayedAt)}
            {/* Indicator only, not an action: marks openings outside the current repertoire. */}
            {stale && (
              <Archive
                className="h-4 w-4"
                role="img"
                aria-label={NOT_PLAYED_RECENTLY}
                data-testid={`${testId}-stale-icon`}
              >
                <title>{NOT_PLAYED_RECENTLY}</title>
              </Archive>
            )}
          </span>
        )}
      </CardHeader>
      <CardBody className="flex flex-col gap-3">
        <div className="flex items-start gap-3">
          <LazyMiniBoard
            fen={row.fen}
            flipped={row.color === 'black'}
            size={BOARD_SIZE}
            lastMove={lastMove}
          />
          <div className="flex min-w-0 flex-1 flex-col gap-2.5">
            <MiniWDLBar win_pct={row.winPct} draw_pct={row.drawPct} loss_pct={row.lossPct} />
            <ScoreBar row={row} testId={testId} />
            <EvalBar row={row} testId={testId} />
          </div>
        </div>
        <VerdictSentence row={row} testId={testId} />
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
