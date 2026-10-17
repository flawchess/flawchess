import { ArrowRightLeft, Swords } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { Button } from '@/components/ui/button';
import { EvalCpuPlaceholder } from '@/components/stats/EvalCpuPlaceholder';
import { VerdictBar } from '@/components/openings/stats/VerdictBar';
import {
  EvalVerdictPopover,
  ScoreVerdictPopover,
} from '@/components/openings/stats/VerdictPopover';
import { useReadiness } from '@/hooks/useReadiness';
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
    games: row.games,
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
 * Detail panel under an expanded repertoire row (D-00): a 200 px board (size={200}) with the Moves / Games
 * links (stacked right of the board on phones), the Score and Eval after opening verdict bars.
 */
export function RepertoireExpandedRow({
  row,
  index,
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
      className="grid gap-4 md:grid-cols-[200px_minmax(0,1fr)] md:gap-6"
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
        </div>
      </div>
      <div className="flex min-w-0 flex-col gap-4">
        <ScoreBar row={row} testId={testId} />
        <EvalBar row={row} testId={testId} />
      </div>
    </div>
  );
}
