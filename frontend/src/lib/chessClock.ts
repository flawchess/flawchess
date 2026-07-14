/**
 * Pure, synchronous, React-free clock and pacing math for bot games (Phase 169).
 *
 * Extracted to a standalone module so the trickiest timing logic in the phase
 * (the D-16 per-move think deadline, the PLAY-04 wall-clock model) is
 * directly unit-testable with fake timers and zero DOM/React, mirroring
 * analysisUrl.ts's "extracted for unit-testability" precedent.
 *
 * Every helper here is deterministic given its inputs: elapsed time is always
 * recomputed from `Date.now()` deltas (never accumulated `setInterval` tick
 * counts, which drift under background-tab throttling — see
 * useFlawChessEngine.ts's identical `Date.now() - anchor` discipline used for
 * its FEN debounce). `useBotGame` (plan 04, amended plan 09) and
 * `ClockDisplay` (plan 05) compose these helpers; neither owns its own timing
 * math.
 *
 * D-15 (2026-07-13, SUPERSEDES 168.5 D-02/D-04/D-05 — reversed, not
 * refined): the bot's clock is HONEST. Its debit is exactly the real
 * wall-clock time its turn consumed (search + reveal delay) plus the Fischer
 * increment on commit — the same rule `applyIncrementMs` + `computeElapsedMs`
 * already give the user. There is no synthetic fraction-of-remaining debit
 * helper and no never-flag clamp constant anywhere in this module (the old
 * 168.5 D-02 machinery converged to a ~6s equilibrium at the shipped 5+3
 * preset and is DELETED here, not guarded — do not reintroduce a
 * synthetic-debit or never-flag concept under any name). The bot CAN lose on
 * time exactly like the user (ROADMAP SC1, amended). As of Plan 10 (gap
 * closure, CR-02) this invariant is ENFORCED at the commit site: `useBotGame`
 * calls `hasFlaggedOnDebit` before applying either mover's move, and only
 * commits when it returns false. `applyIncrementMs`'s floor-at-zero is an
 * increment guard against a negative starting value, NOT a debit clamp — it
 * must never be used to forgive an overrun.
 *
 * D-16: an honest clock with a *fixed* search budget is degenerate (a bot
 * that always spends ~5.4s median against a 3s increment bleeds net time
 * every move). So the bot manages its clock via `computeThinkDeadlineMs`
 * below, a per-move think deadline derived from its own remaining time, that
 * `deadlineSearch.ts` (plan 08 task 2) enforces from OUTSIDE the frozen
 * search core by cutting the in-flight search and returning its best-so-far
 * result.
 *
 * D-19 (must-read before retuning ANY constant below or in botBudget.ts): the
 * bot's calibrated ELO (168.5's fixed 50-node budget, measured by
 * scripts/calibration-harness.mjs, which never runs a clock) holds ONLY at
 * the full node budget. When `computeThinkDeadlineMs` cuts a think short in
 * time trouble, `deadlineSearch.ts` returns a best-so-far snapshot built from
 * fewer nodes, and the bot plays materially weaker than its advertised ELO
 * for that move. This is accepted and desirable — humans get worse in time
 * trouble too — but it means the shipped ELO label is accurate only when the
 * bot is not low on its own clock. A future reader must not "fix" this
 * divergence, and must not mistake calibration-harness numbers for whole-game
 * strength.
 *
 * NOTE: formatClockLabel is a DISPLAY formatter ("m:ss" / "m:ss.d" tenths). It
 * is NOT the PGN `[%clk h:mm:ss]` formatter used for the finished-game export
 * — that lives in botGamePgn.ts (plan 02), which follows lichess's PGN
 * convention instead of this module's UI-facing shorthand.
 */

import type { MoverColor } from '@/lib/liveFlaw';

// ─── Named constants ─────────────────────────────────────────────────────────

/** Minimum synthetic "thinking" reveal delay so near-instant bot moves (e.g.
 * blend=0 resolving in ~0.09s per 168.5 measurement) don't feel robotic. D-03. */
