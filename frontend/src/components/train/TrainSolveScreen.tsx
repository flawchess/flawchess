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
 * Grading (SOLV-03): `startGrading` fires once per puzzle at MOUNT (190-RESEARCH.md
 * Open Question 1 — resolved at mount so the think time is spent searching),
 * not gated on the guess. Phase 235: it passes the server key so the think-time
 * search evaluates the position after the key (D-08); the key is read only
 * there and never rendered before the attempt (D-05). `correct_guess` is read
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
import { Loader2 } from 'lucide-react';
import { buildAnalysisFenUrl, buildGameAnalysisUrl } from '@/lib/analysisUrl';
import { trackFeature } from '@/lib/analytics';
import { ChessBoard } from '@/components/board/ChessBoard';
import type { BoardArrow, SquareMarker } from '@/components/board/ChessBoard';
import { Button } from '@/components/ui/button';
import { LoadError } from '@/components/ui/load-error';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { TrainReveal } from '@/components/train/TrainReveal';
import { TrainMoveTreeList } from '@/components/train/TrainMoveTreeList';
import { TrainRevealActionBar } from '@/components/train/TrainRevealActionBar';
import { EvalBar } from '@/components/analysis/EvalBar';
import type {
  ServerGradedMove,
  SolveRecheck,
  SolveResponse,
  TrainPuzzle,
  TrainSettingsResponse,
  VettedMove,
} from '@/types/train';
import type { UseTrainSessionResult } from '@/hooks/useTrainSession';
import { useFitBoardToViewport } from '@/hooks/useFitBoardToViewport';
import { useIsDesktop, useIsSmUp } from '@/hooks/useIsDesktop';
import { useTrainRevealTree } from '@/hooks/useTrainRevealTree';
import type { RevealEvalReading, RevealUserMove, TrainRevealTree } from '@/hooks/useTrainRevealTree';
import { useTrainLiveAlternatives } from '@/hooks/useTrainLiveAlternatives';
import type { TreeSeedEval } from '@/hooks/useTreeMoveGrading';
import { useWakeLock } from '@/hooks/useWakeLock';
import { gradeFromServerPair, type InstantGradeState } from '@/hooks/trainGradingSupport';
import type {
  GradeResult,
  RecheckResult,
  TrainGradingEngine,
} from '@/hooks/useTrainGradingEngine';
import { useEngineDisplaySettings } from '@/lib/engineSettings';
import { evalToExpectedScore, sideToMoveFromFen, terminalPositionEval } from '@/lib/liveFlaw';
import { useMarkPlayActive } from '@/lib/playActive';
import { usePublishMobileBoardControls } from '@/lib/mobileBoardControls';
import type { MobileBoardControls } from '@/lib/mobileBoardControls';
import { playSound } from '@/lib/sounds';
import { saveTrainRevealCache } from '@/lib/trainRevealCache';
import { buildChipGroups, revealBestUciOf } from '@/lib/trainRevealLines';
import type { ChipGroup, GameMoveLineState, RoleKey } from '@/lib/trainRevealLines';
import type { CachedTrainReveal } from '@/lib/trainRevealCache';
import { GUESS_LABELS } from '@/lib/trainGuessLabels';
import type { Guess } from '@/lib/trainGuessLabels';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import { resolveBubbleState } from '@/components/train/trainBubbleState';
import type { TrainBubbleState } from '@/components/train/trainBubbleState';
import {
  GRADING_COPY,
  RECHECK_COPY,
  HILDA_ID,
  introStepCount,
  WALKTHROUGH_STEP_COUNT,
  dropNudgeCopy,
  introCopy,
  movePromptCopy,
  pickPuzzleHost,
  promptCopy,
  verdictCopy,
  walkthroughCopy,
} from '@/lib/trainBotCopy';
import type {
  IntroStep,
  TrainCopyAudience,
  VerdictCopy,
  WalkthroughContext,
} from '@/lib/trainBotCopy';
import { cn } from '@/lib/utils';
import { personaForId } from '@/lib/personas/personaRegistry';
import type { Persona } from '@/lib/personas/personaRegistry';
import { placeholderAvatarFor, resolveAvatarSrc } from '@/lib/personas/personaAvatars';
import { useTrainSettings } from '@/hooks/useTrainSettings';
import { SettingsSheetButton } from '@/components/settings/SettingsSheetButton';
import { useTrainOnboarding } from '@/hooks/useTrainOnboarding';
import { useTrainWalkthrough } from '@/hooks/useTrainWalkthrough';
import { useTrainPuzzleTelemetry } from '@/hooks/useTrainPuzzleTelemetry';
import { TrainBotStepper } from '@/components/train/TrainBotStepper';
import { TrainTourOverlay } from '@/components/train/TrainTourOverlay';
import {
  buildChipFocusOverlay,
  buildTrainFreePlayArrows,
  buildTrainRevealOverlay,
  buildTrainStepMarkers,
  buildTrainStepOverlayArrows,
  classifyTrainMoveQuality,
  trainRootMultiPvFloor,
  TRAIN_STEP_HIGHLIGHT,
} from '@/lib/trainArrows';
import type {
  TrainFineMove,
  TrainMoveQuality,
  TrainOverlayMove,
  TrainPuzzleType,
  TrainRevealOverlay,
} from '@/lib/trainArrows';
import type { PvLine } from '@/hooks/uciParser';
import { scorePuzzle, TRAIN_POINTS_PER_PUZZLE } from '@/lib/trainScore';
import type { TrainMoveTier } from '@/lib/trainScore';
import { buildPhoneGradePayload, instantServerTier } from '@/lib/trainPhoneGrade';
import { shouldRecheck } from '@/lib/trainRecheck';
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
 * Quick 260803-iv6: resolves the Train eval bar's reading: a terminal
 * (mate/draw) verdict first (the rules already know the answer), else the
 * reveal engine's own reading of the shown position (Phase 237 plan 06: one
 * engine follows every node, on the known lines and off them). Kept as a flat,
 * non-exported module-level helper so the component body stays shallow per
 * CLAUDE.md.
 */
function resolveTrainEvalBarReading(fen: string, reading: RevealEvalReading): RevealEvalReading {
  const terminal = terminalPositionEval(fen);
  if (terminal !== null) {
    return { evalCp: terminal.cp, evalMate: terminal.mate, depth: TRAIN_TERMINAL_EVAL_DEPTH };
  }
  return reading;
}

/** The four board props the reveal overlay decides (arrows, badges, last-move
 * square and its highlight color). */
interface RevealBoardOverlay {
  arrows: BoardArrow[];
  markers: SquareMarker[];
  lastMove: { from: string; to: string } | null;
  lastMoveColor: string | undefined;
}

