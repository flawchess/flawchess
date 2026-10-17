/**
 * TrainReveal — the auto-opening post-solve reveal panel.
 *
 * Auto-opens as soon as grading and the solve POST have BOTH landed — no
 * "show solution" tap. Order: the verdict surface (a one-line strip on
 * phones, the full verdict card on desktop, both carrying the same
 * `TrainVerdictDetails` body, which includes the guess feedback), the mastery
 * banner, a chips row (You / Best / Game, each with its quality mark, SAN and
 * eval) with ONE move list under it, then the compact game footer. The chips
 * pick a line, the move list steps it, and the board follows the single
 * `useTrainRevealTree` tree that TrainSolveScreen owns. This component stays
 * presentational for both: it receives the chips and the list element as
 * props. The rewind / Analyze / Next bar lives with the board in
 * TrainSolveScreen.
 *
 * Every chip's eval/PV comes from the client grading engine
 * (`GradeResult.bestLine`/`.playedLine` from `gradeMove`, and the reveal-time
 * "played in game" search) — never a stored server line/eval.
 *
 * No speculative prefetch of answer-adjacent data: the reveal GET this
 * component owns and the game card its footer fetches are both gated on the
 * solve response being present (`verdict !== null`), so neither ever fires
 * before the solve POST has actually succeeded.
 *
 * When the solve POST has NOT succeeded (still pending, or failed), this
 * component renders only the block-and-retry row with a disabled Next
 * (covered by `TrainSolveScreen.test.tsx`).
 */

