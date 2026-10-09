/**
 * TrainReveal — the auto-opening post-solve reveal panel (SOLV-05/06/07-
 * adjacent, D-07..D-12 from Phase 190, D-01..D-05 from Phase 190.1, reworked
 * by Phase 237).
 *
 * Auto-opens as soon as grading and the solve POST have BOTH landed — no
 * "show solution" tap (D-07). Order: the verdict surface (a one-line strip on
 * phones, the full verdict bubble on desktop, both carrying the same
 * `TrainVerdictDetails` body), the mastery banner, a chips row (You / Best /
 * Game, each with its quality mark, SAN and eval) with ONE move list under it,
 * then the compact game footer (SOLV-05). The Your-call card of earlier phases
 * is part of the verdict details now. The three steppable line cards of Phase
 * 190.1 are gone (their history is in git): the chips pick a line, the move list
 * steps it, and the board follows the single `useTrainRevealTree` tree that
 * TrainSolveScreen owns. This component stays presentational for both: it
 * receives the chips and the list element as props. The rewind / Analyze / Next
 * bar lives with the board in TrainSolveScreen.
 *
 * Every chip's eval/PV comes from the client grading engine
 * (`GradeResult.bestLine`/`.playedLine` from `gradeMove`, and the reveal-time
 * "played in game" search from 190.1-01) — never a stored server line/eval
 * (190.1-03 D-01).
 *
 * T-190-16 (Information Disclosure — speculative prefetch): both
 * answer-adjacent fetches this component owns (the reveal GET and the game
 * card) are gated on the solve response being present (`verdict !== null`) —
 * neither ever fires before the solve POST has actually succeeded.
 *
 * When the solve POST has NOT succeeded (still pending, or failed), this
 * component renders only the pre-existing block-and-retry row (190-04) —
 * same test ids, same disabled-Next contract — so 190-04's own regression
 * coverage (`TrainSolveScreen.test.tsx`) keeps passing unchanged.
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
import { verdictStripLine } from '@/lib/trainBotCopy';
import type { TrainCopyAudience, VerdictCopy, WalkthroughTarget } from '@/lib/trainBotCopy';
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
  /** The session-scoped grading engine (190.1-01) — threaded from
   * `TrainSolveScreen`, which already holds it. Supplies the reveal-time
   * "played in game" search via `startGameMoveSearch`. */
  gradingEngine: TrainGradingEngine;
  /** The guess the user committed before playing a move — spelled out on the
   * verdict row with the SAME wording as the guess buttons (190.1-03 D-03).
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
   * Phase 236 (D-14/D-15): non-null while a server-graded move's background
   * phone grade is outstanding. Only its key is read here; the chips carry the
   * loading/failed state.
   */
  instantGrade?: InstantGradeState | null;
  /**
   * Phase 237 (D-02): the chips row, built once by the board owner
   * (`buildChipGroups`) so the same groups seed the move tree. Empty before the
   * verdict.
   */
  chips: readonly ChipGroup[];
  /** The chip whose line the list shows (the tree's `activeChip`), or null. */
  activeChip: RoleKey | null;
  /** A chip tap (D-01: the board owner jumps the tree to the puzzle position). */
  onChipSelect: (key: RoleKey) => void;
  /** The single move list under the chips (plan 04's `TrainMoveTreeList`). A slot
   * so this component stays presentational; the tree lives in the board owner. */
  treeList: ReactNode;
  /**
   * 190.1-04 (D-02): reports the reveal query's resolved game-move UCI to the
   * board owner (TrainSolveScreen), which needs it to draw the thin white
   * game-move arrow, without lifting the reveal query itself out of this
   * component. Called with `null` on cleanup (puzzle transition/unmount) so a
   * stale prior-puzzle game move never leaks into the next puzzle's arrows.
   */
  onGameMoveUciChange?: (uci: string | null) => void;
  /**
   * Fired by the game footer's open-on-the-analysis-board link, immediately
   * before it navigates. Wired to the SAME `handleAnalyzeClick` as the
   * board's Analyze button: that handler writes the reveal cache, which is
   * what lets a Back from /analysis restore this reveal instead of dropping
   * the user on a fresh puzzle. A footer link that navigated without it
   * would look identical and silently lose the reveal on Back.
   */
  onAnalyzeClick?: () => void;
  /**
   * Phase 237: reports every state of the reveal-time "played in game" search
   * (idle / loading / ready with the line / error) to the board owner, which
   * builds the standalone game chip from it (loading spinner, failed state) and
   * derives the game move's QUALITY from the line. `{ status: 'idle' }` on
   * cleanup/re-dispatch so a stale line never outlives its search. The search
   * is skipped entirely (idle) when the game move coincides with the played or
   * best move: the merged chip carries that surviving entry's line.
   */
  onGameMoveLineStateChange?: (state: GameMoveLineState) => void;
  /**
   * Phase 200 (LEGEND-04/D-02/D-03): exactly the alternative fine moves
   * actually drawn as green arrows on the board (`revealOverlay.alsoFineMoves`
   * from the board owner) — never the overflow past the puzzle-type arrow
   * cap. Defaults to empty so the list simply doesn't render before a verdict
   * has landed. Rendered in the guess card's body since UAT round 6.
   */
  alsoFineMoves?: TrainFineMove[];
  /**
   * Phase 237 plan 10 (D-10): the first-reveal tour's active target, or null
   * when no tour is showing. Rings the strip / verdict bubble (`verdict`) and
   * the move list (`tree`, `lines`); the chips row is never ringed (the active
   * chip's own ring marks it, Phase 237 UAT); `board` and `bar` are ringed by
   * the board owner. Independent of the chip
   * focus: the tour must never touch which arrow is lit.
   */
  walkthroughTarget?: WalkthroughTarget | null;
  /**
   * Phase 237 plan 08 (ROADMAP item 1, D-05..D-08): the verdict surface. Phones
   * get the collapsed strip, desktop the full verdict bubble at the top of the
   * right column; both render the same `TrainVerdictDetails` body. The bot, the
   * opener (a random draw) and the best-move flag are resolved ONCE per verdict
   * by the board owner.
   */
  verdictBot: Persona | null;
  verdictOpening: VerdictCopy | null;
  /** True when the played move is the engine's best: the exact predicate that
   * merges the You and Best chips, so the clause can never say "best move" next
   * to separate chips (D-06). */
  isBest: boolean;
  sessionDate?: string;
  expiresOn?: string;
  isWarmup: boolean;
  audience: TrainCopyAudience;
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
  onAnalyzeClick,
  onGameMoveLineStateChange,
  alsoFineMoves = [],
  walkthroughTarget = null,
  verdictBot,
  verdictOpening,
  isBest,
  sessionDate,
  expiresOn,
  isWarmup,
  audience,
  onStripExpand,
}: TrainRevealProps): ReactElement | null {
  const { startGameMoveSearch } = gradingEngine;
  const isDesktop = useIsDesktop();

  // T-190-16: disabled until the solve POST has landed — no speculative
  // pre-attempt fetch, no answer-key data reachable before this gate flips.
  const revealQuery = useQuery<PuzzleRevealResponse>({
    queryKey: ['train-reveal', sessionId, puzzle.position],
    queryFn: () => trainApi.revealPuzzle(sessionId as number, puzzle.position),
    enabled: verdict !== null && sessionId !== null,
    staleTime: Infinity, // the answer key never changes once solved
  });

  // 190.1-01, D-01 point 3 / T-190.1-02: dispatched exclusively off
  // `revealQuery.data` — reachable only once the reveal GET has itself
  // succeeded, which is already gated on the solve POST having landed. No
  // engine search on the game move can fire before that.
  const gameMoveUci = revealQuery.data?.played_in_game_move_uci ?? null;

  // 190.1-04 (D-02): report the resolved game-move UCI to the board owner so
  // it can draw the thin white game-move arrow — fires whenever the reveal
  // query's played_in_game_move_uci resolves, and with null on cleanup
  // (puzzle transition/unmount) so a stale value never leaks forward.
  useEffect(() => {
    onGameMoveUciChange?.(gameMoveUci);
    return () => {
      onGameMoveUciChange?.(null);
    };
  }, [gameMoveUci, onGameMoveUciChange]);

  // RESEARCH Pitfall 5: a primitive dep, so the grade landing (the pending state
  // replaced by a gradeResult with the same best UCI) does not re-dispatch the
  // game search.
  const revealBestUci = revealBestUciOf(gradeResult, instantGrade);
  useEffect(() => {
    if (gameMoveUci === null) {
      onGameMoveLineStateChange?.({ status: 'idle' });
      return;
    }
    // 190.1-03 D-03: when the game move coincides with the played move or the
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
      // Phase 237: a stale search state must never outlive its search.
      onGameMoveLineStateChange?.({ status: 'idle' });
    };
  }, [gameMoveUci, puzzle.fen, startGameMoveSearch, playedMoveUci, revealBestUci, onGameMoveLineStateChange]);

  if (verdict === null) {
    // Grading/solve has not landed successfully yet. Only the pre-existing
    // block-and-retry row applies (190-04) — same shape, same test ids.
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

  // PROG-03/D-14: the mastery banner supersedes the old plain "Mastered —
  // retired." comeback hint. Same trigger condition the removed
  // `comebackHint` used — a herring or a sharp filler carries no SR
  // bookkeeping (POOL-08/WARM-04) so neither ever shows the banner. Phase
  // 206 (D-19): `verdict.source === 'sr_item'` replaces the old
  // `puzzle_type !== 'herring'` proxy — a sharp filler has `puzzle_type:
  // 'sharp'`, which the old two-way check would have wrongly satisfied.
  const showFlawFixedBanner =
    verdict.source === 'sr_item' && verdict.item_status === 'mastered';
  const gameMoveSan = revealQuery.data?.played_in_game_san ?? null;
  // Phase 237: a game move with a known SAN but no derivable UCI (an
  // unparseable SAN) has no line to pre-load, so it renders as a non-interactive
  // chip instead of a button.
  const sanOnlyGameMove = gameMoveUci === null ? gameMoveSan : null;
  // Phase 206 (D-20): unlike the D-19 predicates above, this has no
  // synchronous-timing requirement — it only adds a line once the async
  // reveal resolves, never gates a suppression, so reading `revealQuery.data`
  // here is safe.
  const motif = revealQuery.data?.motif ?? null;
  const showChipRow = chips.length > 0 || sanOnlyGameMove !== null;
  const tourRingVerdict = walkthroughTarget === 'verdict';

  // Quick 260803-iv6 (Task 3): the guess card states the verdict but never
  // says WHY it landed where it did — one locked prose sentence, derived
  // next to `showAlsoFine` since both render inside the same card body.
  // `verdict.source === 'sr_item'` (Phase 206, D-19) is the "one of the
  // user's own blunders vs a red herring/sharp filler" predicate — the SAME
  // one the game footer below already uses, no extra field needed. Reads
  // `verdict`, not `revealQuery.data`, for the same synchronous-timing
  // reason the game footer's comment documents below (RESEARCH Pitfall 1).
  // `move_quality` joins it (2026-08-03 bug fix) so the sentence can never
  // claim the user PLAYED the critical move on the strength of the guess
  // alone; see `guessFeedbackProse`.
  // Phase 235 (D-15): the D-15 line reads the SERVER's `disagreement` flag only
  // (never the phone's own outcome, T-235-07). The key SAN comes from
  // `gradeResult.bestMoveUci` because on the keyed path that IS the server key
  // (plan 02, D-09).
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
        audience={audience}
        guess={guess}
        guessProse={guessProse}
        motif={motif}
        alsoFineSanList={alsoFineSanList}
      />
    ) : null;

  return (
    // lg:mt-[46px] (190.1 UAT round 4): on desktop the board column starts
    // with its progress block (20px text row + 4px gap + 6px bar + the
    // column's 16px gap = 46px before the board itself), so this offset
    // top-aligns the Guess verdict with the TOP OF THE BOARD, not the
    // progress text. Keep in sync with TrainSolveScreen's progress block.
    <div
      className="flex w-full flex-col gap-4 lg:mt-[46px] lg:max-w-sm"
      data-testid="train-reveal"
    >
      {/* 1. The verdict surface (Phase 237 plan 08). Phones: the one-line strip
          (bot avatar + total + clause), collapsed on every reveal; its tap opens
          the full feedback. Desktop: the same card always open, avatar floated
          beside the verdict (Phase 237 UAT). Both carry the SAME `TrainVerdictDetails` body, so the
          clause vocabulary and the Your-call feedback can never drift between
          them. The points shown come from the server's verdict fields via
          `scorePuzzle` (D-23 Option B); `isBest` only selects wording. */}
      {verdictBot !== null && verdictOpening !== null && (
        isDesktop ? (
          <TrainVerdictCard persona={verdictBot} ring={tourRingVerdict} renderDetails={renderVerdictDetails} />
        ) : (
          <TrainVerdictStrip
            persona={verdictBot}
            points={scorePuzzle(verdict.correct_guess, verdict.move_quality)}
            line={verdictStripLine(verdict.correct_guess, verdict.move_quality, isBest)}
            onExpand={onStripExpand}
            ring={tourRingVerdict}
          >
            {renderVerdictDetails()}
          </TrainVerdictStrip>
        )
      )}

      {/* 2. Flaw fixed banner (PROG-03/D-14) — supersedes the D-12 plain
          "Mastered — retired." comeback hint; nothing for a herring or a
          non-mastered item. */}
      {showFlawFixedBanner && <TrainFlawFixedBanner fen={puzzle.fen} />}

      {revealQuery.isError && (
        <p className="text-sm font-semibold text-muted-foreground" data-testid="train-reveal-error">
          Couldn&apos;t load the full reveal details.
        </p>
      )}

      {/* 3. Phase 237 (D-01..D-03): the chips row — one per DISTINCT first
          move, merged when two or three coincide ("Move = Best") — and the
          one move list showing the focused chip's pre-loaded line (plus the
          user's own sidelines). Every eval/line comes from the client grading
          engine (`gradeResult` or the reveal-time search), never a stored
          server line. */}
      {showChipRow && (
        <div data-tour-target="chips">
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
          className={cn(
            (walkthroughTarget === 'tree' || walkthroughTarget === 'lines') &&
              'rounded-md ring-2 ring-brand-brown',
          )}
        >
          {treeList}
        </div>
      )}

      {/* 4. Game footer (190.1-03 D-03): "Game: <TC> · vs <opponent> (<elo>) ·
          <date>" with the open-on-the-analysis-board link. Phase 237 plan 08
          moved it, with its `sr_item` gate and game query, into
          TrainRevealGameFooter. */}
      <TrainRevealGameFooter puzzle={puzzle} verdict={verdict} onAnalyzeClick={onAnalyzeClick} />
    </div>
  );
}