interface RevealBoardOverlayInput {
  /** The engine's arrows for the shown position (drawn only off the known lines). */
  offLineArrows: BoardArrow[];
  /** The reveal engine's staleness-guarded lines for the shown position. */
  liveLines: readonly PvLine[];
  /** The Stockfish arrows setting: how many live moves a stepped position may draw. */
  liveArrowCount: number;
  tree: Pick<
    TrainRevealTree,
    'isAtRoot' | 'isOffLine' | 'stepInfo' | 'activeChip' | 'lastMove' | 'boardMarkers' | 'lastMoveColor'
  >;
  chips: readonly ChipGroup[];
  revealOverlay: TrainRevealOverlay;
  /** Quick 261010-e5l: the soft root's latched live alternatives, drawn only at the puzzle position. */
  liveAlternatives: readonly TrainFineMove[];
  /** The puzzle's arrival move (the highlight at the puzzle position). */
  puzzleLastMove: { from: string; to: string } | null;
}

/**
 * Phase 237: what the reveal board draws. A position off every known line (the
 * user's own sideline) draws the engine's blue arrows and the played move's
 * grade. A list-stepped line position
 * shows the quality-colored last move, the first move's badge and a blue
 * pointer at the line's next move (the solution overlay is cleared), plus the
 * live engine's other top moves as translucent secondaries once deep enough,
 * with the line's pointer painted on top. At the puzzle position the full reveal
 * overlay is drawn with ONLY the focused chip's arrow and badge lit and every
 * other one dimmed, never hidden (`buildChipFocusOverlay`); with no chip focused
 * (D-04) everything dims. Quick 261010-e5l: a soft puzzle's live engine
 * alternatives join that overlay as green arrows with 'good' badges.
 */
