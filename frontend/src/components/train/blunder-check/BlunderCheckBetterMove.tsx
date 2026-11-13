/**
 * BlunderCheckBetterMove: the "Find a better move" step after a caught blunder (Phase 249, D-12, D-17).
 *
 * The board returns to the pre-blunder position and the user plays a better move (drag-drop or
 * click-click). The move is graded like a personalized puzzle: the key move and the moves the
 * server graded itself are posted at once (the server decides those, D-17); any other move is
 * graded by the session's browser engine against the server key, and the phone's tier rides
 * along as `client_tier`. The points shown are always the server's response (Pitfall 13), with
 * the Train point sounds.
 *
 * A grading failure never leaves a silent spinner: "Couldn't check your move." with a Retry
 * that re-grades the same move (TrainSolveScreen precedent: restart a dead engine first and
 * re-issue the anchor search only once it is back).
 *
 * Known behavior: a reload during this step resumes on the next window, so this better move
 * earns nothing (the same spirit as D-18's "a slow reload usually counts as a timeout").
 *
 * No Umami event is added for blunder check (D-19).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Dispatch, ReactElement } from 'react';
import { Chess } from 'chess.js';
import { ChessBoard } from '@/components/board/ChessBoard';
import { BlunderCheckPointsFlash } from '@/components/train/blunder-check/BlunderCheckPointsFlash';
import { BlunderCheckStage } from '@/components/train/blunder-check/BlunderCheckStage';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import { TrainScoreChip } from '@/components/train/TrainVerdictDetails';
import { Button } from '@/components/ui/button';
import type { useBlunderCheckSession } from '@/hooks/useBlunderCheckSession';
import type { TrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import { moveSoundFor, serverDecidedTier } from '@/lib/blunderCheckDrill';
import type { DrillEvent, DrillProgress, DrillState } from '@/lib/blunderCheckDrill';
import { uciToSquares } from '@/lib/sanToSquares';
import { buildTrainRevealOverlay } from '@/lib/trainArrows';
import type { Persona } from '@/lib/personas/personaRegistry';
import { playSound } from '@/lib/sounds';
import type { SoundEvent } from '@/lib/sounds';
import type { BetterMoveTask, BetterMoveTier } from '@/types/blunderCheck';

type DrillDispatch = Dispatch<DrillEvent>;
type BetterMoveAsync = ReturnType<typeof useBlunderCheckSession>['betterMove']['mutateAsync'];
type BetterMoveState = Extract<
  DrillState,
  { phase: 'better_move' | 'better_move_grading' | 'better_move_feedback' }
>;

/** The better move's tier as a sound: the Train point sounds, the 0-points sound for a miss (D-12). */
const SOUND_BY_TIER: Record<BetterMoveTier, SoundEvent> = {
  good: 'score-full',
  inaccuracy: 'score-partial',
  wrong: 'game-loss',
};

/** What the user is told about the graded better move (neutral: own and foreign windows alike). */
const TIER_FEEDBACK_COPY: Record<BetterMoveTier, string> = {
  good: 'Good move',
  inaccuracy: 'Decent move',
  wrong: 'Not a better move',
};

interface PlayedMove {
  from: string;
  to: string;
  fen: string;
}

/** The move on `fen` from `from` to `to` (auto-queen), or null when it is illegal. */
function legalMove(fen: string, from: string, to: string): { uci: string; played: PlayedMove } | null {
  const chess = new Chess(fen);
  try {
    const move = chess.move({ from, to, promotion: 'q' });
    const uci = `${move.from}${move.to}${move.promotion ?? ''}`;
    return { uci, played: { from: move.from, to: move.to, fen: chess.fen() } };
  } catch {
    return null;
  }
}

/** The server's tier when it decides this move, else the browser engine's reading; throws on a grading failure. */
async function tierFor(
  task: BetterMoveTask,
  playedUci: string,
  gradeMove: TrainGradingEngine['gradeMove'],
): Promise<BetterMoveTier> {
  const decided = serverDecidedTier(task, playedUci);
  if (decided !== null) return decided;
  const result = await gradeMove(task.fen, playedUci);
  return result.moveTier;
}

