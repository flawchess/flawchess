/**
 * BlunderCheckDrill: the board loop of one blunder-check window (Phase 249, D-12, D-13, D-18).
 *
 * Renders the pure drill reducer's window phases (`lib/blunderCheckDrill.ts`) and runs
 * the effects that feed it: the window start request, the lead-in replay ticks, the
 * feedback hold, the move + reply ticks and the per-move countdown. The window replays its
 * lead-in at a fixed pace, then shows the judged move as an arrow (the piece still on its
 * source square) and asks "Good move or blunder?". The move and the opponent's reply are only
 * played after the server graded a correct "Good". Every grade, point total and the
 * countdown length come from the server; the copy is neutral for own and foreign windows
 * (D-09), never "your move".
 *
 * No Umami event is added for blunder check (D-19).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Dispatch, ReactElement, ReactNode } from 'react';
import axios from 'axios';
import { Clock } from 'lucide-react';
import { ChessBoard } from '@/components/board/ChessBoard';
import type { BoardArrow, SquareMarker } from '@/components/board/ChessBoard';
import { BlunderCheckBetterMove } from '@/components/train/blunder-check/BlunderCheckBetterMove';
import { BlunderCheckPointsFlash } from '@/components/train/blunder-check/BlunderCheckPointsFlash';
import { BlunderCheckSolution } from '@/components/train/blunder-check/BlunderCheckSolution';
import {
  BlunderCheckStage,
  BlunderCheckStageMessage,
} from '@/components/train/blunder-check/BlunderCheckStage';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import { Button } from '@/components/ui/button';
import { LoadError } from '@/components/ui/load-error';
import { useBlunderCheckSession } from '@/hooks/useBlunderCheckSession';
import { useMoveTimer } from '@/hooks/useMoveTimer';
import type { TrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import { useWakeLock } from '@/hooks/useWakeLock';
import {
  BANK_COIN_COUNT,
  BANK_COIN_INTERVAL_MS,
  BANK_HOLD_MS,
  CLEARED_SOUND_DELAY_MS,
  COIN_SOUND_MS,
  FEEDBACK_DISPLAY_MS,
  LEAD_IN_PLY_INTERVAL_MS,
  LEAD_IN_START_DELAY_MS,
  MOVE_REPLY_DELAY_MS,
  applyUcis,
  bankingProgress,
  drillProgress,
  flashFor,
  moveSoundFor,
} from '@/lib/blunderCheckDrill';
import type {
  DrillEvent,
  DrillProgress,
  DrillState,
  DrillWindow,
  FeedbackFlash,
} from '@/lib/blunderCheckDrill';
import { prefersReducedMotion } from '@/lib/confetti';
import { saveBlunderCheckSolutionCache } from '@/lib/blunderCheckSolutionCache';
import type { CachedBlunderCheckSolution } from '@/lib/blunderCheckSolutionCache';
import { personaForId } from '@/lib/personas/personaRegistry';
import type { Persona } from '@/lib/personas/personaRegistry';
import { useMarkPlayActive } from '@/lib/playActive';
import { uciToSquares } from '@/lib/sanToSquares';
import { playSound } from '@/lib/sounds';
import { MOVE_QUALITY_BLUNDER, MOVE_QUALITY_GOOD, ZONE_DANGER } from '@/lib/theme';
import { TRAIN_PLAYED_MOVE_ARROW_WIDTH } from '@/lib/trainArrows';
import { pickPuzzleHost } from '@/lib/trainBotCopy';
import type { RevealTreeSnapshot } from '@/lib/trainRevealLines';
import type { AnswerKind, AnswerResponse } from '@/types/blunderCheck';

/** The countdown turns red, and the low-time sound plays, once this little time is left. */
const MOVE_TIMER_WARN_MS = 3000;
const MS_PER_SECOND = 1000;
const HTTP_CONFLICT = 409;
/** The `detail` of the 409 the server answers when the client's prompt is no longer the open one. */
const STALE_PROMPT_DETAIL = 'stale_prompt';

