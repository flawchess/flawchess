/**
 * TrainVerdictDetails — the full verdict feedback body, shared by the desktop
 * verdict card and the phone strip's expansion.
 *
 * In order: the bot verdict (opener, position fact, guess and move clauses
 * with their point pills, "Also fine, e.g. ...", look-closer line), then, below
 * a divider (Phase 264 D-08, D-14, D-24), the additional info, each line only
 * when it exists: the game-move line and the return tail. There are no
 * buttons here: Analyze and Next live in the reveal action bar.
 *
 * Also home of `TrainScoreChip`, the "+N" pill shared with the strip and the
 * points flash over the board.
 */

import { useLayoutEffect, useRef } from 'react';
import type { ReactElement, ReactNode, RefObject } from 'react';
import { GameMoveLine, GameMoveLinePlaceholder, VerdictExtras } from '@/components/train/GameMoveLine';
import type { GameBlunderPart, GameMoveHead } from '@/lib/gameBlunderSentence';
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
  /** Comma-joined SAN of the alternative fine moves; '' hides the line. */
  alsoFineSanList: string;
  /** The game-move line's parts (`gameBlunderParts`); empty: no line. */
  gameMove: readonly GameBlunderPart[];
  /** The line's subject: the game move's SAN and quality icon. */
  gameMoveHead: GameMoveHead;
  /**
   * The reveal that carries the line is still loading for a personalized puzzle. The body
   * then reserves the line's slot and latches its height (see `useHeightLatch`).
   */
  gameMovePending: boolean;
  /**
   * The desktop card floats the bot avatar here, so the verdict
   * paragraph wraps to its right while the extras below the separator keep
   * the full width. The phone strip shows its avatar in the header line.
   */
  leading?: ReactNode;
}

/**
 * The verdict paragraph: opener + position fact + guess/move clauses with
 * inline pills + "Also fine, e.g. ..." + optional look-closer line (0-1 pts).
 * `showLookCloser` is false when the game-move line replaces it (Phase 264
 * D-08), and while the reveal that decides this is still loading. "Also fine"
 * sits before the look-closer line, so it never moves when that line comes or
 * goes; it is part of the verdict, not additional info (owner, D-24).
 */
function VerdictParagraph({
  opening,
  clause,
  alsoFineSanList,
  showLookCloser,
}: Pick<TrainVerdictDetailsProps, 'opening' | 'clause' | 'alsoFineSanList'> & { showLookCloser: boolean }): ReactElement {
  return (
    <p data-testid="train-bot-verdict-line">
      {opening.opener} <span data-testid="train-bot-fact">{clause.fact}</span> {clause.guessLabel}{' '}
      <TrainScoreChip points={clause.guessPoints} testid="train-bot-pill-guess" />
      {clause.joiner}
      {clause.moveLabel} <TrainScoreChip points={clause.movePoints} testid="train-bot-pill-move" />.
      {alsoFineSanList !== '' && (
        <>
          {' '}
          {/* "e.g." because the vetted list is not exhaustive: a soft puzzle serves only the deep
              best + second-best, and even the herring ladder stops at MultiPV-5, so other good
              moves may exist beyond what the server certified. */}
          <span data-testid="train-reveal-also-fine">Also fine, e.g. {alsoFineSanList}.</span>
        </>
      )}
      {opening.lookCloser !== null && showLookCloser && (
        <>
          {' '}
          <span data-testid="train-bot-look-closer">{opening.lookCloser}</span>
        </>
      )}
    </p>
  );
}

/**
 * The return tail's text, '' for none.
 *
 * A `trainRevealCache` entry written by an older bundle
 * restores a verdict without `source` at runtime despite the TS type calling
 * it required. A return tail can only be trusted once the item's
 * SOURCE is known (herring/filler never return; sr_item's tail depends on
 * item_status/due_date) — so a missing `source` renders no return tail at
 * all, the one nullish default at this consumption site, rather than
 * guessing from a possibly-unrelated due_date.
 */
function returnTailOf({
  verdict,
  sessionDate,
  expiresOn,
}: Pick<TrainVerdictDetailsProps, 'verdict' | 'sessionDate' | 'expiresOn'>): string {
  if (verdict.source === undefined) return '';
  return returnPhrase({
    source: verdict.source,
    item_status: verdict.item_status,
    due_date: verdict.due_date,
    session_date: sessionDate,
    expires_on: expiresOn,
  });
}

