import { ArrowRightLeft, Swords } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { EvalCpuPlaceholder } from '@/components/stats/EvalCpuPlaceholder';
import { VerdictBar } from '@/components/openings/stats/VerdictBar';
import {
  EvalVerdictPopover,
  ScoreVerdictPopover,
} from '@/components/openings/stats/VerdictPopover';
import { useReadiness } from '@/hooks/useReadiness';
import { formatSignedGap, gapVerdictColor } from '@/lib/gapBar';
import { findingArrows, findingMoveText } from '@/lib/openingInsights';
import { lastMoveSquares } from '@/lib/sanToSquares';
import {
  EVAL_VERDICT_BAND,
  SCORE_VERDICT_BAND,
  evalBaselinePawns,
  formatEvalCompact,
  formatScorePercent,
  openingVerdict,
  openingVerdictReason,
  scoreDelta,
  stripEcoSuffix,
} from '@/lib/openingVerdict';
import { ARROW_NEUTRAL } from '@/lib/theme';
import { cn } from '@/lib/utils';
import type { OpeningInsightFinding } from '@/types/insights';

const BOARD_SIZE = 120;
const PERCENT_SCALE = 100;
/** The backend's name for a line without an openings-table match. */
const UNNAMED_SENTINEL = '<unnamed line>';
const OLDER_GAMES_LABEL = 'older games';
const NO_VALUE = '—';
const EVAL_LABEL = 'Eval after opening';

/** "Last seen October 2026" (title of the older-games chip); undefined without a date. */
function lastSeenTitle(iso: string | null | undefined): string | undefined {
  if (!iso) return undefined;
  const month = new Date(iso).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
  return `Last seen ${month}`;
}

/** Marks a finding whose games all predate the current repertoire (D-04). */
function OlderGamesChip({ finding, testId }: { finding: OpeningInsightFinding; testId: string }) {
  if (finding.is_current) return null;
  return (
    <span
      className="inline-block rounded-full bg-white/10 px-2 py-px text-sm font-semibold whitespace-nowrap text-muted-foreground"
      title={lastSeenTitle(finding.last_played_at)}
      data-testid={testId}
    >
      {OLDER_GAMES_LABEL}
    </span>
  );
}

/** Opening name without ECO (italic for the unnamed sentinel); the board shows the position. */
function FindingSubtitle({ finding }: { finding: OpeningInsightFinding }) {
  const unnamed = finding.opening_name === UNNAMED_SENTINEL;
  return <span className={cn(unnamed && 'italic')}>{stripEcoSuffix(finding.display_name)}</span>;
}

function ScoreLine({ finding, testId }: { finding: OpeningInsightFinding; testId: string }) {
  const input = {
    delta: scoreDelta(finding.score),
    band: SCORE_VERDICT_BAND,
    confidence: finding.confidence,
    games: finding.n_games,
  };
  const verdict = openingVerdict(input);
  return (
    <div className="flex items-center justify-between gap-2 text-sm">
      <span className="inline-flex items-center gap-1">
        <span>
          You score{' '}
          <strong
            className="tabular-nums"
            style={verdict !== 'typical' ? { color: gapVerdictColor(verdict) } : undefined}
            data-testid={`${testId}-score`}
          >
            {formatScorePercent(finding.score)}
          </strong>
        </span>
        <ScoreVerdictPopover
          testId={`${testId}-score-info`}
          score={finding.score}
          games={finding.n_games}
          wins={finding.wins}
          draws={finding.draws}
          losses={finding.losses}
          reason={openingVerdictReason(input)}
          ci99Low={finding.ci99_low ?? null}
          ci99High={finding.ci99_high ?? null}
          pValue={finding.p_value}
        />
      </span>
      <span className="text-muted-foreground tabular-nums">
        {finding.n_games.toLocaleString('en-US')} games
      </span>
    </div>
  );
}

