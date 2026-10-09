/**
 * useTrainWalkthrough — Phase 222 (D-24/D-12), rewritten by Phase 237 plan 10
 * for the chips + single move tree reveal and reworked by the Phase 237 UAT:
 * the first-reveal walkthrough's step state and everything that moves it,
 * extracted from `TrainSolveScreen` so the handlers and the scroll effect do
 * not push the component over its statement gate.
 *
 * Owns: the step index (reset per puzzle by the caller), the active-step
 * resolution against the settings watermark, the reveal bar's Next while the
 * tour runs (`consumeNext`), the tour overlay's hidden flag (`hide` on any
 * interaction with the reveal, `reopen` from Hilda's badge), the phone
 * scroll-to-target effect, and the stamp fired when the user leaves the reveal
 * from the last step.
 *
 * Phase 237 UAT (G-01): there is ONE Next, the reveal bar's. The tour never
 * auto-advances and never gates Next on the step's action; an interaction only
 * hides the phone overlay so the board is readable, and the next Next shows it
 * again with the next step.
 */
import { useCallback, useEffect, useState } from 'react';
import type { RefObject } from 'react';
import { WALKTHROUGH_STEP_COUNT, walkthroughCopy } from '@/lib/trainBotCopy';
import type { WalkthroughContext, WalkthroughStep, WalkthroughTarget } from '@/lib/trainBotCopy';
import { prefersReducedMotion } from '@/lib/confetti';
import { animateScrollTop } from '@/lib/animatedScroll';
import type { TrainSettingsResponse } from '@/types/train';
import type { OnboardingStep } from '@/hooks/useTrainOnboarding';

/** Targets whose element the phone scrolls into view during the tour (D-10);
 * the strip, the board row and the bar are already on screen (or fixed) and
 * need no scroll. `lines` scrolls to the chips. */
const WALKTHROUGH_SCROLL_TARGETS: ReadonlySet<WalkthroughTarget> = new Set<WalkthroughTarget>([
  'chips',
  'tree',
  'lines',
]);

/** Gap kept between the scrolled-to element and the pinned board block above
 * it or the fixed bottom bar below it. */
const WALKTHROUGH_SCROLL_GAP_PX = 12;

/**
 * Duration of the phone scroll tween. Quick task 260914-uer (QUICK-03): an
 * explicit rAF tween (`animateScrollTop`), half the speed of the browser's
 * native smooth scroll; this number is the single knob.
 */
const WALKTHROUGH_SCROLL_DURATION_MS = 700;

export interface UseTrainWalkthroughInput {
  /** `useTrainSettings().data` — undefined while loading or failed. */
  settings: TrainSettingsResponse | undefined;
  /** True once a verdict (`SolveResponse`) has landed for the puzzle on screen. */
  hasVerdict: boolean;
  /** Whether the action bar carries Analyze (own-game puzzle). */
  hasAnalyze: boolean;
  /** The second role of the merged Move chip ("Move = Best" / "Move = Game"), or
   * null when the Move chip stands alone — step 2 explains only what is shown. */
  mergedChip: WalkthroughContext['mergedChip'];
  isDesktop: boolean;
  /** The solve screen root — the tour targets are looked up inside it. */
  screenRef: RefObject<HTMLDivElement | null>;
  /** The phone-pinned progress + board block. */
  pinnedRef: RefObject<HTMLDivElement | null>;
  stamp: (step: OnboardingStep) => void;
}

export interface UseTrainWalkthroughResult {
  /** Non-null exactly while the walkthrough is showing. */
  activeStep: WalkthroughStep | null;
  /** The active step's spotlight target, or null while inactive. */
  target: WalkthroughTarget | null;
  /** The copy context the active step was resolved with (screen conditions). */
  context: WalkthroughContext;
  /** Resets the step index — call on every puzzle transition (D-12). */
  reset: () => void;
  /** The reveal bar's Next while the tour runs: on any step but the last it
   * advances the tour (showing the overlay again) and returns true, so the
   * caller must NOT also leave the puzzle. False when the tour is inactive or on
   * its last step: the bar's Next is then the real next-puzzle Next. */
  consumeNext: () => boolean;
  /** True while the phone overlay is hidden (after an interaction) until the
   * next Next or a tap on Hilda's badge. */
  overlayHidden: boolean;
  /** Hides the phone overlay: a chip tap, a list step, a board touch or fork,
   * a strip expand. Never moves the tour. Stable identity. */
  hide: () => void;
  /** Hilda's badge: shows the current step's overlay again. Stable identity. */
  reopen: () => void;
  /** Call when the user leaves the reveal through the action row (Next or
   * Analyze): stamps `reveal_walkthrough` if the walkthrough is on its last
   * step, else a no-op. */
  leave: () => void;
}

/**
 * Resolves whether the walkthrough is active this render — null while
 * inactive (settings not yet loaded, no verdict yet, or
 * `reveal_walkthrough_seen_at` already stamped), else the active step index.
 */
function resolveWalkthroughStep(
  settings: TrainSettingsResponse | undefined,
  hasVerdict: boolean,
  step: WalkthroughStep,
): WalkthroughStep | null {
  if (settings === undefined) return null;
  if (!hasVerdict) return null;
  if (settings.reveal_walkthrough_seen_at !== null) return null;
  return step;
}

