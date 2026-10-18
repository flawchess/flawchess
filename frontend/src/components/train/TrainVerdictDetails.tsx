/**
 * TrainVerdictDetails — the full verdict feedback body, shared by the desktop
 * verdict card and the phone strip's expansion.
 *
 * In order: the bot verdict (opener, position fact, guess and move clauses
 * with their point pills, look-closer line), the return tail on its own muted
 * line, and an extras line (motif, "Also fine, e.g. ...") shown only when
 * either exists. There are no buttons here: Analyze and Next live in the
 * reveal action bar.
 *
 * Also home of `TrainScoreChip`, the "+N" pill shared with the strip and the
 * points flash over the board.
 */

import type { ReactElement, ReactNode } from 'react';
import { returnPhrase } from '@/lib/trainBotCopy';
import type { VerdictClauseParts, VerdictCopy } from '@/lib/trainBotCopy';
import { TRAIN_VERDICT_CORRECT, TRAIN_VERDICT_INCORRECT } from '@/lib/theme';
import type { SolveResponse } from '@/types/train';

/**
 * The reveal's score chip. It always states what the line actually SCORED
 * (guess: 0 or 1; move: 0, 1 for an inaccuracy, or 2), so the reveal and the
 * "Points: +N" flash over the board add up to the same total. Green whenever
 * anything was earned, red at zero. Shared by the verdict clause's inline
 * guess/move pills, the same "+N" scoring language.
 */
export function TrainScoreChip({ points, testid }: { points: number; testid: string }): ReactElement {
  return (
    <span
      // rounded-full + slightly wider padding: the same pill shape as the
      // "Points: +N" flash over the board, so the two surfaces read as the
      // same scoring language.
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
  /** The scored sentence, from `verdictClauseParts` (the board owner builds it
   * once so the strip line and this body read the same input). */
  clause: VerdictClauseParts;
  sessionDate: string | undefined;
  expiresOn: string | undefined;
  isWarmup: boolean;
  motif: string | null;
  /** Comma-joined SAN of the alternative fine moves; '' hides the line. */
  alsoFineSanList: string;
  /**
   * The desktop card floats the bot avatar here, so the verdict
   * paragraph wraps to its right while the extras below the separator keep
   * the full width. The phone strip shows its avatar in the header line.
   */
  leading?: ReactNode;
}

/**
 * The verdict paragraph: opener + position fact + guess/move clauses with
 * inline pills + optional look-closer line (0-1 pts).
 */
function VerdictParagraph({ opening, clause }: Pick<TrainVerdictDetailsProps, 'opening' | 'clause'>): ReactElement {
  return (
    <p data-testid="train-bot-verdict-line">
      {opening.opener} <span data-testid="train-bot-fact">{clause.fact}</span> {clause.guessLabel}{' '}
      <TrainScoreChip points={clause.guessPoints} testid="train-bot-pill-guess" />
      {clause.joiner}
      {clause.moveLabel} <TrainScoreChip points={clause.movePoints} testid="train-bot-pill-move" />.
      {opening.lookCloser !== null && (
        <>
          {' '}
          <span data-testid="train-bot-look-closer">{opening.lookCloser}</span>
        </>
      )}
    </p>
  );
}

/**
 * The return tail, on its own muted line under the verdict.
 *
 * A `trainRevealCache` entry written by an older bundle
 * restores a verdict without `source` at runtime despite the TS type calling
 * it required. A return tail can only be trusted once the item's
 * SOURCE is known (herring/filler never return; sr_item's tail depends on
 * item_status/due_date) — so a missing `source` renders no return tail at
 * all, the one nullish default at this consumption site, rather than
 * guessing from a possibly-unrelated due_date.
 */
function ReturnTail({
  verdict,
  sessionDate,
  expiresOn,
  isWarmup,
}: Pick<TrainVerdictDetailsProps, 'verdict' | 'sessionDate' | 'expiresOn' | 'isWarmup'>): ReactElement | null {
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
        });
  if (returnTail === '') return null;
  // A mastered/parked/herring/filler item's tail explains WHY it won't
  // return — it is not itself a return promise. `train-bot-return-tail`
  // (the testid a future date-check UI could key off) is reserved for the
  // two genuine promises (next-session / in-N-days).
  const isReturnPromise =
    verdict.source === 'sr_item' && verdict.item_status !== 'mastered' && verdict.item_status !== 'parked';
  return (
    <p className="text-muted-foreground" data-testid={isReturnPromise ? 'train-bot-return-tail' : 'train-bot-tail'}>
      {returnTail}
    </p>
  );
}

export function TrainVerdictDetails({
  verdict,
  opening,
  clause,
  sessionDate,
  expiresOn,
  isWarmup,
  motif,
  alsoFineSanList,
  leading,
}: TrainVerdictDetailsProps): ReactElement {
  const showExtras = motif !== null || alsoFineSanList !== '';
  return (
    <div className="flex flex-col gap-2">
      {/* flow-root contains the floated avatar, so a verdict shorter than the
          avatar never lets the separator block wrap up beside it. */}
      <div className="flow-root">
        {leading}
        <VerdictParagraph opening={opening} clause={clause} />
        <ReturnTail verdict={verdict} sessionDate={sessionDate} expiresOn={expiresOn} isWarmup={isWarmup} />
      </div>
      {showExtras && (
        <p className="border-t border-border pt-2 text-sm" data-testid="train-verdict-extras">
          {motif !== null && (
            <span className="text-sm text-muted-foreground" data-testid="train-reveal-motif">
              Motif: {motif}
            </span>
          )}
          {motif !== null && alsoFineSanList !== '' && ' · '}
          {alsoFineSanList !== '' && (
            // "e.g." because the vetted list is not exhaustive: a soft puzzle
            // serves only the deep best + second-best, and even the herring
            // ladder stops at MultiPV-5 — other good moves may exist beyond
            // what the server certified.
            <span data-testid="train-reveal-also-fine">Also fine, e.g. {alsoFineSanList}</span>
          )}
        </p>
      )}
    </div>
  );
}
