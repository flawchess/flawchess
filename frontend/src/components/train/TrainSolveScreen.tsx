/**
 * TrainSolveScreen — the guess -> one move -> grade -> verdict slice of the
 * Train solve loop (SOLV-01/02/03/04, D-05/D-06/D-13, Phase 190 Plans 01+04).
 *
 * D-05 (LOCKED): the board is fully visible for study but rejects every
 * piece input until the user commits a binary guess ("Only one" /
 * "Several", Phase 222 D-09); the guess buttons sit where the move prompt
 * lives.
 * After the guess, exactly one move is accepted (SOLV-02) — every subsequent
 * drop is rejected.
 *
 * Grading (SOLV-03): `startGrading(puzzle.fen)` fires once per puzzle at
 * MOUNT (190-RESEARCH.md Open Question 1 — resolved at mount to maximise the
 * D-06 fast-path hit rate), not gated on the guess. `correct_guess` is read
 * ONLY from the server's `SolveResponse` — never recomputed client-side
 * (POOL-10).
 *
 * Persistence (190-04 Task 3, T-190-12): once grading resolves, the verdict
 * renders from `trainSession.lastSolveResponse` (the solve mutation's own
 * `data`) rather than a copy held in local state — so a retried solve
 * (`trainSession.retrySolve`) surfaces its result exactly the same way a
 * first-try success does, with no separate wiring. `advance()` itself is a
 * no-op until the CURRENT puzzle's solve has actually succeeded (the hook's
 * own gate); the Next button's `disabled` attribute mirrors that but is not
 * the only thing enforcing it (defense in depth — the hook's gate is what the
 * forced-failure test actually asserts against).
 *
 * Plan 05 replaces the inline verdict/error/Next block with `TrainReveal`
 * (the reveal panel — verdicts, honest copy, best line, opt-in tactic
 * stepper, game card, deep link). `TrainReveal` fetches the reveal GET, the
 * game card, and the tactic-lines PV itself, all gated on the solve response
 * being present (T-190-16) — none of that data is requested before the
 * solve POST resolves.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, ReactElement } from 'react';
import { Chess, type Move } from 'chess.js';
import { Loader2, Search } from 'lucide-react';
import { Link } from 'react-router';
import { buildGameAnalysisUrl } from '@/lib/analysisUrl';
import { ChessBoard } from '@/components/board/ChessBoard';
import { Button } from '@/components/ui/button';
import { LoadError } from '@/components/ui/load-error';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { TrainReveal, TrainScoreChip } from '@/components/train/TrainReveal';
import type { TrainRevealStep } from '@/components/train/TrainReveal';
import { EvalBar } from '@/components/analysis/EvalBar';
import type { SolveResponse, TrainPuzzle, TrainSettingsResponse, VettedMove } from '@/types/train';
import type { UseTrainSessionResult } from '@/hooks/useTrainSession';
import { useFitBoardToViewport } from '@/hooks/useFitBoardToViewport';
import { useIsDesktop } from '@/hooks/useIsDesktop';
import { useTrainFreePlay, uciFromDrop } from '@/hooks/useTrainFreePlay';
import { useStockfishEngine, type StockfishEngineState } from '@/hooks/useStockfishEngine';
import type { PvLine } from '@/hooks/uciParser';
import { useWakeLock } from '@/hooks/useWakeLock';
import type { GradeResult, TrainEngineLine, TrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import { evalToExpectedScore, sideToMoveFromFen, terminalPositionEval } from '@/lib/liveFlaw';
import { useMarkPlayActive } from '@/lib/playActive';
import { usePublishMobileBoardControls } from '@/lib/mobileBoardControls';
import { playSound } from '@/lib/sounds';
import { saveTrainRevealCache } from '@/lib/trainRevealCache';
import type { CachedTrainReveal } from '@/lib/trainRevealCache';
import { GUESS_LABELS } from '@/lib/trainGuessLabels';
import type { Guess } from '@/lib/trainGuessLabels';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import { resolveBubbleState } from '@/components/train/trainBubbleState';
import type { TrainBubbleState } from '@/components/train/trainBubbleState';
import {
  GRADING_COPY,
  HILDA_ID,
  introStepCount,
  WALKTHROUGH_STEP_COUNT,
  dropNudgeCopy,
  introCopy,
  movePromptCopy,
  pickBot,
  promptCopy,
  returnPhrase,
  verdictCopy,
  walkthroughCopy,
} from '@/lib/trainBotCopy';
import type { IntroStep, TrainCopyAudience, VerdictCopy, WalkthroughStep } from '@/lib/trainBotCopy';
import { cn } from '@/lib/utils';
import { personaForId } from '@/lib/personas/personaRegistry';
import type { Persona } from '@/lib/personas/personaRegistry';
import { placeholderAvatarFor, resolveAvatarSrc } from '@/lib/personas/personaAvatars';
import { useTrainSettings } from '@/hooks/useTrainSettings';
import { useTrainOnboarding } from '@/hooks/useTrainOnboarding';
import { useTrainWalkthrough } from '@/hooks/useTrainWalkthrough';
import { TrainBotStepper } from '@/components/train/TrainBotStepper';
import {
  applyTrainSpotlight,
  buildTrainFreePlayArrows,
  buildTrainRevealOverlay,
  buildTrainStepArrows,
  buildTrainStepMarkers,
  classifyTrainMoveQuality,
  TRAIN_STEP_HIGHLIGHT,
} from '@/lib/trainArrows';
import type { TrainMoveQuality, TrainOverlayMove } from '@/lib/trainArrows';
import { scorePuzzle, MOVE_TIER_POINTS, GUESS_POINTS, TRAIN_POINTS_PER_PUZZLE } from '@/lib/trainScore';
import type { TrainMoveTier } from '@/lib/trainScore';
import {
  SEV_INACCURACY,
  SEV_MISTAKE,
  ZONE_DANGER,
  ZONE_SUCCESS,
  TRAIN_POINTS_FG_ON_DARK,
  TRAIN_POINTS_FG_ON_LIGHT,
  STOCKFISH_ACCENT,
} from '@/lib/theme';

export interface TrainSolveScreenProps {
  puzzle: TrainPuzzle;
  trainSession: UseTrainSessionResult;
  gradingEngine: TrainGradingEngine;
  /** Called instead of `trainSession.advance()` when the Next control is
   * pressed on a landed verdict. Defaults to `trainSession.advance` — Plan
   * 05 Task 3 wires a real callback from Train.tsx that also handles the
   * session-complete -> score-screen transition. */
  onNext?: () => void;
  /**
   * 190.1 UAT round 5 (Analyze -> browser back): a previously solved
   * puzzle's cached solution state. When set, it always describes `puzzle`
   * itself (Train.tsx passes the cached puzzle alongside it), and the screen
   * mounts straight into the reveal — guess/played-move/grade seeded from
   * the cache, `moveApplied` locked, and NO mount grading search (the puzzle
   * is already solved; no move will ever be graded). The reveal's own
   * game-move search still runs — it is independent of the mount search.
   */
  restoredSolve?: CachedTrainReveal | null;
  /** D-03 (Phase 224): true when the account has at least one imported game
   * (`hasImportedGames`, `useUserProfile().data`). Selects the intro/verdict
   * copy variant threaded through the bot bubble. */
  hasGames: boolean;
  /** D-03 (Phase 224): from `useUserProfile().data`, never `useAuth().user`
   * (FLAWCHESS-64). Adds the sign-up clause to the games-less copy. */
  isGuest: boolean;
}

/**
 * Bounded readiness window (190-04 T-190-13): if the grading engine's Worker
 * never reports `isReady` within this budget — or errors at any point — the
 * solve screen stops offering the guess/move flow (which would otherwise hang
 * on "Checking your move…" forever) and surfaces `train-engine-error` with a
 * restart affordance instead. Generous above real WASM init time (seconds,
 * not tens of seconds) but finite so a genuinely dead engine is never a
 * silent, indefinite wait.
 */
const TRAIN_ENGINE_READY_TIMEOUT_MS = 15000;

/**
 * Desktop board width (190 UAT): 50% larger than the 400px ChessBoard default.
 * Shared between the `ChessBoard maxWidth` prop and the board column's
 * `max-width` so the progress bar always spans exactly the board's width
 * (same pattern as Bots.tsx's BOT_BOARD_MAX_WIDTH_PX).
 */
const TRAIN_BOARD_MAX_WIDTH_PX = 600;

/**
 * 190.1 UAT round 4: on a short browser window the board shrinks with the
 * viewport height. Floor for that shrink — below it the page scrolls instead,
 * rather than shrinking the board into unusability. Well under the old
 * `TRAIN_BOARD_MAX_WIDTH_PX / 2` (191 UAT: that floor bound before the
 * measured fit ran out of room, which is what pinned the button row to the
 * bottom edge on a short window); 240px is still ~30px squares.
 */
const TRAIN_BOARD_MIN_WIDTH_PX = 240;
/**
 * Space kept free below the board column — the page container's own `py-6`
 * bottom padding (24px) plus visual breathing room, so the
 * Solution/Analyze/Next row is never flush against the viewport edge.
 */
const TRAIN_BOARD_BOTTOM_GUTTER_PX = 40;
/*
 * Phase 222 UAT: below Tailwind's `lg` breakpoint the board is WIDTH-bound
 * only — the height fit (`useFitBoardToViewport`) runs on desktop alone
 * (`useIsDesktop`). Plan 06 had folded the phone bottom bar into the fit's
 * gutter instead, which on a 375x667 phone shrank the board to its 240px
 * floor and left wide empty margins beside it; the user's call is a
 * full-width board with the bot bubble scrolling underneath the pinned board.
 * Below `lg` the measured column is also `display: contents` (see the JSX),
 * so the fit could not measure it there anyway.
 */
/*
 * Plan 06 UAT: stepper bubbles never scroll internally — the intro and
 * first-reveal walkthrough copy is instead split into short steps that each
 * fit above the fold at 375x667 (see `STEPPER_COPY_MAX_CHARS` in
 * trainBotCopy.ts for the calibrated budget).
 */

/**
 * 190.1 UAT round 7 / SEED-119: pill background+foreground for the
 * "Points: +N" reveal flash — dark green for a perfect 3, yellow for 2
 * (an inaccuracy still earned the guess point plus one move point), orange
 * for 1, red for 0. Yellow needs its own near-black foreground
 * (`TRAIN_POINTS_FG_ON_LIGHT`) — `SEV_INACCURACY` is a light amber that
 * near-white text cannot clear — while the three dark tiers share
 * `TRAIN_POINTS_FG_ON_DARK`.
 */
const TRAIN_POINTS_FLASH_COLORS: Record<number, { bg: string; fg: string }> = {
  0: { bg: ZONE_DANGER, fg: TRAIN_POINTS_FG_ON_DARK },
  1: { bg: SEV_MISTAKE, fg: TRAIN_POINTS_FG_ON_DARK },
  2: { bg: SEV_INACCURACY, fg: TRAIN_POINTS_FG_ON_LIGHT },
  3: { bg: ZONE_SUCCESS, fg: TRAIN_POINTS_FG_ON_DARK },
};

