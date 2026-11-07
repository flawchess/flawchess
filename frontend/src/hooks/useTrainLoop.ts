/**
 * useTrainLoop — the session, grading engine and loop state of the /train
 * layout (`pages/Train.tsx`), moved out of the page so the layout can know the
 * immersive state synchronously and so the Leaderboard tab can exist without a
 * session.
 *
 * Visiting /train never auto-starts a session — the landing
 * always shows a status line plus a single Start/Resume button, and the loop
 * begins only on that press. `useTrainSession.startSession()` is fired
 * automatically below once Today has been visited, but that is a status READ
 * (there is no separate preview endpoint — see useTrainSession.ts's module
 * docstring), not entering the loop: `hasEnteredLoop` is the only thing that
 * reveals `TrainSolveScreen`, and it flips only on a user press inside
 * `TrainStartScreen` (via `enterLoop`).
 *
 * Today latch (`todayVisited`): a deep link to /train/leaderboard must create
 * no session row (the activity dashboards read session rows as visits) and
 * load no grading engine. The session read and the Worker are therefore gated
 * on a one-way latch that flips the first time Today is active and never flips
 * back, so Today -> Leaderboard -> Today fires exactly one POST and constructs
 * exactly one Worker.
 *
 * The grading engine's Worker is created HERE, at the page level — session
 * scope, not per-puzzle — and threaded down to
 * `TrainSolveScreen` so exactly one Worker exists for the whole session.
 *
 * Session-complete -> score-screen
 * transition: when the final puzzle's solve response reports
 * `session_complete` and the user presses Next on its reveal, `handleNext`
 * shows `TrainScoreScreen` instead of calling `trainSession.advance()` (which
 * would otherwise leave `currentPuzzle` parked on the last puzzle rather than
 * becoming null — there is no "puzzle past the end" state to fall through to
 * automatically). `showScoreScreen` is local view state, not the accurate
 * source of truth on a later day's revisit — that's `TrainStartScreen`'s
 * 'completed' landing state, which reads real session
 * data on a fresh mount instead of this transient in-session flag. The score
 * screen's "Done" routes into exactly that state via
 * `returnToLanding`, which re-reads session status rather than merely
 * flipping the flag back.
 *
 * Leaving a reveal via its Analyze deep link and pressing
 * the browser back button restores that puzzle's SOLVED reveal (not the
 * start screen) from the sessionStorage cache written on the Analyze click —
 * see `trainRevealCache.ts` and the `restoredReveal` state below.
 */

