/**
 * TrainVerdictDetails — Phase 237 plan 08 (D-07): the full verdict feedback
 * body, shared by the desktop verdict bubble and the phone strip's expansion.
 *
 * In order: the bot verdict (opener, clause with its point pills, look-closer
 * line, return tail), the Your-call feedback (call label, guess prose,
 * motif) and the "Also fine, e.g. ..." list. Nothing the old bubble and Your-call
 * card showed is dropped, and there are no buttons here: Analyze and Next live in
 * the reveal action bar.
 *
 * Also home of `TrainScoreChip`, the "+N" pill shared with the strip and the
 * points flash over the board.
 */

import type { ReactElement, ReactNode } from 'react';
import { returnPhrase, verdictClauseParts } from '@/lib/trainBotCopy';
import type { TrainCopyAudience, VerdictCopy } from '@/lib/trainBotCopy';
import { TRAIN_VERDICT_CORRECT, TRAIN_VERDICT_INCORRECT } from '@/lib/theme';
import { GUESS_CALL_LABELS } from '@/lib/trainGuessLabels';
import type { Guess } from '@/lib/trainGuessLabels';
import type { SolveResponse } from '@/types/train';

/**
 * Phase 200 UAT round 3: the reveal's score chip. It always states what the
 * line actually SCORED (guess: 0 or 1; move: 0, 1 for an inaccuracy, or 2), so
 * the reveal and the "Points: +N" flash over the board add up to the same total.
 * Green whenever anything was earned, red at zero. Phase 222 (D-23): shared by
 * the verdict clause's inline guess/move pills, the same "+N" scoring language.
 */
export function TrainScoreChip({ points, testid }: { points: number; testid: string }): ReactElement {
  return (
    <span
      // rounded-full + slightly wider padding: the same pill shape as the
      // "Points: +N" flash over the board (Phase 200 UAT round 3), so the two
      // surfaces read as the same scoring language.
      className="shrink-0 rounded-full px-2 py-0.5 text-sm font-semibold text-white"
      style={{ backgroundColor: points > 0 ? TRAIN_VERDICT_CORRECT : TRAIN_VERDICT_INCORRECT }}
      data-testid={testid}
    >
      +{points}
    </span>
  );
}

export interface TrainVerdictDetailsProps {
  verdict: SolveResponse;
  /** The opener + look-closer, resolved ONCE per verdict by the board owner (the
   * opener is a random draw, so a per-render draw would flip it on every render). */
  opening: VerdictCopy;
  /** True when the played move is the engine's best (the chip-merge predicate). */
  isBest: boolean;
  sessionDate: string | undefined;
  expiresOn: string | undefined;
  isWarmup: boolean;
  audience: TrainCopyAudience;
  guess: Guess | null;
  guessProse: string | null;
  motif: string | null;
  /** Comma-joined SAN of the alternative fine moves; '' hides the line. */
  alsoFineSanList: string;
  /**
   * Phase 237 UAT: the desktop card floats the bot avatar here, so the verdict
   * paragraph wraps to its right while the Your-call block below the separator
   * keeps the full width. The phone strip shows its avatar in the header line.
   */
  leading?: ReactNode;
}

/**
 * The verdict paragraph: opener + clause with inline pills + optional
 * look-closer line (0-1 pts) + the D-15/D-16 return tail.
 *
 * RESEARCH Pitfall 7: a `trainRevealCache` entry written by a pre-206 bundle
 * restores a verdict without `source` at runtime despite the TS type calling
 * it required. Per D-16, a return tail can only be trusted once the item's
 * SOURCE is known (herring/filler never return; sr_item's tail depends on
 * item_status/due_date) — so a missing `source` renders no return tail at
 * all, the one nullish default at this consumption site, rather than
 * guessing from a possibly-unrelated due_date.
 */