type BlunderCheckSession = ReturnType<typeof useBlunderCheckSession>;
type StartWindowAsync = BlunderCheckSession['startWindow']['mutateAsync'];
type AnswerAsync = BlunderCheckSession['answer']['mutateAsync'];
type DrillDispatch = Dispatch<DrillEvent>;
/** The phases that play the window's board loop (lead-in, prompt, grading, feedback, move + reply). */
type InWindowState = Extract<
  DrillState,
  { phase: 'lead_in' | 'prompt' | 'grading' | 'feedback' | 'advancing' }
>;
type SolutionAsync = BlunderCheckSession['solution']['mutateAsync'];

/**
 * Whether the prompted move is still to be played: it is drawn as an arrow from its
 * source square until the move is applied to the board (after a correct "Good").
 */
function showsPromptArrow(state: InWindowState): boolean {
  if (state.phase === 'lead_in') return false;
  return !(state.phase === 'advancing' && state.step === 1);
}

/**
 * The server's grade as a sound (D-12). A catch gets the Train full-score sound; a lost pot
 * (a missed blunder or a timeout that forfeits points) gets the pot's own tumble; a wrong
 * answer where no points moved, the 0-points sound. A "Good" call is silent here: its sound is
 * the coin, played as its point lands in the pot (BlunderCheckScore), like every gain's. The
 * "Good" call that clears a herring (every move called good) gets the full-score sound too, but
 * only once that last point's coin has sounded (Phase 249 UAT): the two used to play over
 * each other.
 */
function playAnswerSound(response: AnswerResponse): void {
  if (response.result === 'caught') playSound('score-full');
  else if (response.outcome === 'cleared') {
    // Without motion nothing flies, so the coin plays at once (BlunderCheckScore).
    const delay = prefersReducedMotion() ? COIN_SOUND_MS : CLEARED_SOUND_DELAY_MS;
    setTimeout(() => playSound('score-full'), delay);
  } else if (response.result === 'correct_safe') return;
  else if (response.points_forfeited > 0) playSound('pot-bust');
  else playSound('game-loss');
}

/** The pot being banked: a few coins dropping into the total, each overlapping the last. */
function playBankCoins(): void {
  for (let coin = 0; coin < BANK_COIN_COUNT; coin += 1) {
    setTimeout(() => playSound('pot-gain'), coin * BANK_COIN_INTERVAL_MS);
  }
}

/**
 * Next on a solution banks the window's pot first: the pot badge slides into the banked
 * total, which counts up, with the coins' sound; the next window loads once that is done
 * (BANK_HOLD_MS). An empty pot, or reduced motion, moves on at once.
 */
function useBankOnNext(
  state: DrillState,
  dispatch: DrillDispatch,
): { banking: boolean; handleNext: () => void } {
  // The window whose pot is being banked; cleared as the hold ends, so a later session's
  // window at the same position does not start out banking.
  const [bankingPosition, setBankingPosition] = useState<number | null>(null);
  const holdTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(
    () => () => {
      if (holdTimer.current !== null) clearTimeout(holdTimer.current);
    },
    [],
  );
  const position = state.phase === 'solution' ? state.window.position : null;
  const pot = state.phase === 'solution' ? state.window.windowPoints : 0;
  const banking = position !== null && bankingPosition === position;

  const handleNext = useCallback((): void => {
    // A second click during the hold must not skip a window.
    if (position === null || banking) return;
    if (pot > 0) playBankCoins();
    if (pot <= 0 || prefersReducedMotion()) {
      dispatch({ type: 'NEXT_WINDOW' });
      return;
    }
    setBankingPosition(position);
    holdTimer.current = setTimeout(() => {
      holdTimer.current = null;
      setBankingPosition(null);
      dispatch({ type: 'NEXT_WINDOW' });
    }, BANK_HOLD_MS);
  }, [position, pot, banking, dispatch]);

  return { banking, handleNext };
}

/** The flash to show for the graded answer, kept up through the move + reply so it can finish. */
function flashOf(state: InWindowState): FeedbackFlash | null {
  if (state.phase !== 'feedback' && state.phase !== 'advancing') return null;
  const flash = flashFor(state.graded);
  return flash.amount > 0 ? flash : null;
}