import { useCallback, useEffect, useState } from 'react';
import { useTrainSession } from '@/hooks/useTrainSession';
import type { UseTrainSessionResult } from '@/hooks/useTrainSession';
import { useTrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import type { TrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import { clearTrainRevealCache, readTrainRevealCache } from '@/lib/trainRevealCache';
import type { CachedTrainReveal } from '@/lib/trainRevealCache';
import type { TrainSessionResponse } from '@/types/train';

/**
 * Whether the layout is in an immersive state (hide the subnav, give the solve
 * screen the page): the solve loop, the score screen, or a cached restored
 * reveal. Pure so the first-paint rule is unit-testable.
 */
export function resolveTrainImmersive(input: {
  isToday: boolean;
  showLoop: boolean;
  showScoreScreen: boolean;
  restoredReveal: CachedTrainReveal | null;
  session: TrainSessionResponse | null;
  isSessionError: boolean;
}): boolean {
  if (!input.isToday) return false;
  if (input.showLoop || input.showScoreScreen) return true;
  // Bug-prone spot: restoredActive is false until the session loads, so a cached
  // reveal must count from first paint or the subnav flashes on Analyze -> back.
  // The cache is read in a useState initializer, so this is true on the first
  // render. `session === null` is that first-paint case; a stale cache from
  // another session flips to false in the same render that delivers the
  // mismatching session, before the clearing effect runs. `isSessionError`
  // keeps an error screen from losing its tabs. `!isToday` (above) keeps a
  // cached reveal from hiding the subnav on another tab, where no session will
  // ever arrive to validate it.
  if (input.restoredReveal === null || input.isSessionError) return false;
  return input.session === null || input.session.session_id === input.restoredReveal.sessionId;
}

export interface UseTrainLoopResult {
  trainSession: UseTrainSessionResult;
  gradingEngine: TrainGradingEngine;
  /** One-way latch: true from the first time Today is active. */
  todayVisited: boolean;
  /** Hide the subnav and give the solve screen the page; see `resolveTrainImmersive`. */
  immersive: boolean;
  showLoop: boolean;
  showScoreScreen: boolean;
  restoredActive: boolean;
  restoredReveal: CachedTrainReveal | null;
  /** Start/Resume press: stamps the session entered server-side, then reveals the loop. */
  enterLoop: () => void;
  handleNext: () => void;
  handleRestoredNext: () => void;
  returnToLanding: () => void;
  /** Ask for a session re-read; runs once Today is active. Stable identity. */
  requestSessionReread: () => void;
}

export function useTrainLoop({
  isToday,
  canTrain,
}: {
  isToday: boolean;
  canTrain: boolean;
}): UseTrainLoopResult {
  // Adjusted during render so the effect below sees the flipped value on the
  // first pass, with no extra frame. Deliberately STATE rather than a ref
  // latch: the StrictMode comment on the effect forbids a ref latch around
  // `startSession`, and state feeding the effect's deps keeps its double-invoke
  // recovery intact.
  const [todayVisited, setTodayVisited] = useState(isToday);
  if (isToday && !todayVisited) setTodayVisited(true);

  const trainSession = useTrainSession();
  const gradingEngine = useTrainGradingEngine({ enabled: canTrain && todayVisited });
  const [hasEnteredLoop, setHasEnteredLoop] = useState(false);
  const [showScoreScreen, setShowScoreScreen] = useState(false);
  // Analyze -> browser back: a cached solved reveal,
  // read once at mount. While it validates against the freshly resumed
  // session (same session_id), the page skips the start screen and mounts
  // straight into that puzzle's solved reveal — see trainRevealCache.ts.
  const [restoredReveal, setRestoredReveal] = useState<CachedTrainReveal | null>(() =>
    readTrainRevealCache(),
  );

  // Set when a view is torn down off Today (or a late settings save asks for a
  // re-read); consumed by the effect below once Today is active again.
  const [sessionStale, setSessionStale] = useState(false);
  // Pitfall: browser Back out of the running loop now lands on a sibling tab
  // with the loop state still alive (the layout stays mounted). Clear the loop
  // flags the moment Today is left so Forward / Today cannot re-mount a solve
  // screen on a stale verdict or score, and mark the session stale. Adjusted
  // during render so no frame shows the solve screen on the other tab.
  // `restoredReveal` is left untouched on the way out.
  if (!isToday && (hasEnteredLoop || showScoreScreen)) {
    setHasEnteredLoop(false);
    setShowScoreScreen(false);
    setSessionStale(true);
  }

  const { startSession, resetSolve } = trainSession;
  useEffect(() => {
    // This only waits for the profile to resolve and for Today to have been
    // visited before firing the status read.
    //
    // NO ref latch here, deliberately. A "fire only once per mount" latch
    // looks harmless but hangs the page under StrictMode (dev): React mounts,
    // runs this effect, unmounts, and remounts. The throwaway first pass
    // fires the mutation, and TanStack's MutationObserver.onUnsubscribe
    // detaches the observer from that in-flight mutation when the simulated
    // unmount removes its last listener (query-core mutationObserver.js) —
    // re-subscribing never re-attaches, so the result freezes at
    // isPending:true and onSuccess never runs. The landing screen then sits
    // on "Loading…" forever, and a reload does not help. The second effect
    // pass calling startSession() again IS the recovery: mutate() rebuilds
    // the mutation and re-adds the live observer. Composition is idempotent
    // server-side (it resumes the day's open session), so the extra dev-only
    // call is free. `startSession` is stable (see useTrainSession), so this
    // runs once per mount in production, and again only if canTrain or
    // todayVisited flips.
    if (!canTrain || !todayVisited) return;
    startSession();
  }, [canTrain, todayVisited, startSession]);

  // Deferred re-read after leaving the loop off Today, or after a settings
  // save that landed while another tab was showing. The re-read is load-bearing
  // (`solved_count` is the compose-time value, see `returnToLanding`) and must
  // wait for Today because D-06 forbids a POST on another tab.
  useEffect(() => {
    if (!isToday || !sessionStale) return;
    setSessionStale(false);
    resetSolve();
    startSession();
  }, [isToday, sessionStale, resetSolve, startSession]);

  // Stable on purpose: it is passed down as `TrainScheduleSettings`'s `onSaved`,
  // which sits in the dependency list of that component's debounced save
  // effect, so a changing identity would re-run it and double-save while a save
  // is in flight. It replaces passing `startSession` straight through: the
  // landing stays mounted but hidden on the other tabs, and a debounced save can
  // fire `onSaved` there, which would POST off Today. This only flags the
  // session stale; the effect above does the re-read once Today is active.
  const requestSessionReread = useCallback(() => {
    setSessionStale(true);
  }, []);

  // Drop a cached reveal from another session (e.g. a new day's session was
  // composed since the cache was written) — never restore across sessions.
  const session = trainSession.session;
  useEffect(() => {
    if (restoredReveal !== null && session !== null && session.session_id !== restoredReveal.sessionId) {
      clearTrainRevealCache();
      setRestoredReveal(null);
    }
  }, [restoredReveal, session]);

  const restoredActive =
    restoredReveal !== null && session !== null && session.session_id === restoredReveal.sessionId;

  const showLoop =
    hasEnteredLoop && !showScoreScreen && !restoredActive && trainSession.currentPuzzle !== null;

  const immersive = resolveTrainImmersive({
    isToday,
    showLoop,
    showScoreScreen,
    restoredReveal,
    session,
    isSessionError: trainSession.isSessionError,
  });

  function enterLoop(): void {
    trainSession.markSessionEntered();
    setHasEnteredLoop(true);
  }

  function handleNext(): void {
    // A stale Analyze-click cache must never restore a puzzle the user has
    // already moved past — clear it the moment the loop advances.
    clearTrainRevealCache();
    if (trainSession.lastSolveResponse?.session_complete) {
      setShowScoreScreen(true);
      return;
    }
    trainSession.advance();
  }

  // Next on a RESTORED reveal: leave restore mode and continue the normal
  // loop at the resumed queue's head (or the score screen when the restored
  // puzzle had completed the session).
  function handleRestoredNext(): void {
    clearTrainRevealCache();
    const wasComplete = restoredReveal?.verdict.session_complete === true;
    setRestoredReveal(null);
    setHasEnteredLoop(true);
    if (wasComplete) setShowScoreScreen(true);
  }

  // Leave whatever in-loop view is showing and re-read session status, exactly
  // as a fresh page mount would. The re-read is load-bearing, not a refresh
  // nicety: `TrainStartScreen`'s landing state is resolved from
  // `session.solved_count`, which is still the compose-time value in local
  // state, so skipping it would render a "Start session" landing on a day the
  // user has already finished.
  function returnToLanding(): void {
    clearTrainRevealCache();
    setRestoredReveal(null);
    setHasEnteredLoop(false);
    setShowScoreScreen(false);
    // Drop the last solve verdict too, so the session
    // just left cannot bleed into the next one. Without this the mutation
    // still held the previous session's response when the user pressed Start
    // again (dev-clock time travel is the fast way to hit this), and the
    // freshly mounted solve screen replayed its result sound and points flash
    // over the first puzzle. TrainSolveScreen guards its own mount as well —
    // this keeps the page state honest to the "as a fresh page mount would"
    // contract above.
    trainSession.resetSolve();
    startSession();
  }

  return {
    trainSession,
    gradingEngine,
    todayVisited,
    immersive,
    showLoop,
    showScoreScreen,
    restoredActive,
    restoredReveal,
    enterLoop,
    handleNext,
    handleRestoredNext,
    returnToLanding,
    requestSessionReread,
  };
}
