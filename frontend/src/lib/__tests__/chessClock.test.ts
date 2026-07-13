/**
 * chessClock.ts unit tests (Phase 169 Plan 01, amended Plan 08 gap closure).
 *
 * All functions under test are pure and synchronous, so no fake timers or DOM
 * are needed — every "elapsed"/"pause"/"deadline" scenario is driven by
 * explicit millisecond inputs rather than real Date.now()/setInterval calls,
 * matching how useBotGame (plan 04, amended plan 09) actually calls these
 * helpers with its own wall-clock anchors.
 *
 * Behaviors verified (RESEARCH.md Validation Architecture test map, amended
 * by 169-CONTEXT.md's 2026-07-13 Decision Amendments):
 * - PLAY-03: Fischer increment application
 * - PLAY-04: wall-clock elapsed delta + visibility-pause anchor shift
 * - D-15/D-16: the bot's clock is honest (no synthetic debit, no never-flag
 *   clamp) and `computeThinkDeadlineMs` derives its per-move think deadline
 * - D-07: low-time tenths display formatting
 */

import { describe, it, expect } from 'vitest';
import {
  applyIncrementMs,
  computeElapsedMs,
  shiftAnchorForPause,
  computeThinkDeadlineMs,
  computeRevealDelayMs,
  computeChargeableElapsedMs,
  hasFlaggedOnDebit,
  isLowTime,
  formatClockLabel,
  REVEAL_DELAY_MIN_MS,
  REVEAL_DELAY_MAX_MS,
  LOW_TIME_THRESHOLD_MS,
  BOT_THINK_DEADLINE_MIN_MS,
  BOT_THINK_DEADLINE_MAX_MS,
} from '../chessClock';

describe('applyIncrementMs (PLAY-03 Fischer increment)', () => {
  it('adds the increment exactly to the mover remaining time', () => {
    expect(applyIncrementMs(5000, 2000)).toBe(7000);
  });

  it('never returns a negative value', () => {
    expect(applyIncrementMs(-5000, 0)).toBe(0);
  });
});

describe('computeElapsedMs (PLAY-04 wall-clock delta)', () => {
  it('returns now - anchor regardless of how many ticks elapsed', () => {
    // No setInterval involved at all — a caller could have "ticked" any
    // number of times between anchor and now, the result only depends on
    // the two timestamps.
    expect(computeElapsedMs(1_000_000, 1_004_500)).toBe(4500);
  });

  it('is zero when now equals the anchor', () => {
    expect(computeElapsedMs(2_000_000, 2_000_000)).toBe(0);
  });
});

describe('visibility pause (PLAY-04)', () => {
  it('charges zero time for a 60s hidden interval', () => {
    const turnStartedAt = 1_000_000;
    const hiddenForMs = 60_000;

    // Tab goes hidden immediately at turn start; anchor shifts forward by
    // the full hidden duration on resume.
    const shiftedAnchor = shiftAnchorForPause(turnStartedAt, hiddenForMs);

    // "now" is exactly when the tab becomes visible again (no additional
    // visible time has passed yet) — elapsed must be zero.
    const nowAtResume = turnStartedAt + hiddenForMs;
    expect(computeElapsedMs(shiftedAnchor, nowAtResume)).toBe(0);
  });

  it('still counts time that elapses after the hidden interval ends', () => {
    const turnStartedAt = 1_000_000;
    const hiddenForMs = 60_000;
    const visibleAfterMs = 3_000;

    const shiftedAnchor = shiftAnchorForPause(turnStartedAt, hiddenForMs);
    const now = turnStartedAt + hiddenForMs + visibleAfterMs;

    expect(computeElapsedMs(shiftedAnchor, now)).toBe(visibleAfterMs);
  });
});

describe('computeThinkDeadlineMs (D-16 per-move think deadline)', () => {
  it('at a full 5+3 clock, comfortably exceeds the 168.5-04 measured ~5.4s median search', () => {
    const MEASURED_MEDIAN_SEARCH_MS = 5400;
    expect(computeThinkDeadlineMs(300_000, 3_000)).toBeGreaterThan(MEASURED_MEDIAN_SEARCH_MS);
  });

  it('shrinks monotonically as remainingMs shrinks, holding incrementMs fixed', () => {
    const incrementMs = 3_000;
    const deadlineAtLowClock = computeThinkDeadlineMs(20_000, incrementMs);
    const deadlineAtHighClock = computeThinkDeadlineMs(200_000, incrementMs);

    expect(deadlineAtLowClock).toBeLessThan(deadlineAtHighClock);
  });

  it('never falls below the min band nor exceeds the max band while the bot can afford it', () => {
    // Small remaining clock, zero increment: raw formula undershoots the
    // band floor, but the clock can still easily afford the floored value.
    const belowBand = computeThinkDeadlineMs(10_000, 0);
    expect(belowBand).toBe(BOT_THINK_DEADLINE_MIN_MS);

    // Very long remaining clock with a large increment: raw formula
    // overshoots the band ceiling, and the clock can easily afford the
    // capped value.
    const aboveBand = computeThinkDeadlineMs(1_000_000, 10_000);
    expect(aboveBand).toBe(BOT_THINK_DEADLINE_MAX_MS);
  });

  it('never schedules a think the bot cannot afford, and never goes negative', () => {
    // Tiny remaining clock, huge increment: the raw/banded formula would
    // exceed the clock outright — the affordability cap must win.
    const deadline = computeThinkDeadlineMs(1_000, 10_000);
    expect(deadline).toBeLessThan(1_000);
    expect(deadline).toBeGreaterThanOrEqual(0);
  });

  it('still yields a usable positive deadline at zero increment', () => {
    expect(computeThinkDeadlineMs(300_000, 0)).toBeGreaterThan(0);
  });
});

