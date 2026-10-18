import { ArrowRightLeft, Swords } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { ScoreLine } from '@/components/openings/stats/ScoreLine';
import {
  CardVerdictGrid,
  EvalVerdictLine,
  LastPlayedIndicator,
  VerdictSentence,
} from '@/components/openings/stats/CardParts';
import { CARD_BOARD_SIZE, CARD_LINK_BUTTON_CLASS } from '@/components/openings/stats/cardLayout';
import { findingArrows, findingMoveText, isOwnMove } from '@/lib/openingInsights';
import { lastMoveSquares } from '@/lib/sanToSquares';
import {
  percentOf,
  scoreAccentColor,
  scoreVerdictInput,
  stripEcoSuffix,
  type EvalSample,
} from '@/lib/openingVerdict';
import { MOVE_PILL_NEUTRAL_BG, MOVE_PILL_TINT_PCT } from '@/lib/theme';
import { cn } from '@/lib/utils';
import type { OpeningInsightFinding } from '@/types/insights';

/** The backend's name for a line without an openings-table match. */
const UNNAMED_SENTINEL = '<unnamed line>';
const OWN_MOVE_LABEL = 'Your move';
const OPPONENT_MOVE_LABEL = 'Their reply';

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
        <LastPlayedIndicator
          lastPlayedAt={finding.last_played_at}
          stale={!finding.is_current}
          testId={testId}
        />
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

function evalSample(finding: OpeningInsightFinding): EvalSample {
  return {
    avgEvalPawns: finding.avg_eval_pawns ?? null,
    evalN: finding.eval_n ?? 0,
    confidence: finding.eval_confidence ?? 'low',
    color: finding.color,
  };
}

interface FindingCardProps {
  finding: OpeningInsightFinding;
  testId: string;
  onOpenMoves: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}

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
  const scoreInput = scoreVerdictInput(finding.score, finding.confidence, finding.n_games);
  const sample = evalSample(finding);
  const accentColor = scoreAccentColor(scoreInput);
  return (
    <Card data-testid={testId} accentColor={accentColor}>
      <CardHeader as="h4" size="compact" className="items-start text-base">
        <FindingTitle finding={finding} accentColor={accentColor} testId={testId} />
      </CardHeader>
      <CardBody className="flex flex-col gap-3">
        <CardVerdictGrid
          board={
            <LazyMiniBoard
              fen={finding.entry_fen}
              flipped={finding.color === 'black'}
              size={CARD_BOARD_SIZE}
              arrows={arrows}
              lastMove={lastMove}
            />
          }
          metrics={
            <>
              <div className="space-y-1.5">
                <ScoreLine
                  score={finding.score}
                  games={finding.n_games}
                  wins={finding.wins}
                  draws={finding.draws}
                  losses={finding.losses}
                  input={scoreInput}
                  ciLow={finding.ci_low ?? null}
                  ciHigh={finding.ci_high ?? null}
                  pValue={finding.p_value}
                  testId={testId}
                />
                <MiniWDLBar
                  win_pct={percentOf(finding.wins, finding.n_games)}
                  draw_pct={percentOf(finding.draws, finding.n_games)}
                  loss_pct={percentOf(finding.losses, finding.n_games)}
                />
              </div>
              <EvalVerdictLine
                sample={sample}
                ciLow={finding.eval_ci_low_pawns ?? null}
                ciHigh={finding.eval_ci_high_pawns ?? null}
                pValue={finding.eval_p_value ?? null}
                testId={testId}
              />
            </>
          }
          sentence={<VerdictSentence scoreInput={scoreInput} evalSample={sample} testId={testId} />}
        />
        <div className="flex items-center gap-4">
          <button
            type="button"
            className={CARD_LINK_BUTTON_CLASS}
            aria-label="Open this line in the Move Explorer"
            data-testid={`${testId}-btn-moves`}
            onClick={() => onOpenMoves(finding)}
          >
            <ArrowRightLeft className="h-3.5 w-3.5" />
            <span>Moves</span>
          </button>
          <button
            type="button"
            className={CARD_LINK_BUTTON_CLASS}
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