import { useEffect } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { trainApi } from '@/api/client';
import { useIsDesktop } from '@/hooks/useIsDesktop';
import { Button } from '@/components/ui/button';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { TrainFlawFixedBanner } from '@/components/train/TrainFlawFixedBanner';
import { TrainLineChips } from '@/components/train/TrainLineChips';
import { TrainRevealGameFooter } from '@/components/train/TrainRevealGameFooter';
import { TrainVerdictDetails } from '@/components/train/TrainVerdictDetails';
import { TrainVerdictCard, TrainVerdictStrip } from '@/components/train/TrainVerdictStrip';
import type { TrainFineMove } from '@/lib/trainArrows';
import { scorePuzzle } from '@/lib/trainScore';
import { cn } from '@/lib/utils';
import { TOUR_SPOTLIGHT_CLASS } from '@/lib/theme';
import { verdictStripLine } from '@/lib/trainBotCopy';
import type { VerdictCopy, TourTarget } from '@/lib/trainBotCopy';
import type { Persona } from '@/lib/personas/personaRegistry';
import { guessFeedbackProse } from '@/lib/trainGuessLabels';
import type { Guess } from '@/lib/trainGuessLabels';
import { revealBestUciOf, sanFromUci } from '@/lib/trainRevealLines';
import type { ChipGroup, GameMoveLineState, RoleKey } from '@/lib/trainRevealLines';
import type { GradeResult, TrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import type { InstantGradeState } from '@/hooks/trainGradingSupport';
import type { PuzzleRevealResponse, SolveResponse, TrainPuzzle } from '@/types/train';

export interface TrainRevealProps {
  puzzle: TrainPuzzle;
  /** Active session id — needed for the reveal GET's URL. Null only in a
   * defensive/impossible state (a solve response cannot exist without an
   * active session), guarded by the query's own `enabled` gate. */
  sessionId: number | null;
  /** The solved puzzle's server verdict, or null while the solve mutation is
   * still pending/erroring (see module docstring). */
  verdict: SolveResponse | null;
  isSolveError: boolean;
  onRetrySolve: () => void;
  onNext: () => void;
  /** The session-scoped grading engine — threaded from
   * `TrainSolveScreen`, which already holds it. Supplies the reveal-time
   * "played in game" search via `startGameMoveSearch`. */
  gradingEngine: TrainGradingEngine;
  /** The guess the user committed before playing a move — spelled out on the
   * verdict row with the SAME wording as the guess buttons.
   * Null only in a defensive/impossible state (a verdict cannot exist
   * without a prior guess commit). */
  guess: Guess | null;
  /** The UCI of the move the user actually played — doubles as the 'your'
   * role's key for deciding whether the game move needs its own search. */
  playedMoveUci: string | null;
  /** The `gradeMove` result for `playedMoveUci` — only its key line is read
   * here (to skip the game-move search when the game move IS the best move). */
  gradeResult: GradeResult | null;
  /**
   * Non-null while a server-graded move's background
   * phone grade is outstanding. Only its key is read here; the chips carry the
   * loading/failed state.
   */
  instantGrade?: InstantGradeState | null;
  /**
   * The chips row, built once by the board owner
   * (`buildChipGroups`) so the same groups seed the move tree. Empty before the
   * verdict.
   */
  chips: readonly ChipGroup[];
  /** The chip whose line the list shows (the tree's `activeChip`), or null. */
  activeChip: RoleKey | null;
  /** A chip tap (the board owner jumps the tree to the puzzle position). */
  onChipSelect: (key: RoleKey) => void;
  /** The single move list under the chips (`TrainMoveTreeList`). A slot
   * so this component stays presentational; the tree lives in the board owner. */
  treeList: ReactNode;
  /**
   * Reports the reveal query's resolved game-move UCI to the
   * board owner (TrainSolveScreen), which needs it to draw the thin white
   * game-move arrow, without lifting the reveal query itself out of this
   * component. Called with `null` on cleanup (puzzle transition/unmount) so a
   * stale prior-puzzle game move never leaks into the next puzzle's arrows.
   */
  onGameMoveUciChange?: (uci: string | null) => void;
  /**
   * Reports every state of the reveal-time "played in game" search
   * (idle / loading / ready with the line / error) to the board owner, which
   * builds the standalone game chip from it (loading spinner, failed state) and
   * derives the game move's QUALITY from the line. `{ status: 'idle' }` on
   * cleanup/re-dispatch so a stale line never outlives its search. The search
   * is skipped entirely (idle) when the game move coincides with the played or
   * best move: the merged chip carries that surviving entry's line.
   */
  onGameMoveLineStateChange?: (state: GameMoveLineState) => void;
  /**
   * Exactly the alternative fine moves
   * actually drawn as green arrows on the board (`revealOverlay.alsoFineMoves`
   * from the board owner) — never the overflow past the puzzle-type arrow
   * cap. Defaults to empty so the list simply doesn't render before a verdict
   * has landed.
   */
  alsoFineMoves?: TrainFineMove[];
  /**
   * The reveal tour's active target, or null when no
   * tour is showing. Spotlights (the shared TOUR_SPOTLIGHT_CLASS
   * glow) the strip / verdict bubble (`verdict`), the chips row (`chips`, the
   * active chip keeps its own selection ring), the move list (`tree`) and the
   * chips-plus-list region (`lines`); `board` and `bar` are spotlit by the board
   * owner. Independent of the chip focus: the tour must never touch which arrow
   * is lit.
   */
  tourTarget?: TourTarget | null;
  /**
   * The verdict surface. Phones
   * get the collapsed strip, desktop the full verdict bubble at the top of the
   * right column; both render the same `TrainVerdictDetails` body. The bot, the
   * opener (a random draw) and the best-move flag are resolved ONCE per verdict
   * by the board owner.
   */
  verdictBot: Persona | null;
  verdictOpening: VerdictCopy | null;
  /** True when the played move is the engine's best: the exact predicate that
   * merges the You and Best chips, so the clause can never say "best move" next
   * to separate chips. */
  isBest: boolean;
  sessionDate?: string;
  expiresOn?: string;
  isWarmup: boolean;
  /** Fired once per strip expansion (collapsed -> open), for the board owner's
   * telemetry. The Umami event itself is sent by the strip. */
  onStripExpand?: () => void;
}

export function TrainReveal({
  puzzle,
  sessionId,
  verdict,
  isSolveError,
  onRetrySolve,
  onNext,
  gradingEngine,
  guess,
  playedMoveUci,
  gradeResult,
  instantGrade = null,
  chips,
  activeChip,
  onChipSelect,
  treeList,
  onGameMoveUciChange,
  onGameMoveLineStateChange,
  alsoFineMoves = [],
  tourTarget = null,
  verdictBot,
  verdictOpening,
  isBest,
  sessionDate,
  expiresOn,
  isWarmup,
  onStripExpand,
}: TrainRevealProps): ReactElement | null {
  const { startGameMoveSearch } = gradingEngine;
  const isDesktop = useIsDesktop();

  // Disabled until the solve POST has landed — no speculative
  // pre-attempt fetch, no answer-key data reachable before this gate flips.
  const revealQuery = useQuery<PuzzleRevealResponse>({
    queryKey: ['train-reveal', sessionId, puzzle.position],
    queryFn: () => trainApi.revealPuzzle(sessionId as number, puzzle.position),
    enabled: verdict !== null && sessionId !== null,
    staleTime: Infinity, // the answer key never changes once solved
  });

  // Dispatched exclusively off
  // `revealQuery.data` — reachable only once the reveal GET has itself
  // succeeded, which is already gated on the solve POST having landed. No
  // engine search on the game move can fire before that.
  const gameMoveUci = revealQuery.data?.played_in_game_move_uci ?? null;

  // Report the resolved game-move UCI to the board owner so
  // it can draw the thin white game-move arrow — fires whenever the reveal
  // query's played_in_game_move_uci resolves, and with null on cleanup
  // (puzzle transition/unmount) so a stale value never leaks forward.
  useEffect(() => {
    onGameMoveUciChange?.(gameMoveUci);
    return () => {
      onGameMoveUciChange?.(null);
    };
  }, [gameMoveUci, onGameMoveUciChange]);

  // A primitive dep, so the grade landing (the pending state
  // replaced by a gradeResult with the same best UCI) does not re-dispatch the
  // game search.
  const revealBestUci = revealBestUciOf(gradeResult, instantGrade);
  useEffect(() => {
    if (gameMoveUci === null) {
      onGameMoveLineStateChange?.({ status: 'idle' });
      return;
    }
    // When the game move coincides with the played move or the
    // engine's best move, the merged chip uses that SURVIVING entry's line —
    // no reveal-time search is dispatched at all.
    const coincidesWithYourOrBest = gameMoveUci === playedMoveUci || gameMoveUci === revealBestUci;
    if (coincidesWithYourOrBest) {
      onGameMoveLineStateChange?.({ status: 'idle' });
      return;
    }
    let cancelled = false;
    onGameMoveLineStateChange?.({ status: 'loading' });
    startGameMoveSearch(puzzle.fen, gameMoveUci)
      .then((line) => {
        if (cancelled) return;
        onGameMoveLineStateChange?.({ status: 'ready', line });
      })
      .catch(() => {
        if (cancelled) return;
        onGameMoveLineStateChange?.({ status: 'error' });
      });
    return () => {
      cancelled = true;
      // A stale search state must never outlive its search.
      onGameMoveLineStateChange?.({ status: 'idle' });
    };
  }, [gameMoveUci, puzzle.fen, startGameMoveSearch, playedMoveUci, revealBestUci, onGameMoveLineStateChange]);

  if (verdict === null) {
    // Grading/solve has not landed successfully yet. Only the block-and-retry
    // row applies.
    if (!isSolveError) return null;
    return (
      <div className="flex flex-col items-center gap-2" data-testid="train-solve-error">
        <p className="text-sm font-semibold">Couldn&apos;t save your result.</p>
        <Button
          variant="brand-outline"
          className={TRAIN_BUTTON_CLASS}
          data-testid="btn-train-solve-retry"
          onClick={onRetrySolve}
        >
          Retry
        </Button>
        <Button
          variant="default"
          className={TRAIN_BUTTON_CLASS}
          data-testid="btn-train-next"
          disabled
          onClick={onNext}
        >
          Next
        </Button>
      </div>
    );
  }

  // Mastery banner: only for an SR item (`verdict.source === 'sr_item'`) that
  // reached mastered. Herrings and sharp fillers carry no SR bookkeeping.
  // Don't test `puzzle_type !== 'herring'`: a sharp filler satisfies it.
  const showFlawFixedBanner =
    verdict.source === 'sr_item' && verdict.item_status === 'mastered';
  const gameMoveSan = revealQuery.data?.played_in_game_san ?? null;
  // A game move with a known SAN but no derivable UCI (an
  // unparseable SAN) has no line to pre-load, so it renders as a non-interactive
  // chip instead of a button.
  const sanOnlyGameMove = gameMoveUci === null ? gameMoveSan : null;
  // Unlike the `sr_item` predicate above, this has no
  // synchronous-timing requirement — it only adds a line once the async
  // reveal resolves, never gates a suppression, so reading `revealQuery.data`
  // here is safe.
  const motif = revealQuery.data?.motif ?? null;
  const showChipRow = chips.length > 0 || sanOnlyGameMove !== null;
  const tourSpotlightVerdict = tourTarget === 'verdict';

  // The verdict details state the verdict but never say why; this derives one
  // prose sentence (`guessFeedbackProse`). `verdict.source === 'sr_item'` is
  // the "user's own blunder vs a red herring/sharp filler" predicate, the same
  // one the game footer uses. Reads `verdict`, not `revealQuery.data`, for the
  // synchronous-timing reason the game footer's comment documents.
  // `move_quality` joins it so the sentence can never claim the user played
  // the critical move on the strength of the guess alone.
  // The disagreement line reads the SERVER's `disagreement` flag only (never
  // the phone's own outcome). The key SAN comes from `gradeResult.bestMoveUci`
  // because on the keyed path that IS the server key.
  const disagreement = verdict.disagreement ?? false;
  const keySan = disagreement ? sanFromUci(puzzle.fen, gradeResult?.bestMoveUci ?? null) : null;
  const guessProse =
    guess !== null
      ? guessFeedbackProse(
          guess,
          verdict.correct_guess,
          verdict.source === 'sr_item',
          verdict.move_quality,
          disagreement,
          keySan,
        )
      : null;
  const alsoFineSanList = alsoFineMoves
    .map((f) => sanFromUci(puzzle.fen, f.uci))
    .filter((san): san is string => san !== null)
    .join(', ');

  const renderVerdictDetails = (leading?: ReactNode): ReactNode =>
    verdictOpening !== null ? (
      <TrainVerdictDetails
        leading={leading}
        verdict={verdict}
        opening={verdictOpening}
        isBest={isBest}
        sessionDate={sessionDate}
        expiresOn={expiresOn}
        isWarmup={isWarmup}
        guess={guess}
        guessProse={guessProse}
        motif={motif}
        alsoFineSanList={alsoFineSanList}
      />
    ) : null;

  return (
    // lg:mt-[46px]: on desktop the board column starts
    // with its progress block (20px text row + 4px gap + 6px bar + the
    // column's 16px gap = 46px before the board itself), so this offset
    // top-aligns the Guess verdict with the TOP OF THE BOARD, not the
    // progress text. Keep in sync with TrainSolveScreen's progress block.
    <div
      className="flex w-full flex-col gap-4 lg:mt-[46px] lg:max-w-sm"
      data-testid="train-reveal"
    >
      {/* 1. The verdict surface. Phones: the one-line strip
          (bot avatar + total + clause), collapsed on every reveal; its tap opens
          the full feedback. Desktop: the same card always open, avatar floated
          beside the verdict. Both carry the SAME `TrainVerdictDetails` body, so
          the clause vocabulary and the guess feedback can never drift between
          them. The points shown come from the server's verdict fields via
          `scorePuzzle`; `isBest` only selects wording. */}
      {verdictBot !== null && verdictOpening !== null && (
        isDesktop ? (
          <TrainVerdictCard persona={verdictBot} spotlight={tourSpotlightVerdict} renderDetails={renderVerdictDetails} />
        ) : (
          <TrainVerdictStrip
            persona={verdictBot}
            points={scorePuzzle(verdict.correct_guess, verdict.move_quality)}
            line={verdictStripLine(verdict.correct_guess, verdict.move_quality, isBest)}
            onExpand={onStripExpand}
            spotlight={tourSpotlightVerdict}
          >
            {renderVerdictDetails()}
          </TrainVerdictStrip>
        )
      )}

      {/* 2. Flaw fixed banner; nothing for a herring or a non-mastered item. */}
      {showFlawFixedBanner && <TrainFlawFixedBanner fen={puzzle.fen} />}

      {revealQuery.isError && (
        <p className="text-sm font-semibold text-muted-foreground" data-testid="train-reveal-error">
          Couldn&apos;t load the full reveal details.
        </p>
      )}

      {/* 3. The chips row — one per DISTINCT first
          move, merged when two or three coincide ("Move = Best") — and the
          one move list showing the focused chip's pre-loaded line (plus the
          user's own sidelines). Every eval/line comes from the client grading
          engine (`gradeResult` or the reveal-time search), never a stored
          server line. The tour spotlights the chips row, the
          list, or (the understand step) this wrapper around both; the wrapper
          keeps the reveal column's gap, so the layout does not move. */}
      {(showChipRow || chips.length > 0) && (
        <div
          data-testid="train-lines-tour-target"
          className={cn('flex flex-col gap-4 rounded-md', tourTarget === 'lines' && TOUR_SPOTLIGHT_CLASS)}
        >
          {showChipRow && (
            <div
              data-tour-target="chips"
              className={cn('rounded-md', tourTarget === 'chips' && TOUR_SPOTLIGHT_CLASS)}
            >
              <TrainLineChips
                chips={chips}
                activeChip={activeChip}
                onSelect={onChipSelect}
                sanOnlyGameMove={sanOnlyGameMove}
              />
            </div>
          )}
          {chips.length > 0 && (
            <div
              data-tour-target="tree"
              data-testid="train-tree-tour-ring"
              className={cn('rounded-md', tourTarget === 'tree' && TOUR_SPOTLIGHT_CLASS)}
            >
              {treeList}
            </div>
          )}
        </div>
      )}

      {/* 4. Game footer: "Game: <TC> · vs <opponent> (<elo>) · <date>", with
          its `sr_item` gate and game query, in TrainRevealGameFooter. */}
      <TrainRevealGameFooter puzzle={puzzle} verdict={verdict} />
    </div>
  );
}