describe('computeRevealDelayMs (D-03 reveal-delay floor)', () => {
  it('returns the minimum when rng returns 0', () => {
    expect(computeRevealDelayMs(() => 0)).toBe(REVEAL_DELAY_MIN_MS);
  });

  it('stays within [min, max) for rng in [0, 1)', () => {
    const stubbedRngValues = [0, 0.25, 0.5, 0.75, 0.999];
    for (const value of stubbedRngValues) {
      const delay = computeRevealDelayMs(() => value);
      expect(delay).toBeGreaterThanOrEqual(REVEAL_DELAY_MIN_MS);
      expect(delay).toBeLessThan(REVEAL_DELAY_MAX_MS);
    }
  });
});

describe('computeChargeableElapsedMs (D-20 in-progress pause)', () => {
  it('returns now - anchor when the tab is visible (pausedAtMs === null)', () => {
    expect(computeChargeableElapsedMs(1000, null, 33000)).toBe(32000);
  });

  it('freezes elapsed time at the pause instant when the tab is hidden right now', () => {
    // anchor 1000, hidden at 3000, now 33000 -> 2000 (frozen at the hide
    // instant, NOT 32000 which a raw now-minus-anchor read would give).
    expect(computeChargeableElapsedMs(1000, 3000, 33000)).toBe(2000);
  });

  it('never returns a negative value for a well-formed anchor <= pausedAt', () => {
    expect(computeChargeableElapsedMs(1000, 1000, 33000)).toBe(0);
  });

  it('composes with shiftAnchorForPause: the in-progress freeze plus the resume-edge shift charges only the visible time', () => {
    const anchorMs = 1_000_000;
    const hideAtMs = anchorMs + 2_000; // 2s visible before hiding
    const stillHiddenNowMs = hideAtMs + 40_000; // 40s hidden so far, still hidden

    // While still hidden: elapsed is frozen at the pause instant, so a tick
    // firing during the hidden window reads exactly the pre-hide visible time.
    expect(computeChargeableElapsedMs(anchorMs, hideAtMs, stillHiddenNowMs)).toBe(2_000);

    // On resume, the hidden interval that just ENDED is discounted via the
    // existing retroactive shift — composing the two mechanisms.
    const resumeAtMs = hideAtMs + 40_000; // tab becomes visible again
    const pausedForMs = resumeAtMs - hideAtMs;
    const shiftedAnchor = shiftAnchorForPause(anchorMs, pausedForMs);
    const laterVisibleMs = resumeAtMs + 3_000; // 3s more visible time passes

    // Total charged time = 2s (pre-hide) + 3s (post-resume) = 5s; the 40s
    // hidden window never reaches the charged total either way it's read.
    expect(computeChargeableElapsedMs(shiftedAnchor, null, laterVisibleMs)).toBe(5_000);
  });
});

describe('hasFlaggedOnDebit (D-15 honest flag)', () => {
  it('flags when the debit exceeds the remaining time', () => {
    expect(hasFlaggedOnDebit(3000, 6600)).toBe(true);
  });

  it('flags when the debit exactly consumes the remaining time (matches the tick\'s remaining <= 0 rule)', () => {
    expect(hasFlaggedOnDebit(3000, 3000)).toBe(true);
  });

  it('does not flag when the debit is less than the remaining time', () => {
    expect(hasFlaggedOnDebit(3000, 1400)).toBe(false);
  });
});

describe('isLowTime / formatClockLabel (D-07 low-time tenths display)', () => {
  it('is not low-time exactly at the threshold (strict less-than)', () => {
    expect(isLowTime(LOW_TIME_THRESHOLD_MS)).toBe(false);
    expect(isLowTime(LOW_TIME_THRESHOLD_MS - 1)).toBe(true);
  });

  it('emits "m:ss" with no decimal above the low-time threshold', () => {
    expect(formatClockLabel(125_000)).toBe('2:05');
    expect(formatClockLabel(LOW_TIME_THRESHOLD_MS)).toBe('0:10');
  });

  it('emits a tenths decimal below the low-time threshold', () => {
    expect(formatClockLabel(9_400)).toBe('0:09.4');
  });

  it('clamps zero/negative remaining time to "0:00"', () => {
    expect(formatClockLabel(0)).toBe('0:00');
    expect(formatClockLabel(-500)).toBe('0:00');
  });
});