/**
 * Quick 260803-iv6 (Task 1): the horizontal space the eval-bar column plus
 * its gutter takes out of the board row — 20px `w-5` bar + 8px `gap-2`. This
 * is the single-bar counterpart of Analysis.tsx's `BOARD_EVAL_BARS_ALLOWANCE_PX`
 * (which reserves the SAME chrome twice, once per side, for its two bars).
 */
const TRAIN_EVAL_BAR_CHROME_PX = 28;

/**
 * Quick 260803-iv6: synthetic search depth handed to `EvalBar` for a terminal
 * (checkmate/stalemate) position, so a decisive mate clears `EvalBar`'s own
 * `depth >= 8` mate-fill gate instead of collapsing to the neutral midpoint.
 * Same device Analysis.tsx uses for its own terminal eval.
 */
const TRAIN_TERMINAL_EVAL_DEPTH = 99;

/**
 * Quick 260803-iv6: resolves the Train eval bar's reading from whichever
 * source currently owns the shown position — a terminal (mate/draw) verdict
 * first (the rules already know the answer), then the free-play engine's own
 * top line while exploring, else the standalone eval-bar engine. Kept as a
 * flat, non-exported module-level helper (guard-clause returns, no nesting
 * past depth 2) so the component body stays shallow per CLAUDE.md.
 */
function resolveTrainEvalBarReading(
  fen: string,
  isExploring: boolean,
  freePlayTop: PvLine | null,
  engine: StockfishEngineState,
): { evalCp: number | null; evalMate: number | null; depth: number } {
  const terminal = terminalPositionEval(fen);
  if (terminal !== null) {
    return { evalCp: terminal.cp, evalMate: terminal.mate, depth: TRAIN_TERMINAL_EVAL_DEPTH };
  }
  if (isExploring) {
    return {
      evalCp: freePlayTop?.evalCp ?? null,
      evalMate: freePlayTop?.evalMate ?? null,
      depth: freePlayTop?.depth ?? 0,
    };
  }
  return { evalCp: engine.evalCp, evalMate: engine.evalMate, depth: engine.depth };
}

/**
 * Phase 222 (D-12/RESEARCH Finding D): resolves whether the first-session
 * intro stepper is active this render, and whether the WHOLE bubble must
 * stay silent because the outcome is still ambiguous (first puzzle, settings
 * not yet loaded — RESEARCH's "render no bubble copy until data !== undefined"
 * rule, so a first-timer never sees the regular prompt flash before the intro
 * replaces it). Module-level so the settings-shape branching never touches
 * `TrainSolveScreen`'s own pinned complexity (FINDING B).
 */
function resolveIntroState(
  settings: TrainSettingsResponse | undefined,
  settingsFailed: boolean,
  isFirstPuzzle: boolean,
  introStep: IntroStep,
): { activeIntroStep: IntroStep | null; suppressPrompt: boolean } {
  // Bug fix (phase 222 code review CR-01): `settings === undefined` covers
  // BOTH "still loading" and "the fetch failed for good" (TanStack settles
  // into `isError` with `data` still undefined). Suppressing the prompt in
  // the failed case hid the guess buttons on every session's first puzzle
  // with no error shown. A failed fetch now degrades to the regular prompt
  // (no intro — the stamp state is unknown, so it simply replays next time).
  if (settingsFailed) return { activeIntroStep: null, suppressPrompt: false };
  if (settings === undefined) return { activeIntroStep: null, suppressPrompt: isFirstPuzzle };
  if (!isFirstPuzzle) return { activeIntroStep: null, suppressPrompt: false };
  if (settings.intro_seen_at !== null) return { activeIntroStep: null, suppressPrompt: false };
  return { activeIntroStep: introStep, suppressPrompt: false };
}

/** D-07: the two guess buttons, shared by the regular prompt, the drop-nudge
 * copy, and the intro stepper's closing step (D-05) — one render site so the
 * three call sites can never drift on labels/testids/styling. */
function guessButtons(onGuess: (guess: Guess) => void): ReactElement {
  return (
    // Phase 222 UAT: both buttons the same width — a two-column grid with
    // `auto-cols-fr` sizes every column to the widest label, and the grid
    // itself shrink-wraps so the bubble's `justify-end` row still right-aligns it.
    <div className="grid grid-flow-col auto-cols-fr gap-2" data-testid="train-guess-buttons">
      <Button
        variant="brand-outline"
        className={TRAIN_BUTTON_CLASS}
        data-testid="btn-train-guess-critical"
        onClick={() => onGuess('critical')}
      >
        {GUESS_LABELS.critical}
      </Button>
      <Button
        variant="brand-outline"
        className={TRAIN_BUTTON_CLASS}
        data-testid="btn-train-guess-several"
        onClick={() => onGuess('several')}
      >
        {GUESS_LABELS.several}
      </Button>
    </div>
  );
}

/** D-23: the verdict clause's two labeled phrases (guess/move) with their
 * point values — mirrors `trainBotCopy.ts`'s `verdictClause` wording exactly,
 * but split apart so the caller can render each point value as a real
 * `TrainScoreChip` pill instead of literal "[+N]" bracket text (plan 01 kept
 * the bracket text in the pure copy module; wiring live pills is this plan's
 * job). Lives here (not `trainBotCopy.ts`) because it exists only to feed
 * JSX pills — the pure module stays React-free. */
function verdictClauseParts(
  correctGuess: boolean,
  moveQuality: TrainMoveTier,
): { guessLabel: string; guessPoints: 0 | 1; moveLabel: string; movePoints: 0 | 1 | 2 } {
  const guessLabel = correctGuess ? 'Right call' : 'Wrong call';
  const guessPoints: 0 | 1 = correctGuess ? GUESS_POINTS : 0;
  const movePoints = MOVE_TIER_POINTS[moveQuality] as 0 | 1 | 2;
  if (moveQuality === 'good') {
    const moveLabel = correctGuess ? 'right move' : 'but the right move';
    return { guessLabel, guessPoints, moveLabel, movePoints };
  }
  if (moveQuality === 'inaccuracy') {
    return { guessLabel, guessPoints, moveLabel: 'decent move', movePoints };
  }
  return { guessLabel, guessPoints, moveLabel: 'wrong move', movePoints };
}

/**
 * Phase 222 (D-23): resolves the verdict bubble's body — opener + clause with
 * inline `TrainScoreChip` pills + optional look-closer line (0-1 pts) + the
 * D-15/D-16 return tail. Module-level (RESEARCH Finding B) so this state's
 * own decision points never raise `TrainSolveScreen`'s pinned complexity.
 *
 * RESEARCH Pitfall 7: a `trainRevealCache` entry written by a pre-206 bundle
 * restores a verdict without `source` at runtime despite the TS type calling
 * it required. Per D-16, a return tail can only be trusted once the item's
 * SOURCE is known (herring/filler never return; sr_item's tail depends on
 * item_status/due_date) — so a missing `source` renders no return tail at
 * all, the one nullish default at this consumption site, rather than
 * guessing from a possibly-unrelated due_date.
 */
function renderVerdictBubbleBody(
  verdict: SolveResponse,
  opening: VerdictCopy,
  sessionDate: string | undefined,
  expiresOn: string | undefined,
  isWarmup: boolean,
  audience: TrainCopyAudience,
  actions: ReactElement,
): { copy: ReactElement; actions: ReactElement } {
  const clause = verdictClauseParts(verdict.correct_guess, verdict.move_quality);
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
  return {
    // One flowing paragraph, not one <p> per sentence: the three stacked
    // lines ate too much vertical space on phones, where the bubble sits
    // above the board. The testids stay on inline spans.
    copy: (
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
    ),
    actions,
  };
}

/**
 * Phase 222 (D-24): resolves the first-reveal walkthrough's bubble body — one
 * of the Hilda steps, each with its own copy and a Next control. The real
 * Solution/Analyze/Next row (`verdictActions`) IS the last step's control —
 * the last step's copy explains those buttons, so they must be visible (and
 * ringed) while Hilda's line about them is on screen. Phase 222 UAT round 3
 * dropped the separate "Got it": leaving the reveal through that row (Next or
 * Analyze) is what completes the walkthrough. Module-level (RESEARCH Finding
 * B) so this state's own branching never raises `TrainSolveScreen`'s own
 * pinned complexity.
 */
function renderWalkthroughBubbleBody(
  step: WalkthroughStep,
  onNext: () => void,
  verdictActions: ReactElement,
  hasAnalyze: boolean,
  hasSolution: boolean,
): { copy: ReactElement; actions: ReactElement } {
  const { copy } = walkthroughCopy(step, hasAnalyze, hasSolution);
  // Phase 222 UAT round 3: the last step's control IS the real action row —
  // no separate "Got it". Next/Analyze there both end the walkthrough (and
  // stamp it, see `handleWalkthroughLeave` in TrainSolveScreen).
  // UAT round 4: no spotlight ring around the action row — the buttons
  // themselves are the obvious target of the last step's copy.
  const lastControl = <div className="flex flex-wrap justify-end gap-2">{verdictActions}</div>;
  return {
    copy: (
      <p data-testid="train-bot-walkthrough">{copy}</p>
    ),
    actions: (
      <TrainBotStepper
        stepCount={WALKTHROUGH_STEP_COUNT}
        step={step}
        onNext={onNext}
        nextTestId="btn-train-bot-walkthrough-next"
        lastControl={lastControl}
      >
        {null}
      </TrainBotStepper>
    ),
  };
}

/** Sketch 004 (phase 222 UAT): the verdict bot's face inside the points pop
 * over the board. 40px — the sketch's `avatar md`. */
const POINTS_FLASH_AVATAR_CLASS = 'size-10';

function PointsFlashAvatar({ persona }: { persona: Persona }): ReactElement {
  const avatar = placeholderAvatarFor(persona);
  const avatarSrc = resolveAvatarSrc(persona);
  return (
    <span
      aria-hidden="true"
      className={cn(
        'flex shrink-0 items-center justify-center overflow-hidden rounded-full text-xl',
        POINTS_FLASH_AVATAR_CLASS,
      )}
      style={{ backgroundColor: avatar.tint }}
      data-testid="train-points-flash-avatar"
    >
      {avatarSrc !== undefined ? (
        <img src={avatarSrc} alt="" className="h-full w-full object-cover" />
      ) : (
        avatar.emoji
      )}
    </span>
  );
}