interface SubmitContext {
  sessionId: number;
  position: number;
  task: BetterMoveTask;
}

/** Grades one better move and posts it; a grading failure is reported, a post failure ends the drill. */
async function gradeAndPost(
  context: SubmitContext,
  playedUci: string,
  api: { betterMove: BetterMoveAsync; gradeMove: TrainGradingEngine['gradeMove'] },
  dispatch: DrillDispatch,
  onGradeFailed: () => void,
): Promise<void> {
  let tier: BetterMoveTier;
  try {
    tier = await tierFor(context.task, playedUci, api.gradeMove);
  } catch {
    onGradeFailed();
    return;
  }
  try {
    const response = await api.betterMove({
      sessionId: context.sessionId,
      position: context.position,
      body: { played_uci: playedUci, client_tier: tier },
    });
    playSound(SOUND_BY_TIER[response.tier]);
    dispatch({ type: 'BETTER_MOVE_GRADED', response });
  } catch {
    dispatch({ type: 'FAILED', message: 'Failed to submit the better move' });
  }
}

/**
 * The better-move grading flow: the anchor search on entry, the grade-and-post run for a move,
 * and the retry. Returns the drop handler, the failure flag and the retry action.
 */
function useBetterMoveGrading(
  state: BetterMoveState,
  dispatch: DrillDispatch,
  betterMove: BetterMoveAsync,
  engine: TrainGradingEngine,
  onMovePlayed: (played: PlayedMove) => void,
): { handleDrop: (from: string, to: string) => boolean; gradeFailed: boolean; retry: () => void } {
  const { startGrading, gradeMove, restartEngine, hasError } = engine;
  const { task } = state;
  const [gradeFailed, setGradeFailed] = useState(false);
  const [retryNonce, setRetryNonce] = useState(0);
  const lastRetryRef = useRef(0);
  // A synchronous guard: the phase flips a render after the drop, and a retry must not race a run.
  const inFlight = useRef(false);
  const sessionId = state.session.sessionId;
  const position = state.window.position;
  const playedUci = state.phase === 'better_move_grading' ? state.playedUci : null;

  // The think-time anchor search of the key move, once per window. Never aborted on unmount:
  // the solution screen's line searches queue behind it through the engine's stop/queue.
  useEffect(() => {
    startGrading(task.fen, task.key_uci);
  }, [startGrading, task.fen, task.key_uci]);

  const run = useCallback(
    (uci: string): void => {
      if (inFlight.current) return;
      inFlight.current = true;
      const context: SubmitContext = { sessionId, position, task };
      gradeAndPost(context, uci, { betterMove, gradeMove }, dispatch, () => setGradeFailed(true)).finally(
        () => {
          inFlight.current = false;
        },
      );
    },
    [sessionId, position, task, betterMove, gradeMove, dispatch],
  );

  const handleDrop = (from: string, to: string): boolean => {
    if (state.phase !== 'better_move') return false;
    const move = legalMove(task.fen, from, to);
    if (move === null) return false;
    const sound = moveSoundFor(task.fen, move.uci);
    if (sound !== null) playSound(sound);
    onMovePlayed(move.played);
    dispatch({ type: 'BETTER_MOVE_SUBMITTED', playedUci: move.uci });
    run(move.uci);
    return true;
  };

  // A retry re-issues the anchor search and the grading of the same move. After an engine
  // failure the Worker is restarted first and `hasError` clears only once the new one is up,
  // so the re-issue waits for that (an inline call raced the stale Worker, see TrainSolveScreen).
  useEffect(() => {
    if (retryNonce === 0 || lastRetryRef.current === retryNonce) return;
    if (hasError || playedUci === null) return;
    lastRetryRef.current = retryNonce;
    startGrading(task.fen, task.key_uci);
    run(playedUci);
  }, [retryNonce, hasError, playedUci, startGrading, task.fen, task.key_uci, run]);

  const retry = (): void => {
    setGradeFailed(false);
    if (hasError) restartEngine();
    setRetryNonce((nonce) => nonce + 1);
  };

  return { handleDrop, gradeFailed, retry };
}

