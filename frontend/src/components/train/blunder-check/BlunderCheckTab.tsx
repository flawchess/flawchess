/**
 * BlunderCheckTab: the beta-only "Blunder check" Train tab (Phase 249, D-01).
 *
 * The session host: it owns the drill reducer (`lib/blunderCheckDrill.ts`), shows the
 * start screen while the drill is idle. The board loop, timer and solution render in the
 * drill area, each with the progress row (window counter, bar, the server's points) on top
 * of the board; the end screen replaces it.
 *
 * Mounted only for beta users (Train.tsx redirects everyone else), and nothing here
 * tracks an Umami event: the tab is URL-routed and sessions live in the database
 * (D-19).
 */

import { useEffect, useReducer, useRef, useState } from 'react';
import type { Dispatch, ReactElement } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { LoadError } from '@/components/ui/load-error';
import { TRAIN_CTA_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { BlunderCheckDrill } from '@/components/train/blunder-check/BlunderCheckDrill';
import { BlunderCheckEndScreen } from '@/components/train/blunder-check/BlunderCheckEndScreen';
import { BlunderCheckStageMessage } from '@/components/train/blunder-check/BlunderCheckStage';
import { useBlunderCheckSession } from '@/hooks/useBlunderCheckSession';
import { useTrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import { drillProgress, drillReducer, initialDrillState } from '@/lib/blunderCheckDrill';
import {
  clearBlunderCheckSolutionCache,
  readBlunderCheckSolutionCache,
} from '@/lib/blunderCheckSolutionCache';
import type { DrillEvent, DrillState } from '@/lib/blunderCheckDrill';
import { unlockAudio } from '@/lib/sounds';
import type { BlunderCheckSessionResponse, SessionResultResponse } from '@/types/blunderCheck';

const HTTP_CONFLICT = 409;

/** The phases that take over the page (the tab bar and medal host are hidden). */
const IMMERSIVE_PHASES: ReadonlySet<DrillState['phase']> = new Set([
  // loading_window is immersive too, so the tab bar does not flash between two windows.
  'loading_window',
  'lead_in',
  'prompt',
  'grading',
  'feedback',
  'advancing',
  'better_move',
  'better_move_grading',
  'better_move_feedback',
  'solution_loading',
  'solution',
]);

interface StartScreenProps {
  isLoading: boolean;
  isError: boolean;
  /** The caller's open session, null when there is none. */
  openSession: BlunderCheckSessionResponse | null;
  isStarting: boolean;
  composeError: unknown;
  onStart: () => void;
}

function StartScreen({
  isLoading,
  isError,
  openSession,
  isStarting,
  composeError,
  onStart,
}: StartScreenProps): ReactElement {
  const composeFailed = composeError !== null && composeError !== undefined;
  const nothingComposable =
    axios.isAxiosError(composeError) && composeError.response?.status === HTTP_CONFLICT;
  return (
    <div
      className="mx-auto flex w-full max-w-md flex-col gap-4"
      data-testid="blunder-check-start-screen"
    >
      <h2 className="text-lg font-semibold">Blunder check</h2>
      <p className="text-sm text-muted-foreground">
        Check each move before it is played: Good move or blunder?
      </p>
      <p className="text-sm text-muted-foreground" data-testid="blunder-check-pot-rule">
        Every correct Good call adds a point to the pot. Miss the blunder, or run out of time,
        and the pot is lost.
      </p>
      {openSession?.current_position != null && (
        <p className="text-sm" data-testid="blunder-check-open-session">
          Session in progress: sequence {openSession.current_position + 1} of{' '}
          {openSession.window_count}
        </p>
      )}
      {isError && <LoadError resource="blunder check" data-testid="blunder-check-load-error" />}
      {nothingComposable && (
        <p className="text-sm text-muted-foreground" data-testid="blunder-check-none-available">
          No blunder-check sequences are available yet. Import and analyze more games, then try
          again.
        </p>
      )}
      {composeFailed && !nothingComposable && (
        <LoadError resource="blunder check" data-testid="blunder-check-compose-error" />
      )}
      {!isError && (
        <Button
          variant="default"
          className={TRAIN_CTA_BUTTON_CLASS}
          disabled={isLoading || isStarting}
          onClick={onStart}
          data-testid="blunder-check-btn-start"
        >
          {openSession !== null ? 'Resume' : 'Start'}
        </Button>
      )}
    </div>
  );
}

/**
 * Finishes the session when the reducer reaches 'finishing' (after the last window's Next,
 * or on a resume where every window had already ended). The server answers the same result
 * again if it was already finished, so a retry (or a dev-mode effect re-run) is safe.
 */
function useFinishSession(
  state: DrillState,
  dispatch: Dispatch<DrillEvent>,
  finishAsync: (sessionId: number) => Promise<SessionResultResponse>,
): { failed: boolean; retry: () => void } {
  const finishing = state.phase === 'finishing';
  const sessionId = state.phase === 'finishing' ? state.session.sessionId : 0;
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!finishing) return;
    let cancelled = false;
    setFailed(false);
    finishAsync(sessionId).then(
      (result) => {
        if (!cancelled) dispatch({ type: 'SESSION_FINISHED', result });
      },
      () => {
        if (!cancelled) setFailed(true);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [finishing, sessionId, attempt, finishAsync, dispatch]);
  return { failed, retry: () => setAttempt((count) => count + 1) };
}

function FinishingView({ failed, onRetry }: { failed: boolean; onRetry: () => void }): ReactElement {
  if (!failed) {
    return (
      <p className="text-center text-sm text-muted-foreground" data-testid="blunder-check-finishing">
        Finishing session...
      </p>
    );
  }
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4" data-testid="blunder-check-finish-error">
      <p className="text-sm text-muted-foreground" data-testid="blunder-check-finish-error-copy">
        Failed to finish the session. Something went wrong. Please try again in a moment.
      </p>
      <Button
        variant="brand-outline"
        className={TRAIN_CTA_BUTTON_CLASS}
        onClick={onRetry}
        data-testid="blunder-check-btn-retry"
      >
        Retry
      </Button>
    </div>
  );
}

export function BlunderCheckTab({
  onImmersiveChange,
}: {
  onImmersiveChange: (immersive: boolean) => void;
}): ReactElement {
  // Analyze -> browser Back: a cached solution, read once at mount. The drill mounts straight
  // into it (immersive from the first paint) instead of the start screen.
  const [restored] = useState(readBlunderCheckSolutionCache);
  const [state, dispatch] = useReducer(
    drillReducer,
    restored,
    (cached): DrillState => cached?.state ?? initialDrillState,
  );
  const session = useBlunderCheckSession();
  const { openSession, compose } = session;
  // The cache lives only while its solution is on screen: Next, a reset or an error drops it.
  const onSolution = state.phase === 'solution';
  useEffect(() => {
    if (!onSolution) clearBlunderCheckSolutionCache();
  }, [onSolution]);
  // A restored solution must belong to the caller's open session (a stale entry from an
  // older session, or another account in the same browser tab, falls back to the start screen).
  const restoredSessionId =
    restored !== null && state.phase === 'solution' && state.solution === restored.state.solution
      ? restored.state.session.sessionId
      : null;
  const openSessionId = openSession.isSuccess ? (openSession.data?.session_id ?? null) : undefined;
  useEffect(() => {
    if (restoredSessionId === null || openSessionId === undefined) return;
    if (openSessionId !== restoredSessionId) dispatch({ type: 'RESET' });
  }, [restoredSessionId, openSessionId]);
  // One grading Worker for the whole session, created only once the drill has started (a tab
  // visit before Start constructs none): it grades off-key better moves and searches the
  // solution lines.
  const gradingEngine = useTrainGradingEngine({ enabled: state.phase !== 'idle' });
  const finishSession = useFinishSession(state, dispatch, session.finish.mutateAsync);
  // A synchronous guard: `compose.isPending` only flips after the next render, so a fast
  // double click would otherwise send two requests (T-249-29).
  const startInFlight = useRef(false);

  const immersive = IMMERSIVE_PHASES.has(state.phase);
  useEffect(() => {
    onImmersiveChange(immersive);
    return () => onImmersiveChange(false);
  }, [immersive, onImmersiveChange]);

  function handleStart(): void {
    if (startInFlight.current) return;
    startInFlight.current = true;
    // The lead-in's move sounds play from timers, not from a tap: unlock audio in this one.
    unlockAudio();
    compose.mutate(undefined, {
      onSuccess: (session) => dispatch({ type: 'SESSION_READY', session }),
      onSettled: () => {
        startInFlight.current = false;
      },
    });
  }

  if (state.phase === 'error') {
    return (
      <div className="mx-auto flex w-full max-w-md flex-col gap-4" data-testid="blunder-check-error">
        <LoadError resource="blunder check" />
        <Button
          variant="brand-outline"
          className={TRAIN_CTA_BUTTON_CLASS}
          onClick={() => {
            dispatch({ type: 'RESET' });
            // Bug fix (Phase 249 review): the start screen showed the progress fetched when
            // the session was composed ("sequence 1 of N") after a failure mid-session.
            void session.refreshOpenSession();
          }}
          data-testid="blunder-check-btn-reset"
        >
          Back to start
        </Button>
      </div>
    );
  }

  if (state.phase === 'idle') {
    return (
      <StartScreen
        isLoading={openSession.isPending}
        isError={openSession.isError}
        openSession={openSession.data ?? null}
        isStarting={compose.isPending}
        composeError={compose.error}
        onStart={handleStart}
      />
    );
  }

  if (state.phase === 'session_end') {
    return (
      <BlunderCheckEndScreen result={state.result} onDone={() => dispatch({ type: 'RESET' })} />
    );
  }

  const progress = drillProgress(state);
  return (
    <div className="flex w-full flex-col gap-4" data-testid="blunder-check-session">
      {state.phase === 'finishing' && progress !== null && (
        <BlunderCheckStageMessage progress={progress}>
          <FinishingView failed={finishSession.failed} onRetry={finishSession.retry} />
        </BlunderCheckStageMessage>
      )}
      <div data-testid="blunder-check-drill-area">
        <BlunderCheckDrill
          state={state}
          dispatch={dispatch}
          session={session}
          engine={gradingEngine}
          restored={restored}
        />
      </div>
    </div>
  );
}