/**
 * How far (px) the page must scroll so a phone tour target is fully visible
 * between the pinned board block and the fixed bottom bar: the least scroll
 * that clears the target's bottom, but never so far that its top slides behind
 * the pinned block. <= 0 means no scroll.
 *
 * Phase 237 UAT (G-01): the tour copy now sits in an overlay on the board, so
 * there is no in-flow bubble to scroll to; the strip and chips usually fit
 * under the board as they are and need no scroll at all.
 */
function computeTourScrollDelta(pinnedHeight: number, target: DOMRect, visibleBottom: number): number {
  const overflow = target.bottom + WALKTHROUGH_SCROLL_GAP_PX - visibleBottom;
  if (overflow <= 0) return 0;
  return Math.min(overflow, target.top - pinnedHeight - WALKTHROUGH_SCROLL_GAP_PX);
}

/** The top edge of the fixed phone bottom bar (the reveal's action bar), or the
 * viewport bottom when no fixed bar is mounted (sm..lg keeps it in flow). */
function visibleBottomEdge(): number {
  const bar = document.querySelector('[data-testid="mobile-board-controls-bar"]');
  return bar instanceof HTMLElement ? bar.getBoundingClientRect().top : window.innerHeight;
}

export function useTrainWalkthrough(input: UseTrainWalkthroughInput): UseTrainWalkthroughResult {
  const { settings, hasVerdict, hasAnalyze, mergedChip, isDesktop, screenRef, pinnedRef } = input;
  const { stamp } = input;
  // Only meaningful while `resolveWalkthroughStep` reports it active;
  // otherwise ignored. The caller resets it per puzzle so an abandoned
  // stepper replays on the next reveal (D-12).
  const [step, setStep] = useState<WalkthroughStep>(0);
  // Phase 237 UAT (G-01): the phone overlay hides on any reveal interaction so
  // the arrows and moves it covers are readable; Next or Hilda's badge shows it
  // again. Reset per puzzle with the step.
  const [overlayHidden, setOverlayHidden] = useState(false);
  const activeStep = resolveWalkthroughStep(settings, hasVerdict, step);
  const context: WalkthroughContext = { hasAnalyze, mergedChip, isDesktop };
  const target = activeStep === null ? null : walkthroughCopy(activeStep, context).spotlightTarget;
  const isLastStep = activeStep === WALKTHROUGH_STEP_COUNT - 1;
  const consumesNext = activeStep !== null && !isLastStep;

  const reset = useCallback(() => {
    setStep(0);
    setOverlayHidden(false);
  }, []);
  const consumeNext = useCallback((): boolean => {
    if (!consumesNext) return false;
    setStep((current) => Math.min(current + 1, WALKTHROUGH_STEP_COUNT - 1) as WalkthroughStep);
    setOverlayHidden(false);
    return true;
  }, [consumesNext]);
  const hide = useCallback(() => setOverlayHidden(true), []);
  const reopen = useCallback(() => setOverlayHidden(false), []);

  // D-10: on a phone, entering a step whose target sits below the fold scrolls
  // it into view (the page may scroll during the tour only; desktop shows
  // everything in its own column). Measured from the pinned block's own height
  // (not its current bottom edge) because the block re-anchors to the viewport
  // top as the page scrolls.
  useEffect(() => {
    if (target === null || isDesktop || !WALKTHROUGH_SCROLL_TARGETS.has(target)) return;
    const scrollTo = target === 'tree' ? 'tree' : 'chips';
    const element = screenRef.current?.querySelector(`[data-tour-target="${scrollTo}"]`);
    const pinned = pinnedRef.current;
    if (!(element instanceof HTMLElement) || pinned === null) return;
    const delta = computeTourScrollDelta(
      pinned.getBoundingClientRect().height,
      element.getBoundingClientRect(),
      visibleBottomEdge(),
    );
    if (delta <= 0) return;
    // The page itself is the scroller here (the feedback scrolls behind the
    // pinned board); `document.scrollingElement` is the element whose
    // `scrollTop` moves it (`documentElement` is the standards-mode fallback,
    // and what jsdom offers). Reduced motion jumps instantly via a 0ms duration.
    const scroller = document.scrollingElement ?? document.documentElement;
    animateScrollTop(scroller as HTMLElement, delta, prefersReducedMotion() ? 0 : WALKTHROUGH_SCROLL_DURATION_MS);
  }, [target, isDesktop, screenRef, pinnedRef]);

  // D-12 (UAT round 3): the walkthrough is stamped as seen when the user
  // LEAVES the first reveal through its last step's action row (Next or
  // Analyze). Guarded on the LAST step so an abandoned walkthrough (unmount,
  // reload) still replays next time; the stamp's `onSuccess` writes the
  // settings cache, which flips `activeStep` to null (same settings-only-guard
  // pattern plan 04 used for the intro stamp). Rewind stays inside the reveal
  // and never completes it.
  const leave = useCallback(() => {
    if (!isLastStep) return;
    stamp('reveal_walkthrough');
  }, [isLastStep, stamp]);

  return { activeStep, target, context, reset, consumeNext, overlayHidden, hide, reopen, leave };
}
