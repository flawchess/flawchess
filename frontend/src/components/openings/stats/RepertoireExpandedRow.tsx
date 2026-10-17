import { ArrowRightLeft, BookmarkMinus, BookmarkPlus, Swords } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { ScoreChart } from '@/components/charts/ScoreChart';
import { Button } from '@/components/ui/button';
import { LoadError } from '@/components/ui/load-error';
import { EvalCpuPlaceholder } from '@/components/stats/EvalCpuPlaceholder';
import { VerdictBar } from '@/components/openings/stats/VerdictBar';
import {
  EvalVerdictPopover,
  ScoreVerdictPopover,
} from '@/components/openings/stats/VerdictPopover';
import { useCreatePositionBookmark, useDeletePositionBookmark } from '@/hooks/usePositionBookmarks';
import { useReadiness } from '@/hooks/useReadiness';
import type { FilterState } from '@/components/filters/FilterPanel';
import { formatSignedGap } from '@/lib/gapBar';
import {
  EVAL_VERDICT_BAND,
  SCORE_VERDICT_BAND,
  evalBaselinePawns,
  formatEvalCompact,
  formatScorePercent,
  openingVerdict,
  openingVerdictReason,
  scoreDelta,
} from '@/lib/openingVerdict';
import { pgnToSanArray } from '@/lib/pgn';
import { formatRelativeDate } from '@/lib/relativeDate';
import { useOpeningRowTimeSeries } from '@/pages/openings/useOpeningRowTimeSeries';
import type { RepertoireRowModel } from '@/pages/openings/useRepertoireRows';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';

const BOARD_SIZE = 200;
const NO_VALUE = '—';
const EVAL_LABEL = 'Eval after opening';
const SCORE_HINT = 'Wins plus half the draws; the middle tick is 50%';
const EVAL_HINT = 'Engine evaluation when the middlegame starts, from your side';

interface RepertoireExpandedRowProps {
  row: RepertoireRowModel;
  /** Table row index; builds the testids (names repeat once ECO codes are dropped). */
  index: number;
  /** Sidebar filters (debounced) that scope the lazily fetched score series. */
  debouncedFilters: FilterState;
  onOpenMoves: (pgn: string, color: 'white' | 'black') => void;
  onOpenGames: (pgn: string, color: 'white' | 'black') => void;
  onOpenBookmarkGames: (bookmark: PositionBookmarkResponse) => void;
}

function BarLabel({ label, hint }: { label: string; hint: string }) {
  return (
    <span className="flex flex-wrap items-baseline gap-x-2">
      <span className="font-medium text-foreground">{label}</span>
      <span className="text-muted-foreground">{hint}</span>
    </span>
  );
}

