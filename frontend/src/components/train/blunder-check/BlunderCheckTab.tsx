/**
 * BlunderCheckTab: the blunder-check drill host, mounted by the Train page under Today
 * (Phase 251 D-18, D-20). There is no start screen and no beta gate: the Today card's
 * Start button mounts this host, which composes (or resumes) the session on mount.
 *
 * It owns the drill reducer (`lib/blunderCheckDrill.ts`). The board loop, timer and
 * solution render in the drill area, each with the progress row (window counter, bar,
 * the server's points) on top of the board; the end screen replaces it. `onExit` hands
 * control back to the page, which unmounts the host and shows the Today card again (the
 * end screen's Done, the error and "nothing available" Back buttons, and a stale
 * restored solution).
 *
 * The only Umami event here is the level step's option-change: the level is a settings row
 * overwritten in place, so the event is the only record of the change. Sessions live in the
 * database and send nothing (D-19).
 *
 * One-time level step (D-20): when the progress says a level is needed, the host shows the level
 * step instead of composing, saves the pick, and composes only after the save succeeded.
 */

import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import type { Dispatch, ReactElement } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { LoadError } from '@/components/ui/load-error';
import { TRAIN_CTA_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { BlunderCheckDrill } from '@/components/train/blunder-check/BlunderCheckDrill';
import { BlunderCheckEndScreen } from '@/components/train/blunder-check/BlunderCheckEndScreen';
import { BlunderCheckLevelStep } from '@/components/train/blunder-check/BlunderCheckLevelStep';
import { BlunderCheckStageMessage } from '@/components/train/blunder-check/BlunderCheckStage';
import { useBlunderCheckSession } from '@/hooks/useBlunderCheckSession';
import { useTrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import { useTrainProgress } from '@/hooks/useTrainProgress';
import { useTrainSettings } from '@/hooks/useTrainSettings';
import { drillProgress, drillReducer, initialDrillState } from '@/lib/blunderCheckDrill';
import {
  clearBlunderCheckSolutionCache,
  readBlunderCheckSolutionCache,
} from '@/lib/blunderCheckSolutionCache';
import { trackFeature } from '@/lib/analytics';
import { unlockAudio } from '@/lib/sounds';
import type { DrillEvent, DrillState } from '@/lib/blunderCheckDrill';
import type { SessionResultResponse } from '@/types/blunderCheck';
import type { BlunderCheckLevel } from '@/types/train';

const HTTP_CONFLICT = 409;

/** The level preselected on the one-time level step (D-20). */
const DEFAULT_LEVEL: BlunderCheckLevel = 'intermediate';

/** The phases that take over the page (the tab bar and medal host are hidden). */
const IMMERSIVE_PHASES: ReadonlySet<DrillState['phase']> = new Set([
  // idle is the composing wait (and its failure with a Back button): immersive from the
  // first paint, so the tab bar does not flash between the Start tap and the first window.
  'idle',
  // loading_window is immersive too, so the tab bar does not flash between two windows.
  'loading_window',
  'ready_gate',
  'beginning',
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

interface ComposeStatusProps {
  composeError: unknown;
  onExit: () => void;
}

/** What the host shows while the session is composing (idle phase): a loading line, or the
 * failure with a Back button. A 409 means the pool has no sequence to hand out yet. */
function ComposeStatus({ composeError, onExit }: ComposeStatusProps): ReactElement {
  const composeFailed = composeError !== null && composeError !== undefined;
  if (!composeFailed) {
    return (
      <p className="text-center text-sm text-muted-foreground" data-testid="blunder-check-composing">
        Preparing your blunder check...
      </p>
    );
  }
  const nothingComposable =
    axios.isAxiosError(composeError) && composeError.response?.status === HTTP_CONFLICT;
  return (
    <div
      className="mx-auto flex w-full max-w-md flex-col gap-4"
      data-testid="blunder-check-compose-failed"
    >
      {nothingComposable ? (
        <p className="text-sm text-muted-foreground" data-testid="blunder-check-none-available">
          No blunder-check sequences are available yet. Import and analyze more games, then try
          again.
        </p>
      ) : (
        <LoadError resource="blunder check" data-testid="blunder-check-compose-error" />
      )}
      <Button
        variant="brand-outline"
        className={TRAIN_CTA_BUTTON_CLASS}
        onClick={onExit}
        data-testid="blunder-check-btn-back"
      >
        Back
      </Button>
    </div>
  );
}

interface LevelGate {
  /** The progress response is in: it is safe to choose between the level step and composing. */
  ready: boolean;
  /** The progress could not be loaded: composing blind could skip a needed level step. */
  loadError: unknown;
  awaitingLevel: boolean;
  /** The level save, or the settings fetch it needs, is in flight. */
  saving: boolean;
  saveFailed: boolean;
  confirm: (level: BlunderCheckLevel) => void;
}

/**
 * The one-time level step's gate (D-20). The server says in `modes.blunder_check.needs_level`
 * whether this user must pick a level before the first drill (no rated games, no stored level,
 * guests included). The host waits for the progress response before composing, shows the step
 * while a level is needed, and composes only once the level save succeeded, so the first session
 * is built from the stored level (RESEARCH Pattern 8).
 */
function useLevelGate(): LevelGate {
  const progress = useTrainProgress();
  const {
    data: settings,
    isPending,
    isError,
    isSaving,
    isSaveError,
    save,
    refetch,
  } = useTrainSettings();
  const [levelSaved, setLevelSaved] = useState(false);
  const needsLevel = progress.data?.modes.blunder_check.needs_level ?? false;
  const confirm = useCallback(
    (level: BlunderCheckLevel): void => {
      // Inside the tap, before the async save: the lead-in's move sounds play from timers.
      unlockAudio();
      // The PUT is a full replace of the schedule fields, so it needs the stored values.
      if (settings === undefined) {
        void refetch();
        return;
      }
      save(
        {
          weekdayMask: settings.weekday_mask,
          puzzlesPerSession: settings.puzzles_per_session,
          reminderEnabled: settings.reminder_enabled,
          reminderHour: settings.reminder_hour,
          reminderIntentAt: settings.reminder_intent_at,
          blunderCheckLevel: level,
        },
        {
          onSuccess: () => {
            // A settings row overwritten in place: the event is the only record of the change.
            trackFeature('option-change', { target: 'train-blunder-check-level', value: level });
            setLevelSaved(true);
          },
        },
      );
    },
    [settings, save, refetch],
  );
  return {
    ready: progress.data !== undefined,
    loadError: progress.data === undefined && progress.isError ? progress.error : null,
    awaitingLevel: needsLevel && !levelSaved,
    // The settings fetch counts as saving: Start stays off until the values to send are known.
    saving: isSaving || isPending,
    saveFailed: isSaveError || isError,
    confirm,
  };
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
  onExit,
}: {
  onImmersiveChange: (immersive: boolean) => void;
  /** Leave the drill and return to the Today card. */
  onExit: () => void;
}): ReactElement {
  // Analyze -> browser Back: a cached solution, read once at mount. The drill mounts straight
  // into it (immersive from the first paint) instead of composing a session.
  const [restored] = useState(readBlunderCheckSolutionCache);
  const [state, dispatch] = useReducer(
    drillReducer,
    restored,
    (cached): DrillState => cached?.state ?? initialDrillState,
  );
  const session = useBlunderCheckSession();
  const levelGate = useLevelGate();
  const { openSession, compose } = session;
  // The cache lives only while its solution is on screen: Next, a reset or an error drops it.
  const onSolution = state.phase === 'solution';
  useEffect(() => {
    if (!onSolution) clearBlunderCheckSolutionCache();
  }, [onSolution]);
  // A restored solution must belong to the caller's open session (a stale entry from an
  // older session, or another account in the same browser tab, drops back to Today).
  const restoredSessionId =
    restored !== null && state.phase === 'solution' && state.solution === restored.state.solution
      ? restored.state.session.sessionId
      : null;
  const openSessionId = openSession.isSuccess ? (openSession.data?.session_id ?? null) : undefined;
  useEffect(() => {
    if (restoredSessionId === null || openSessionId === undefined) return;
    if (openSessionId === restoredSessionId) return;
    // Bug fix: drop the stale entry here, not through the effect above. The page's onExit
    // unmounts this host in the same commit as the RESET, so that effect never ran and the
    // entry outlived the exit: every later Start (the card's, and the puzzle score screen's
    // "Continue with Blunder Check") mounted straight into it and bounced back to Today.
    clearBlunderCheckSolutionCache();
    dispatch({ type: 'RESET' });
    onExit();
  }, [restoredSessionId, openSessionId, onExit]);
  // One grading Worker for the whole session, created only once the drill has started (a
  // composing host constructs none): it grades off-key better moves and searches the
  // solution lines.
  const gradingEngine = useTrainGradingEngine({ enabled: state.phase !== 'idle' });
  const finishSession = useFinishSession(state, dispatch, session.finish.mutateAsync);
  // A synchronous guard: `compose.isPending` only flips after the next render, so a double
  // tap on the card's Start (or a StrictMode effect re-run) would otherwise send two
  // requests (T-249-29, T-251-22).
  const startInFlight = useRef(false);

  const immersive = IMMERSIVE_PHASES.has(state.phase);
  useEffect(() => {
    onImmersiveChange(immersive);
    return () => onImmersiveChange(false);
  }, [immersive, onImmersiveChange]);

  const { mutate: composeSession } = compose;
  const handleStart = useCallback((): void => {
    if (startInFlight.current) return;
    startInFlight.current = true;
    composeSession(undefined, {
      onSuccess: (composed) => dispatch({ type: 'SESSION_READY', session: composed }),
      onSettled: () => {
        startInFlight.current = false;
      },
    });
  }, [composeSession]);
  // Compose (or resume) on mount unless the host mounted into a restored solution, once the
  // progress says no level step is pending. Audio was unlocked in the Start tap that mounted this
  // host, or in the level step's own Start (the lead-in's move sounds play from timers).
  const { ready: levelGateReady, awaitingLevel } = levelGate;
  useEffect(() => {
    if (restored === null && levelGateReady && !awaitingLevel) handleStart();
  }, [restored, levelGateReady, awaitingLevel, handleStart]);

  // The way out when the session cannot go on here (the error screen's Back, or a session
  // finished on another device).
  const leaveSession = (): void => {
    dispatch({ type: 'RESET' });
    // Bug fix (Phase 249 review): the open-session query kept the progress fetched
    // when the session was composed after a failure mid-session.
    void session.refreshOpenSession();
    onExit();
  };

  if (state.phase === 'error') {
    return (
      <div className="mx-auto flex w-full max-w-md flex-col gap-4" data-testid="blunder-check-error">
        <LoadError resource="blunder check" />
        <Button
          variant="brand-outline"
          className={TRAIN_CTA_BUTTON_CLASS}
          onClick={leaveSession}
          data-testid="blunder-check-btn-reset"
        >
          Back
        </Button>
      </div>
    );
  }

  if (state.phase === 'idle') {
    if (restored === null && levelGate.ready && levelGate.awaitingLevel) {
      return (
        <BlunderCheckLevelStep
          initialLevel={DEFAULT_LEVEL}
          saving={levelGate.saving}
          error={levelGate.saveFailed}
          onConfirm={levelGate.confirm}
          onBack={onExit}
        />
      );
    }
    return <ComposeStatus composeError={compose.error ?? levelGate.loadError} onExit={onExit} />;
  }

  if (state.phase === 'session_end') {
    return <BlunderCheckEndScreen result={state.result} onDone={onExit} />;
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
          onSessionGone={leaveSession}
        />
      </div>
    </div>
  );
}