function EvalLine({ finding, testId }: { finding: OpeningInsightFinding; testId: string }) {
  const { tier2 } = useReadiness();
  // Eval needs Stockfish analysis: show the pending placeholder until tier 2 is reached.
  if (!tier2) return <EvalCpuPlaceholder />;
  const avg = finding.avg_eval_pawns ?? null;
  const evalN = finding.eval_n ?? 0;
  if (avg === null || evalN <= 0) {
    return (
      <div className="flex items-center justify-between text-sm" data-testid={`${testId}-eval-none`}>
        <span className="text-muted-foreground">{EVAL_LABEL}</span>
        <span className="text-muted-foreground">{NO_VALUE}</span>
      </div>
    );
  }
  const baseline = evalBaselinePawns(finding.color);
  const input = {
    delta: avg - baseline,
    band: EVAL_VERDICT_BAND,
    confidence: finding.eval_confidence ?? 'low',
    // WR-02: the 20-game verdict floor applies to the eval sample (eval_n), not the game count:
    // the mean excludes mate/NULL evals and trims outliers, so a 40-game opening can rest on 11 evals.
    games: evalN,
  };
  const verdict = openingVerdict(input);
  return (
    <VerdictBar
      delta={input.delta}
      band={EVAL_VERDICT_BAND}
      verdict={verdict}
      valueText={formatEvalCompact(avg)}
      zeroTickDelta={-baseline}
      centreSwatch={finding.color}
      testId={`${testId}-eval`}
      ariaLabel={`${EVAL_LABEL} ${formatSignedGap(avg)}, centred on an average ${finding.color} game at ${formatSignedGap(baseline)}`}
      leading={<span className="text-muted-foreground">{EVAL_LABEL}</span>}
      trailing={
        <EvalVerdictPopover
          testId={`${testId}-eval-info`}
          label={EVAL_LABEL}
          avgEvalPawns={avg}
          evalN={evalN}
          color={finding.color}
          reason={openingVerdictReason(input)}
          ci99Low={finding.eval_ci99_low_pawns ?? null}
          ci99High={finding.eval_ci99_high_pawns ?? null}
          pValue={finding.eval_p_value ?? null}
        />
      }
    />
  );
}

function pct(count: number, total: number): number {
  return total > 0 ? (count / total) * PERCENT_SCALE : 0;
}

interface FindingCardProps {
  finding: OpeningInsightFinding;
  testId: string;
  onOpenMoves: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
  /** "Not clear yet" cards draw the move arrow uncoloured: only a 99% finding gets red or green. */
  neutralArrow?: boolean;
}

const LINK_BUTTON_CLASS =
  'flex items-center gap-1 text-sm text-brand-brown-light transition-colors hover:text-brand-brown-highlight';

/**
 * Move-led finding card (D-00): the move first, then the opening name, a 120 px
 * board with the move arrow, the score with its popover and WDL bar, the eval bar centred on
 * the colour baseline.
 */
export function FindingCard({
  finding,
  testId,
  onOpenMoves,
  onOpenGames,
  neutralArrow = false,
}: FindingCardProps) {
  const arrows = findingArrows(finding);
  const lastMove = lastMoveSquares(finding.entry_san_sequence) ?? undefined;
  return (
    <Card data-testid={testId}>
      <CardHeader as="h4" size="compact" className="flex-col items-start gap-0.5">
        <span className="flex flex-wrap items-center gap-2 text-base">
          <span data-testid={`${testId}-move`}>After {findingMoveText(finding)}</span>
          <OlderGamesChip finding={finding} testId={`${testId}-older`} />
        </span>
        <span className="max-w-full truncate font-normal text-muted-foreground">
          <FindingSubtitle finding={finding} />
        </span>
      </CardHeader>
      <CardBody className="flex items-start gap-3">
        <LazyMiniBoard
          fen={finding.entry_fen}
          flipped={finding.color === 'black'}
          size={BOARD_SIZE}
          arrows={neutralArrow ? arrows?.map((arrow) => ({ ...arrow, color: ARROW_NEUTRAL })) : arrows}
          lastMove={lastMove}
        />
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <ScoreLine finding={finding} testId={testId} />
          <MiniWDLBar
            win_pct={pct(finding.wins, finding.n_games)}
            draw_pct={pct(finding.draws, finding.n_games)}
            loss_pct={pct(finding.losses, finding.n_games)}
          />
          <EvalLine finding={finding} testId={testId} />
          <div className="flex items-center gap-4">
            <button
              type="button"
              className={LINK_BUTTON_CLASS}
              aria-label="Open this line in the Move Explorer"
              data-testid={`${testId}-btn-moves`}
              onClick={() => onOpenMoves(finding)}
            >
              <ArrowRightLeft className="h-3.5 w-3.5" />
              <span>Moves</span>
            </button>
            <button
              type="button"
              className={LINK_BUTTON_CLASS}
              aria-label={`View ${finding.n_games} games for this line`}
              data-testid={`${testId}-btn-games`}
              onClick={() => onOpenGames(finding)}
            >
              <Swords className="h-3.5 w-3.5" />
              <span className="tabular-nums">{finding.n_games}</span>
              <span>Games</span>
            </button>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
