import { Archive, ArrowRightLeft, Swords } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { EvalCpuPlaceholder } from '@/components/stats/EvalCpuPlaceholder';
import { VerdictBar } from '@/components/openings/stats/VerdictBar';
import { ScoreLine } from '@/components/openings/stats/ScoreLine';
import { EvalVerdictPopover } from '@/components/openings/stats/VerdictPopover';
import { useReadiness } from '@/hooks/useReadiness';
import { formatSignedGap } from '@/lib/gapBar';
import { findingArrows, findingMoveText, isOwnMove } from '@/lib/openingInsights';
import { formatRelativeDate } from '@/lib/relativeDate';
import { lastMoveSquares } from '@/lib/sanToSquares';
import {
  EVAL_VERDICT_BAND,
  SCORE_VERDICT_BAND,
  evalBaselinePawns,
  formatEvalCompact,
  openingVerdict,
  openingVerdictReason,
  openingVerdictSentence,
  scoreAccentColor,
  scoreDelta,
  stripEcoSuffix,
  type OpeningVerdictInput,
} from '@/lib/openingVerdict';
import { MOVE_PILL_NEUTRAL_BG, MOVE_PILL_TINT_PCT } from '@/lib/theme';
import { cn } from '@/lib/utils';
import type { OpeningInsightFinding } from '@/types/insights';

/** Same board as the repertoire cards, so both card kinds share one layout. */
const BOARD_SIZE = 128;
const PERCENT_SCALE = 100;
/** The backend's name for a line without an openings-table match. */
const UNNAMED_SENTINEL = '<unnamed line>';
const NOT_PLAYED_RECENTLY = 'Not played recently';
const NO_VALUE = '—';
const EVAL_LABEL = 'Eval after opening';
const EVAL_LABEL_SHORT = 'Eval';
const OWN_MOVE_LABEL = 'Your move';
const OPPONENT_MOVE_LABEL = 'Their reply';

/**
 * "3 weeks ago" plus the archive icon for a finding outside the current repertoire (D-04), the
 * same top-right indicator as the repertoire cards. Nothing when there is neither a date nor
 * the stale flag.
 */
function LastPlayed({ finding, testId }: { finding: OpeningInsightFinding; testId: string }) {
  const stale = !finding.is_current;
  if (!finding.last_played_at && !stale) return null;
  return (
    <span
      className="ml-auto flex shrink-0 items-center gap-1.5 text-sm font-normal whitespace-nowrap text-muted-foreground"
      data-testid={`${testId}-last-played`}
    >
      {finding.last_played_at && formatRelativeDate(finding.last_played_at)}
      {/* Indicator only, not an action: marks findings outside the current repertoire. */}
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
  );
}

/** The move in a pill tinted by the card's score verdict. */
function MovePill({
  finding,
  accentColor,
  testId,
}: {
  finding: OpeningInsightFinding;
  accentColor: string | undefined;
  testId: string;
}) {
  const style = accentColor
    ? {
        backgroundColor: `color-mix(in oklch, ${accentColor} ${MOVE_PILL_TINT_PCT}%, transparent)`,
        borderColor: accentColor,
      }
    : { backgroundColor: MOVE_PILL_NEUTRAL_BG, borderColor: 'transparent' };
  return (
    <span
      className="inline-block rounded-md border px-2 py-0.5 whitespace-nowrap text-foreground"
      style={style}
      data-testid={`${testId}-move`}
    >
      {findingMoveText(finding)}
    </span>
  );
}

/**
 * Move-led title: the move pill, whose move it is and the last-played date on the first row, the
 * opening name without ECO under it (italic when unnamed). Opening cards lead with the name instead, so the two card kinds read
 * differently at a glance.
 */
function FindingTitle({
  finding,
  accentColor,
  testId,
}: {
  finding: OpeningInsightFinding;
  accentColor: string | undefined;
  testId: string;
}) {
  const unnamed = finding.opening_name === UNNAMED_SENTINEL;
  return (
    <span className="flex min-w-0 flex-1 flex-col gap-1" data-testid={`${testId}-title`}>
      {/* The last-played date shares this row (items-center), so it lines up with "Your move"
          instead of sitting at the top of the taller pill row. */}
      <span className="flex items-center gap-2">
        <MovePill finding={finding} accentColor={accentColor} testId={testId} />
        <span
          className="whitespace-nowrap text-sm font-normal text-muted-foreground"
          data-testid={`${testId}-mover`}
        >
          {isOwnMove(finding) ? OWN_MOVE_LABEL : OPPONENT_MOVE_LABEL}
        </span>
        <LastPlayed finding={finding} testId={testId} />
      </span>
      <span
        className={cn('break-words text-sm font-normal text-muted-foreground', unnamed && 'italic')}
        data-testid={`${testId}-opening`}
      >
        {stripEcoSuffix(finding.display_name)}
      </span>
    </span>
  );
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
      leading={
        // Phones shorten the label so it fits beside the value on one line (as RepertoireCard).
        <span className="text-muted-foreground">
          <span className="sm:hidden">{EVAL_LABEL_SHORT}</span>
          <span className="max-sm:hidden">{EVAL_LABEL}</span>
        </span>
      }
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
 * Move-led finding card (D-00), laid out like the repertoire cards: a header led by the move pill
 * and whose move it is, with the opening name under it, a 128 px board with the move arrow beside the score line, WDL bar and eval bar, the
 * verdict sentence under the eval bar, and a score-verdict left spine.
 */
export function FindingCard({
  finding,
  testId,
  onOpenMoves,
  onOpenGames,
}: FindingCardProps) {
  const arrows = findingArrows(finding);
  const lastMove = lastMoveSquares(finding.entry_san_sequence) ?? undefined;
  const accentColor = scoreAccentColor(scoreInput(finding));
  return (
    <Card data-testid={testId} accentColor={accentColor}>
      <CardHeader as="h4" size="compact" className="items-start text-base">
        <FindingTitle finding={finding} accentColor={accentColor} testId={testId} />
      </CardHeader>
      <CardBody className="flex flex-col gap-3">
        {/* Same grid as RepertoireCard: from sm up the sentence sits under the eval bar beside
            the board; phones are too narrow for that column, so it spans the card width. */}
        <div className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-3 gap-y-3 sm:gap-y-2.5">
          <div className="sm:row-span-2">
            <LazyMiniBoard
              fen={finding.entry_fen}
              flipped={finding.color === 'black'}
              size={BOARD_SIZE}
              arrows={arrows}
              lastMove={lastMove}
            />
          </div>
          <div className="flex min-w-0 flex-col gap-2.5">
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
          <div className="col-span-2 sm:col-span-1 sm:col-start-2">
            <VerdictSentence finding={finding} testId={testId} />
          </div>
        </div>
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