function isStalePromptError(error: unknown): boolean {
  if (!axios.isAxiosError(error) || error.response?.status !== HTTP_CONFLICT) return false;
  const data = error.response.data as { detail?: unknown } | undefined;
  return data?.detail === STALE_PROMPT_DETAIL;
}

/** Feeds the lead-in replay ticks: a start delay, then one fixed-pace tick per ply. */
function useLeadInTicks(state: DrillState, dispatch: DrillDispatch): void {
  const shownCount = state.phase === 'lead_in' ? state.window.shownUcis.length : 0;
  const active = state.phase === 'lead_in';
  useEffect(() => {
    if (!active) return;
    const delay = shownCount === 0 ? LEAD_IN_START_DELAY_MS : LEAD_IN_PLY_INTERVAL_MS;
    const timer = setTimeout(() => dispatch({ type: 'LEAD_IN_TICK' }), delay);
    return () => clearTimeout(timer);
  }, [active, shownCount, dispatch]);
}

/**
 * Holds the feedback (the answer's or the better move's), then plays the prompted move and the
 * reply at a fixed pace. After the better move the same hold hands over to the solution.
 */
function useAfterAnswerTicks(state: DrillState, dispatch: DrillDispatch): void {
  const phase = state.phase;
  const step = state.phase === 'advancing' ? state.step : 0;
  useEffect(() => {
    if (phase === 'feedback' || phase === 'better_move_feedback') {
      const timer = setTimeout(() => dispatch({ type: 'FEEDBACK_DONE' }), FEEDBACK_DISPLAY_MS);
      return () => clearTimeout(timer);
    }
    if (phase === 'advancing') {
      const timer = setTimeout(() => dispatch({ type: 'ADVANCE_TICK' }), MOVE_REPLY_DELAY_MS);
      return () => clearTimeout(timer);
    }
  }, [phase, step, dispatch]);
}

