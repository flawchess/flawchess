/**
 * useTrainPuzzleTelemetry — Phase 233 think-time measurement for one Train
 * puzzle (D-02): `guess_ms` (engine-ready board -> guess press) and `move_ms`
 * (guess press -> graded drop), VISIBLE time only with the hidden-tab span
 * kept as `think_hidden_ms` (D-04), plus `client` (D-09) and `resumed`.
 *
 * All mutable state lives in refs and every returned callback is
 * `useCallback`-stable. The solve snapshot is frozen at move time and never
 * recomputed, so a solve retry resends the identical telemetry. Telemetry is
 * a recorded outcome only; it never feeds grading or scoring (D-05).
 */

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { postReviewKeepalive } from '@/api/client';
import { telemetryClient } from '@/lib/deviceClass';
import { updateTrainRevealCacheReview } from '@/lib/trainRevealCache';
import {
  buildReviewTelemetry,
  buildSolveTelemetry,
  isUsableReviewSnapshot,
  noteThinkStarted,
  REVIEW_CARD_HOVER_MIN_MS,
  type CardEngageKind,
  type ReviewCounters,
  type ReviewTelemetrySnapshot,
} from '@/lib/trainTelemetry';
import { applyVisibility, readStopwatch, startStopwatch, type VisibleStopwatch } from '@/lib/visibleStopwatch';
import type { SolveTelemetry } from '@/types/train';

interface UseTrainPuzzleTelemetryOptions {
  sessionId: number | null;
  position: number;
  /** Grading engine ready: before this the guess UI does not exist ("Loading engine…"). */
  isReady: boolean;
  /** A restored (already solved) reveal: no think phase to measure. */
  isRestored: boolean;
  /** The verdict has landed: the reveal is open and the review timer runs (D-03). */
  hasVerdict: boolean;
  /** Review totals persisted in the reveal cache (Analyze round trip); seeds the timer when restored. */
  restoredReview: ReviewTelemetrySnapshot | undefined;
}

interface TrainPuzzleTelemetry {
  markGuess: () => void;
  markMove: () => void;
  solveTelemetry: () => SolveTelemetry | undefined;
  /** Next on the reveal: flush this puzzle's review totals once (exit 'next'). */
  flushReviewOnNext: () => void;
  /** Analyze click: the current review totals for the reveal cache. Does NOT stop the timer. */
  snapshotReviewForAnalyze: () => ReviewTelemetrySnapshot | undefined;
  /** A user prev/next/token click on a reveal line stepper (D-14). */
  onLineUserStep: () => void;
  /** A user-played free-play move: a drop or an engine-line click (D-14). */
  onExploreMove: () => void;
  /** The first-reveal walkthrough is active: sticky for this puzzle (D-13). */
  markWalkthroughActive: () => void;
  /** A reveal card was engaged (D-11): a tap/click opens it at once, a desktop hover counts after the hold time. */
  onCardEngage: (key: string, kind: CardEngageKind) => void;
  /** The number of cards currently shown on the reveal (D-12); the hook keeps the maximum. */
  onCardsTotalChange: (total: number) => void;
}

/** The review stopwatch plus the row it belongs to (never read from later props). */
interface ReviewState {
  stopwatch: VisibleStopwatch;
  sessionId: number | null;
  position: number;
}

function emptyCounters(): ReviewCounters {
  return {
    lineSteps: 0,
    exploreMoves: 0,
    analyzeOpened: false,
    walkthrough: false,
    cardKeys: new Set<string>(),
    cardsTotal: 0,
  };
}

function isTabHidden(): boolean {
  return typeof document !== 'undefined' && document.visibilityState === 'hidden';
}