/** The return tail, the last muted line below the divider (Phase 264 D-14: moved down from under the verdict). */
function ReturnTail({ verdict, text }: { verdict: SolveResponse; text: string }): ReactElement {
  // A mastered/parked/herring/foreign item's tail explains WHY it won't
  // return — it is not itself a return promise. `train-bot-return-tail`
  // (the testid a future date-check UI could key off) is reserved for the
  // two genuine promises (next-session / in-N-days).
  const isReturnPromise =
    verdict.source === 'sr_item' && verdict.item_status !== 'mastered' && verdict.item_status !== 'parked';
  return (
    <p className="text-muted-foreground" data-testid={isReturnPromise ? 'train-bot-return-tail' : 'train-bot-tail'}>
      {text}
    </p>
  );
}

/** Raise the node's min-height to its current height, so it never shrinks below it. */
function ratchet(node: HTMLDivElement): void {
  const height = node.offsetHeight;
  if (height > parseFloat(node.style.minHeight || '0')) node.style.minHeight = `${height}px`;
}

/**
 * Keeps the body from changing height when the reveal lands (frontend/CLAUDE.md: slots that
 * appear and disappear need their height reserved). While the reveal is pending the body
 * reserves the game-move slot (two lines, D-25) and that height is latched as the min-height for
 * this verdict. The settled body is never taller in the common case: a line with a tag or a type
 * part and the score sentence fills both lines on desktop, and a score-only line or the
 * look-closer sentence leaves one line of spare room. Known limit: a line with two tags, a type
 * part and the score wraps to a third line on phones, and the body then grows by that line;
 * reserving the worst case would leave more blank room on most puzzles.
 *
 * After that, the body only grows for this verdict, never shrinks (a ratchet). Bug fix (D-24):
 * the "Also fine" list is partly live (engine alternatives arrive over a couple of seconds and
 * can drop out again), and inside the verdict paragraph a list crossing a line break made the
 * bubble flicker 171 -> 190 -> 171 -> 190 px. With the ratchet it grows at most once. Cleared when
 * the verdict changes; re-measured on a window resize.
 */
function useHeightLatch(verdict: SolveResponse, pending: boolean): RefObject<HTMLDivElement | null> {
  const ref = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    const node = ref.current;
    if (node === null) return;
    const clear = (): void => {
      node.style.minHeight = '';
    };
    // Review fix: a pixel height latched at one width is wrong after a rotation, an unfold or a
    // resize (the text reflows), so the latch is dropped then instead of leaving blank room.
    // Review fix (D-25): and re-taken at the new width right away (reading offsetHeight lays out
    // without the old min-height). A phone's toolbar hiding fires `resize` without changing the
    // body's size, so the ResizeObserver alone would have left it unlatched.
    const onResize = (): void => {
      clear();
      ratchet(node);
    };
    window.addEventListener('resize', onResize);
    // Guarded for environments without ResizeObserver; the unit tests install a stub.
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(() => ratchet(node));
    observer?.observe(node);
    return () => {
      window.removeEventListener('resize', onResize);
      observer?.disconnect();
      clear();
    };
  }, [verdict]);
  useLayoutEffect(() => {
    const node = ref.current;
    if (node === null || !pending) return;
    node.style.minHeight = `${node.offsetHeight}px`;
  }, [verdict, pending]);
  return ref;
}

export function TrainVerdictDetails({
  verdict,
  opening,
  clause,
  sessionDate,
  expiresOn,
  alsoFineSanList,
  gameMove,
  gameMoveHead,
  gameMovePending,
  leading,
}: TrainVerdictDetailsProps): ReactElement {
  const latchRef = useHeightLatch(verdict, gameMovePending);
  const returnTail = returnTailOf({ verdict, sessionDate, expiresOn });
  const hasGameMove = gameMove.length > 0;
  // D-08: the "Game move:" line replaces the look-closer line.
  const showLookCloser = !gameMovePending && !hasGameMove;
  const showExtras = hasGameMove || gameMovePending || returnTail !== '';
  return (
    <div ref={latchRef} className="flex flex-col gap-2">
      {/* flow-root contains the floated avatar, so a verdict shorter than the
          avatar never lets the separator block wrap up beside it. */}
      <div className="flow-root">
        {leading}
        <VerdictParagraph
          opening={opening}
          clause={clause}
          alsoFineSanList={alsoFineSanList}
          showLookCloser={showLookCloser}
        />
      </div>
      {showExtras && (
        <VerdictExtras testid="train-verdict-extras">
          {gameMovePending ? <GameMoveLinePlaceholder /> : <GameMoveLine parts={gameMove} head={gameMoveHead} />}
          {returnTail !== '' && <ReturnTail verdict={verdict} text={returnTail} />}
        </VerdictExtras>
      )}
    </div>
  );
}
