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

import { WDL_WIN, CELEBRATION_GOLD, CELEBRATION_AMBER } from '@/lib/theme';

/** Confetti particle colors — reuses the WDL win color plus two warm accents
 * (gold/amber) so the burst reads as a celebratory palette rather than a
 * single flat green. All colors come from theme.ts per CLAUDE.md. */
const CONFETTI_COLORS = [WDL_WIN, CELEBRATION_GOLD, CELEBRATION_AMBER];

/** Origin y for both bursts — slightly below center so the confetti arcs
 * upward over the board rather than starting at the very top of the
 * viewport. */
const CONFETTI_ORIGIN_Y = 0.6;

/** Particle counts for the two bursts (left-leaning + right-leaning) that
 * together read as one symmetric celebration burst. */
const CONFETTI_PARTICLE_COUNT = 60;

/**
 * Fires a short two-burst confetti celebration (one angled from each side)
 * over the current viewport. Call only on a human win, and only when
 * `!prefersReducedMotion()`.
 */
export function fireWinConfetti(): void {
  confetti({
    particleCount: CONFETTI_PARTICLE_COUNT,
    angle: 60,
    spread: 55,
    origin: { x: 0, y: CONFETTI_ORIGIN_Y },
    colors: CONFETTI_COLORS,
  });
  confetti({
    particleCount: CONFETTI_PARTICLE_COUNT,
    angle: 120,
    spread: 55,
    origin: { x: 1, y: CONFETTI_ORIGIN_Y },
    colors: CONFETTI_COLORS,
  });
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