export const REVEAL_DELAY_MIN_MS = 500;

/** Maximum synthetic reveal delay — keeps the ~0.5-1.5s ballpark 168.5 locked
 * so a 5+0 blitz game still paces plausibly. D-03. */
export const REVEAL_DELAY_MAX_MS = 1500;

/** Below this remaining-time threshold the clock display switches to tenths
 * precision and urgent styling (lichess-style low-time display). D-07. */
export const LOW_TIME_THRESHOLD_MS = 10000;

/**
 * D-16 think-deadline divisor: `remainingMs / BOT_MOVES_TO_GO` is the
 * baseline per-move time slice, the standard "moves-to-go" chess-engine
 * time-management convention. Tuned by feel against the 168.5-04 measured
 * search cost (median ~5.4s, worst-case ~12.7s per move at the locked
 * 50-node budget): 30 gives a full-clock 5+3 bot a ~10s baseline slice —
 * comfortably above the median so contested opening/middlegame thinks run to
 * completion — while still shrinking fast enough in the endgame (fewer
 * moves realistically remain, but this constant intentionally does NOT
 * adapt to game phase — Claude's-discretion simplicity) that the bot is
 * forced to speed up well before its clock actually empties.
 */
export const BOT_MOVES_TO_GO = 30;

/** Share of the Fischer increment folded into the D-16 think deadline
 * (`incrementMs * BOT_THINK_INCREMENT_SHARE`). Less than 1.0 so the bot
 * banks a small margin of every increment toward the NEXT move's deadline
 * rather than spending the whole increment on the move that earned it —
 * this is what lets `computeThinkDeadlineMs` grow the deadline again as
 * increments accumulate faster than the clock drains. Tuned by feel. */
export const BOT_THINK_INCREMENT_SHARE = 0.7;

/** D-16 deadline band floor — even in genuine time trouble the bot gets at
 * least this long to think, so the D-18 min-node floor below has a
 * realistic chance of being reached before a deadline abort fires. Tuned by
 * feel: comfortably above `BOT_MOVE_OVERHEAD_MS` so the band floor and the
 * affordability cap (see `computeThinkDeadlineMs`) rarely fight each other. */
export const BOT_THINK_DEADLINE_MIN_MS = 800;

/** D-16 deadline band ceiling — caps the think deadline from a very full or
 * very long-format clock so the bot doesn't sit and "overthink" a settled
 * position; also keeps a single move's deadline from ever exceeding the
 * 168.5-04 measured worst-case-plus-margin search cost (~12.7s) by very
 * much, since nothing is gained past that point (the search would have
 * finished naturally on its own budget anyway). Tuned by feel. */
export const BOT_THINK_DEADLINE_MAX_MS = 15000;

/** Reserve subtracted from the bot's remaining clock before it is allowed to
 * schedule a think, so a scheduled deadline (plus normal move-commit/PGN
 * bookkeeping overhead) can never itself push the bot's clock to exactly
 * zero or below by construction. This is the affordability cap in
 * `computeThinkDeadlineMs`, NOT a never-flag clamp (D-15): a bot whose
 * remaining clock is already below this reserve gets a deadline of 0 (an
 * immediate cut, gated only by the D-18 node floor in `deadlineSearch.ts`)
 * and can still flag if the floor overruns what little clock remains — that
 * is the intended, honest behavior. Tuned by feel. */
export const BOT_MOVE_OVERHEAD_MS = 300;

// Unit-conversion constants (not tunable thresholds, but named per CLAUDE.md's
// no-magic-numbers rule so formatClockLabel's body stays literal-free).
const MS_PER_SECOND = 1000;
const SECONDS_PER_MINUTE = 60;
const MS_PER_DECISECOND = 100;
const DECISECONDS_PER_SECOND = 10;
const DECISECONDS_PER_MINUTE = SECONDS_PER_MINUTE * DECISECONDS_PER_SECOND;
const CLOCK_LABEL_PAD_WIDTH = 2;