function ScoreBar({ row, testId }: { row: RepertoireRowModel; testId: string }) {
  const input = {
    delta: scoreDelta(row.score),
    band: SCORE_VERDICT_BAND,
    confidence: row.scoreConfidence,
    games: row.games,
  };
  return (
    <VerdictBar
      delta={input.delta}
      band={SCORE_VERDICT_BAND}
      verdict={openingVerdict(input)}
      valueText={formatScorePercent(row.score)}
      testId={`${testId}-score-bar`}
      ariaLabel={`Score ${formatScorePercent(row.score)}, centred on 50%`}
      leading={<BarLabel label="Score" hint={SCORE_HINT} />}
      trailing={
        <ScoreVerdictPopover
          testId={`${testId}-score-bar-info`}
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
  if (row.avgEvalPawns === null || row.evalN <= 0) {
    return (
      <div className="space-y-1.5" data-testid={`${testId}-eval-bar-none`}>
        <BarLabel label={EVAL_LABEL} hint={EVAL_HINT} />
        <span className="text-muted-foreground">{NO_VALUE}</span>
      </div>
    );
  }
  const baseline = evalBaselinePawns(row.color);
  const input = {
    delta: row.avgEvalPawns - baseline,
    band: EVAL_VERDICT_BAND,
    confidence: row.evalConfidence,
    // WR-02: the 20-game verdict floor applies to the eval sample (eval_n), not the game count:
    // the mean excludes mate/NULL evals and trims outliers, so a 40-game opening can rest on 11 evals.
    games: row.evalN,
  };
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
      leading={<BarLabel label={EVAL_LABEL} hint={EVAL_HINT} />}
      trailing={
        <EvalVerdictPopover
          testId={`${testId}-eval-bar-info`}
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

/**
 * Bookmark / Remove bookmark link. Both mutations invalidate the bookmark and most-played
 * queries, so the row moves between the groups once the lists refetch. No Umami event: the
 * bookmark row is DB-known.
 */
function BookmarkLink({ row, testId }: { row: RepertoireRowModel; testId: string }) {
  const create = useCreatePositionBookmark();
  const remove = useDeletePositionBookmark();
  const bookmark = row.bookmark;
  const pending = create.isPending || remove.isPending;
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
    <Button
      size="sm"
      variant="brand-outline"
      className="justify-start"
      disabled={pending}
      onClick={handleClick}
      data-testid={`${testId}-btn-bookmark`}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" />
      <span>{bookmark ? 'Remove bookmark' : 'Bookmark'}</span>
    </Button>
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
  // The block only mounts while the row is expanded, so mounting is the lazy trigger.
  const { series, isLoading, isError } = useOpeningRowTimeSeries({
    row,
    debouncedFilters,
    enabled: true,
  });
  const windowSize = series?.data[0]?.window_size;
  return (
    <div className="min-w-0" data-testid={`${testId}-chart`}>
      <h4 className="mb-2 text-sm font-semibold text-muted-foreground">Score over time</h4>
      {isError ? (
        <LoadError resource="the score chart" data-testid={`${testId}-chart-error`} />
      ) : isLoading || !series ? (
        <p className="text-sm text-muted-foreground" data-testid={`${testId}-chart-loading`}>
          Loading score chart...
        </p>
      ) : (
        <>
          <ScoreChart series={series} showVolume testId={`${testId}-score-chart`} />
          {windowSize !== undefined && (
            <p className="mt-1 text-sm text-muted-foreground" data-testid={`${testId}-chart-caption`}>
              Line: your score over your last {windowSize} games in this opening · grey bars: games
              per week · dashed line = 50% · palm tree = a break of 3+ months
              {row.lastPlayedAt ? ` · last played ${formatRelativeDate(row.lastPlayedAt)}` : ''}
            </p>
          )}
        </>
      )}
    </div>
  );
}

/**
 * Detail panel under an expanded repertoire row (D-00): a 200 px board (size={200}) with the Moves / Games
 * links (stacked right of the board on phones), the Score and Eval after opening verdict bars.
 */
export function RepertoireExpandedRow({
  row,
  index,
  debouncedFilters,
  onOpenMoves,
  onOpenGames,
  onOpenBookmarkGames,
}: RepertoireExpandedRowProps) {
  const testId = `repertoire-row-${index}`;
  const handleGames = () => {
    if (row.bookmark) onOpenBookmarkGames(row.bookmark);
    else onOpenGames(row.moveLine, row.color);
  };
  return (
    <div
      className="grid gap-4 md:grid-cols-[200px_minmax(0,1fr)] md:gap-6 xl:grid-cols-[200px_minmax(0,1fr)_320px]"
      data-testid={`${testId}-expanded`}
    >
      <div className="flex items-start gap-4 md:flex-col md:gap-2.5">
        <LazyMiniBoard fen={row.fen} flipped={row.color === 'black'} size={BOARD_SIZE} />
        <div className="flex min-w-0 flex-col gap-3.5 md:flex-row md:flex-wrap md:gap-x-4 md:gap-y-2">
          <Button
            size="sm"
            variant="brand-outline"
            className="justify-start"
            aria-label="Open this line in the Move Explorer"
            data-testid={`${testId}-btn-moves`}
            onClick={() => onOpenMoves(row.moveLine, row.color)}
          >
            <ArrowRightLeft className="h-3.5 w-3.5 shrink-0" />
            <span>Moves</span>
          </Button>
          <Button
            size="sm"
            variant="brand-outline"
            className="justify-start"
            aria-label={`View ${row.games} games for this line`}
            data-testid={`${testId}-btn-games`}
            onClick={handleGames}
          >
            <Swords className="h-3.5 w-3.5 shrink-0" />
            <span className="tabular-nums">{row.games.toLocaleString('en-US')}</span>
            <span>Games</span>
          </Button>
          <BookmarkLink row={row} testId={testId} />
        </div>
      </div>
      <div className="flex min-w-0 flex-col gap-4">
        <ScoreBar row={row} testId={testId} />
        <EvalBar row={row} testId={testId} />
      </div>
      <div className="min-w-0 md:col-span-2 xl:col-span-1">
        <ScoreOverTime row={row} testId={testId} debouncedFilters={debouncedFilters} />
      </div>
    </div>
  );
}
