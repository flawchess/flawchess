/**
 * useBotGameClock — clock/turn-timing sub-hook of useBotGame. Owns the
 * clock-tick display loop, the turn-anchor mount-init and hidden-tab pause
 * bookkeeping, and the pause-aware elapsed-time accounting the rest of the
 * bot-game hooks debit moves against.
 *
 * Its reads and writes are confined to its own refs and state
 * (`clockBaseRef`, `turnStartedAtRef`, `pausedAtRef`,
 * `whiteClockMs`/`blackClockMs`).
 *
 * The refs stay private and every access goes through a named function
 * (`applyMoveDebit`, `resetClock`, `getClockBase`, `resetTurnAnchor`,
 * `chargeableElapsedMs`, `flagIfOutOfTime`), because ESLint's
 * `react-hooks/exhaustive-deps` cannot prove a ref returned from a custom hook
 * stable: it only recognizes a ref created by a literal `useRef()` call in
 * the same function scope that reads it. Returning the refs would surface a
 * "missing dependency" warning at every caller's `useCallback`/`useEffect`.
 * For the same reason the turn-anchor mount-init effect and the hidden-tab
 * pause effect, which exclusively touch `turnStartedAtRef`/`pausedAtRef`,
 * live here alongside the clock-tick effect.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';

import type { MoverColor } from '@/lib/liveFlaw';
import {
  applyIncrementMs,
  computeChargeableElapsedMs,
  hasFlaggedOnDebit,
  isLowTime,
  shiftAnchorForPause,
} from '@/lib/chessClock';
import type { BotGameOutcome } from '@/lib/botGameEnd';
import { playSound } from '@/lib/sounds';
import type { BotGameSnapshot } from '@/lib/botGameSnapshot';

/** Display-clock recompute cadence — matches lichess-style clocks;
 * the displayed value is always recomputed from a wall-clock anchor, never
 * accumulated from this interval's tick count. */
const CLOCK_TICK_INTERVAL_MS = 100;

/** Fresh clock bases for a new/resumed-without-snapshot game, in
 * milliseconds. Private to this module: called by the `clockBaseRef`
 * initializer (mount) and by `resetClock()` (`useBotGame`'s `newGame()`). */
function freshClockBase(baseSeconds: number): { white: number; black: number } {
  const ms = baseSeconds * 1000;
  return { white: ms, black: ms };
}

export interface UseBotGameClockOptions {
  /** An optional snapshot to seed the clock bases from. */
  resume?: BotGameSnapshot;
  /** Starting clock time for both sides, in seconds (settings.baseSeconds). */
  baseSeconds: number;
  /** Which color the human player is playing. */
  userColor: MoverColor;
  /** Gates the tick and the turn-anchor mount-init effect —
   * no clock runs while a resumed game's resume gate is still on screen. */
  live: boolean;
  /** Whose turn it currently is in the live game. */
  activeColor: MoverColor;
  /** Set once the game has ended; null while in progress. */
  outcome: BotGameOutcome | null;
  /** The user's low-time sound fires exactly once per game — owned by
   * `useBotGameSnapshot` (seeded from a resume), mutated here. */
  hasFiredLowTimeRef: RefObject<boolean>;
  /** Ends the game. `flagIfOutOfTime` and the tick's own timeout
   * check both call through to this. */
  finalizeGame: (finished: BotGameOutcome) => void;
}

export interface UseBotGameClockResult {
  /** White's remaining clock time, ms, recomputed from a wall-clock anchor. */
  whiteClockMs: number;
  /** Black's remaining clock time, ms, recomputed from a wall-clock anchor. */
  blackClockMs: number;
  /** Resets the turn anchor to now, re-baselining an
   * in-progress pause alongside it. Called from `commitMove`. */
  resetTurnAnchor: () => void;
  /** The single pause-aware elapsed-time source. */
  chargeableElapsedMs: () => number;
  /** The commit-time flag test. Both move paths (`attemptMove`,
   * `runBotTurn`) call this BEFORE applying the move. */
  flagIfOutOfTime: (mover: MoverColor, debitMs: number) => boolean;
  /**
   * Debits `debitMs` (plus the Fischer increment) from `mover`'s clock base
   * and mirrors the result into the render-facing state. Returns the
   * settled remaining time so the caller can pass it to `annotateClock`.
   */
  applyMoveDebit: (mover: MoverColor, debitMs: number, incrementMs: number) => number;
  /** Resets the clock to a fresh base for `baseSeconds`, clears any
   * in-progress pause, and re-baselines the turn anchor. Called from
   * `useBotGame`'s `newGame()`. */
  resetClock: () => void;
  /** Live read of the authoritative clock base (both colors) — used by
   * `runBotTurn`'s think-deadline calc and the hidden-tab snapshot fold,
   * both of which need the raw `{ white, black }` pair rather than a
   * single mover's value. */
  getClockBase: () => { white: number; black: number };
}

/**
 * Clock/turn-timing sub-hook of `useBotGame`. See file header.
 */