/** Loads the window the reducer waits on; a failure ends the drill in the error phase. */
function useWindowLoader(
  state: DrillState,
  dispatch: DrillDispatch,
  startWindow: StartWindowAsync,
): void {
  const loading = state.phase === 'loading_window';
  const sessionId = state.phase === 'loading_window' ? state.session.sessionId : 0;
  const position = state.phase === 'loading_window' ? state.position : 0;
  useEffect(() => {
    if (!loading) return;
    let cancelled = false;
    startWindow({ sessionId, position }).then(
      (response) => {
        if (!cancelled) dispatch({ type: 'WINDOW_LOADED', response });
      },
      () => {
        if (!cancelled) dispatch({ type: 'FAILED', message: 'Failed to start the sequence' });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [loading, sessionId, position, startWindow, dispatch]);
}

/**
 * Fetches the ended window's solution. A failure keeps the screen with a Retry: the window has
 * ended and its points are banked, so there is nothing to reset (D-14).
 */
function useSolutionLoader(
  state: DrillState,
  dispatch: DrillDispatch,
  solutionAsync: SolutionAsync,
): { failed: boolean; retry: () => void } {
  const loading = state.phase === 'solution_loading';
  const sessionId = state.phase === 'solution_loading' ? state.session.sessionId : 0;
  const position = state.phase === 'solution_loading' ? state.window.position : 0;
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!loading) return;
    let cancelled = false;
    solutionAsync({ sessionId, position }).then(
      (solution) => {
        if (!cancelled) dispatch({ type: 'SOLUTION_LOADED', solution });
      },
      () => {
        if (!cancelled) setFailed(true);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [loading, sessionId, position, attempt, solutionAsync, dispatch]);
  return {
    failed,
    retry: () => {
      setFailed(false);
      setAttempt((count) => count + 1);
    },
  };
}

interface AnswerContext {
  sessionId: number;
  position: number;
  moveIndex: number;
}

/** Server state wins: re-fetch the window after a stale prompt and resume from what it says. */
async function reloadWindow(
  { sessionId, position }: AnswerContext,
  startWindow: StartWindowAsync,
  dispatch: DrillDispatch,
): Promise<void> {
  try {
    const response = await startWindow({ sessionId, position });
    dispatch({ type: 'WINDOW_LOADED', response });
  } catch {
    dispatch({ type: 'FAILED', message: 'Failed to reload the sequence' });
  }
}

/** Posts one answer and feeds the server's grade back; a stale prompt re-fetches the window. */
async function postAnswer(
  context: AnswerContext,
  kind: AnswerKind,
  clientElapsedMs: number,
  api: { answer: AnswerAsync; startWindow: StartWindowAsync },
  dispatch: DrillDispatch,
): Promise<void> {
  try {
    const response = await api.answer({
      sessionId: context.sessionId,
      position: context.position,
      body: { move_index: context.moveIndex, answer: kind, client_elapsed_ms: clientElapsedMs },
    });
    playAnswerSound(response);
    dispatch({ type: 'ANSWER_GRADED', response });
  } catch (error) {
    if (isStalePromptError(error)) {
      await reloadWindow(context, api.startWindow, dispatch);
      return;
    }
    dispatch({ type: 'FAILED', message: 'Failed to submit the answer' });
  }
}

/** The countdown inside the bubble, with a clock icon; it keeps its place while hidden. */
function MoveTimer({
  remainingMs,
  visible,
}: {
  remainingMs: number;
  visible: boolean;
}): ReactElement {
  const warn = remainingMs <= MOVE_TIMER_WARN_MS;
  return (
    <span
      className={`flex shrink-0 items-center gap-1 font-semibold tabular-nums ${visible ? '' : 'invisible'}`}
      style={warn ? { color: ZONE_DANGER } : undefined}
      data-testid="blunder-check-timer"
    >
      <Clock className="size-4" aria-hidden="true" />
      {Math.ceil(remainingMs / MS_PER_SECOND)}s
    </span>
  );
}

/** The two answer buttons, the same width (the personalized-puzzle guess-button grid). */
function AnswerButtons({
  answerable,
  onAnswer,
}: {
  answerable: boolean;
  onAnswer: (answer: AnswerKind) => void;
}): ReactElement {
  return (
    <div className="grid grid-flow-col auto-cols-fr gap-2" data-testid="blunder-check-answer-buttons">
      <Button
        variant="brand-outline"
        className={TRAIN_BUTTON_CLASS}
        disabled={!answerable}
        onClick={() => onAnswer('safe')}
        data-testid="blunder-check-btn-safe"
      >
        Good
      </Button>
      <Button
        variant="brand-outline"
        className={TRAIN_BUTTON_CLASS}
        disabled={!answerable}
        onClick={() => onAnswer('blunder')}
        data-testid="blunder-check-btn-blunder"
      >
        Blunder
      </Button>
    </div>
  );
}

/**
 * Plays the move sound for each ply the window puts on the board (the lead-in replay, the
 * prompted move and the reply). Only a single-ply step sounds: a resumed window lands with
 * its plies already played.
 */
function useMoveSounds(window: DrillWindow): void {
  const previous = useRef<{ position: number; count: number } | null>(null);
  useEffect(() => {
    const count = window.shownUcis.length;
    const before = previous.current;
    previous.current = { position: window.position, count };
    if (before === null || before.position !== window.position || count !== before.count + 1) {
      return;
    }
    const uci = window.shownUcis[count - 1];
    if (uci === undefined) return;
    const sound = moveSoundFor(applyUcis(window.startFen, window.shownUcis.slice(0, -1)), uci);
    if (sound !== null) playSound(sound);
  }, [window]);
}

/**
 * The wait for a window's solution, with the window's last position still on the board, so
 * the board does not vanish and come back between the drill and its solution (Phase 249 UAT).
 */
function SolutionLoadingView({
  state,
  progress,
  children,
}: {
  state: Extract<DrillState, { phase: 'solution_loading' }>;
  progress: DrillProgress;
  children: ReactNode;
}): ReactElement {
  const { window } = state;
  const fen = useMemo(
    () => applyUcis(window.startFen, window.shownUcis),
    [window.startFen, window.shownUcis],
  );
  const lastUci = window.shownUcis[window.shownUcis.length - 1];
  return (
    <BlunderCheckStage
      progress={progress}
      testId="blunder-check-solution-loading-stage"
      renderBoard={(boardMaxWidthPx) => (
        <ChessBoard
          position={fen}
          flipped={window.orientation === 'black'}
          lastMove={uciToSquares(lastUci ?? null)}
          onPieceDrop={() => false}
          maxWidth={boardMaxWidthPx}
          id="chessboard"
        />
      )}
    >
      {children}
    </BlunderCheckStage>
  );
}

function WindowView({
  state,
  progress,
  persona,
  remainingMs,
  onAnswer,
}: {
  state: InWindowState;
  progress: DrillProgress;
  persona: Persona;
  remainingMs: number;
  onAnswer: (answer: AnswerKind) => void;
}): ReactElement {
  const { window, prompt } = state;
  useMoveSounds(window);
  const fen = useMemo(
    () => applyUcis(window.startFen, window.shownUcis),
    [window.startFen, window.shownUcis],
  );
  const lastUci = window.shownUcis[window.shownUcis.length - 1];
  const lastMove = uciToSquares(lastUci ?? null);
  // Null once the prompted move is on the board (and for a malformed UCI): no arrow, no badge.
  const promptSquares = showsPromptArrow(state) ? uciToSquares(prompt.move_uci) : null;
  const arrows: BoardArrow[] = promptSquares !== null
    ? [
        {
          startSquare: promptSquares.from,
          endSquare: promptSquares.to,
          // Hatched good green and blunder red: which of the two is the question.
          color: MOVE_QUALITY_GOOD,
          hatchColor: MOVE_QUALITY_BLUNDER,
          width: TRAIN_PLAYED_MOVE_ARROW_WIDTH,
          layerKey: 'prompt',
          // Flashes twice as it appears, then stays: this is the move being asked about.
          isFlashIn: !prefersReducedMotion(),
        },
      ]
    : [];
  // The same question as a badge on the move's target square, where a graded move
  // carries its quality badge.
  const squareMarkers: SquareMarker[] = promptSquares !== null
    ? [{ square: promptSquares.to, goodOrBlunder: true }]
    : [];
  const flash = flashOf(state);
  // A piece moved while the question is open: the board stays locked, and the bubble shakes
  // with a golden border (the personalized-puzzle drop nudge) to point at the buttons.
  const promptKey = `${window.position}:${prompt.move_index}`;
  const [nudge, setNudge] = useState<{ promptKey: string; nonce: number } | null>(null);
  const nudgeNonce = nudge !== null && nudge.promptKey === promptKey ? nudge.nonce : 0;
  const nudged = state.phase === 'prompt' && nudgeNonce > 0;
  const handlePieceDrop = (): boolean => {
    // No moves during the drill: the user only rates the arrow.
    if (state.phase === 'prompt') setNudge({ promptKey, nonce: nudgeNonce + 1 });
    return false;
  };
  const timerVisible = state.phase === 'lead_in' || state.phase === 'prompt';

  return (
    <BlunderCheckStage
      progress={progress}
      testId="blunder-check-window"
      renderBoard={(boardMaxWidthPx) => (
        <>
          <ChessBoard
            position={fen}
            flipped={window.orientation === 'black'}
            lastMove={lastMove}
            arrows={arrows}
            squareMarkers={squareMarkers}
            onPieceDrop={handlePieceDrop}
            maxWidth={boardMaxWidthPx}
            id="chessboard"
          />
          {flash !== null && (
            <BlunderCheckPointsFlash
              key={promptKey}
              amount={flash.amount}
              variant={flash.variant}
            />
          )}
        </>
      )}
    >
      {/* The question, the countdown and the answer buttons in the host's speech bubble
          (the personalized-puzzle chat row). */}
      <TrainBotBubble
        persona={persona}
        state={nudged ? 'drop-nudge' : 'prompt'}
        nudgeNonce={nudgeNonce}
        actions={<AnswerButtons answerable={state.phase === 'prompt'} onAnswer={onAnswer} />}
      >
        <div className="flex items-center justify-between gap-3" data-testid="blunder-check-prompt">
          <p>Good move or blunder?</p>
          <MoveTimer remainingMs={remainingMs} visible={timerVisible} />
        </div>
      </TrainBotBubble>
    </BlunderCheckStage>
  );
}

/** The timer key of the prompt on screen, stable through grading and feedback. */
function promptKeyOf(state: DrillState): string {
  if (!('window' in state) || !('prompt' in state)) return 'none';
  return `${state.window.position}:${state.prompt.move_index}`;
}

/**
 * The answer handler plus the per-move countdown. The countdown runs only in the prompt phase
 * (after the lead-in, or after feedback and the move + reply animation) and is as long as
 * the server's timer_remaining_ms, so a reload never buys time (D-13, D-18).
 */
function useAnswering(
  state: DrillState,
  dispatch: DrillDispatch,
  api: { answer: AnswerAsync; startWindow: StartWindowAsync },
): { remainingMs: number; handleAnswer: (answer: AnswerKind) => void } {
  // The moment the prompt phase began, for the client_elapsed_ms the server records.
  const promptStartedAt = useRef(0);
  const promptKey = promptKeyOf(state);
  const inPrompt = state.phase === 'prompt';
  useEffect(() => {
    if (!inPrompt) return;
    promptStartedAt.current = performance.now();
    // The judged move's arrow has just appeared: the question sound (Phase 249 UAT; it
    // used to sound like a move, as the lead-in's plies do).
    playSound('question');
  }, [inPrompt, promptKey]);
  // A synchronous guard: the phase flips a render after the click, so a fast double click
  // (or a click racing the timeout) would otherwise post two answers.
  const answerInFlight = useRef(false);

  const handleAnswer = useCallback(
    (kind: AnswerKind): void => {
      if (state.phase !== 'prompt' || answerInFlight.current) return;
      answerInFlight.current = true;
      const context: AnswerContext = {
        sessionId: state.session.sessionId,
        position: state.window.position,
        moveIndex: state.prompt.move_index,
      };
      const clientElapsedMs = Math.round(performance.now() - promptStartedAt.current);
      dispatch({ type: 'ANSWER_SUBMITTED', answer: kind });
      postAnswer(context, kind, clientElapsedMs, api, dispatch).finally(() => {
        answerInFlight.current = false;
      });
    },
    [state, dispatch, api],
  );

  const timerMs = state.phase === 'lead_in' || state.phase === 'prompt' ? state.timerMs : 0;
  const { remainingMs } = useMoveTimer({
    durationMs: timerMs,
    running: inPrompt,
    promptKey,
    onTimeout: () => handleAnswer('timeout'),
  });

  // The low-time warning, once per prompt, as the countdown reaches its last seconds.
  const lowTime = inPrompt && remainingMs > 0 && remainingMs <= MOVE_TIMER_WARN_MS;
  const lowTimeSoundedFor = useRef<string | null>(null);
  useEffect(() => {
    if (!lowTime || lowTimeSoundedFor.current === promptKey) return;
    lowTimeSoundedFor.current = promptKey;
    playSound('low-time');
  }, [lowTime, promptKey]);

  return { remainingMs, handleAnswer };
}

function SolutionLoading({
  failed,
  onRetry,
}: {
  failed: boolean;
  onRetry: () => void;
}): ReactElement {
  if (!failed) {
    return (
      <p
        className="text-center text-sm text-muted-foreground"
        data-testid="blunder-check-solution-loading"
      >
        Loading solution...
      </p>
    );
  }
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4" data-testid="blunder-check-solution-error">
      <LoadError resource="the solution" />
      <Button variant="brand-outline" onClick={onRetry} data-testid="blunder-check-btn-retry-solution">
        Retry
      </Button>
    </div>
  );
}

export function BlunderCheckDrill({
  state,
  dispatch,
  session,
  engine,
  restored,
}: {
  state: DrillState;
  dispatch: DrillDispatch;
  session: BlunderCheckSession;
  /** The session-scoped grading engine owned by the tab (better-move grading and solution lines). */
  engine: TrainGradingEngine;
  /** The solution the tab mounted into after Analyze -> Back, else null. */
  restored: CachedBlunderCheckSolution | null;
}): ReactElement | null {
  // Suppress the mobile app header while the drill is on screen (same pattern as
  // TrainSolveScreen); the wake lock keeps the phone awake through the countdowns.
  useMarkPlayActive();
  useWakeLock();

  // mutateAsync is stable across renders, so these are safe effect dependencies.
  const startWindowAsync = session.startWindow.mutateAsync;
  const answerAsync = session.answer.mutateAsync;
  const api = useMemo(
    () => ({ answer: answerAsync, startWindow: startWindowAsync }),
    [answerAsync, startWindowAsync],
  );

  useWindowLoader(state, dispatch, startWindowAsync);
  useLeadInTicks(state, dispatch);
  useAfterAnswerTicks(state, dispatch);
  const { remainingMs, handleAnswer } = useAnswering(state, dispatch, api);
  const solutionLoader = useSolutionLoader(state, dispatch, session.solution.mutateAsync);
  const { banking, handleNext } = useBankOnNext(state, dispatch);

  // A random bot hosts each window (the personalized-puzzle host draw, without the tour's
  // narrator); it asks the question, takes the better move and gives the solution.
  const hostKey = 'window' in state ? state.window.position : null;
  // eslint-disable-next-line react-hooks/exhaustive-deps -- `hostKey` is not read inside: it only re-runs the random draw for each new window.
  const drawnPersona = useMemo(() => pickPuzzleHost(true), [hostKey]);
  // A solution restored after Analyze -> Back keeps the host that gave it (and its move tree).
  const restoredHere =
    restored !== null && state.phase === 'solution' && state.solution === restored.state.solution
      ? restored
      : null;
  const persona = personaForId(restoredHere?.personaId) ?? drawnPersona;

  // Leaving through Analyze caches the solution on screen, so the browser's Back lands on it
  // again instead of the start screen (the personalized-puzzle behaviour).
  const handleAnalyze = useCallback(
    (revealTree?: RevealTreeSnapshot): void => {
      if (state.phase !== 'solution') return;
      saveBlunderCheckSolutionCache({ state, personaId: persona.id, revealTree });
    },
    [state, persona.id],
  );

  const liveProgress = drillProgress(state);
  if (liveProgress === null) return null;
  const progress: DrillProgress = banking ? bankingProgress(liveProgress) : liveProgress;

  switch (state.phase) {
    case 'loading_window':
      return (
        <BlunderCheckStageMessage progress={progress}>
          <p className="text-center text-sm text-muted-foreground" data-testid="blunder-check-loading">
            Loading sequence...
          </p>
        </BlunderCheckStageMessage>
      );
    case 'lead_in':
    case 'prompt':
    case 'grading':
    case 'feedback':
    case 'advancing':
      return (
        <WindowView
          state={state}
          progress={progress}
          persona={persona}
          remainingMs={remainingMs}
          onAnswer={handleAnswer}
        />
      );
    case 'better_move':
    case 'better_move_grading':
    case 'better_move_feedback':
      return (
        <BlunderCheckBetterMove
          key={state.window.position}
          state={state}
          progress={progress}
          persona={persona}
          dispatch={dispatch}
          betterMove={session.betterMove.mutateAsync}
          engine={engine}
        />
      );
    case 'solution_loading':
      return (
        <SolutionLoadingView state={state} progress={progress}>
          <SolutionLoading failed={solutionLoader.failed} onRetry={solutionLoader.retry} />
        </SolutionLoadingView>
      );
    case 'solution':
      return (
        <BlunderCheckSolution
          key={state.window.position}
          solution={state.solution}
          orientation={state.window.orientation}
          progress={progress}
          persona={persona}
          onNext={handleNext}
          engine={engine}
          onAnalyze={handleAnalyze}
          restoredTree={restoredHere?.revealTree ?? null}
        />
      );
    default:
      // finishing renders in the tab (idle, session_end and error have no progress).
      return null;
  }
}