/**
 * Phase 200 (D-11)-era action row (Solution/Analyze/Next), relocated (D-10)
 * from the below-board sibling into the verdict bubble's own actions slot.
 * A real component (rendered via JSX at the call site below), NOT a plain
 * helper function called directly — `handleShowSolution` reads
 * `keepSpotlightRef.current` transitively (via `returnToSolution`), and
 * `react-hooks/refs` flags a ref-reading closure passed into an ordinary
 * function call during render; passing it as a JSX prop (the same pattern
 * already used for `onReturnToSolution`/`onClick` elsewhere in this file) is
 * the sanctioned shape. Module-level so the `isBoardDeparted`/`gameId`/`ply`
 * branching never raises `TrainSolveScreen`'s own pinned complexity (FINDING
 * B) — this is exactly the branch removal the plan's headroom accounting
 * relies on.
 */
function VerdictActions({
  isBoardDeparted,
  gameId,
  ply,
  onShowSolution,
  onAnalyzeClick,
  onNext,
}: {
  isBoardDeparted: boolean;
  gameId: number | null;
  ply: number;
  onShowSolution: () => void;
  onAnalyzeClick: () => void;
  onNext: () => void;
}): ReactElement {
  return (
    <>
      {isBoardDeparted && (
        <Button
          variant="brand-outline"
          className={TRAIN_BUTTON_CLASS}
          data-testid="btn-train-solution"
          onClick={onShowSolution}
        >
          Solution
        </Button>
      )}
      {gameId !== null && (
        <Button asChild variant="brand-outline" className={TRAIN_BUTTON_CLASS}>
          <Link
            to={buildGameAnalysisUrl(gameId, ply > 0 ? ply - 1 : null)}
            data-testid="btn-train-analyze"
            aria-label="Analyze this position"
            onClick={onAnalyzeClick}
          >
            <Search className="h-4 w-4 mr-1" />
            Analyze
          </Link>
        </Button>
      )}
      <Button
        variant="default"
        className={TRAIN_BUTTON_CLASS}
        data-testid="btn-train-next"
        onClick={onNext}
      >
        Next
      </Button>
    </>
  );
}

/** Inputs `renderTrainBotBubbleBody` needs beyond `bubbleState` itself —
 * bundled so growing the state machine (intro, drop-nudge, verdict) never
 * grows a raw parameter list. */
interface BubbleBodyDeps {
  sideToMove: 'white' | 'black';
  /** The committed call, echoed by the move prompt (phase 222 UAT). */
  guess: Guess | null;
  onGuess: (guess: Guess) => void;
  /** RESEARCH Finding D: true only while the FIRST puzzle's intro-or-not
   * outcome is still ambiguous (settings not yet loaded) — suppresses the
   * regular prompt so it can never flash before the intro replaces it. */
  suppressPrompt: boolean;
  onIntroNext: () => void;
  onIntroGuess: (guess: Guess) => void;
  /** Non-null exactly when `bubbleState.kind === 'verdict'` (hasVerdict is
   * the top precedence rung in `resolveBubbleState`, so the two are always
   * in lockstep). */
  verdict: SolveResponse | null;
  /** UAT round 4: resolved ONCE per verdict by the caller (`useMemo`), never
   * inside this render helper — `verdictCopy` draws a random opener, and a
   * per-render draw flipped "Nice."/"Solid." on every board interaction,
   * re-wrapping the bubble and twitching the layout. */
  verdictOpening: VerdictCopy | null;
  sessionDate: string | undefined;
  expiresOn: string | undefined;
  verdictActions: ReactElement;
  /** Phase 222 (D-24): non-null exactly while the first-reveal walkthrough is
   * active for this verdict — see `resolveWalkthroughStep`. */
  activeWalkthroughStep: WalkthroughStep | null;
  onWalkthroughNext: () => void;
  /** Phase 222 UAT round 3: whether the action row carries Solution (the
   * board was departed — a free-play move or a stepped line). */
  hasSolution: boolean;
  /** Phase 222 UAT round 3: a warm-up first session gets one extra intro step. */
  isWarmup: boolean;
  /** Plan 06 UAT: whether the action row carries Analyze (own-game puzzle,
   * `game_id` set) — walkthrough step 3 must not describe a missing button. */
  hasAnalyze: boolean;
  /** D-03 (Phase 224): threaded into `introCopy`/`introStepCount` (the
   * welcome/warm-up intro copy) and `returnPhrase` (the verdict's warm-up
   * return tail) via `renderVerdictBubbleBody`. */
  audience: TrainCopyAudience;
}

/**
 * Phase 222 (D-07/D-09/D-22/D-23): resolves the single chat-row bubble's
 * copy and action row for every state — `prompt`, `move`, `grading`,
 * `intro`, `drop-nudge`, `verdict`. Kept as a flat, non-exported module-level
 * helper (mirrors `resolveTrainEvalBarReading` above) so growing the bubble
 * state machine adds a guard clause HERE, never a branch inside
 * `TrainSolveScreen` itself — the mechanism that keeps the component's own
 * cyclomatic complexity from rising as more states are added.
 */
function renderTrainBotBubbleBody(
  bubbleState: TrainBubbleState,
  deps: BubbleBodyDeps,
): { copy: ReactElement; actions?: ReactElement } | null {
  if (bubbleState.kind === 'prompt') {
    if (deps.suppressPrompt) return null;
    return {
      copy: <p data-testid="train-guess-prompt">{promptCopy(deps.sideToMove)}</p>,
      actions: guessButtons(deps.onGuess),
    };
  }
  if (bubbleState.kind === 'move') {
    return {
      copy: <p data-testid="train-move-prompt">{movePromptCopy(deps.sideToMove, deps.guess)}</p>,
    };
  }
  if (bubbleState.kind === 'grading') {
    return {
      copy: (
        <span className="flex items-center gap-2" data-testid="train-grading-indicator">
          <Loader2 className="size-4 animate-spin text-muted-foreground" aria-hidden="true" />
          {GRADING_COPY}
        </span>
      ),
    };
  }
  if (bubbleState.kind === 'intro') {
    return {
      copy: <p>{introCopy(bubbleState.step, deps.sideToMove, deps.isWarmup, deps.audience).copy}</p>,
      actions: (
        <TrainBotStepper
          stepCount={introStepCount(deps.isWarmup, deps.audience)}
          step={bubbleState.step}
          onNext={deps.onIntroNext}
          lastControl={guessButtons(deps.onIntroGuess)}
        >
          {null}
        </TrainBotStepper>
      ),
    };
  }
  if (bubbleState.kind === 'drop-nudge') {
    return {
      copy: <p data-testid="train-guess-prompt">{dropNudgeCopy(deps.sideToMove)}</p>,
      actions: guessButtons(deps.onGuess),
    };
  }
  if (bubbleState.kind === 'verdict' && deps.verdict !== null && deps.verdictOpening !== null) {
    if (deps.activeWalkthroughStep !== null) {
      return renderWalkthroughBubbleBody(
        deps.activeWalkthroughStep,
        deps.onWalkthroughNext,
        deps.verdictActions,
        deps.hasAnalyze,
        deps.hasSolution,
      );
    }
    return renderVerdictBubbleBody(
      deps.verdict,
      deps.verdictOpening,
      deps.sessionDate,
      deps.expiresOn,
      deps.isWarmup,
      deps.audience,
      deps.verdictActions,
    );
  }
  return null;
}

/**
 * Phase 222 (D-02/D-03/D-05): the persona that should speak the current
 * bubble state — Hilda/Tank during the intro stepper (fixed hosts, never
 * randomly cast), the outcome-matched stern/friendly bot during the verdict,
 * else the regular-session random smart host. Module-level so this dispatch
 * never raises `TrainSolveScreen`'s own pinned complexity (FINDING B).
 */
function resolveBubblePersona(
  bubbleState: TrainBubbleState,
  sideToMove: 'white' | 'black',
  regularBot: Persona,
  verdictBot: Persona | null,
  activeWalkthroughStep: WalkthroughStep | null,
  isWarmup: boolean,
  audience: TrainCopyAudience,
): Persona {
  if (bubbleState.kind === 'intro') {
    return (
      personaForId(introCopy(bubbleState.step, sideToMove, isWarmup, audience).personaId) ?? regularBot
    );
  }
  // Phase 222 (D-05/D-24): the first-reveal walkthrough is always taught by
  // Hilda, never the outcome-matched verdict bot.
  if (bubbleState.kind === 'verdict' && activeWalkthroughStep !== null) {
    return personaForId(HILDA_ID) ?? regularBot;
  }
  if (bubbleState.kind === 'verdict' && verdictBot !== null) return verdictBot;
  return regularBot;
}