export function useBotGameClock(options: UseBotGameClockOptions): UseBotGameClockResult {
  const {
    resume,
    baseSeconds,
    userColor,
    live,
    activeColor,
    outcome,
    hasFiredLowTimeRef,
    finalizeGame,
  } = options;

  const clockBaseRef = useRef<{ white: number; black: number }>(
    resume ? { white: resume.whiteClockMs, black: resume.blackClockMs } : freshClockBase(baseSeconds),
  );
  /** Wall-clock anchor for the current turn. Set to the real `Date.now()` by
   * the turn-anchor mount-init effect below (react-hooks/purity forbids
   * calling `Date.now()` directly as a `useRef` initializer, since that
   * reads impure state during render) — this placeholder value is never
   * actually read. Deliberately NOT seeded from `resume` — gated by `live`
   * instead. */
  const turnStartedAtRef = useRef<number>(0);
  const pausedAtRef = useRef<number | null>(null);

  const [whiteClockMs, setWhiteClockMs] = useState(resume?.whiteClockMs ?? baseSeconds * 1000);
  const [blackClockMs, setBlackClockMs] = useState(resume?.blackClockMs ?? baseSeconds * 1000);

  /**
   * Resets the turn anchor to now — and, if a pause is currently
   * in progress (the tab is hidden right now), re-baselines the pause
   * timestamp to the SAME instant. Without the second half, a move
   * committing while the tab is hidden (a bot's think resolving in the
   * background) lets the eventual resume handler shift the fresh anchor by
   * the FULL pre-commit hidden duration, landing it in the future and
   * crediting the next mover phantom time (a negative elapsed reading).
   * Used everywhere the anchor is reset: `commitMove` and `resetClock`.
   */
  const resetTurnAnchor = useCallback((): void => {
    const now = Date.now();
    turnStartedAtRef.current = now;
    if (pausedAtRef.current !== null) pausedAtRef.current = now;
  }, []);

  /**
   * The SINGLE pause-aware elapsed-time source for this hook. The resume
   * edge (the hidden-tab pause effect's `shiftAnchorForPause` call below)
   * shifts the anchor retroactively, which cannot help a tick or a
   * bot-commit landing DURING the hidden period: those would charge raw
   * background wall-clock time. Every elapsed-time consumer (the tick's flag
   * check, the bot's committed debit, the user's move debit) MUST call this
   * instead of a raw now-minus-anchor read.
   */
  const chargeableElapsedMs = useCallback((): number => {
    return computeChargeableElapsedMs(turnStartedAtRef.current, pausedAtRef.current, Date.now());
  }, []);

  /**
   * The commit-time flag test. The 100 ms tick alone cannot decide whether an
   * overrunning mover lost on time (it is a race), and a node-floor overrun
   * (or a grading call outlasting a tight think deadline) makes an overrun
   * routine, not theoretical, for a low-clock bot. Both move paths
   * (`attemptMove`, `runBotTurn`) MUST call this BEFORE applying the move,
   * and treat a `true` return as "the move must not commit."
   */
  const flagIfOutOfTime = useCallback(
    (mover: MoverColor, debitMs: number): boolean => {
      if (!hasFlaggedOnDebit(clockBaseRef.current[mover], debitMs)) return false;
      clockBaseRef.current[mover] = 0;
      if (mover === 'white') setWhiteClockMs(0);
      else setBlackClockMs(0);
      const winner: MoverColor = mover === 'white' ? 'black' : 'white';
      finalizeGame({ reason: 'timeout', winner });
      return true;
    },
    [finalizeGame],
  );

  /** See `UseBotGameClockResult.applyMoveDebit`. By construction the caller
   * already called `flagIfOutOfTime` before reaching this point, so
   * `debitMs` never exceeds the mover's remaining time — no floor-at-zero
   * clamp here (a floor would forgive an overrun, a never-flag pattern the
   * honest bot clock deliberately does not have). */
  const applyMoveDebit = useCallback(
    (mover: MoverColor, debitMs: number, incrementMs: number): number => {
      const remainingBeforeIncrement = clockBaseRef.current[mover] - debitMs;
      const remainingAfterIncrement = applyIncrementMs(remainingBeforeIncrement, incrementMs);
      clockBaseRef.current[mover] = remainingAfterIncrement;
      if (mover === 'white') setWhiteClockMs(remainingAfterIncrement);
      else setBlackClockMs(remainingAfterIncrement);
      return remainingAfterIncrement;
    },
    [],
  );

  /** See `UseBotGameClockResult.resetClock`. */
  const resetClock = useCallback((): void => {
    clockBaseRef.current = freshClockBase(baseSeconds);
    pausedAtRef.current = null;
    resetTurnAnchor();
    setWhiteClockMs(clockBaseRef.current.white);
    setBlackClockMs(clockBaseRef.current.black);
  }, [baseSeconds, resetTurnAnchor]);

  /** See `UseBotGameClockResult.getClockBase`. Always reads the LIVE
   * `clockBaseRef.current` at call time, not a memoized snapshot. */
  const getClockBase = useCallback((): { white: number; black: number } => clockBaseRef.current, []);

  // ─── Turn-anchor mount init ─────────────────────────────────────────────
  //
  // Sets the real wall-clock anchor once on mount (react-hooks/purity
  // forbids `Date.now()` inside the `turnStartedAtRef` useRef initializer
  // above). Declared BEFORE the clock-tick effect so it runs first within
  // the same commit — React runs passive effects in declaration order.
  //
  // Anchor after live: gated by `live` — for a fresh game `live` is true
  // from mount so this fires immediately. For a resumed game it no-ops until
  // `confirmLive()` flips `live` to true, at which point this effect
  // re-runs (its dep array includes `live`) and sets the anchor at THAT
  // moment — no clock runs while the resume gate is on screen.

  useEffect(() => {
    if (!live) return;
    const now = Date.now();
    turnStartedAtRef.current = now;
    // Bug fix: `visibilitychange` fires only on a TRANSITION, so a game
    // mounting into an ALREADY-hidden tab (background-tab open, session restore,
    // prerender, bfcache) never ran the hidden branch below — `pausedAtRef` stayed
    // null, `chargeableElapsedMs` degraded to a raw now-minus-anchor read, and the
    // tick flagged the active side on pure background wall-clock time. The resume
    // handler could not undo it either: its `!== null` guard fails, so the anchor
    // shift never runs and the overcharge is permanent. Seed the pause from the
    // INITIAL visibility state.
    if (document.visibilityState === 'hidden') pausedAtRef.current = now;
  }, [live]);

  // ─── Clock tick (wall-clock delta, never accumulated ticks) ────────────────
  //
  // The ACTIVE side's displayed clock is recomputed from the pause-aware
  // chargeableElapsedMs helper on every tick — flag-on-time (the only
  // loop-owned end condition) fires here.
  //
  // Gated by `live` — no clock runs while a resumed game's gate is still on
  // screen (see the turn-anchor mount-init effect above).

  useEffect(() => {
    if (!live) return;
    if (outcome) return;

    const tick = (): void => {
      const elapsed = chargeableElapsedMs();
      // Display-only floor (never applied to clockBaseRef.current itself) —
      // the tick's own remaining<=0 check below is what actually ends the
      // game; this only keeps the shown value from going negative for one
      // render.
      const rawRemaining = clockBaseRef.current[activeColor] - elapsed;
      const remaining = Math.max(0, rawRemaining);

      if (activeColor === 'white') setWhiteClockMs(remaining);
      else setBlackClockMs(remaining);

      // The user's low-time sound fires exactly once at the threshold
      // crossing, on the user's own clock only — not a repeating tick.
      if (activeColor === userColor && !hasFiredLowTimeRef.current && isLowTime(remaining)) {
        hasFiredLowTimeRef.current = true;
        playSound('low-time');
      }

      if (remaining <= 0) {
        // This check is INTENTIONALLY ungated by color — the bot can lose on
        // time exactly like the user. Do NOT add an
        // `activeColor === settings.userColor` guard here (the old never-flag
        // model did, and the honest bot clock reverses it). A bot whose
        // deadline-cut think still outlasts its remaining clock flags, and the
        // user wins — that is intended behavior, not a bug.
        const winner: MoverColor = activeColor === 'white' ? 'black' : 'white';
        finalizeGame({ reason: 'timeout', winner });
      }
    };

    tick();
    const id = setInterval(tick, CLOCK_TICK_INTERVAL_MS);
    return () => clearInterval(id);
    // hasFiredLowTimeRef arrives as a stable RefObject prop (always the same
    // identity), so listing it changes nothing about when this effect
    // re-runs; it only satisfies exhaustive-deps' static proof.
  }, [live, activeColor, outcome, finalizeGame, userColor, chargeableElapsedMs, hasFiredLowTimeRef]);

  // ─── Hidden-tab pause (matters most during the bot's think) ─────────────────

  useEffect(() => {
    const handleVisibility = (): void => {
      if (document.visibilityState === 'hidden') {
        // Idempotent: a duplicate 'hidden' event (Safari fires visibilitychange
        // alongside pagehide, and again on bfcache restore) must not re-baseline
        // an in-progress pause forward — that would silently charge the interval
        // between the two events.
        if (pausedAtRef.current === null) pausedAtRef.current = Date.now();
      } else if (pausedAtRef.current !== null) {
        const pausedForMs = Date.now() - pausedAtRef.current;
        turnStartedAtRef.current = shiftAnchorForPause(turnStartedAtRef.current, pausedForMs);
        pausedAtRef.current = null;
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  return {
    whiteClockMs,
    blackClockMs,
    resetTurnAnchor,
    chargeableElapsedMs,
    flagIfOutOfTime,
    applyMoveDebit,
    resetClock,
    getClockBase,
  };
}