export function useTrainPuzzleTelemetry(options: UseTrainPuzzleTelemetryOptions): TrainPuzzleTelemetry {
  const { sessionId, position, isReady, isRestored, hasVerdict, restoredReview } = options;

  // Last `${sessionId}:${position}` the refs were reset for. Refs reset only
  // when this key CHANGES, so React StrictMode's dev double effect invocation
  // can neither restart the timer nor read its own marker as a resume.
  const keyRef = useRef<string | null>(null);
  const stopwatchRef = useRef<VisibleStopwatch | null>(null);
  const resumedRef = useRef(false);
  const guessMarkRef = useRef<number | null>(null);
  const frozenRef = useRef<SolveTelemetry | null>(null);
  const reviewRef = useRef<ReviewState | null>(null);
  // Engagement counters (D-14): cumulative totals for this puzzle's reveal.
  const countersRef = useRef<ReviewCounters>(emptyCounters());
  // The one pending desktop hover (D-11) and the card it is armed for.
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hoverKeyRef = useRef<string | null>(null);

  const clearHover = useCallback((): void => {
    if (hoverTimerRef.current !== null) clearTimeout(hoverTimerRef.current);
    hoverTimerRef.current = null;
    hoverKeyRef.current = null;
  }, []);
  // Set ONLY by the Next flush: after it every later trigger for this puzzle is a no-op.
  const nextFlushedRef = useRef(false);
  // A non-Next flush was already sent in the current hidden span (cleared on visible).
  const hiddenFlushedRef = useRef(false);
  // True while the mount effect is set up; the deferred unmount flush checks it.
  const aliveRef = useRef(false);

  useEffect(() => {
    const key = `${sessionId ?? 'none'}:${position}`;
    if (keyRef.current !== key) {
      // The very first key leaves the counters alone: the child TrainReveal's
      // mount effect (which reports the cards total) runs BEFORE this parent
      // effect, and the refs are still pristine on a first mount anyway.
      const isFirstKey = keyRef.current === null;
      keyRef.current = key;
      clearHover();
      if (!isFirstKey) countersRef.current = emptyCounters();
      stopwatchRef.current = null;
      resumedRef.current = false;
      guessMarkRef.current = null;
      frozenRef.current = null;
      reviewRef.current = null;
      nextFlushedRef.current = false;
      // The reset itself does not flush: per Train.tsx the key changes without an
      // unmount only through handleNext, which flushes Next first.
      hiddenFlushedRef.current = false;
    }
    if (!isReady || isRestored || stopwatchRef.current !== null) return;
    // A mount into an already-hidden tab starts paused (useBotGameClock CR-01).
    stopwatchRef.current = startStopwatch(Date.now(), isTabHidden());
    resumedRef.current = sessionId === null ? false : noteThinkStarted(sessionId, position);
  }, [sessionId, position, isReady, isRestored, clearHover]);

  // Review timer (D-03): starts when the verdict lands. Declared AFTER the
  // reset effect so a key change clears the previous puzzle's state first.
  useEffect(() => {
    if (!hasVerdict || reviewRef.current !== null) return;
    // A restored reveal continues the totals already flushed (Analyze round trip).
    const seed = isRestored && isUsableReviewSnapshot(restoredReview) ? restoredReview : undefined;
    reviewRef.current = { stopwatch: startStopwatch(Date.now(), isTabHidden(), seed), sessionId, position };
    if (seed !== undefined) {
      // Cards are merged, not replaced: the child reveal may already have reported
      // its total on this very mount (its effect runs before this one).
      const current = countersRef.current;
      countersRef.current = {
        lineSteps: seed.lineSteps ?? 0,
        exploreMoves: seed.exploreMoves ?? 0,
        analyzeOpened: seed.analyzeOpened ?? false,
        walkthrough: seed.walkthrough ?? false,
        cardKeys: new Set([...(seed.cardKeys ?? []), ...current.cardKeys]),
        cardsTotal: Math.max(seed.cardsTotal ?? 0, current.cardsTotal),
      };
    }
  }, [hasVerdict, sessionId, position, isRestored, restoredReview]);

  // Single source of the review totals for the Analyze snapshot, the Next flush
  // and the non-Next flush: stopwatch totals plus the engagement counters.
  const takeReviewSnapshot = useCallback((): ReviewTelemetrySnapshot | undefined => {
    const review = reviewRef.current;
    if (review === null) return undefined;
    const counters = countersRef.current;
    return {
      ...readStopwatch(review.stopwatch, Date.now()),
      lineSteps: counters.lineSteps,
      exploreMoves: counters.exploreMoves,
      analyzeOpened: counters.analyzeOpened,
      walkthrough: counters.walkthrough,
      cardKeys: [...counters.cardKeys],
      cardsTotal: counters.cardsTotal,
    };
  }, []);

  // The ONE funnel for every non-Next exit (page hidden, pagehide, unmount).
  // It NEVER sets the Next-flushed guard: the user can come back (tab visible
  // again, the Analyze return) and press Next, whose cumulative values must
  // still overwrite per key. Reads only refs (no stale closure).
  const flushReviewNonNext = useCallback((): void => {
    const review = reviewRef.current;
    if (nextFlushedRef.current || review === null || review.sessionId === null) return;
    const hidden = isTabHidden();
    // review_ms is paused while hidden and the user cannot interact, so a second
    // body in the same hidden span (the pagehide after visibilitychange-hidden on
    // a tab close) could only repeat the values.
    if (hidden && hiddenFlushedRef.current) return;
    // 'pagehide' here means "left the reveal without pressing Next" (D-07), not
    // literally the pagehide event.
    const snapshot = takeReviewSnapshot();
    if (snapshot === undefined) return;
    postReviewKeepalive(review.sessionId, review.position, buildReviewTelemetry(snapshot, countersRef.current, 'pagehide'));
    // Mirror the SAME snapshot into a matching reveal-cache entry (update-only):
    // on a plain Analyze click this runs from the unmount microtask right after
    // handleAnalyzeClick saved the entry, so the entry ends up holding exactly
    // what the row received and the restored reveal's later flushes are never smaller.
    updateTrainRevealCacheReview(review.sessionId, review.position, snapshot);
    if (hidden) hiddenFlushedRef.current = true;
  }, [takeReviewSnapshot]);

  useEffect(() => {
    aliveRef.current = true;
    const handleVisibility = (): void => {
      const hidden = isTabHidden();
      const now = Date.now();
      const sw = stopwatchRef.current;
      if (sw !== null) stopwatchRef.current = applyVisibility(sw, hidden, now);
      const review = reviewRef.current;
      if (review !== null) {
        reviewRef.current = { ...review, stopwatch: applyVisibility(review.stopwatch, hidden, now) };
      }
      // D-11: a hover cannot be held on a hidden page. This also keeps every
      // counter frozen while hidden, which the one-flush-per-hidden-span
      // dedupe in flushReviewNonNext relies on.
      if (hidden) clearHover();
      if (hidden) flushReviewNonNext();
      else hiddenFlushedRef.current = false;
    };
    // pagehide, never unload/beforeunload (they break the bfcache and are
    // unreliable on mobile Safari).
    const handlePageHide = (): void => flushReviewNonNext();
    document.addEventListener('visibilitychange', handleVisibility);
    window.addEventListener('pagehide', handlePageHide);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibility);
      window.removeEventListener('pagehide', handlePageHide);
      aliveRef.current = false;
      clearHover();
      // React StrictMode (main.tsx) runs a simulated unmount in dev and re-runs
      // the setup synchronously before this microtask, which then sees alive and
      // sends nothing; a real unmount (route change, the Analyze link, a Train.tsx
      // transition) sends one. The keepalive transport is used because the
      // component is going away.
      queueMicrotask(() => {
        if (!aliveRef.current) flushReviewNonNext();
      });
    };
  }, [flushReviewNonNext, clearHover]);

  const markGuess = useCallback((): void => {
    const sw = stopwatchRef.current;
    if (sw === null || guessMarkRef.current !== null) return;
    guessMarkRef.current = readStopwatch(sw, Date.now()).visibleMs;
  }, []);

  const markMove = useCallback((): void => {
    if (frozenRef.current !== null) return;
    const sw = stopwatchRef.current;
    const client = telemetryClient();
    if (sw === null) {
      frozenRef.current = buildSolveTelemetry({
        guessMs: null,
        moveMs: null,
        thinkHiddenMs: null,
        client,
        resumed: resumedRef.current,
      });
      return;
    }
    const totals = readStopwatch(sw, Date.now());
    const guessMark = guessMarkRef.current;
    frozenRef.current = buildSolveTelemetry({
      guessMs: guessMark,
      moveMs: guessMark === null ? null : totals.visibleMs - guessMark,
      thinkHiddenMs: totals.hiddenMs,
      client,
      resumed: resumedRef.current,
    });
  }, []);

  const solveTelemetry = useCallback((): SolveTelemetry | undefined => frozenRef.current ?? undefined, []);

  const flushReviewOnNext = useCallback((): void => {
    const review = reviewRef.current;
    if (nextFlushedRef.current || review === null || review.sessionId === null) return;
    const snapshot = takeReviewSnapshot();
    if (snapshot === undefined) return;
    // Fix (233 review WR-02): Next used to go through an axios XHR with this
    // guard set before any response, so a request cancelled by an unload right
    // after Next (e.g. the last puzzle navigating away) or a failed one was lost
    // for good, and the row kept exit='pagehide' (breaking the D-07 "next puzzle
    // shown" derivation). The keepalive transport outlives the page.
    postReviewKeepalive(review.sessionId, review.position, buildReviewTelemetry(snapshot, countersRef.current, 'next'));
    nextFlushedRef.current = true;
  }, [takeReviewSnapshot]);

  // D-14: the flag is set BEFORE the snapshot so the Analyze snapshot, and the
  // unmount flush that follows a plain Analyze click, both carry it.
  const snapshotReviewForAnalyze = useCallback((): ReviewTelemetrySnapshot | undefined => {
    countersRef.current = { ...countersRef.current, analyzeOpened: true };
    return takeReviewSnapshot();
  }, [takeReviewSnapshot]);

  const onLineUserStep = useCallback((): void => {
    countersRef.current = { ...countersRef.current, lineSteps: countersRef.current.lineSteps + 1 };
  }, []);

  const onExploreMove = useCallback((): void => {
    countersRef.current = { ...countersRef.current, exploreMoves: countersRef.current.exploreMoves + 1 };
  }, []);

  const addCard = useCallback((key: string): void => {
    const counters = countersRef.current;
    if (counters.cardKeys.has(key)) return;
    countersRef.current = { ...counters, cardKeys: new Set(counters.cardKeys).add(key) };
  }, []);

  const onCardEngage = useCallback(
    (key: string, kind: CardEngageKind): void => {
      if (kind === 'hover-end') {
        if (hoverKeyRef.current === key) clearHover();
        return;
      }
      clearHover();
      if (kind === 'open') {
        addCard(key);
        return;
      }
      hoverKeyRef.current = key;
      hoverTimerRef.current = setTimeout(() => {
        hoverTimerRef.current = null;
        hoverKeyRef.current = null;
        addCard(key);
      }, REVIEW_CARD_HOVER_MIN_MS);
    },
    [addCard, clearHover],
  );

  const onCardsTotalChange = useCallback((total: number): void => {
    const counters = countersRef.current;
    if (total > counters.cardsTotal) countersRef.current = { ...counters, cardsTotal: total };
  }, []);

  const markWalkthroughActive = useCallback((): void => {
    countersRef.current = { ...countersRef.current, walkthrough: true };
  }, []);

  return useMemo(
    () => ({
      markGuess,
      markMove,
      solveTelemetry,
      flushReviewOnNext,
      snapshotReviewForAnalyze,
      onLineUserStep,
      onExploreMove,
      markWalkthroughActive,
      onCardEngage,
      onCardsTotalChange,
    }),
    [
      markGuess,
      markMove,
      solveTelemetry,
      flushReviewOnNext,
      snapshotReviewForAnalyze,
      onLineUserStep,
      onExploreMove,
      markWalkthroughActive,
      onCardEngage,
      onCardsTotalChange,
    ],
  );
}