function resolveRevealBoardOverlay({
  offLineArrows,
  liveLines,
  liveArrowCount,
  tree,
  chips,
  revealOverlay,
  liveAlternatives,
  puzzleLastMove,
}: RevealBoardOverlayInput): RevealBoardOverlay {
  if (tree.isOffLine) {
    return {
      arrows: offLineArrows,
      markers: tree.boardMarkers,
      lastMove: tree.lastMove,
      lastMoveColor: tree.lastMoveColor,
    };
  }
  const step = tree.stepInfo;
  if (step !== null) {
    // The first move carries its chip's quality; deeper moves are engine
    // continuations and read as 'good' (190.1 UAT round 3).
    const firstMoveQuality = chips.find((chip) => chip.key === step.line)?.quality ?? null;
    const quality: TrainMoveQuality | null = step.isFirstMove ? firstMoveQuality : 'good';
    return {
      arrows: buildTrainStepOverlayArrows(step.nextMoveUci, liveLines, liveArrowCount),
      markers: buildTrainStepMarkers(step.lastMoveUci, quality, step.isFirstMove),
      lastMove: { from: step.lastMoveUci.slice(0, 2), to: step.lastMoveUci.slice(2, 4) },
      lastMoveColor: quality !== null ? TRAIN_STEP_HIGHLIGHT[quality] : undefined,
    };
  }
  if (!tree.isAtRoot) {
    return { arrows: [], markers: [], lastMove: tree.lastMove, lastMoveColor: undefined };
  }
  const focusedChip = chips.find((chip) => chip.key === tree.activeChip);
  const lit = buildChipFocusOverlay(
    revealOverlay,
    focusedChip !== undefined ? [focusedChip.uci] : null,
    liveAlternatives,
  );
  return { arrows: lit.arrows, markers: lit.markers, lastMove: puzzleLastMove, lastMoveColor: undefined };
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
  /** Phase 222 UAT round 3: a warm-up first session gets one extra intro step. */
  isWarmup: boolean;
  /** D-03 (Phase 224): threaded into `introCopy`/`introStepCount` (the
   * welcome/warm-up intro copy). */
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
  if (bubbleState.kind === 'grading' && bubbleState.recheck) {
    // Phase 235 (D-12): the disagreement re-check is running (a few extra seconds).
    return {
      copy: (
        <span className="flex items-center gap-2" data-testid="train-recheck-indicator">
          <Loader2 className="size-4 animate-spin text-muted-foreground" aria-hidden="true" />
          {RECHECK_COPY}
        </span>
      ),
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
  if (bubbleState.kind === 'submitting') {
    // Phase 236 (D-16): the instant solve POST round trip. A bare spinner, no
    // copy: the move was taken, and nothing says it is being "checked".
    return {
      copy: (
        <span
          className="flex items-center"
          role="status"
          aria-label="Saving your move"
          data-testid="train-submitting-indicator"
        >
          <Loader2 className="size-4 animate-spin text-muted-foreground" aria-hidden="true" />
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
  if (bubbleState.kind === 'verdict') {
    // Phase 237 plans 08/10: the verdict itself (strip on phones, bubble on
    // desktop) and the first-reveal tour bubble both live in TrainReveal now;
    // the left slot stays empty from the verdict on.
    return null;
  }
  return null;
}

/**
 * Phase 222 (D-02/D-03/D-05): the persona that should speak the current
 * bubble state — Hilda during the intro stepper (fixed host, never
 * randomly cast), else the puzzle's random host, which also speaks the
 * verdict (Phase 237 UAT). Module-level so this dispatch
 * never raises `TrainSolveScreen`'s own pinned complexity (FINDING B).
 */
function resolveBubblePersona(
  bubbleState: TrainBubbleState,
  sideToMove: 'white' | 'black',
  regularBot: Persona,
  verdictBot: Persona | null,
  isWarmup: boolean,
  audience: TrainCopyAudience,
): Persona {
  if (bubbleState.kind === 'intro') {
    return (
      personaForId(introCopy(bubbleState.step, sideToMove, isWarmup, audience).personaId) ?? regularBot
    );
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
  // Phase 236 Pitfall 4: bumped on every puzzle change; a background grade only
  // writes state or a late phone_grade record while its captured value still matches.
  const instantAttemptRef = useRef(0);
  // Phase 236 (D-14/D-15): the reveal's view of a server-graded move whose phone
  // grade has not landed (null on the normal path and once it landed).
  const [instantGrade, setInstantGrade] = useState<InstantGradeState | null>(null);
  // Phase 236 (D-16): the instant solve POST is in flight. Distinct from
  // `isGrading`, which would show the "Checking your move…" copy.
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGrading, setIsGrading] = useState(false);
  // Phase 235 (D-12): true only around the single `recheckMove` await.
  const [isRechecking, setIsRechecking] = useState(false);
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
  // 190.1 UAT / Phase 237: the reveal-time search's state, reported up from
  // TrainReveal (idle / loading / ready with the line / error). Its line derives
  // the game move's quality badge; the whole state builds the standalone game
  // chip's loading/failed look. Deliberately NOT reset by the per-puzzle effect
  // below: TrainReveal reports `loading` synchronously from its own effect, which
  // runs BEFORE this component's on the same commit (a restored reveal mounts
  // with the reveal query already cached), so a reset here would wipe it and
  // leave the game chip loading forever. The search's own cleanup reports idle.
  const [gameMoveLineState, setGameMoveLineState] = useState<GameMoveLineState>({ status: 'idle' });
  const gameMoveLine = gameMoveLineState.status === 'ready' ? gameMoveLineState.line : null;
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
  // Phase 211 (Plan 03): derived HERE, above the tree seed memo, so the
  // hoisted `vettedMoves` memo below can feed BOTH the reveal overlay and the
  // tree's grading seed from one place.
  const liveVerdict =
    trainSession.lastSolvedPosition === puzzle.position ? trainSession.lastSolveResponse : null;
  const verdict = liveVerdict ?? restoredSolve?.verdict ?? null;
  const revealPuzzleType: TrainPuzzleType = verdict?.puzzle_type ?? 'sharp';

  // Phase 233 (D-02): think-time telemetry for this puzzle. Prefer the restored
  // reveal's session id (Pitfall 6: `trainSession.session` is null briefly on a
  // restored mount). `isReady` gates the timer start: the guess UI does not
  // exist while "Loading engine…" shows (Pitfall 8). Never read by scoring (D-05).
  const puzzleTelemetry = useTrainPuzzleTelemetry({
    sessionId: restoredSolve?.sessionId ?? trainSession.session?.session_id ?? null,
    position: puzzle.position,
    isReady: gradingEngine.isReady,
    isRestored: restoredSolve !== null,
    hasVerdict: verdict !== null,
    restoredReview: restoredSolve?.reviewTelemetry,
  });

  // Phase 211 (D-01/D-06): the server's certified "also fine" set — the
  // single source BOTH consumers read: the reveal overlay's green alternative
  // arrows AND the tree seed's root-ply key (do not inline the default
  // at either call site). The `?? []` here is the ONE nullish default for
  // the served list on this whole screen: a `trainRevealCache` entry written
  // by a pre-211 bundle restores a verdict with no `vetted_moves` key at
  // runtime even though the compiler sees the optional field — keeping
  // exactly one default is what makes the D-10 mutation test meaningful.
  const vettedMoves = useMemo<VettedMove[]>(() => verdict?.vetted_moves ?? [], [verdict]);

  // D-03: the single read site and the single default for the server-graded
  // set. Read only after the move (the re-check gate), never rendered
  // pre-attempt.
  const serverGradedMoves = useMemo<ServerGradedMove[]>(
    () => puzzle.server_graded_moves ?? [],
    [puzzle.server_graded_moves],
  );

  // The tree's grading seed: the grading engine's verdict for the puzzle
  // position, so a move forked from the puzzle position is graded without waiting
  // for the reveal engine to re-search a position the solve loop already
  // searched. Phase 211 (D-06): the seed also carries the SAME served vetted list
  // the reveal overlay draws (the hoisted `vettedMoves` memo above, the single
  // stale-cache default site), so a root fork's badge and the "Also fine" row can
  // never read different keys. Phase 236: null while an instant grade is pending
  // is fine, the reveal engine is off then and grades once it starts.
  const treeSeedEval = useMemo<TreeSeedEval | null>(
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
  // Phase 228 (D-13): the Stockfish arrows setting sets how many live engine
  // arrows draw off the known lines. Quick 261009-por: it also caps the live
  // secondary arrows drawn under the line pointer on a stepped known line.
  const { sfArrows } = useEngineDisplaySettings();
  // 190.1 UAT round 7: the points earned by a LIVE solve, shown as a short
  // "Points: +N" pop animation over the board as the reveal opens. Set by the
  // result-sound effect below (so it can never fire for a restored reveal),
  // cleared on puzzle transition. The element's CSS animation ends at
  // opacity 0 with fill-mode forwards, so no unmount timer is needed.
  const [pointsFlash, setPointsFlash] = useState<number | null>(null);
  // Phase 200 UAT round 5: board orientation. Defaults to the solver's own
  // color (a black-to-move puzzle starts flipped, as it always has) and is
  // toggled by the phone bottom bar's flip button. Reset on every puzzle
  // transition by the same effect that resets the rest of the solve state —
  // orientation is a per-position affordance, not a session preference.
  const [flipped, setFlipped] = useState(puzzle.side_to_move === 'black');
  const handleFlipBoard = useCallback(() => setFlipped((prev) => !prev), []);
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
  // WR-02: exactly one reveal action bar is mounted. From `sm` up it is the in-flow
  // bar under the board; below `sm` it is the fixed bottom bar fed by the published
  // payload. Both used to mount (one CSS-hidden), duplicating btn-train-next /
  // btn-train-analyze / train-reveal-action-bar testids in the DOM.
  const isSmUp = useIsSmUp();

  // 190.1 UAT: the played move's classified quality — derived once here and
  // shared by the board overlay below AND the reveal's chips (marks), so the two
  // surfaces can never drift.
  //
  // Phase 211 (D-03/D-07): when the verdict carries the server's graded-ES
  // pair (a key-move override), the badge derives from THOSE numbers through
  // the same classifier — before this phase the board badge and the score
  // chip were always equal only because the server echoed the client's own
  // assertion; now the server can legitimately disagree with the client
  // engine's search, and the display must follow the server. Off-key moves
  // (graded_es_* null/absent) keep the client-engine derivation.
  //
  // Phase 236 (D-16): on the instant path the verdict lands before the phone
  // grade, so the badge follows the server's pair while `gradeResult` is null.
  // `revealBestUci` is the key until the grade replaces it (same UCI after).
  const revealBestUci = revealBestUciOf(gradeResult, instantGrade);
  // Phase 237 (D-06): the exact predicate that merges the You and Best chips, so
  // the verdict clause ("best move" vs "good move") can never disagree with the
  // chips row. Only wording depends on it, never points.
  const playedIsBest = lastPlayedUci !== null && lastPlayedUci === revealBestUci;
  const playedMoveQuality = useMemo<TrainMoveQuality | null>(() => {
    if (lastPlayedUci === null) return null;
    const isBest = lastPlayedUci === revealBestUci;
    if (verdict?.graded_es_before != null && verdict?.graded_es_after != null) {
      return classifyTrainMoveQuality(verdict.graded_es_before, verdict.graded_es_after, isBest);
    }
    if (gradeResult === null) return null;
    return classifyTrainMoveQuality(gradeResult.esBefore, gradeResult.esAfter, isBest);
  }, [gradeResult, lastPlayedUci, verdict, revealBestUci]);

  // The game move's quality: derived from the coinciding best/played move
  // when no reveal-time search ran, else from the searched line's eval via
  // the SAME expected-score pipeline the verdict uses.
  const gameMoveQuality = useMemo<TrainMoveQuality | null>(() => {
    if (gameMoveUci === null) return null;
    if (gameMoveUci === revealBestUci) return 'best';
    if (gameMoveUci === lastPlayedUci) return playedMoveQuality;
    // The eval-derived branch needs the phone's root reading (esBefore).
    if (gradeResult === null || gameMoveLine === null) return null;
    const mover = sideToMoveFromFen(puzzle.fen);
    const esGame = evalToExpectedScore(gameMoveLine.evalCp, gameMoveLine.evalMate, mover);
    return classifyTrainMoveQuality(gradeResult.esBefore, esGame, false);
  }, [gameMoveUci, gradeResult, revealBestUci, lastPlayedUci, playedMoveQuality, gameMoveLine, puzzle.fen]);

  // Phase 237 (D-02): the chips, built ONCE here from everything this screen
  // owns, so the same groups seed the move tree and render in the chips row.
  // T-237-07 (T-190-16): empty until the solve verdict has landed, so no answer
  // line exists on the client before the attempt.
  const chips = useMemo<ChipGroup[]>(
    () =>
      verdict === null
        ? []
        : buildChipGroups({
            puzzleFen: puzzle.fen,
            playedMoveUci: lastPlayedUci,
            gradeResult,
            instantGrade,
            gameMoveUci,
            gameMoveLine: gameMoveLineState,
            playedMoveQuality,
            gameMoveQuality,
          }),
    [
      verdict,
      puzzle.fen,
      lastPlayedUci,
      gradeResult,
      instantGrade,
      gameMoveUci,
      gameMoveLineState,
      playedMoveQuality,
      gameMoveQuality,
    ],
  );

  // The walkthrough hook is declared AFTER the tree (it needs the tree's
  // callbacks), but the tree's step and move callbacks must hide the phone tour
  // overlay: route them through a ref the walkthrough fills in below.
  const walkthroughHideRef = useRef<() => void>(() => undefined);
  const handleTreeUserStep = useCallback(() => {
    puzzleTelemetry.onLineUserStep();
    walkthroughHideRef.current();
  }, [puzzleTelemetry]);

  // Phase 237 plan 06 (D-13/D-14): every user-played move after the verdict is
  // counted (board drops and Stockfish-row clicks); the FIRST fork per puzzle also
  // sends one Umami event. Called from the tree's user-move commands (a drop or a
  // row click), never from an effect, so a mount or a restore sends nothing. The
  // ref resets with the puzzle in the per-puzzle reset effect below.
  const sidelineForkTrackedRef = useRef(false);
  const handleRevealUserMove = useCallback(
    ({ source, forked }: RevealUserMove) => {
      // D-13: the telemetry fork flag (review_explored) follows the same `forked`
      // the Umami event uses; a move onto a known line is a board move, not a fork.
      puzzleTelemetry.onExploreMove(source, forked);
      if (forked && !sidelineForkTrackedRef.current) {
        sidelineForkTrackedRef.current = true;
        trackFeature('action', { target: 'train-sideline-fork' });
      }
      // Phase 237 UAT (G-01): a move on the board hides the tour overlay.
      walkthroughHideRef.current();
    },
    [puzzleTelemetry],
  );

  // Phase 237: the reveal's single move tree — every chip's pre-loaded line plus
  // the user's own forks, graded and engine-backed (plan 06: a post-verdict drop
  // forks in place; there is no separate free-play mode). Inert until the verdict
  // lands. The reveal engine stays off while the Phase 236 background grade is
  // pending so nothing competes with the phone-accuracy search.
  const revealTree = useTrainRevealTree({
    startFen: puzzle.fen,
    active: verdict !== null,
    chips,
    onUserMove: handleRevealUserMove,
    onUserStep: handleTreeUserStep,
    // Phase 237 plan 09 (D-12): a chip tap AND a line-matching root move both report
    // here (the hook's selectChip and playMove fire it), so the telemetry counts both.
    onChipSelect: puzzleTelemetry.onChipSelect,
    // Analyze -> Back: rebuild the focused chip, the sidelines and the shown node.
    restored: restoredSolve?.revealTree ?? null,
    seedEval: treeSeedEval,
    engineEnabled: instantGrade?.status !== 'pending',
    // Quick 261010-e5l: a soft puzzle's root searches best + 3 for live alternatives.
    rootMinMultiPv: trainRootMultiPvFloor(revealPuzzleType),
    // Phase 237 plan 07: ArrowLeft / ArrowRight / Home on desktop (inert until the verdict).
    navContainerRef: boardRef,
  });

  /**
   * Phase 200 (EXPLORE-04) / Phase 237 plan 07: rewind (the old Solution button)
   * brings the board back to the puzzle position in one tap: the tree rewinds to
   * its root (the default chip is lit again) and its sidelines stay listed. The
   * board orientation is left alone: flip is a permanent bar control now, and a
   * puzzle transition still restores the solver-colour default (per-puzzle effect).
   */
  const { goToRoot: revealGoToRoot, goBack: revealGoBack, goForward: revealGoForward } = revealTree;
  const handleRewind = useCallback((): void => {
    revealGoToRoot();
    // Phase 229 D-12 / Phase 237 D-14: drill outcomes are DB-known, but rewinding
    // to the solution is not; the kept 'train-solution' target (never renamed).
    trackFeature('action', { target: 'train-solution' });
  }, [revealGoToRoot]);

  // Phase 237 plan 09 (D-12): the most chips shown on this reveal. The hook keeps
  // the maximum, so a game chip that arrives late raises the total and a reset to
  // zero chips (the next puzzle, before its verdict) reports nothing.
  const { onChipsTotalChange } = puzzleTelemetry;
  const chipCount = chips.length;
  useEffect(() => {
    if (chipCount > 0) onChipsTotalChange(chipCount);
  }, [chipCount, onChipsTotalChange]);

  // Phase 237 plan 07: the bar's Analyze / Next handlers are plain functions
  // defined further down (they close over a lot of reveal state). The published
  // payload needs referentially stable callbacks, so it calls through refs that
  // an effect refreshes every render (same shape as `walkthroughTreeStepRef`).
  const nextFromRevealRef = useRef<() => void>(() => undefined);
  const analyzeFromRevealRef = useRef<() => void>(() => undefined);
  const handleBarNext = useCallback(() => nextFromRevealRef.current(), []);
  const handleBarAnalyzeClick = useCallback(() => analyzeFromRevealRef.current(), []);
  // Analyze opens the user's own source game one move before the mistake. Every
  // other puzzle opens just its position: a red herring's game_id routinely
  // points at ANOTHER user's game (the herring pool is shared), which Analyze
  // used to open in full, and a sharp filler or an orphaned herring has no game
  // at all, which used to hide Analyze. Reads `verdict.source` like the game
  // footer (Analyze only renders once the verdict exists); a stale verdict
  // without `source` keeps the game link whenever there is a game.
  const analyzeOpens: WalkthroughContext['analyzeOpens'] =
    puzzle.game_id !== null && verdict?.source !== 'red_herring' ? 'game' : 'position';
  const analyzeTo = useMemo<string>(
    () =>
      analyzeOpens === 'game' && puzzle.game_id !== null
        ? buildGameAnalysisUrl(puzzle.game_id, puzzle.ply > 0 ? puzzle.ply - 1 : null)
        : buildAnalysisFenUrl(puzzle.fen, puzzle.side_to_move),
    [analyzeOpens, puzzle.game_id, puzzle.ply, puzzle.fen, puzzle.side_to_move],
  );

  // Phase 222 (D-24): the first-reveal walkthrough — step state, the bar-Next
  // routing, the phone overlay's hidden flag, the phone scroll-to-target effect
  // and the leave-stamp all live in the hook; this component only reads
  // `activeStep` / `target` (the strip, board-row, list and bar rings) and
  // threads the handlers through.
  // Phase 237 plan 10 (D-09): the tour explains "Move = Best" / "Move = Game" only
  // when that merged chip is actually on screen: the Move chip's second role.
  const mergedChip = useMemo<WalkthroughContext['mergedChip']>(() => {
    const secondRole = chips.find((chip) => chip.roles.includes('your'))?.roles.find((role) => role !== 'your');
    return secondRole === 'best' || secondRole === 'game' ? secondRole : null;
  }, [chips]);
  const walkthrough = useTrainWalkthrough({
    settings,
    hasVerdict: verdict !== null,
    analyzeOpens,
    mergedChip,
    isDesktop,
    screenRef,
    pinnedRef,
    stamp,
  });
  const hideTourOverlay = walkthrough.hide;
  useEffect(() => {
    walkthroughHideRef.current = hideTourOverlay;
  }, [hideTourOverlay]);
  // The strip's expand feeds the telemetry flag AND hides the tour overlay.
  const { markStripExpanded } = puzzleTelemetry;
  const handleStripExpand = useCallback(() => {
    markStripExpanded();
    hideTourOverlay();
  }, [markStripExpanded, hideTourOverlay]);
  const walkthroughTarget = walkthrough.target;
  // Phase 237 UAT: Hilda's tour is an overlay on the board at every width
  // (G-01 for phones; on desktop a tour bubble stacked over the verdict bubble
  // put two avatars on top of each other).
  const tourPersona = personaForId(HILDA_ID);
  const tourOverlay =
    walkthrough.activeStep === null || tourPersona === undefined ? null : (
      <TrainTourOverlay
        persona={tourPersona}
        copy={walkthroughCopy(walkthrough.activeStep, walkthrough.context).copy}
        step={walkthrough.activeStep}
        stepCount={WALKTHROUGH_STEP_COUNT}
        hidden={walkthrough.overlayHidden}
        onReopen={walkthrough.reopen}
      />
    );
  // Phase 233 (D-13): sticky flag, so the walkthrough being active at ANY point
  // on this reveal counts (not read at flush time, after the leave-stamp).
  const walkthroughActive = walkthrough.activeStep !== null;
  useEffect(() => {
    if (walkthroughActive) puzzleTelemetry.markWalkthroughActive();
  }, [walkthroughActive, puzzleTelemetry]);
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
  const { startGrading, abortGrading, gradeMove, recheckMove, restartEngine, isReady, hasError } =
    gradingEngine;

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
    // Pitfall 4: TrainSolveScreen is one instance across puzzles, so a background
    // grade started on the previous puzzle must prove it still belongs to the
    // puzzle on screen (gradeInBackground compares against this counter).
    instantAttemptRef.current += 1;
    // 190.1 UAT round 5: a restored puzzle (Analyze -> back) seeds its cached
    // solved state instead of the fresh-puzzle reset, and skips the mount
    // grading search entirely — no move will ever be graded for it. The
    // Next-press transition to a fresh puzzle re-fires this effect with
    // restoredSolve already null (both change on the same render).
    setGuess(restoredSolve?.guess ?? null);
    setBoardFen(puzzle.fen);
    setMoveApplied(restoredSolve !== null);
    setIsGrading(false);
    setIsRechecking(false);
    setInstantGrade(null);
    setIsSubmitting(false);
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
    // card still rendered. `gameMoveLineState` is deliberately NOT reset here
    // either, see its declaration. The move tree resets itself, keyed on
    // `puzzle.fen` and the verdict.
    setPointsFlash(null);
    setFlipped(puzzle.side_to_move === 'black');
    // Phase 222 (D-12): an abandoned intro stepper replays next time — reset
    // the step index on every puzzle transition, not just the first.
    // `nudgeNonce` resets too, so a drop rejected on the PREVIOUS puzzle
    // never leaves the new one's bubble showing a stale nudge pulse.
    setIntroStep(0);
    walkthrough.reset();
    setNudgeNonce(0);
    // Phase 200 (EXPLORE-05) / Phase 237: the next puzzle always starts in the
    // pristine reveal state, never mid-sideline: the move tree re-roots itself on
    // `puzzle.fen` (and tears down its engine), and the per-puzzle fork-event
    // ref resets here.
    sidelineForkTrackedRef.current = false;
    trainSession.resetSolve();
    if (restoredSolve === null) startGrading(puzzle.fen, puzzle.key_move_uci ?? null);
    return () => {
      abortGrading();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- trainSession.resetSolve is a stable useCallback from the hook (it closes over the mutation's own `.reset`, bound once per observer — see useTrainSession's stability comment; it was NOT stable before that fix, so this line's original claim was aspirational). Including the whole trainSession object would re-fire this effect every render. restoredSolve only ever changes together with puzzle.fen (Train.tsx pairs them), so puzzle.fen already covers it — as does puzzle.side_to_move, which is a function of the FEN. walkthrough.reset is stable per puzzle.
  }, [puzzle.fen, puzzle.key_move_uci, startGrading, abortGrading, walkthrough.reset]);

  /**
   * Phase 235 (D-10/D-19): the disagreement re-check. Runs for a sharp keyed
   * puzzle whose off-key, off-runner-up move the 1.5 s grade rated good, and
   * (quick 261008-ob1) for any keyed puzzle whose off-key move it rated
   * inaccuracy, so short-search noise cannot cost a move point.
   * The key, type and runner-up are read here, after the move and before the
   * POST, and never rendered (D-05). Resolves null when no re-check applies or
   * it failed (recheckMove never rejects, D-20).
   */
  async function runRecheck(grade: GradeResult, playedUci: string): Promise<RecheckResult | null> {
    const eligible = shouldRecheck({
      puzzleType: puzzle.puzzle_type ?? null,
      keyUci: puzzle.key_move_uci ?? null,
      runnerUpUci: puzzle.runner_up_uci ?? null,
      playedUci,
      tier: grade.moveTier,
      serverGradedUcis: serverGradedMoves.map((m) => m.uci),
    });
    if (!eligible) return null;
    // D-12: the wait copy lives exactly as long as the single re-check await;
    // the finally clears it for a null (timeout/failure) or a throw alike.
    setIsRechecking(true);
    try {
      return await recheckMove(puzzle.fen, playedUci);
    } finally {
      setIsRechecking(false);
    }
  }

  /**
   * Phase 236 (D-09/D-10): the played move is one the server grades itself, so
   * POST at once instead of waiting for the phone's 1.5 s grade.
   *
   * D-09: the verdict renders from the SolveResponse; the asserted tier is never
   * rendered. D-10: the tier is the composition-time server tier, which
   * `_resolve_grade` path 1 normally replaces with the live one. D-11: never
   * re-checked. D-12/D-13: no phone_grade on this POST (frozen that way for
   * retrySolve); the late 1.5 s reading rides the review flush instead. D-16:
   * `isGrading` stays false so "Checking your move…" never shows; the bubble
   * shows a copy-less spinner (`isSubmitting`) for the round trip instead.
   */
  async function solveInstantly(
    playedGuess: Guess,
    playedUci: string,
    tier: TrainMoveTier,
    keyUci: string,
  ): Promise<void> {
    setGradingError(false);
    // D-14: the reveal opens on the verdict with the Your-move card loading.
    setInstantGrade({ status: 'pending', keyUci, keyLine: null });
    // Started BEFORE the POST so the engine works during the round trip.
    gradeInBackground(playedUci);
    setIsSubmitting(true);
    try {
      await trainSession.solvePuzzle({
        position: puzzle.position,
        guess: playedGuess,
        played_move: playedUci,
        move_quality: tier,
        // Frozen at move time, so a retry resends the identical object.
        telemetry: puzzleTelemetry.solveTelemetry(),
      });
    } catch {
      // The solve-POST failure surfaces via trainSession.isSolveError (locked
      // copy + Retry, which calls trainSession.retrySolve() and resends this
      // SAME frozen body). The global mutation-cache handler in queryClient.ts
      // already reports it.
    } finally {
      setIsSubmitting(false);
    }
  }

  /**
   * Phase 236 D-12: grade the played move in the background so the 1.5 s reading
   * can ride the review flush. A rejection (timeout, engine error) is silent:
   * the verdict is already server-final, so no gradingError and no record
   * (D-15, Pitfall 8). A grade that settles after the user moved on is dropped
   * (Pitfall 4).
   * Known gap (review WR-02, deliberately not fixed): a Next pressed before this
   * grade lands records no phone_grade. A trailing review flush cannot recover it,
   * because the next puzzle's startGrading reuses the single grading Worker and
   * supersedes this in-flight search, so it never produces a reading. Recovering it
   * would mean delaying Next until the grade settles (or a second Worker), which
   * trades against the instant-verdict goal and is an owner decision. The audit
   * therefore under-samples fast Next presses; read it with that bias in mind.
   */
  function gradeInBackground(playedUci: string): void {
    const attempt = instantAttemptRef.current;
    const sessionId = trainSession.session?.session_id ?? null;
    const position = puzzle.position;
    gradeMove(puzzle.fen, playedUci, {
      // D-14: the solution card shows the think-time after-key line as soon as
      // the anchor has settled, before the played move's search finishes.
      onKeyLine: (keyLine) => {
        if (attempt !== instantAttemptRef.current) return;
        setInstantGrade((state) => (state === null ? state : { ...state, keyLine }));
      },
    }).then(
      (grade) => {
        if (attempt !== instantAttemptRef.current) return;
        setGradeResult(grade);
        setInstantGrade(null);
        if (grade.phoneReading == null) return;
        puzzleTelemetry.setLatePhoneGrade(sessionId, position, buildPhoneGradePayload(grade.phoneReading));
      },
      () => {
        // D-15: no gradingError and no record; the Your-move card falls back to a
        // header-only card and the verdict stays server-final.
        if (attempt !== instantAttemptRef.current) return;
        setInstantGrade((state) => (state === null ? state : { ...state, status: 'failed' }));
      },
    );
  }

  async function gradeAndSolve(playedGuess: Guess, playedUci: string): Promise<void> {
    const keyUci = puzzle.key_move_uci ?? null;
    const instantTier = instantServerTier(serverGradedMoves, playedUci, keyUci);
    if (instantTier !== null && keyUci !== null) {
      await solveInstantly(playedGuess, playedUci, instantTier, keyUci);
      return;
    }
    setIsGrading(true);
    setGradingError(false);
    let grade: GradeResult;
    let recheck: SolveRecheck | null = null;
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
    // D-04: the phone_grade record is always the 1.5 s reading, captured before
    // a re-check can replace `grade`.
    const phoneReading = grade.phoneReading ?? null;
    // D-11: a completed re-check replaces the 1.5 s grade whatever it says.
    const rechecked = await runRecheck(grade, playedUci);
    if (rechecked !== null) {
      grade = rechecked.grade;
      recheck = rechecked.recheck;
    }
    setGradeResult(grade);
    try {
      await trainSession.solvePuzzle({
        position: puzzle.position,
        guess: playedGuess,
        played_move: playedUci,
        move_quality: grade.moveTier,
        // Frozen at move time, so a retry resends the identical object.
        telemetry: puzzleTelemetry.solveTelemetry(),
        // D-17: every completed re-check rides the POST; none on a stall (D-20).
        // Frozen with the rest of the payload, so retrySolve never re-runs it.
        ...(recheck !== null ? { recheck } : {}),
        // D-13: the 1.5 s phone reading rides every keyed solve; frozen with the
        // payload, so retrySolve resends it unchanged.
        ...(phoneReading !== null ? { phone_grade: buildPhoneGradePayload(phoneReading) } : {}),
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
    startGrading(puzzle.fen, puzzle.key_move_uci ?? null);
  }, [isReady, engineRetryNonce, startGrading, puzzle.fen, puzzle.key_move_uci]);

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
      // Phase 200 (EXPLORE-01/02/D-12) / Phase 237: once the verdict has landed,
      // a further drop forks (or extends) a sideline IN PLACE on the one move
      // tree: no mode toggle, no second board, no second grading attempt. The
      // tree validates the drop against the position it shows, exactly as the
      // analysis board does, and a drop that matches a known line or an existing
      // sideline just moves along it (a board move, not a fork, D-13).
      // Guardrail (Pitfall 3, extended): this branch sits STRICTLY after the
      // guess and moveApplied guards above, which are what hold SOLV-02 at
      // exactly one graded attempt, and it never reaches `gradeMove` or the
      // solve POST below. Do not reorder these guards, and do not widen the
      // graded path (below) to read displayFen.
      if (verdict === null) return false; // solve/grading still pending
      return revealTree.playMove(source, target);
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
    puzzleTelemetry.markMove();
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

  // Phase 200 (D-12) / Phase 237: the live board position. Once the verdict has landed the board follows the reveal tree
  // (the puzzle position at its root); before that it shows the move just played.
  const displayFen = verdict !== null ? revealTree.fen : boardFen;

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
  // Phase 236 (RESEARCH Pitfall 2 / A1): not while the instant path's background
  // search is pending. The bar's own Worker would compete with that search
  // exactly on the population whose server tier is the phone-accuracy ground
  // truth. The bar appears up to ~1.5 s later on instant-path solves; the verdict
  // is not delayed.
  const showEvalBar = showResultRow && instantGrade?.status !== 'pending';
  // Phase 237 plan 07 (T-237-12): on phones the reveal bar replaces the main nav
  // buttons in the fixed bottom bar for the WHOLE reveal, from the moment the
  // verdict lands (`showResultRow`); null before it and on unmount, so a stale
  // payload can never press Next for a puzzle no longer on screen. The sm+ hosts
  // render the same bar in the page flow below.
  const revealCanReset = !revealTree.isAtRoot;
  const revealCanGoBack = revealTree.canGoBack;
  const revealCanGoForward = revealTree.canGoForward;
  const mobileBoardControls = useMemo<MobileBoardControls | null>(
    () =>
      verdict !== null && showResultRow && !isSmUp
        ? {
            onBack: revealGoBack,
            onForward: revealGoForward,
            onReset: handleRewind,
            onFlip: handleFlipBoard,
            canGoBack: revealCanGoBack,
            canGoForward: revealCanGoForward,
            canReset: revealCanReset,
            onNext: handleBarNext,
            analyzeTo,
            onAnalyzeClick: handleBarAnalyzeClick,
          }
        : null,
    [
      verdict,
      showResultRow,
      isSmUp,
      revealGoBack,
      revealGoForward,
      handleRewind,
      handleFlipBoard,
      revealCanGoBack,
      revealCanGoForward,
      revealCanReset,
      handleBarNext,
      analyzeTo,
      handleBarAnalyzeClick,
    ],
  );
  usePublishMobileBoardControls(mobileBoardControls);

  // Phase 237 plan 06: the reveal tree's one engine follows the shown position
  // and feeds the bar on every node (known lines and sidelines alike), so there is
  // no second engine and no concurrent search.
  const evalBarReading = resolveTrainEvalBarReading(displayFen, revealTree.evalReading);

  // 190.1-04 (D-02, reworked per 190.1 UAT): reveal-board overlay — the blue
  // best-move arrow, green alternative-good-move arrows capped by puzzle
  // type, the played-move arrow colored by its own quality, the thin white
  // game-move arrow, plus a move-quality corner badge on every arrow's
  // target square. Empty until the verdict has actually landed.
  const revealOverlay = useMemo(() => {
    const playedMove: TrainOverlayMove | null =
      lastPlayedUci !== null && playedMoveQuality !== null
        ? { uci: lastPlayedUci, quality: playedMoveQuality }
        : null;
    return buildTrainRevealOverlay(
      revealPuzzleType,
      // Phase 211 (D-01): the server's certified vetted list — the client
      // engine no longer contributes alternatives to this overlay. The
      // hoisted `vettedMoves` memo above owns the stale-cache default.
      vettedMoves,
      // Phase 236: the key while the phone grade is pending, so the best arrow
      // points at it and the key is never drawn as an "Also fine" arrow
      // (trainArrows.ts filters the alternatives against this UCI).
      revealBestUci,
      playedMove,
      gameMoveUci !== null ? { uci: gameMoveUci, quality: gameMoveQuality } : null,
      verdict !== null,
    );
  }, [
    verdict,
    revealPuzzleType,
    vettedMoves,
    revealBestUci,
    lastPlayedUci,
    playedMoveQuality,
    gameMoveUci,
    gameMoveQuality,
  ]);

  // Quick 261010-e5l: a soft puzzle's live engine alternatives, latched from
  // the root search. Owner UAT 2026-10-10: presented like the certified ones,
  // so the "Also fine" text lists them after the server alternatives.
  const liveAlternatives = useTrainLiveAlternatives(
    {
      puzzleType: revealPuzzleType,
      puzzleFen: puzzle.fen,
      bestMoveUci: revealBestUci,
      playedMoveUci: lastPlayedUci,
      drawnAlternatives: revealOverlay.alsoFineMoves,
    },
    revealTree.isAtRoot,
    revealTree.pvLines,
  );
  const alsoFineMoves = useMemo(
    () => [...revealOverlay.alsoFineMoves, ...liveAlternatives],
    [revealOverlay.alsoFineMoves, liveAlternatives],
  );

  // Phase 200 UAT round 5 / Phase 228 D-13: off the known lines the arrows are the
  // reveal engine's own top moves for the shown position (the analysis board's
  // blue Stockfish pointers), as many as the Stockfish arrows setting asks for
  // (0 draws none). The reveal legend arrows are separate and unaffected.
  // Memoized on the staleness-guarded `pvLines` (a stable identity until the
  // engine commits) and the count, so a re-render that changes neither hands
  // `ChessBoard` the same array.
  const offLineArrows = useMemo(
    () => buildTrainFreePlayArrows(revealTree.pvLines, sfArrows),
    [revealTree.pvLines, sfArrows],
  );
  // Phase 237: ONE resolver picks the board overlay: a sideline, a stepped list
  // position, or the puzzle position with the focused chip's arrow lit.
  const boardOverlay = resolveRevealBoardOverlay({
    offLineArrows,
    liveLines: revealTree.pvLines,
    liveArrowCount: sfArrows,
    tree: revealTree,
    chips,
    revealOverlay,
    liveAlternatives,
    puzzleLastMove: lastMove,
  });
  const boardArrows = boardOverlay.arrows;
  const boardMarkers = boardOverlay.markers;
  const boardLastMove = boardOverlay.lastMove;
  const boardLastMoveColor = boardOverlay.lastMoveColor;

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

  // Phase 237 (D-01): a chip tap. The tree jumps the board to the puzzle position
  // with that chip's arrow lit (unless the board is already on its line); the
  // same tap hides the tour overlay so the lit arrow is readable.
  function handleChipSelect(key: RoleKey): void {
    revealTree.selectChip(key);
    hideTourOverlay();
  }

  // 190.1 UAT round 5: leaving the reveal via Analyze caches the full
  // solution state, so the browser back button restores THIS solved reveal
  // instead of the start screen (a resumed session no longer contains the
  // solved puzzle, and the grade result lives only in this page's memory).
  function handleAnalyzeClick(): void {
    // Phase 229 D-12: both Analyze buttons land here (handleAnalyzeFromReveal calls through),
    // so tracking here, before the cache-state early return, counts each click exactly once.
    trackFeature('action', { target: 'analyze' });
    const sessionId = trainSession.session?.session_id;
    if (sessionId == null || verdict === null || guess === null || lastPlayedUci === null) return;
    // Phase 236 review WR-02: an Analyze click before the instant path's background
    // grade landed (gradeResult still null) used to cache nothing, so browser Back
    // lost the solved reveal. Cache a stand-in built from the server's graded pair
    // instead. The unmount's abortGrading still ends the search, so that solve
    // sends no phone_grade (accepted gap, see the Next path in gradeInBackground).
    const cachedGrade =
      gradeResult ?? (instantGrade !== null ? gradeFromServerPair(verdict, instantGrade) : null);
    if (cachedGrade === null) return;
    saveTrainRevealCache({
      sessionId,
      puzzle,
      verdict,
      verdictBotId: verdictBot?.id,
      guess,
      playedMoveUci: lastPlayedUci,
      gradeResult: cachedGrade,
      // Phase 233: the review totals so far, so the restored reveal continues one timer.
      reviewTelemetry: puzzleTelemetry.snapshotReviewForAnalyze(),
      // Phase 237 (guardrail): the focused chip, every sideline and the exact node,
      // so Analyze -> Back lands where the user left (UCI paths, not node ids).
      revealTree: revealTree.snapshot(),
    });
  }

  // Phase 222 (D-02): a random bot hosts the puzzle, memoised per puzzle
  // (`puzzle.position` — Math.random, not seeded, not persisted; a reload may
  // recast, which D-02 accepts). Phase 237 UAT: any persona can host, and the
  // host also speaks the verdict below. Hilda is excluded unless the settings
  // confirm the first-reveal tour was already seen (still loading counts as
  // pending), since she narrates that tour herself.
  const tourMaybePending = settings?.reveal_walkthrough_seen_at == null;
  // eslint-disable-next-line react-hooks/exhaustive-deps -- `puzzle.position` is intentionally NOT read inside the callback: it exists purely to re-run the draw (a fresh Math.random) on every puzzle transition, per D-02. `tourMaybePending` is read at that moment only, so a settings load mid-puzzle never recasts the host.
  const bot = useMemo(() => pickPuzzleHost(tourMaybePending), [puzzle.position]);

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
    puzzleTelemetry.markGuess();
    setGuess(guessValue);
  }

  // Phase 233 (D-02): the prompt and drop-nudge guess buttons both land here.
  function handleGuess(guessValue: Guess): void {
    puzzleTelemetry.markGuess();
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
  // Phase 237 UAT: the bot that narrated the puzzle also gives the feedback
  // (it used to be a fresh stern/friendly draw, so a different bot answered
  // the move it had just asked for). The verdict copy is persona-independent.
  const verdictBot = useMemo<Persona | null>(() => {
    if (verdictPoints === null) return null;
    return personaForId(restoredSolve?.verdictBotId) ?? bot;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- recast exactly when `verdict` itself changes (D-03), not when `verdictPoints`/`restoredSolve`/`bot` alone are read; all are fixed per puzzle (same memo dep above / nulled or redrawn on the same puzzle transition), so this can never drift.
  }, [verdict]);
  // UAT round 4: the opener is a random draw, so it is resolved once per
  // verdict here rather than on every render inside the bubble body.
  const verdictOpening = useMemo<VerdictCopy | null>(() => {
    if (verdict === null || verdictPoints === null) return null;
    return verdictCopy(verdictPoints, verdict.correct_guess, verdict.move_quality, playedIsBest);
  }, [verdict, verdictPoints, playedIsBest]);

  function handleNextFromReveal(): void {
    // Phase 237 UAT (G-01): the bar's Next is the tour's only Next; on any tour
    // step but the last it advances the tour and the puzzle stays.
    if (walkthrough.consumeNext()) return;
    // Phase 233 (D-03): flush BEFORE anything that advances the puzzle or unmounts
    // the screen (the next puzzle's key reset must not run first, Pitfall 5).
    puzzleTelemetry.flushReviewOnNext();
    walkthrough.leave();
    handleNext();
  }
  function handleAnalyzeFromReveal(): void {
    walkthrough.leave();
    handleAnalyzeClick();
  }
  useEffect(() => {
    nextFromRevealRef.current = handleNextFromReveal;
    analyzeFromRevealRef.current = handleAnalyzeFromReveal;
  });

  const bubbleState = resolveBubbleState({
    hasVerdict: verdict !== null,
    isGrading,
    isRechecking,
    isSubmitting,
    guessMade: guess !== null,
    introStep: activeIntroStep,
    nudgeActive: nudgeNonce > 0,
  });
  const bubbleBody = renderTrainBotBubbleBody(bubbleState, {
    sideToMove: puzzle.side_to_move,
    guess,
    onGuess: handleGuess,
    suppressPrompt,
    onIntroNext: handleIntroNext,
    onIntroGuess: handleIntroGuess,
    isWarmup,
    audience,
  });
  const bubblePersona = resolveBubblePersona(
    bubbleState,
    puzzle.side_to_move,
    bot,
    verdictBot,
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
      {/* Phase 222 UAT: one compact row — "n of m", the bar, "x / y pts".
          On phones (below `sm`) the mobile header is suppressed during play,
          so the row spans only the board and the settings cogwheel takes the
          corner above the eval-bar slot (same `w-5` + `gap-2` geometry as the
          board row below). At `sm`+ the desktop nav carries its own cog. */}
      <div className="flex w-full items-center gap-2">
      <div className="flex min-w-0 flex-1 items-center gap-3">
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
        {/* The h-8 tap target overhangs the 20px slot on all sides (-my-1.5
            keeps the row at its text height, so the board is not pushed down). */}
        <div className="flex w-5 shrink-0 justify-center sm:hidden">
          <SettingsSheetButton
            testId="btn-train-settings"
            className="-my-1.5 h-8 w-8 shrink-0 text-muted-foreground"
          />
        </div>
      </div>
      <div
        ref={boardRef}
        className={cn(
          'flex w-full flex-row items-stretch gap-2',
          // Phase 222 UAT: the walkthrough's free-play step rings the board row.
          walkthroughTarget === 'board' && 'rounded-md ring-2 ring-brand-brown ring-offset-4 ring-offset-background',
        )}
      >
        <div
          className="relative min-w-0 flex-1"
          // Phase 237 UAT (G-01): any touch on the board (the overlay is
          // pointer-events-none, so a touch on it lands here too) hides the
          // tour overlay. Capture phase, so the board's own handlers
          // cannot swallow it.
          onPointerDownCapture={tourOverlay !== null ? hideTourOverlay : undefined}
        >
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
          {tourOverlay}
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
      {/* Phase 237 plan 07: the reveal's action bar in the page flow under the board
          from `sm` up (tablet and desktop; phones get the same bar in the fixed
          bottom bar through the published payload). Desktop adds the key hint. */}
      {verdict !== null && showResultRow && isSmUp && (
        <TrainRevealActionBar
          onRewind={handleRewind}
          onBack={revealGoBack}
          onForward={revealGoForward}
          onFlip={handleFlipBoard}
          canRewind={revealCanReset}
          canGoBack={revealCanGoBack}
          canGoForward={revealCanGoForward}
          analyzeTo={analyzeTo}
          onAnalyzeClick={handleBarAnalyzeClick}
          onNext={handleBarNext}
          framed
          className="w-full"
        />
      )}
      </div>
      {/* Phase 236 review WR-01 (D-15): a landed verdict is never displaced by the
          engine-error or engine-loading branches. On the instant path the verdict is
          server-final while the background grade still runs, so a Worker error (e.g. a
          wasm OOM) after the verdict used to swap the bubble, and with it the
          Solution/Analyze/Next row, for "Failed to load the grading engine" + Retry
          (whose restartEngine would re-grade an already-solved puzzle). Both branches
          now apply only while there is no verdict. */}
      {engineFailed && verdict === null ? (
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
      ) : !isReady && verdict === null ? (
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
          gradingEngine={gradingEngine}
          guess={guess}
          playedMoveUci={lastPlayedUci}
          gradeResult={gradeResult}
          instantGrade={instantGrade}
          chips={chips}
          activeChip={revealTree.activeChip}
          onChipSelect={handleChipSelect}
          treeList={<TrainMoveTreeList tree={revealTree} flipped={flipped} />}
          onGameMoveUciChange={setGameMoveUci}
          onGameMoveLineStateChange={setGameMoveLineState}
          alsoFineMoves={alsoFineMoves}
          walkthroughTarget={walkthroughTarget}
          verdictBot={verdictBot}
          verdictOpening={verdictOpening}
          isBest={playedIsBest}
          sessionDate={trainSession.session?.session_date}
          expiresOn={trainSession.session?.expires_on}
          isWarmup={isWarmup}
          audience={audience}
          onStripExpand={handleStripExpand}
        />
      )}
    </div>
  );
}
