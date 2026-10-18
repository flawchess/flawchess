import { ArrowRightLeft, Swords } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { EvalCpuPlaceholder } from '@/components/stats/EvalCpuPlaceholder';
import { VerdictBar } from '@/components/openings/stats/VerdictBar';
import { ScoreLine } from '@/components/openings/stats/ScoreLine';
import { EvalVerdictPopover } from '@/components/openings/stats/VerdictPopover';
import { useReadiness } from '@/hooks/useReadiness';
import { formatSignedGap } from '@/lib/gapBar';
import { findingArrows, findingMoveText } from '@/lib/openingInsights';
import { lastMoveSquares } from '@/lib/sanToSquares';
import {
  EVAL_VERDICT_BAND,
  SCORE_VERDICT_BAND,
  evalBaselinePawns,
  formatEvalCompact,
  openingVerdict,
  openingVerdictReason,
  openingVerdictSentence,
  scoreDelta,
  stripEcoSuffix,
  type OpeningVerdictInput,
} from '@/lib/openingVerdict';
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

function scoreInput(finding: OpeningInsightFinding): OpeningVerdictInput {
  return {
    delta: scoreDelta(finding.score),
    band: SCORE_VERDICT_BAND,
    confidence: finding.confidence,
    games: finding.n_games,
  };
}

/** Null when the finding has no eval to judge. */
function evalInput(finding: OpeningInsightFinding): OpeningVerdictInput | null {
  const avg = finding.avg_eval_pawns ?? null;
  const evalN = finding.eval_n ?? 0;
  if (avg === null || evalN <= 0) return null;
  return {
    delta: avg - evalBaselinePawns(finding.color),
    band: EVAL_VERDICT_BAND,
    confidence: finding.eval_confidence ?? 'low',
    // WR-02: the 20-game verdict floor applies to the eval sample (eval_n), not the game count:
    // the mean excludes mate/NULL evals and trims outliers, so a 40-game opening can rest on 11 evals.
    games: evalN,
  };
}

function EvalLine({ finding, testId }: { finding: OpeningInsightFinding; testId: string }) {
  const { tier2 } = useReadiness();
  // Eval needs Stockfish analysis: show the pending placeholder until tier 2 is reached.
  if (!tier2) return <EvalCpuPlaceholder />;
  const avg = finding.avg_eval_pawns ?? null;
  const evalN = finding.eval_n ?? 0;
  const input = evalInput(finding);
  if (avg === null || input === null) {
    return (
      <div className="flex items-center justify-between text-sm" data-testid={`${testId}-eval-none`}>
        <span className="text-muted-foreground">{EVAL_LABEL}</span>
        <span className="text-muted-foreground">{NO_VALUE}</span>
      </div>
    );
  }
  const baseline = evalBaselinePawns(finding.color);
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
          ciLow={finding.eval_ci_low_pawns ?? null}
          ciHigh={finding.eval_ci_high_pawns ?? null}
          pValue={finding.eval_p_value ?? null}
        />
      }
    />
  );
}

/** The Score and Eval verdicts read together in one muted line. */
function VerdictSentence({ finding, testId }: { finding: OpeningInsightFinding; testId: string }) {
  const { tier2 } = useReadiness();
  const evalIn = tier2 ? evalInput(finding) : null;
  const sentence = openingVerdictSentence(
    openingVerdictReason(scoreInput(finding)),
    evalIn ? openingVerdictReason(evalIn) : null,
  );
  return (
    <p className="text-sm text-muted-foreground" data-testid={`${testId}-sentence`}>
      {sentence}
    </p>
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
      <CardBody className="flex flex-col gap-3">
        <div className="flex items-start gap-3">
          <LazyMiniBoard
            fen={finding.entry_fen}
            flipped={finding.color === 'black'}
            size={BOARD_SIZE}
            arrows={arrows}
            lastMove={lastMove}
          />
          <div className="flex min-w-0 flex-1 flex-col gap-2.5">
            <div className="space-y-1.5">
              <ScoreLine
                score={finding.score}
                games={finding.n_games}
                wins={finding.wins}
                draws={finding.draws}
                losses={finding.losses}
                input={scoreInput(finding)}
                ciLow={finding.ci_low ?? null}
                ciHigh={finding.ci_high ?? null}
                pValue={finding.p_value}
                testId={testId}
              />
              <MiniWDLBar
                win_pct={pct(finding.wins, finding.n_games)}
                draw_pct={pct(finding.draws, finding.n_games)}
                loss_pct={pct(finding.losses, finding.n_games)}
              />
            </div>
            <EvalLine finding={finding} testId={testId} />
          </div>
        </div>
        <VerdictSentence finding={finding} testId={testId} />
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
      </CardBody>
    </Card>
  );
}