export function TrainSolveScreen({
  puzzle,
  trainSession,
  gradingEngine,
  onNext,
  restoredSolve = null,
  hasGames,
  isGuest,
}: TrainSolveScreenProps): ReactElement {
  // D-03 (Phase 224): built once per render, threaded through unchanged —
  // no new branch is added HERE, the audience is only ever passed through.
  const audience: TrainCopyAudience = { hasGames, isGuest };
  // Suppress the mobile app header while a puzzle is on screen — the board
  // needs the vertical space (ProtectedLayout reads this flag; same pattern
  // as BotsGame).
  useMarkPlayActive();

  // Keep the phone awake while a puzzle or its reveal is on screen — both are
  // long reading states with no touch input, so the OS auto-lock timer would
  // otherwise fire mid-solve. Scoped to this component on purpose: the start
  // and score screens must NOT hold the lock (a user who walks away there
  // should get their normal auto-lock).
  useWakeLock();

  // Phase 222 (D-10): the reveal's mute toggle is retired — `/bots` is now
  // the app's only mute control (re-homing recorded as a follow-up seed at
  // phase close). Reveal-line stepping still plays move sounds via the
  // shared `playSound`/mute preference; only the toggle affordance is gone.

  // Phase 222 (D-12): the shared settings cache — already warm app-wide for
  // every non-guest (RESEARCH Finding D: `useReminderResurrectRedirect`/
  // `useDevicePushResync` mount `useTrainSettings` from `App.tsx`), so this
  // costs no extra request. `stamp` posts the one-shot onboarding watermark.
  const { data: settings, isError: settingsFailed } = useTrainSettings();
  const { stamp } = useTrainOnboarding();

  // Initial state seeds from `restoredSolve` (190.1 UAT round 5) so a
  // restored reveal never flashes the guess prompt before the mount effect
  // runs; the per-puzzle effect below re-seeds identically on transitions.
  const [guess, setGuess] = useState<Guess | null>(restoredSolve?.guess ?? null);
  // Phase 222 (D-05): the first-session intro stepper's active step. Only
  // meaningful while `resolveIntroState` reports it active (first puzzle,
  // settings loaded, `intro_seen_at === null`) — otherwise ignored.
  const [introStep, setIntroStep] = useState<IntroStep>(0);
  // Phase 222 (D-08): bumped on every drop rejected for lack of a guess.
  // Fed to `TrainBotBubble` as its remount `key` so a REPEATED nudge replays
  // the pulse (RESEARCH Pitfall 3) — a class toggle alone cannot restart an
  // already-running CSS animation on a node that never unmounts.
  const [nudgeNonce, setNudgeNonce] = useState(0);
  const [boardFen, setBoardFen] = useState(puzzle.fen);
  const [moveApplied, setMoveApplied] = useState(restoredSolve !== null);
  const [isGrading, setIsGrading] = useState(false);
  const [gradingError, setGradingError] = useState(false);
  const [lastPlayedUci, setLastPlayedUci] = useState<string | null>(
    restoredSolve?.playedMoveUci ?? null,
  );
  // 190.1-03: the resolved GradeResult from the LAST gradeMove call for this
  // puzzle — threaded to TrainReveal so its steppable line boxes (YOUR MOVE /
  // BEST MOVE) render from the exact same engine output the verdict itself
  // was computed from, never a second derivation.
  const [gradeResult, setGradeResult] = useState<GradeResult | null>(
    restoredSolve?.gradeResult ?? null,
  );
  // 190.1-04 (D-02): the reveal query's resolved game-move UCI, reported up
  // from TrainReveal via onGameMoveUciChange — needed here (not lifted into
  // TrainReveal itself) so the board's arrows prop can include the thin white
  // game-move arrow alongside the best/played-move arrows.
  const [gameMoveUci, setGameMoveUci] = useState<string | null>(null);
  // 190.1 UAT: the reveal-time search's resolved game-move line (null while
  // pending/errored/coincident) — its eval derives the game move's quality
  // badge on the board overlay.
  const [gameMoveLine, setGameMoveLine] = useState<TrainEngineLine | null>(null);
  // 190.1 UAT: the reveal panel's current line-stepping state — non-null while
  // a line is stepped away from its start. While stepping, the solution
  // overlay (arrows + quality badges) is cleared, the reported last move gets
  // a quality-colored square highlight, and the line's next move renders as a
  // blue engine arrow.
  const [lineStep, setLineStep] = useState<TrainRevealStep | null>(null);
  // Phase 200 (EXPLORE-01/02), reworked per Phase 200 UAT: the free-play
  // branching move tree — reachable only once the verdict has landed
  // (handlePieceDrop's post-verdict branch below). Seeded from the
  // stepped-line prefix when there is one (EXPLORE-02), or an empty prefix
  // from the pristine reveal. Torn down by handleShowSolution (EXPLORE-04) and
  // the per-puzzle reset effect (EXPLORE-05).
  //
  // The hook owns its OWN Stockfish Worker (EXPLORE-05: a second, independent
  // engine instance — never a repurposed grading engine) and grades every
  // freely played move from it. See useTrainFreePlay's docstring.
  //
  // 190.1 UAT round 5: a restored reveal's verdict comes from the cache (the
  // solve mutation belongs to the unmounted prior page visit) — but a LIVE
  // solve response always wins, and the restored fallback disappears the
  // moment the puzzle transitions (restoredSolve nulls together with it).
  //
  // Bug fix (FLAWCHESS-64): the live verdict counts only when it belongs to
  // the puzzle currently on screen. `resetSolve()` runs in the puzzle-keyed
  // effect below, which React fires AFTER the child TrainReveal's own effects,
  // so a bare `lastSolveResponse` left one commit where the next puzzle was
  // already rendered while the previous puzzle's verdict was still set —
  // TrainReveal's query key flipped to the new position and fetched the reveal
  // for a puzzle that had never been attempted (a guaranteed 409). Pairing the
  // verdict with `lastSolvedPosition` closes that window at the source, and
  // also stops the reveal panel from rendering the old solution for one frame.
  //
  // Phase 211 (Plan 03): derived HERE, above the free-play seed memo, so the
  // hoisted `vettedMoves` memo below can feed BOTH the reveal overlay and the
  // free-play seed from one place.
  const liveVerdict =
    trainSession.lastSolvedPosition === puzzle.position ? trainSession.lastSolveResponse : null;
  const verdict = liveVerdict ?? restoredSolve?.verdict ?? null;

  // Phase 211 (D-01/D-06): the server's certified "also fine" set — the
  // single source BOTH consumers read: the reveal overlay's green alternative
  // arrows AND the free-play seed's root-ply key (do not inline the default
  // at either call site). The `?? []` here is the ONE nullish default for
  // the served list on this whole screen: a `trainRevealCache` entry written
  // by a pre-211 bundle restores a verdict with no `vetted_moves` key at
  // runtime even though the compiler sees the optional field — keeping
  // exactly one default is what makes the D-10 mutation test meaningful.
  const vettedMoves = useMemo<VettedMove[]>(() => verdict?.vetted_moves ?? [], [verdict]);

  // `seedEval` hands it the grading engine's verdict for the puzzle position,
  // so the FIRST free move is graded without waiting for the free-play engine
  // to re-search a position the solve loop already searched. Phase 211
  // (D-06): the seed also carries the SAME served vetted list the reveal
  // overlay draws (the hoisted `vettedMoves` memo above — the single
  // stale-cache default site), so the free-play ROOT ply and the "Also fine"
  // row can never read different keys.
  const freePlaySeedEval = useMemo(
    () =>
      gradeResult === null
        ? null
        : {
            cp: gradeResult.bestLine.evalCp,
            mate: gradeResult.bestLine.evalMate,
            bestUci: gradeResult.bestMoveUci,
            vettedMoves,
          },
    [gradeResult, vettedMoves],
  );
  const freePlay = useTrainFreePlay({ startFen: puzzle.fen, seedEval: freePlaySeedEval });
  // Phase 200 (LEGEND-02/D-09): the single active legend spotlight entry —
  // exactly one line box's move is spotlit at a time, or none. Set by
  // TrainReveal's hover/focus/tap handlers via onSpotlightChange, filtered
  // into the board overlay below via applyTrainSpotlight.
  const [spotlight, setSpotlight] = useState<{ key: string; ucis: string[] } | null>(null);
  // 190.1 UAT round 3: the Solution/Analyze/Next row lives HERE, below the
  // board (each button a third of the board's width). Solution bumps this
  // nonce; the reveal's steppers key their reset on it, snapping the board
  // back to the puzzle position with the full solution overlay.
  const [solutionNonce, setSolutionNonce] = useState(0);
  // 190.1 UAT round 7: the points earned by a LIVE solve, shown as a short
  // "Points: +N" pop animation over the board as the reveal opens. Set by the
  // result-sound effect below (so it can never fire for a restored reveal),
  // cleared on puzzle transition. The element's CSS animation ends at
  // opacity 0 with fill-mode forwards, so no unmount timer is needed.
  const [pointsFlash, setPointsFlash] = useState<number | null>(null);
  // Phase 200 UAT round 5: board orientation. Defaults to the solver's own
  // color (a black-to-move puzzle starts flipped, as it always has) and is
  // toggled by the free-play board-controls strip. Reset on every puzzle
  // transition by the same effect that resets the rest of the solve state —
  // orientation is a per-position affordance, not a session preference.
  const [flipped, setFlipped] = useState(puzzle.side_to_move === 'black');
  const handleFlipBoard = useCallback(() => setFlipped((prev) => !prev), []);
  // Quick 260809-g0n: on phones, while free-move mode is active this replaces
  // the main nav buttons in the fixed bottom bar (the /analysis board's
  // mobile-footer treatment) — see MobileBottomBar in App.tsx. The wiring
  // mirrors TrainExplorationPanel's own in-card control strip exactly (same
  // canReset-mirrors-canGoBack semantic) so the two surfaces can never
  // disagree; the in-card strip itself covers `sm` and up.
  const mobileBoardControls = useMemo(
    () =>
      freePlay.isExploring
        ? {
            onBack: freePlay.goBack,
            onForward: freePlay.goForward,
            onReset: freePlay.goToRoot,
            onFlip: handleFlipBoard,
            canGoBack: freePlay.canGoBack,
            canGoForward: freePlay.canGoForward,
            canReset: freePlay.canGoBack,
          }
        : null,
    [
      freePlay.isExploring,
      freePlay.goBack,
      freePlay.goForward,
      freePlay.goToRoot,
      freePlay.canGoBack,
      freePlay.canGoForward,
      handleFlipBoard,
    ],
  );
  usePublishMobileBoardControls(mobileBoardControls);
  // 191 UAT: the board column shrinks to whatever vertical room the viewport
  // actually leaves (see useFitBoardToViewport) — measured, not a hard-coded
  // chrome estimate, so the button row below the board always keeps its
  // gutter no matter what else the page renders above the column.
  const columnRef = useRef<HTMLDivElement>(null);
  const boardRef = useRef<HTMLDivElement>(null);
  // Phase 222 UAT round 3: the solve screen root and the phone-pinned
  // progress+board block, for the walkthrough's scroll-to-cards effect.
  const screenRef = useRef<HTMLDivElement>(null);
  const pinnedRef = useRef<HTMLDivElement>(null);
  const isDesktop = useIsDesktop();

  // Phase 200 (D-11) + UAT round 9: the board has left the pristine reveal —
  // a line is stepped, or exploration is running. Gates the Solution button's
  // visibility, and tells the reveal panel that a card click must first bring
  // the board back before spotlighting itself.
  const isBoardDeparted = lineStep !== null || freePlay.isExploring;

  // Phase 222 (D-24): the first-reveal walkthrough — step state, Next, the
  // interaction auto-advances, the phone scroll-to-cards effect and the
  // leave-stamp all live in the hook; this component only reads `activeStep`
  // / `target` (the bubble ring, the board-row ring, the `<TrainReveal>`
  // lines ring) and threads the handlers through.
  const walkthrough = useTrainWalkthrough({
    settings,
    hasVerdict: verdict !== null,
    hasAnalyze: puzzle.game_id !== null,
    hasSolution: isBoardDeparted,
    isDesktop,
    screenRef,
    pinnedRef,
    setSpotlight,
    setLineStep,
    stamp,
  });
  const walkthroughTarget = walkthrough.target;
  const boardMaxWidthPx = useFitBoardToViewport({
    columnRef,
    boardRef,
    maxPx: TRAIN_BOARD_MAX_WIDTH_PX,
    minPx: TRAIN_BOARD_MIN_WIDTH_PX,
    gutterPx: TRAIN_BOARD_BOTTOM_GUTTER_PX,
    enabled: isDesktop,
  });
  const [engineTimedOut, setEngineTimedOut] = useState(false);
  // Bumped by a manual engine retry so the readiness-timeout effect below
  // re-arms its window even when `isReady` itself hasn't changed value yet.
  const [engineRetryNonce, setEngineRetryNonce] = useState(0);

  // Destructured so their (stable, useCallback([])) identities can be listed
  // in the effect's deps array without the effect re-firing on gradingEngine's
  // own per-render object identity.
  const { startGrading, abortGrading, gradeMove, restartEngine, isReady, hasError } = gradingEngine;

  const engineFailed = hasError || engineTimedOut;

  // T-190-13: a bounded readiness window — the Worker either reports ready
  // in time or this fires. Resets (clears) once isReady flips true, and
  // re-arms on a manual retry via `engineRetryNonce`.
  useEffect(() => {
    if (isReady) {
      setEngineTimedOut(false);
      return;
    }
    const timer = setTimeout(() => setEngineTimedOut(true), TRAIN_ENGINE_READY_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [isReady, engineRetryNonce]);

  // Fires the "find the best move" search once per puzzle at mount and resets
  // the per-puzzle UI state. abortGrading on cleanup covers a puzzle
  // transition mid-search (190-RESEARCH.md Pitfall 3).
  //
  // Bug fix (Phase 190-01 checkpoint): this effect used to be guarded by a
  // `startedForFenRef.current === puzzle.fen` ref-check meant to suppress a
  // duplicate `startGrading` dispatch on React StrictMode's dev-only
  // mount->cleanup->mount double-invoke. That guard was itself the bug: the
  // interim cleanup's `abortGrading()` bumps the engine's generation and
  // stops the in-flight search, but the ref then suppressed the SECOND
  // mount's `startGrading` call (same puzzle.fen) entirely — leaving no
  // search running for the puzzle's now-current generation, so
  // `gradeMove`'s internal `await bestSearchReadyRef.current` hung forever
  // (observed in manual browser UAT as "Checking your move…" never
  // resolving). `startGrading`/`abortGrading` are already idempotent and
  // cancellation-safe via the hook's generation counter — calling
  // `startGrading` on every effect invocation (as below) is correct in both
  // StrictMode dev (harmless extra stop+go pair) and production (fires
  // exactly once per real puzzle.fen change).
  useEffect(() => {
    // 190.1 UAT round 5: a restored puzzle (Analyze -> back) seeds its cached
    // solved state instead of the fresh-puzzle reset, and skips the mount
    // grading search entirely — no move will ever be graded for it. The
    // Next-press transition to a fresh puzzle re-fires this effect with
    // restoredSolve already null (both change on the same render).
    setGuess(restoredSolve?.guess ?? null);
    setBoardFen(puzzle.fen);
    setMoveApplied(restoredSolve !== null);
    setIsGrading(false);
    setGradingError(false);
    setLastPlayedUci(restoredSolve?.playedMoveUci ?? null);
    setGradeResult(restoredSolve?.gradeResult ?? null);
    // Bug fix: `gameMoveUci` is deliberately NOT reset here. TrainReveal owns
    // it (its onGameMoveUciChange effect reports the reveal query's UCI and
    // nulls it on cleanup/puzzle transition). When the reveal query resolves
    // synchronously from the TanStack cache (restored reveal via Analyze ->
    // back, staleTime Infinity), TrainReveal's child effect fired FIRST with
    // the UCI and this parent effect then overwrote it with null in the same
    // commit, so the white played-in-game arrow was missing while the legend
    // card still rendered. `gameMoveLine` is safe to reset: it only ever
    // arrives asynchronously, after this effect has run.
    setGameMoveLine(null);
    setLineStep(null);
    setSpotlight(null);
    setPointsFlash(null);
    setFlipped(puzzle.side_to_move === 'black');
    // Phase 222 (D-12): an abandoned intro stepper replays next time — reset
    // the step index on every puzzle transition, not just the first.
    // `nudgeNonce` resets too, so a drop rejected on the PREVIOUS puzzle
    // never leaves the new one's bubble showing a stale nudge pulse.
    setIntroStep(0);
    walkthrough.reset();
    setNudgeNonce(0);
    // Phase 200 (EXPLORE-05): a puzzle transition tears down any active
    // exploration session (and, via the hook's `enabled: isExploring` engine
    // in task 3, its Worker) — the next puzzle always starts in the pristine
    // reveal state, never mid-sideline.
    freePlay.reset();
    trainSession.resetSolve();
    if (restoredSolve === null) startGrading(puzzle.fen);
    return () => {
      abortGrading();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- trainSession.resetSolve is a stable useCallback from the hook (it closes over the mutation's own `.reset`, bound once per observer — see useTrainSession's stability comment; it was NOT stable before that fix, so this line's original claim was aspirational). Including the whole trainSession object would re-fire this effect every render. restoredSolve only ever changes together with puzzle.fen (Train.tsx pairs them), so puzzle.fen already covers it — as does puzzle.side_to_move, which is a function of the FEN. freePlay.reset's identity is keyed on puzzle.fen alone, so it changes with (and only with) that dep.
  }, [puzzle.fen, startGrading, abortGrading, freePlay.reset, walkthrough.reset]);

  async function gradeAndSolve(playedGuess: Guess, playedUci: string): Promise<void> {
    setIsGrading(true);
    setGradingError(false);
    let grade: GradeResult;
    try {
      grade = await gradeMove(puzzle.fen, playedUci);
    } catch {
      // A grading timeout (TRAIN_GRADING_TIMEOUT_MS) or any other grading
      // failure — never a silent, indefinite "Checking your move…" spinner
      // (CLAUDE.md: every mutation path needs an isError branch). Retry
      // re-runs the SAME played move through the grading engine from
      // scratch, since no verdict was ever computed.
      setGradingError(true);
      setIsGrading(false);
      return;
    }
    setGradeResult(grade);
    try {
      await trainSession.solvePuzzle({
        position: puzzle.position,
        guess: playedGuess,
        played_move: playedUci,
        move_quality: grade.moveTier,
      });
      // correct_guess is read ONLY from the server response (POOL-10) — never
      // recomputed client-side. The verdict itself renders from
      // trainSession.lastSolveResponse below, not a local copy.
    } catch {
      // T-190-12: the solve-POST failure surfaces via trainSession.isSolveError
      // below (locked copy + Retry, which calls trainSession.retrySolve() —
      // re-submitting this SAME payload, never re-grading). Do not swallow;
      // do not add a second Sentry error-report call here — the global
      // mutation-cache handler in queryClient.ts already reports it.
    } finally {
      setIsGrading(false);
    }
  }

  function retryGrading(): void {
    if (guess === null || lastPlayedUci === null) return;
    void gradeAndSolve(guess, lastPlayedUci);
  }

  // Bug fix (WR-01): `handleRetryEngine` used to call `startGrading`
  // synchronously right here, but `restartEngine()` only bumps state — the
  // actual Worker teardown/recreate (and `hasErrorRef` reset) happens in the
  // Worker-lifecycle effect on the NEXT commit, which React defers. Calling
  // `startGrading` inline raced the STALE Worker/refs: on an onerror-
  // triggered retry it permanently rejected this puzzle's grading (nothing
  // ever re-issued the search once the new Worker became ready), and on a
  // readiness-timeout-triggered retry it re-triggered the CR-01 not-ready
  // fabrication. Deferred below to the effect keyed on `isReady` actually
  // flipping true after a retry, instead of firing inline.
  const handleRetryEngine = useCallback(() => {
    restartEngine();
    setEngineTimedOut(false);
    setEngineRetryNonce((n) => n + 1);
  }, [restartEngine]);

  // Tracks the last `engineRetryNonce` for which `startGrading` has already
  // been re-dispatched, so this effect fires exactly once per manual retry
  // (not on every render once `isReady` is already true).
  const lastStartedRetryNonceRef = useRef(0);
  useEffect(() => {
    if (!isReady) return;
    if (engineRetryNonce === 0) return; // no manual retry has happened yet
    if (lastStartedRetryNonceRef.current === engineRetryNonce) return;
    lastStartedRetryNonceRef.current = engineRetryNonce;
    startGrading(puzzle.fen);
  }, [isReady, engineRetryNonce, startGrading, puzzle.fen]);

  function handlePieceDrop(source: string, target: string): boolean {
    // D-05: board locked until the binary guess is committed.
    // Phase 222 (D-08): the drop is still rejected — react-chessboard reads
    // `true` as "the move was accepted" and would leave the piece on the
    // target square — but never SILENTLY: bumping the nonce swaps the
    // bubble's copy to the "Decide first, then move" line and (via the
    // bubble's remount key) replays the pulse even on a repeated drop.
    if (guess === null) {
      setNudgeNonce((n) => n + 1);
      return false;
    }
    // SOLV-02: exactly one attempt per puzzle.
    if (moveApplied) {
      // Phase 200 (EXPLORE-01/02/D-12): once the verdict has landed, a
      // further drop starts (or extends) a free-play sideline on this SAME
      // board — no mode toggle, no second board, no second grading attempt.
      // Guardrail (Pitfall 3, extended): this branch sits STRICTLY after the
      // guess and moveApplied guards above, which are what hold SOLV-02 at
      // exactly one graded attempt — do not reorder them, and do not widen
      // the graded path (below) to read displayFen.
      if (verdict === null) return false; // solve/grading still pending
      // Already in free play: the move tree validates (and forks) the drop
      // itself, exactly as the analysis board does.
      if (freePlay.isExploring) {
        const played = freePlay.playMove(source, target);
        if (played) {
          setLineStep(null);
          setSpotlight(null);
        }
        return played;
      }
      // Opening move of a free-play session: validate against displayFen —
      // D-12: the LIVE position on the board (a stepped-into line position, or
      // the puzzle position), never the frozen boardFen — to derive the UCI
      // the tree is seeded with.
      const exploreUci = uciFromDrop(displayFen, source, target);
      if (exploreUci === null) return false;
      freePlay.start(lineStep?.prefixUci ?? [], exploreUci);
      setLineStep(null);
      setSpotlight(null);
      return true;
    }

    const chess = new Chess(boardFen);
    let move: Move;
    try {
      move = chess.move({ from: source, to: target, promotion: 'q' }); // auto-queen
    } catch {
      return false;
    }
    if (!move) return false;

    setMoveApplied(true);
    setBoardFen(chess.fen());
    const playedUci = `${move.from}${move.to}${move.promotion ?? ''}`;
    setLastPlayedUci(playedUci);
    void gradeAndSolve(guess, playedUci);
    return true;
  }

  // SOLV-04/D-13: "i of N" uses the session's FROZEN puzzle_count, never
  // puzzles.length (which can legitimately shrink after a lazy eviction —
  // Phase 189's own documented behavior).
  //
  // Bug fix (190-06 UAT): `currentIndex` is 0-relative to `trainSession.puzzles`
  // (see useTrainSession.ts's module docstring — that array is the FULL
  // session on a fresh load, but only the REMAINING puzzles on a resume), so
  // it alone undercounts a resumed session's true position. The session's
  // own `solved_count`, frozen at load time, is the number of puzzles solved
  // BEFORE this frontend session started; adding it back in recovers the
  // real 1-based position across both the fresh (solved_count === 0) and
  // resume (solved_count > 0) cases.
  const totalPuzzles = trainSession.session?.puzzle_count ?? trainSession.puzzles.length;
  const solvedBeforeThisLoad = trainSession.session?.solved_count ?? 0;
  // 190.1 UAT round 5: a restored reveal shows an ALREADY-solved puzzle — the
  // most recently solved one, so its 1-based position is exactly the resumed
  // session's solved_count (the general formula below would overshoot by one,
  // since it targets the next UNSOLVED puzzle).
  const currentPosition1Based =
    restoredSolve !== null
      ? Math.max(1, solvedBeforeThisLoad)
      : solvedBeforeThisLoad + (trainSession.currentIndex ?? 0) + 1;
  const progressFraction =
    totalPuzzles > 0 ? Math.min(1, Math.max(0, (currentPosition1Based - 1) / totalPuzzles)) : 0;

  // SOLV-02: the opponent's (or the user's own) last move into this position —
  // arrival data only, never the answer. A null arriving move (ply 0) renders
  // no highlight, never a fabricated square.
  const lastMove = puzzle.last_move_uci
    ? { from: puzzle.last_move_uci.slice(0, 2), to: puzzle.last_move_uci.slice(2, 4) }
    : null;

  // Phase 200 (D-12): the live board position — while exploring, the
  // exploration hook's replayed FEN is the single source of truth for both
  // the RENDERED board and handlePieceDrop's exploration-branch move
  // validation above. Deliberately never `boardFen`: every existing
  // `setBoardFen` call site is untouched by this plan, so `boardFen` stays
  // frozen at the pristine/stepped position for the whole exploration
  // session — validating a sideline drop against it would silently re-impose
  // a one-color restriction the moment the sideline's side to move flips
  // (see handlePieceDrop's own comment for the full mechanism).
  const displayFen = freePlay.isExploring ? (freePlay.fen ?? boardFen) : boardFen;

  // T-190-12: the verdict/Next/solve-error row only appears once the local
  // grade+solve pipeline has settled (moveApplied && !isGrading && no
  // grading-level error) — it then distinguishes success (lastSolveResponse
  // set) from a solve-POST failure (isSolveError) via the SAME row. The
  // `verdict` itself is derived above the free-play seed memo (Phase 211
  // moved it up so the seed can carry the served vetted list).
  const showResultRow =
    moveApplied && !isGrading && !gradingError && (verdict !== null || trainSession.isSolveError);

  // Quick 260803-iv6 (Task 1, T-iv6-01): the SAME gate the reveal panel
  // itself uses — a live engine evaluation shown before the reveal opens
  // would hand the user the answer to the "one critical move vs several fine
  // moves" question the puzzle is asking, so the bar cannot appear any
  // earlier than `showResultRow` does.
  const showEvalBar = showResultRow;
  const evalBarFen = showEvalBar && !freePlay.isExploring ? displayFen : null;
  // Deliberately disabled while exploring: `useTrainFreePlay` already owns a
  // FEN-driven Stockfish worker for the explored position (see its own
  // docstring), so this gate keeps exactly one such worker alive at a time
  // for the shown position (the session-scoped grading worker is a third,
  // but is idle once the verdict has landed).
  const evalBarEngine = useStockfishEngine({ fen: evalBarFen, enabled: evalBarFen !== null });
  const freePlayTopLine = freePlay.pvLines[0] ?? null;
  const evalBarReading = resolveTrainEvalBarReading(
    displayFen,
    freePlay.isExploring,
    freePlayTopLine,
    evalBarEngine,
  );

  // 190.1 UAT: the played move's classified quality — derived once here and
  // shared by the board overlay below AND the reveal's line-box header icons
  // (threaded down as a prop), so the two surfaces can never drift.
  //
  // Phase 211 (D-03/D-07): when the verdict carries the server's graded-ES
  // pair (a key-move override), the badge derives from THOSE numbers through
  // the same classifier — before this phase the board badge and the score
  // chip were always equal only because the server echoed the client's own
  // assertion; now the server can legitimately disagree with the client
  // engine's search, and the display must follow the server. Off-key moves
  // (graded_es_* null/absent) keep the client-engine derivation.
  const playedMoveQuality = useMemo<TrainMoveQuality | null>(() => {
    if (gradeResult === null || lastPlayedUci === null) return null;
    const isBest = lastPlayedUci === gradeResult.bestMoveUci;
    if (verdict?.graded_es_before != null && verdict?.graded_es_after != null) {
      return classifyTrainMoveQuality(verdict.graded_es_before, verdict.graded_es_after, isBest);
    }
    return classifyTrainMoveQuality(gradeResult.esBefore, gradeResult.esAfter, isBest);
  }, [gradeResult, lastPlayedUci, verdict]);

  // The game move's quality: derived from the coinciding best/played move
  // when no reveal-time search ran, else from the searched line's eval via
  // the SAME expected-score pipeline the verdict uses.
  const gameMoveQuality = useMemo<TrainMoveQuality | null>(() => {
    if (gameMoveUci === null || gradeResult === null) return null;
    if (gameMoveUci === gradeResult.bestMoveUci) return 'best';
    if (gameMoveUci === lastPlayedUci) return playedMoveQuality;
    if (gameMoveLine === null) return null;
    const mover = sideToMoveFromFen(puzzle.fen);
    const esGame = evalToExpectedScore(gameMoveLine.evalCp, gameMoveLine.evalMate, mover);
    return classifyTrainMoveQuality(gradeResult.esBefore, esGame, false);
  }, [gameMoveUci, gradeResult, lastPlayedUci, playedMoveQuality, gameMoveLine, puzzle.fen]);

  // 190.1-04 (D-02, reworked per 190.1 UAT): reveal-board overlay — the blue
  // best-move arrow, green alternative-good-move arrows capped by puzzle
  // type, the played-move arrow colored by its own quality, the thin white
  // game-move arrow, plus a move-quality corner badge on every arrow's
  // target square. Empty until the verdict has actually landed.
  const revealOverlay = useMemo(() => {
    const playedMove: TrainOverlayMove | null =
      gradeResult !== null && lastPlayedUci !== null && playedMoveQuality !== null
        ? { uci: lastPlayedUci, quality: playedMoveQuality }
        : null;
    return buildTrainRevealOverlay(
      verdict?.puzzle_type ?? 'sharp',
      // Phase 211 (D-01): the server's certified vetted list — the client
      // engine no longer contributes alternatives to this overlay. The
      // hoisted `vettedMoves` memo above owns the stale-cache default.
      vettedMoves,
      gradeResult?.bestMoveUci ?? null,
      playedMove,
      gameMoveUci !== null ? { uci: gameMoveUci, quality: gameMoveQuality } : null,
      verdict !== null,
    );
  }, [verdict, vettedMoves, gradeResult, lastPlayedUci, playedMoveQuality, gameMoveUci, gameMoveQuality]);

  /**
   * 260902-qf7 (reverses Phase 200 UAT): the moves the PRISTINE (un-spotlit)
   * reveal board draws — "Your move", "Best move", AND the played-in-game
   * move. A puzzle mined from the user's own game exists to contrast their
   * guess against what they actually played there, so that contrast must not
   * be hidden behind a hover/tap; only the server-vetted "Also fine"
   * alternatives remain hover/tap-only, surfacing (alone) while their own
   * legend card is spotlit and otherwise staying off the board.
   *
   * Expressed as a DEFAULT active set for `applyTrainSpotlight` rather than a
   * second drawing rule, so the un-spotlit board and a spotlit one go through
   * exactly the same filter. A verdict cannot land without a `gradeResult` and
   * a played move (both live and restored paths set them together), so this is
   * non-empty whenever the overlay itself is non-empty — the empty case would
   * hit `applyTrainSpotlight`'s no-op and simply show everything. `gameMoveUci`
   * is `null` for filler puzzles (and any puzzle not mined from a user's own
   * game), so `.filter` drops it there and the pristine set is unchanged.
   */
  const pristineOverlayUcis = useMemo(
    () =>
      [lastPlayedUci, gradeResult?.bestMoveUci ?? null, gameMoveUci].filter(
        (uci): uci is string => uci !== null,
      ),
    [lastPlayedUci, gradeResult, gameMoveUci],
  );

  // Phase 200 (LEGEND-02): the reveal overlay filtered down to the spotlit
  // legend entry's own arrow(s)/badge, or — with nothing spotlit — down to the
  // pristine your/best pair above.
  const spotlitOverlay = useMemo(
    () => applyTrainSpotlight(revealOverlay, spotlight?.ucis ?? pristineOverlayUcis),
    [revealOverlay, spotlight, pristineOverlayUcis],
  );

  // 190.1 UAT stepping mode: while a reveal line is stepped away from its
  // start, the solution overlay is cleared; the only marks are the stepped
  // move's quality-colored square highlight and a blue arrow for the line's
  // next move. Back at the start (lineStep === null), the full overlay
  // (spotlight-filtered, Pitfall 1: a stray hover while stepping must never
  // touch the step overlay's own blue next-move arrow) and the puzzle's own
  // arrival-move highlight return.
  // Phase 200 UAT round 5: while exploring, the single arrow is the free-play
  // engine's own top move for the shown position — the analysis board's blue
  // Stockfish pointer, in free play too. Memoized so a re-render that doesn't
  // change the best move hands `ChessBoard` the same array identity (the old
  // "no arrows while exploring" rule used a module constant for exactly that).
  const freePlayArrows = useMemo(
    () => buildTrainFreePlayArrows(freePlay.bestMoveUci),
    [freePlay.bestMoveUci],
  );
  const boardArrows = freePlay.isExploring
    ? freePlayArrows
    : lineStep !== null
      ? buildTrainStepArrows(lineStep.nextMoveUci)
      : spotlitOverlay.arrows;
  // 190.1 UAT round 4: while stepping, the line's FIRST move keeps its
  // quality icon badge on the moved-to square (deeper steps show none).
  // Phase 200 UAT: while exploring, the badge is the FREELY PLAYED move's own
  // live grade (useTrainFreePlay) — the original EXPLORE-03 rule of "no badges
  // at all" was reversed, since grading the sideline is the point.
  const boardMarkers = freePlay.isExploring
    ? freePlay.boardMarkers
    : lineStep !== null
      ? buildTrainStepMarkers(lineStep.lastMoveUci, lineStep.quality, lineStep.isFirstMove)
      : spotlitOverlay.markers;
  const boardLastMove = freePlay.isExploring
    ? freePlay.lastMove
    : lineStep !== null
      ? { from: lineStep.lastMoveUci.slice(0, 2), to: lineStep.lastMoveUci.slice(2, 4) }
      : lastMove;
  // Phase 200 UAT: the free-play last-move highlight is quality-colored too
  // (undefined while the move is still ungraded — the board then falls back to
  // its ordinary highlight rather than flashing a wrong color).
  const boardLastMoveColor = freePlay.isExploring
    ? freePlay.lastMoveColor
    : lineStep !== null && lineStep.quality !== null
      ? TRAIN_STEP_HIGHLIGHT[lineStep.quality]
      : undefined;

  // 190.1 UAT rounds 6+7 / SEED-119: the reveal plays a per-score result
  // sound AND pops the "Points: +N" flash over the board the moment a LIVE
  // solve response lands — never for a restored reveal (its solve happened
  // on a prior page visit). The full per-puzzle max (3, guess + a good move)
  // plays FullScore; any lesser positive score (e.g. guess-only,
  // or guess plus an inaccuracy) plays PartialScore; 0 points plays Defeat. The
  // ref keeps StrictMode's dev-only double effect invocation (and any later
  // re-render with the same response object) from playing it twice;
  // playSound itself honors the shared mute preference.
  //
  // Quick 260814-b: the full-score branch now plays `score-full` (its own
  // clip), NOT `game-win`. One solved puzzle and a whole green session used to
  // sound identical, which flattened the session-end payoff; WinChime is now
  // reserved for the session verdict (TrainScoreScreen) and bot-game wins.
  //
  // Bug fix (Phase 200 UAT round 7): the ref is seeded with whatever verdict
  // the solve mutation ALREADY holds at mount, not with null. The solve
  // mutation lives on `useTrainSession` in the page above, which outlives this
  // screen — so a remount (dev-clock time travel drops back to the landing and
  // starts a NEW session, and Train.tsx's `returnToLanding` unmounts/remounts
  // this component) used to see the PREVIOUS session's last verdict as
  // "unsounded" and replayed its result sound (and the points flash) over the
  // first puzzle of the fresh session. A mount-time response is by definition
  // not a live landing: only a response that arrives while this screen is
  // mounted may sound.
  const liveSolveResponse = trainSession.lastSolveResponse;
  const soundedSolveRef = useRef<SolveResponse | null>(liveSolveResponse);
  useEffect(() => {
    if (liveSolveResponse === null || soundedSolveRef.current === liveSolveResponse) return;
    soundedSolveRef.current = liveSolveResponse;
    const points = scorePuzzle(liveSolveResponse.correct_guess, liveSolveResponse.move_quality);
    playSound(
      points === TRAIN_POINTS_PER_PUZZLE ? 'score-full' : points > 0 ? 'score-partial' : 'game-loss',
    );
    setPointsFlash(points);
  }, [liveSolveResponse]);

  // Phase 200 UAT round 3: stepping a line back to its START position restores
  // the pristine solution board, and that board must show the FULL solution —
  // both the Your-move and the Best-move arrow. Without this, the card the user
  // stepped inside is still spotlit (desktop: the pointer never left it while
  // clicking prev; mobile: the tap that opened the line is still active), so
  // the restored "solution" showed that one card's move alone. Only a real
  // non-null -> null transition reaches this (React bails out on an unchanged
  // null), so a stepper's own mount report can never clear a live spotlight.
  //
  // UAT round 9 carve-out: a CARD CLICK also ends the stepped line (it snaps
  // the board back to the solution position), but there the whole point is to
  // spotlight the clicked card — so `returnToSolution` arms this ref and the
  // clear is skipped exactly once. A ref rather than extra state: the flag must
  // be read in the very effect run this transition triggers, and re-rendering
  // for it would be pointless.
  const keepSpotlightRef = useRef(false);
  useEffect(() => {
    if (lineStep !== null) return;
    if (keepSpotlightRef.current) {
      keepSpotlightRef.current = false;
      return;
    }
    setSpotlight(null);
  }, [lineStep]);

  // D-08: as the reveal opens (the solve POST has actually succeeded), the
  // board snaps back to the puzzle position and becomes the stage for
  // stepping the best/tactic line — the played move is reported in the
  // verdict text above, not left on the board.
  useEffect(() => {
    if (verdict !== null) {
      setBoardFen(puzzle.fen);
    }
  }, [verdict, puzzle.fen]);

  const handleNext = onNext ?? trainSession.advance;


  // SEED-119: the badge's color pair for the current pointsFlash tier,
  // falling back to the 0-point entry (never an unreadable bg/fg pair) when
  // pointsFlash holds a value outside the known 0-3 range. The `!` is safe:
  // key 0 is always present in TRAIN_POINTS_FLASH_COLORS by construction.
  const pointsFlashColors =
    pointsFlash !== null
      ? (TRAIN_POINTS_FLASH_COLORS[pointsFlash] ?? TRAIN_POINTS_FLASH_COLORS[0]!)
      : undefined;

  /**
   * Phase 200 UAT round 9: brings the board back to the pristine solution
   * position — every stepper reset (solutionNonce), the board FEN, no stepped
   * line, no exploration — WITHOUT touching the spotlight. Wired to a reveal
   * card click, which re-applies its OWN spotlight right after (and so arms
   * `keepSpotlightRef` above, since ending the stepped line would otherwise
   * clear it again on the next commit).
   */
  function returnToSolution(): void {
    if (lineStep !== null) keepSpotlightRef.current = true;
    setSolutionNonce((n) => n + 1);
    setBoardFen(puzzle.fen);
    setLineStep(null);
    // Phase 200 (EXPLORE-04): one press does both jobs — exit exploration AND
    // the existing stepper reset, so the board always snaps to the pristine
    // reveal in a single tap regardless of which departed state it was in.
    freePlay.reset();
    // Flipping is only offered while exploring, so leaving exploration also
    // restores the puzzle's initial orientation — otherwise the pristine
    // reveal comes back upside down after a flip.
    setFlipped(puzzle.side_to_move === 'black');
  }

  function handleShowSolution(): void {
    returnToSolution();
    // The Solution button restores the FULL overlay, so it drops the spotlight
    // too. Safe alongside the ref `returnToSolution` may have just armed: that
    // ref only suppresses the effect's own clear, never this explicit one.
    setSpotlight(null);
  }

  // 190.1 UAT round 5: leaving the reveal via Analyze caches the full
  // solution state, so the browser back button restores THIS solved reveal
  // instead of the start screen (a resumed session no longer contains the
  // solved puzzle, and the grade result lives only in this page's memory).
  function handleAnalyzeClick(): void {
    const sessionId = trainSession.session?.session_id;
    if (
      sessionId == null ||
      verdict === null ||
      guess === null ||
      lastPlayedUci === null ||
      gradeResult === null
    ) {
      return;
    }
    saveTrainRevealCache({
      sessionId,
      puzzle,
      verdict,
      verdictBotId: verdictBot?.id,
      guess,
      playedMoveUci: lastPlayedUci,
      gradeResult,
    });
  }

  // Phase 222 (D-02): a random smart bot hosts the regular-session guess
  // bubble, memoised per puzzle (`puzzle.position` — Math.random, not seeded,
  // not persisted; a reload may recast, which D-02 accepts). Hilda/Tank
  // (the fixed intro-stepper hosts) and the outcome-matched verdict bot are
  // resolved separately below.
  // eslint-disable-next-line react-hooks/exhaustive-deps -- `puzzle.position` is intentionally NOT read inside the callback: it exists purely to re-run `pickBot` (a fresh Math.random draw) on every puzzle transition, per D-02.
  const bot = useMemo(() => pickBot('smart'), [puzzle.position]);

  // Phase 222 (D-05): the session's FIRST puzzle only — later puzzles always
  // show the regular prompt even if `intro_seen_at` is somehow still null
  // (e.g. a stamp request still in flight when the user reaches puzzle 2).
  const isFirstPuzzle = currentPosition1Based === 1;
  const { activeIntroStep, suppressPrompt } = resolveIntroState(
    settings,
    settingsFailed,
    isFirstPuzzle,
    introStep,
  );

  // Phase 222 UAT round 3: a warm-up first session (games still being
  // analyzed) gets one extra intro step explaining that, right before the
  // closing guess step.
  const isWarmup = trainSession.session?.is_warmup ?? false;

  function handleIntroNext(): void {
    setIntroStep((step) => Math.min(step + 1, introStepCount(isWarmup, audience) - 1) as IntroStep);
  }

  // Phase 222 (D-12): fires the one-shot stamp alongside the existing guess
  // commit — guarded on `intro_seen_at` still being null (the plan's own
  // stated "ref OR settings-null" option; the server's first-write-wins
  // guard, plan 02, is the actual belt-and-braces layer for a same-render
  // double-click race). Nothing stamps on unmount — an abandoned stepper
  // replays next time (D-12).
  function handleIntroGuess(guessValue: Guess): void {
    if (settings?.intro_seen_at == null) {
      stamp('intro');
    }
    setGuess(guessValue);
  }

  // Phase 222 (D-03): points come from `scorePuzzle` — never re-derived —
  // and the verdict bot is memoised per VERDICT (not per points) so a
  // re-render never recasts mid-read.
  const verdictPoints = useMemo<0 | 1 | 2 | 3 | null>(() => {
    if (verdict === null) return null;
    return scorePuzzle(verdict.correct_guess, verdict.move_quality) as 0 | 1 | 2 | 3;
  }, [verdict]);
  // UAT round 4: a reveal restored after the Analyze round trip keeps the bot
  // that spoke the verdict before leaving (`verdictBotId` rides along in the
  // reveal cache) instead of recasting on remount.
  const verdictBot = useMemo<Persona | null>(() => {
    if (verdictPoints === null) return null;
    const restoredBot = personaForId(restoredSolve?.verdictBotId);
    if (restoredBot !== undefined) return restoredBot;
    return pickBot(verdictPoints <= 1 ? 'stern' : 'friendly');
    // eslint-disable-next-line react-hooks/exhaustive-deps -- recast exactly when `verdict` itself changes (D-03), not when `verdictPoints`/`restoredSolve` alone are read; both are fully determined by `verdict` (same memo dep above / nulled on the same puzzle transition), so this can never drift.
  }, [verdict]);
  // UAT round 4: the opener is a random draw, so it is resolved once per
  // verdict here rather than on every render inside the bubble body.
  const verdictOpening = useMemo<VerdictCopy | null>(() => {
    if (verdict === null || verdictPoints === null) return null;
    return verdictCopy(verdictPoints, verdict.correct_guess, verdict.move_quality);
  }, [verdict, verdictPoints]);

  function handleNextFromReveal(): void {
    walkthrough.leave();
    handleNext();
  }
  function handleAnalyzeFromReveal(): void {
    walkthrough.leave();
    handleAnalyzeClick();
  }

  // Phase 222 (D-10): the Solution/Analyze/Next row, now rendered INSIDE the
  // verdict bubble's actions slot rather than the below-board sibling.
  const verdictActions = (
    <VerdictActions
      isBoardDeparted={isBoardDeparted}
      gameId={puzzle.game_id}
      ply={puzzle.ply}
      onShowSolution={handleShowSolution}
      onAnalyzeClick={handleAnalyzeFromReveal}
      onNext={handleNextFromReveal}
    />
  );

  const bubbleState = resolveBubbleState({
    hasVerdict: verdict !== null,
    isGrading,
    guessMade: guess !== null,
    introStep: activeIntroStep,
    nudgeActive: nudgeNonce > 0,
  });
  const bubbleBody = renderTrainBotBubbleBody(bubbleState, {
    sideToMove: puzzle.side_to_move,
    guess,
    onGuess: setGuess,
    suppressPrompt,
    onIntroNext: handleIntroNext,
    onIntroGuess: handleIntroGuess,
    verdict,
    verdictOpening,
    sessionDate: trainSession.session?.session_date,
    expiresOn: trainSession.session?.expires_on,
    verdictActions,
    activeWalkthroughStep: walkthrough.activeStep,
    hasAnalyze: puzzle.game_id !== null,
    hasSolution: isBoardDeparted,
    isWarmup,
    onWalkthroughNext: walkthrough.next,
    audience,
  });
  const bubblePersona = resolveBubblePersona(
    bubbleState,
    puzzle.side_to_move,
    bot,
    verdictBot,
    walkthrough.activeStep,
    isWarmup,
    audience,
  );

  return (
    <div
      // The board column's fitted width, published as a custom property so the
      // MOBILE stack can cap itself with a class (`max-w-[var(...)]`) that
      // `lg:max-w-none` can still override — an inline `max-width` could not be
      // beaten by a breakpoint utility. Below `lg` this makes the reveal panel
      // exactly as wide as the board column, which the sticky pinning below
      // depends on: a wider reveal would scroll past the pinned column's
      // background and show two strips of moving cards flanking the board.
      style={{ '--train-col-max': `${boardMaxWidthPx}px` } as CSSProperties}
      ref={screenRef}
      className="mx-auto flex w-full max-w-[var(--train-col-max)] flex-col items-center gap-4 lg:mx-0 lg:max-w-none lg:flex-row lg:items-start lg:justify-center lg:gap-8"
      data-testid="train-solve-screen"
    >
      <div
        ref={columnRef}
        // Desktop: the left column (progress + board + bot bubble), measured
        // by `useFitBoardToViewport`. Below `lg` it is `display: contents` so
        // the pinned block below becomes a direct child of the page-long outer
        // container — a sticky element only sticks within its parent's box,
        // and this column ends at the bubble, which is exactly where the board
        // must stay pinned while the reveal beneath it is read (phase 222 UAT).
        className="max-lg:contents lg:flex lg:w-full lg:flex-col lg:items-center lg:gap-3"
        style={{ maxWidth: boardMaxWidthPx }}
      >
      <div
        // Mobile: the progress row + board pin to the top of the viewport so
        // the board never scrolls out of sight while the bot bubble and the
        // reveal panel are read beneath it — the reveal's arrows/spotlight are
        // meaningless when the board they annotate is off screen. Desktop
        // already sits the reveal in its own column, so the whole treatment is
        // `max-lg:`. The opaque background is what the scrolled-under content
        // passes behind. Phase 222 UAT: the bot bubble is deliberately OUTSIDE
        // this pinned block (it scrolls away behind the board) so the pinned
        // strip stays short on phones. UAT round 3 dropped the block's own
        // bottom padding: the outer container's gap alone now separates the
        // board from the bubble's avatar.
        ref={pinnedRef}
        className="flex w-full flex-col items-center gap-3 max-lg:sticky max-lg:top-0 max-lg:z-10 max-lg:bg-background"
        data-testid="train-pinned-board"
      >
      {/* Phase 222 UAT: one compact row — "n of m", the bar, "x / y pts". */}
      <div className="flex w-full items-center gap-3">
        <p className="shrink-0 text-sm font-semibold" data-testid="train-progress">
          {currentPosition1Based} of {totalPuzzles}
        </p>
        <div className="h-1.5 min-w-0 flex-1 rounded-full bg-muted" data-testid="train-progress-bar">
          <div
            className="h-1.5 rounded-full bg-brand-brown"
            style={{ width: `${progressFraction * 100}%` }}
          />
        </div>
        {/* SOLV-04/D-04: the running session score, right end of the progress
            row — only once at least one puzzle has actually been scored, so
            the first puzzle of a fresh session never shows "0 / 0 pts". */}
        {trainSession.sessionSolvedCount > 0 && (
          <p className="shrink-0 text-sm font-semibold" data-testid="train-session-score">
            {trainSession.sessionScore} / {trainSession.sessionSolvedCount * TRAIN_POINTS_PER_PUZZLE} pts
          </p>
        )}
      </div>
      <div
        ref={boardRef}
        className={cn(
          'flex w-full flex-row items-stretch gap-2',
          // Phase 222 UAT: the walkthrough's free-play step rings the board row.
          walkthroughTarget === 'board' && 'rounded-md ring-2 ring-brand-brown ring-offset-4 ring-offset-background',
        )}
      >
        <div className="relative min-w-0 flex-1">
          <ChessBoard
            position={displayFen}
            flipped={flipped}
            lastMove={boardLastMove}
            lastMoveColor={boardLastMoveColor}
            onPieceDrop={handlePieceDrop}
            arrows={boardArrows}
            squareMarkers={boardMarkers}
            maxWidth={boardMaxWidthPx - TRAIN_EVAL_BAR_CHROME_PX}
            id="chessboard"
          />
          {/* 190.1 UAT round 7: short "Points: +N" pop over the board as the
              reveal opens. Centering lives in the keyframes' translate(-50%,-50%)
              (NOT Tailwind translate utilities — the animation would overwrite
              them mid-flight); the animation ends at opacity 0 and holds there
              (fill-mode forwards), so the element lingers invisibly (and
              pointer-events-none) until the next puzzle clears the state. */}
          {pointsFlash !== null && (
            <div
              className="animate-train-points-pop pointer-events-none absolute left-1/2 top-1/2 z-10 flex select-none items-center gap-3 whitespace-nowrap rounded-full py-1.5 pl-1.5 pr-6 text-2xl font-bold shadow-lg"
              style={{ backgroundColor: pointsFlashColors?.bg, color: pointsFlashColors?.fg }}
              data-testid="train-points-flash"
            >
              {/* Sketch 004 (phase 222 UAT): the pop carries the verdict bot's
                  face — the same bot that speaks the verdict bubble below. */}
              {verdictBot !== null && <PointsFlashAvatar persona={verdictBot} />}
              <span>+{pointsFlash}</span>
            </div>
          )}
        </div>
        {/* Quick 260803-iv6 (Task 1): the slot is ALWAYS present — that is
            what keeps the board from resizing mid-puzzle when the reveal
            opens (the board's own maxWidth already reserves this column's
            width). Only the EvalBar inside it is conditional on showEvalBar;
            before the reveal an empty frame (phase 222 UAT round 3) fills the
            slot so the board's right edge never reads as an odd gap. */}
        <div className="w-5 shrink-0">
          {!showEvalBar && (
            <div
              aria-hidden="true"
              className="h-full w-full rounded border border-border bg-muted"
              data-testid="train-eval-bar-placeholder"
            />
          )}
          {showEvalBar && (
            <EvalBar
              evalCp={evalBarReading.evalCp}
              evalMate={evalBarReading.evalMate}
              depth={evalBarReading.depth}
              flipped={flipped}
              accentColor={STOCKFISH_ACCENT}
              testId="train-eval-bar"
              className="h-full w-full"
            />
          )}
        </div>
      </div>
      </div>
      {engineFailed ? (
        <div className="flex flex-col items-center gap-2" data-testid="train-engine-error">
          <LoadError resource="the grading engine" />
          <Button
            variant="brand-outline"
            className={TRAIN_BUTTON_CLASS}
            data-testid="btn-train-engine-retry"
            onClick={handleRetryEngine}
          >
            Retry
          </Button>
        </div>
      ) : !isReady ? (
        // CR-01 defense in depth: never offer the guess/move UI before the
        // grading engine's Worker has actually completed its UCI handshake —
        // without this, a fast user (or one on a slow connection where the
        // ~1-2MB WASM asset takes longer to fetch) could commit a graded move
        // while `gradingEngine.search()` would still have fabricated a bogus
        // result. The primary fix (queuing until ready) lives in
        // useTrainGradingEngine.ts; this is the belt-and-suspenders UI gate.
        <div className="flex items-center gap-2" data-testid="train-engine-loading">
          <Loader2 className="size-4 animate-spin text-muted-foreground" aria-hidden="true" />
          <p className="text-sm font-semibold text-muted-foreground">Loading engine…</p>
        </div>
      ) : (
        <>
          {/* Phase 222 (D-07/D-10): the one chat-row bubble slot for every
              state — guess prompt/buttons, intro stepper, drop-nudge, move
              prompt, grading indicator, and the verdict (with the
              Solution/Analyze/Next row inside its actions slot) — all render
              from `bubbleBody`, resolved outside this component
              (`renderTrainBotBubbleBody`) so growing the state machine never
              adds a branch here. `bubbleBody === null` only while settings
              are still loading on the session's first puzzle (RESEARCH
              Finding D) — nothing renders in this slot then. `nudgeNonce` is
              the bubble's own remount key (Pitfall 3: a repeated nudge must
              replay the pulse, not be swallowed as an already-running
              animation). */}
          {bubbleBody !== null && (
            <TrainBotBubble
              persona={bubblePersona}
              state={bubbleState.kind}
              nudgeNonce={nudgeNonce}
              actions={bubbleBody.actions}
              ring={walkthroughTarget === 'verdict'}
            >
              {bubbleBody.copy}
            </TrainBotBubble>
          )}
          {gradingError && (
            <div className="flex flex-col items-center gap-2" data-testid="train-grading-error">
              <LoadError resource="your move grading" />
              <Button
                variant="brand-outline"
                className={TRAIN_BUTTON_CLASS}
                data-testid="btn-train-retry-grading"
                onClick={retryGrading}
              >
                Retry
              </Button>
            </div>
          )}
        </>
      )}
      </div>
      {showResultRow && (
        <TrainReveal
          puzzle={puzzle}
          sessionId={trainSession.session?.session_id ?? null}
          verdict={verdict}
          isSolveError={trainSession.isSolveError}
          onRetrySolve={trainSession.retrySolve}
          onNext={handleNext}
          onFenChange={setBoardFen}
          gradingEngine={gradingEngine}
          guess={guess}
          playedMoveUci={lastPlayedUci}
          gradeResult={gradeResult}
          playedMoveQuality={playedMoveQuality}
          gameMoveQuality={gameMoveQuality}
          onGameMoveUciChange={setGameMoveUci}
          onAnalyzeClick={handleAnalyzeClick}
          onGameMoveLineChange={setGameMoveLine}
          onLineStep={walkthrough.handleLineStep}
          solutionNonce={solutionNonce}
          spotlightKey={spotlight?.key ?? null}
          onSpotlightChange={walkthrough.handleSpotlightChange}
          isBoardDeparted={isBoardDeparted}
          onReturnToSolution={returnToSolution}
          alsoFineMoves={revealOverlay.alsoFineMoves}
          isExploring={freePlay.isExploring}
          freePlay={freePlay}
          onExitExploration={handleShowSolution}
          flipped={flipped}
          onFlipBoard={handleFlipBoard}
          walkthroughLinesRing={walkthroughTarget === 'lines'}
        />
      )}
    </div>
  );
}