// ─── Pure helpers ────────────────────────────────────────────────────────────

/**
 * Applies a Fischer increment to a mover's remaining time after their move.
 * Never returns a negative value.
 */
export function applyIncrementMs(remainingMs: number, incrementMs: number): number {
  return Math.max(0, remainingMs + incrementMs);
}

/**
 * Elapsed time recomputed from a wall-clock anchor, never from accumulated
 * tick counts (PLAY-04) — safe across background-tab throttling.
 */
export function computeElapsedMs(anchorMs: number, nowMs: number): number {
  return nowMs - anchorMs;
}

/**
 * Shifts a turn's wall-clock anchor forward by the hidden-tab pause duration
 * so zero time is charged while the tab was hidden (PLAY-04).
 */
export function shiftAnchorForPause(anchorMs: number, pausedForMs: number): number {
  return anchorMs + pausedForMs;
}

/**
 * D-20 (Plan 10 gap closure, CR-01): the SINGLE "elapsed time that may be
 * charged to a clock" function. When `pausedAtMs` is null the tab is
 * visible and this is identical to `computeElapsedMs(anchorMs, nowMs)`; when
 * it is non-null the tab is hidden RIGHT NOW, and elapsed time is FROZEN at
 * the instant the tab went hidden, so no caller can charge background
 * wall-clock time.
 *
 * `shiftAnchorForPause` is a RETROACTIVE correction applied on the resume
 * edge and therefore cannot help a clock read that runs DURING the hidden
 * period — a throttled background tick, or a bot search resolving while the
 * tab is still hidden (the common case, since Web Workers keep executing
 * when backgrounded). The two compose: this helper covers the in-progress
 * pause, `shiftAnchorForPause` covers the already-finished one. Every clock
 * consumer must go through this function, not a raw now-minus-anchor read.
 */
export function computeChargeableElapsedMs(
  anchorMs: number,
  pausedAtMs: number | null,
  nowMs: number,
): number {
  return computeElapsedMs(anchorMs, pausedAtMs ?? nowMs);
}

/**
 * D-15 (Plan 10 gap closure, CR-02): the commit-time flag test. The caller
 * MUST consult this BEFORE applying a move and end the game as a timeout
 * when it returns true. Forgiving the overrun by flooring the subtraction at
 * zero and then applying the Fischer increment is the never-flag backdoor
 * D-15 forbids — it resurrects a mover that had already lost on time. The
 * D-18 node-floor overrun makes this reachable by design, not merely
 * theoretical.
 */
export function hasFlaggedOnDebit(remainingMs: number, debitMs: number): boolean {
  return remainingMs - debitMs <= 0;
}

/**
 * D-16: derives the bot's per-move think deadline from its own remaining
 * clock time and the increment it plays with. Engine-convention formula,
 * applied in this exact order:
 *
 *   1. `raw = remainingMs / BOT_MOVES_TO_GO + incrementMs * BOT_THINK_INCREMENT_SHARE`
 *   2. clamp `raw` into the `[BOT_THINK_DEADLINE_MIN_MS, BOT_THINK_DEADLINE_MAX_MS]` band
 *   3. hard-cap the banded result at `remainingMs - BOT_MOVE_OVERHEAD_MS` — the
 *      affordability cap that keeps a large increment from scheduling a
 *      think the bot cannot pay for
 *   4. floor at 0
 *
 * The result shrinks monotonically as `remainingMs` shrinks (holding
 * `incrementMs` fixed) — this is what makes the bot speed up in time
 * trouble. The ONLY remaining flag path once this deadline is enforced by
 * `deadlineSearch.ts` is the D-18 node-floor overrun, which is intended
 * (D-15/D-18) — this function itself never clamps toward "never flag".
 */
