/**
 * Bot-win celebration confetti helper (Quick 260723-tqn).
 *
 * Thin wrapper around `canvas-confetti` (an untyped canvas-based one-shot
 * burst renderer, no framework dependency) so `useBotGame`'s `finalizeGame`
 * has a single call site to fire from on a human win. `prefersReducedMotion`
 * guards the call site: reduced-motion users get the outcome sound but no
 * confetti and no result-modal delay (see `useWinCelebrationHold`).
 */

import confetti from 'canvas-confetti';

import { CONFETTI_COLORS } from '@/lib/theme';

/** Origin y for both bursts — slightly below center so the confetti arcs
 * upward over the board rather than starting at the very top of the
 * viewport. */
const CONFETTI_ORIGIN_Y = 0.6;

/** Particle counts for the two bursts (left-leaning + right-leaning) that
 * together read as one symmetric celebration burst. */
const CONFETTI_PARTICLE_COUNT = 60;

/** Spread (degrees) of each full-celebration burst. */
const CONFETTI_SPREAD = 55;

/** Lifetime of every particle, in canvas-confetti "ticks" (one tick per
 * animation frame). Passed EXPLICITLY rather than left at the library
 * default so the burst's duration is a number this module owns and can
 * export — `useWinCelebrationHold` holds the bot-game result modal closed
 * for exactly `CONFETTI_DURATION_MS`, and that coupling has to be a shared
 * constant, not a guess. Phase 223 UAT: the previous 1300ms hold was
 * derived from a guess and expired with roughly half the burst still on
 * screen, so the modal covered the board mid-celebration. */
const CONFETTI_TICKS = 180;

/** Frames per second the ticks above are spent at. Browsers animate
 * requestAnimationFrame at ~60fps; a 120Hz display finishes the burst
 * sooner, which only ever makes the hold slightly generous. */
const CONFETTI_FPS = 60;

/**
 * How long a burst from this module stays on screen, in milliseconds.
 * Exported so the bot-game result modal can wait the celebration out
 * instead of guessing at it.
 */
export const CONFETTI_DURATION_MS = Math.ceil((CONFETTI_TICKS / CONFETTI_FPS) * 1000);

/** Particle count for the muted burst — a visibly smaller celebration for a
 * partial result (the Train score screen's yellow band), so a "decent but not
 * great" session reads as acknowledged rather than celebrated. */
const CONFETTI_PARTIAL_PARTICLE_COUNT = 20;

/** Spread (degrees) of the partial burst — narrower than the full one so the
 * fewer particles still read as a deliberate burst, not a stray scatter. */
const CONFETTI_PARTIAL_SPREAD = 40;

function fireBursts(particleCount: number, spread: number): void {
  confetti({
    particleCount,
    angle: 60,
    spread,
    ticks: CONFETTI_TICKS,
    origin: { x: 0, y: CONFETTI_ORIGIN_Y },
    colors: CONFETTI_COLORS,
  });
  confetti({
    particleCount,
    angle: 120,
    spread,
    ticks: CONFETTI_TICKS,
    origin: { x: 1, y: CONFETTI_ORIGIN_Y },
    colors: CONFETTI_COLORS,
  });
}

/**
 * Fires a short two-burst confetti celebration (one angled from each side)
 * over the current viewport. Call only on a human win, and only when
 * `!prefersReducedMotion()`.
 */
export function fireWinConfetti(): void {
  fireBursts(CONFETTI_PARTICLE_COUNT, CONFETTI_SPREAD);
}

/**
 * Same two-burst shape as `fireWinConfetti` at roughly a third of the
 * particles — the partial-success variant. Same reduced-motion contract:
 * only call when `!prefersReducedMotion()`.
 */
export function firePartialConfetti(): void {
  fireBursts(CONFETTI_PARTIAL_PARTICLE_COUNT, CONFETTI_PARTIAL_SPREAD);
}

/**
 * Reads the OS/browser `prefers-reduced-motion` media query. Treats a
 * missing `window.matchMedia` (SSR, older browsers, some test environments)
 * as "not reduced-motion" — i.e. animate by default — rather than throwing.
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}