function VerdictParagraph({
  verdict,
  opening,
  isBest,
  sessionDate,
  expiresOn,
  isWarmup,
  audience,
}: Pick<
  TrainVerdictDetailsProps,
  'verdict' | 'opening' | 'isBest' | 'sessionDate' | 'expiresOn' | 'isWarmup' | 'audience'
>): ReactElement {
  const clause = verdictClauseParts(verdict.correct_guess, verdict.move_quality, isBest);
  const returnTail =
    verdict.source === undefined
      ? ''
      : returnPhrase({
          source: verdict.source,
          item_status: verdict.item_status,
          due_date: verdict.due_date,
          is_warmup: isWarmup,
          session_date: sessionDate,
          expires_on: expiresOn,
          audience,
        });
  // D-16: a mastered/parked/herring/filler item's tail explains WHY it won't
  // return — it is not itself a return promise. `train-bot-return-tail`
  // (the testid a future date-check UI could key off) is reserved for the
  // two genuine promises (next-session / in-N-days); the terminal variants
  // still render their explanatory text, just without that testid.
  const isReturnPromise =
    verdict.source === 'sr_item' &&
    verdict.item_status !== 'mastered' &&
    verdict.item_status !== 'parked' &&
    returnTail !== '';
  return (
    // One flowing paragraph, not one <p> per sentence: stacked lines ate too
    // much vertical space on phones. The testids stay on inline spans.
    <p data-testid="train-bot-verdict-line">
      {opening.opener} {clause.guessLabel}{' '}
      <TrainScoreChip points={clause.guessPoints} testid="train-bot-pill-guess" />,{' '}
      {clause.moveLabel}{' '}
      <TrainScoreChip points={clause.movePoints} testid="train-bot-pill-move" />.
      {opening.lookCloser !== null && (
        <>
          {' '}
          <span data-testid="train-bot-look-closer">{opening.lookCloser}</span>
        </>
      )}
      {returnTail !== '' && isReturnPromise && (
        <>
          {' '}
          <span data-testid="train-bot-return-tail">{returnTail}</span>
        </>
      )}
      {returnTail !== '' && !isReturnPromise && <> {returnTail}</>}
    </p>
  );
}

export function TrainVerdictDetails({
  verdict,
  opening,
  isBest,
  sessionDate,
  expiresOn,
  isWarmup,
  audience,
  guess,
  guessProse,
  motif,
  alsoFineSanList,
  leading,
}: TrainVerdictDetailsProps): ReactElement {
  return (
    <div className="flex flex-col gap-2">
      {/* flow-root contains the floated avatar, so a verdict shorter than the
          avatar never lets the separator block wrap up beside it. */}
      <div className="flow-root">
        {leading}
        <VerdictParagraph
          verdict={verdict}
          opening={opening}
          isBest={isBest}
          sessionDate={sessionDate}
          expiresOn={expiresOn}
          isWarmup={isWarmup}
          audience={audience}
        />
      </div>
      <div className="flex flex-col gap-2 border-t border-border pt-2" data-testid="train-verdict-guess">
        {/* Phase 237 UAT: no score chip on this line, the verdict clause's guess
            pill above already states the call's points. */}
        <p className="font-semibold">Your call: {guess !== null ? GUESS_CALL_LABELS[guess] : ''}</p>
        {guessProse !== null && (
          <p className="text-sm" data-testid="train-verdict-guess-prose">
            {guessProse}
          </p>
        )}
        {motif !== null && (
          <p className="text-sm text-muted-foreground" data-testid="train-reveal-motif">
            Motif: {motif}
          </p>
        )}
        {alsoFineSanList !== '' && (
          <p className="text-sm" data-testid="train-reveal-also-fine">
            {/* "e.g." because the vetted list is not exhaustive: a soft puzzle
                serves only the deep best + second-best, and even the herring
                ladder stops at MultiPV-5 — other good moves may exist beyond
                what the server certified. */}
            Also fine, e.g. {alsoFineSanList}
          </p>
        )}
      </div>
    </div>
  );
}