export function computeThinkDeadlineMs(remainingMs: number, incrementMs: number): number {
  const raw = remainingMs / BOT_MOVES_TO_GO + incrementMs * BOT_THINK_INCREMENT_SHARE;
  const banded = Math.min(BOT_THINK_DEADLINE_MAX_MS, Math.max(BOT_THINK_DEADLINE_MIN_MS, raw));
  const affordable = Math.min(banded, remainingMs - BOT_MOVE_OVERHEAD_MS);
  return Math.max(0, affordable);
}

/**
 * Randomized reveal-delay floor (D-03) within
 * [REVEAL_DELAY_MIN_MS, REVEAL_DELAY_MAX_MS). `rng` must return a value in
 * [0, 1) — inject a stubbed rng in tests, `Math.random` in the app.
 */
export function computeRevealDelayMs(rng: () => number): number {
  return REVEAL_DELAY_MIN_MS + rng() * (REVEAL_DELAY_MAX_MS - REVEAL_DELAY_MIN_MS);
}

/** Whether remaining time is below the low-time display threshold (D-07). */
export function isLowTime(remainingMs: number): boolean {
  return remainingMs < LOW_TIME_THRESHOLD_MS;
}

/**
 * Module-private zero-clamped subtraction — kept unexported so `npm run
 * knip` does not flag a single-consumer export (its only caller is
 * `foldClockBasesForSnapshot` below).
 */
function foldElapsedIntoClockBase(remainingMs: number, elapsedMs: number): number {
  return Math.max(0, remainingMs - elapsedMs);
}

/**
 * Phase 170 D-01/D-02: the SINGLE place the leave/resume clock-fold
 * asymmetry is expressed. D-01 ("bill think time"): when the USER is the
 * active side, their in-turn `chargeableElapsedMs` is folded into their own
 * clock base before the snapshot is written, so a user who thinks 40s and
 * closes the tab resumes with those 40s spent. D-02 ("refund away time"):
 * when the BOT is the active side, its clock base is returned unchanged as
 * of its last commit — the bot's in-flight search dies with the Web Workers
 * on unload, so billing it for thrown-away work would be wrong (no user
 * exploit exists: refunding the bot's clock only ever helps the bot).
 * Always returns a NEW object; never mutates `bases` — the caller passes
 * `clockBaseRef.current` directly, and mutating it would make the next real
 * `commitMove()` double-subtract the same elapsed time (once via this fold,
 * once via its own `chargeableElapsedMs()` read).
 */
export function foldClockBasesForSnapshot(
  bases: { white: number; black: number },
  activeColor: MoverColor,
  userColor: MoverColor,
  chargeableElapsedMs: number,
): { white: number; black: number } {
  if (activeColor !== userColor) {
    return { ...bases };
  }
  return {
    ...bases,
    [activeColor]: foldElapsedIntoClockBase(bases[activeColor], chargeableElapsedMs),
  };
}

/**
 * Formats remaining time for display: "m:ss" normally, "m:ss.d" (tenths) once
 * isLowTime is true (D-07, lichess-style low-time display). Negative/zero
 * remaining time clamps to "0:00".
 */
export function formatClockLabel(remainingMs: number): string {
  if (remainingMs <= 0) return '0:00';

  if (isLowTime(remainingMs)) {
    const totalDeciseconds = Math.floor(remainingMs / MS_PER_DECISECOND);
    const minutes = Math.floor(totalDeciseconds / DECISECONDS_PER_MINUTE);
    const secondsPart = Math.floor(
      (totalDeciseconds % DECISECONDS_PER_MINUTE) / DECISECONDS_PER_SECOND,
    );
    const tenths = totalDeciseconds % DECISECONDS_PER_SECOND;
    return `${minutes}:${String(secondsPart).padStart(CLOCK_LABEL_PAD_WIDTH, '0')}.${tenths}`;
  }

  const totalSeconds = Math.floor(remainingMs / MS_PER_SECOND);
  const minutes = Math.floor(totalSeconds / SECONDS_PER_MINUTE);
  const seconds = totalSeconds % SECONDS_PER_MINUTE;
  return `${minutes}:${String(seconds).padStart(CLOCK_LABEL_PAD_WIDTH, '0')}`;
}