/** The bubble's copy and, after a grading failure, its Retry action. */
function betterMoveBubble(
  state: BetterMoveState,
  gradeFailed: boolean,
  onRetry: () => void,
): { copy: ReactElement; actions?: ReactElement } {
  if (state.phase === 'better_move_feedback') {
    return {
      copy: (
        <p data-testid="blunder-check-better-move-feedback">
          {TIER_FEEDBACK_COPY[state.betterMove.tier]}
        </p>
      ),
    };
  }
  if (state.phase === 'better_move_grading' && gradeFailed) {
    return {
      copy: <p data-testid="blunder-check-grade-error">Couldn&apos;t check your move.</p>,
      actions: (
        <Button
          variant="brand-outline"
          className={TRAIN_BUTTON_CLASS}
          onClick={onRetry}
          data-testid="blunder-check-btn-retry-grade"
        >
          Retry
        </Button>
      ),
    };
  }
  if (state.phase === 'better_move_grading') {
    return {
      copy: <p data-testid="blunder-check-better-move-checking">Checking your move...</p>,
    };
  }
  // The catch is acknowledged with the server's points for it, the same "+N" pill as the
  // solution verdict, before the user is asked for more (Phase 249 UAT).
  return {
    copy: (
      <p data-testid="blunder-check-better-move-prompt">
        Good call!{' '}
        <TrainScoreChip points={state.graded.points_awarded} testid="blunder-check-pill-catch" /> Now
        find a better move.
      </p>
    ),
  };
}

export function BlunderCheckBetterMove({
  state,
  progress,
  persona,
  dispatch,
  betterMove,
  engine,
}: {
  state: BetterMoveState;
  progress: DrillProgress;
  /** The window's host, speaking the bubble under the board. */
  persona: Persona;
  dispatch: DrillDispatch;
  betterMove: BetterMoveAsync;
  engine: TrainGradingEngine;
}): ReactElement {
  const [played, setPlayed] = useState<PlayedMove | null>(null);
  const { handleDrop, gradeFailed, retry } = useBetterMoveGrading(
    state,
    dispatch,
    betterMove,
    engine,
    setPlayed,
  );
  // Before the user moves, the squares of the move that led here are lit as on any board.
  // The caught blunder was never played, so that is the last move the window showed.
  const previousMove = uciToSquares(
    state.window.shownUcis[state.window.shownUcis.length - 1] ?? null,
  );
  // The caught blunder stays marked while the user looks for a better move, drawn exactly as
  // the solution screen draws the game move: the thin white arrow with the blunder badge.
  const blunderUci = state.prompt.move_uci;
  const blunderOverlay = useMemo(
    () =>
      buildTrainRevealOverlay('herring', [], null, null, { uci: blunderUci, quality: 'blunder' }, true),
    [blunderUci],
  );
  const flashAmount = state.phase === 'better_move_feedback' ? state.betterMove.points_awarded : null;
  const bubble = betterMoveBubble(state, gradeFailed, retry);

  return (
    <BlunderCheckStage
      progress={progress}
      testId="blunder-check-better-move"
      renderBoard={(boardMaxWidthPx) => (
        <>
          <ChessBoard
            position={played?.fen ?? state.task.fen}
            flipped={state.window.orientation === 'black'}
            lastMove={played === null ? previousMove : { from: played.from, to: played.to }}
            // Gone once the user moves: the arrow belongs to the pre-blunder position.
            arrows={played === null ? blunderOverlay.arrows : []}
            squareMarkers={played === null ? blunderOverlay.markers : []}
            onPieceDrop={handleDrop}
            maxWidth={boardMaxWidthPx}
            id="chessboard"
          />
          {flashAmount !== null && (
            // A +0 shows too: the better-move step always tells the user what it was worth.
            <BlunderCheckPointsFlash amount={flashAmount} variant="gain" />
          )}
        </>
      )}
    >
      <TrainBotBubble persona={persona} state="move" actions={bubble.actions}>
        {bubble.copy}
      </TrainBotBubble>
    </BlunderCheckStage>
  );
}
