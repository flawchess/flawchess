/**
 * useTrainWalkthrough: Phase 222 (D-24/D-12), rewritten by Phase 237 plan 10
 * for the chips + single move tree reveal and by Phase 240 (D-06..D-08, D-23)
 * for the split tour: the first-reveal tour's state and everything that moves
 * it, extracted from `TrainSolveScreen` so the handlers and the scroll effect
 * do not push the component over its statement gate.
 *
 * The tour is three parts on consecutive reveals, at most one per reveal. The
 * part due is `tourPartForStage(settings.reveal_tour_stage)`, LATCHED once per
 * reveal at the first render that has a verdict and loaded settings: the leave
 * stamp's `setQueryData` bumps the stage mid-reveal, and without the latch that
 * would switch the part under the user (RESEARCH Pitfall 2). A stale latch can
 * only replay a part (the server no-ops the duplicate advance), never skip one.
 * A reveal restored after the Analyze round trip (`isRestored`) never starts a
 * part: it is the same reveal the user left, so "at most one part per reveal"
 * holds even when the part was finished by the Analyze click; a part left
 * halfway replays on the next puzzle's reveal (D-08).
 *
 * Owns: the latch, the step index within the part (reset per puzzle by the
 * caller), the reveal bar's Next while a part runs (`consumeNext`), the tour
 * overlay's hidden flag (`hide` on any interaction with the reveal, `reopen`
 * from Hilda's badge), the phone scroll-to-target effect, and the stamp fired
 * when the user leaves the reveal from a part's last step.
 *
 * Phase 237 UAT (G-01): there is ONE Next, the reveal bar's. The tour never
 * auto-advances and never gates Next on the step's action; an interaction only
 * hides the phone overlay so the board is readable, and the next Next shows it
 * again with the next step.
 */
import { useCallback, useEffect, useState } from 'react';
import type { RefObject } from 'react';
import { isRevealTourDone, tourPartForStage, tourPartSteps, tourStepCopy } from '@/lib/trainBotCopy';
import type {
  TourPart,
  TourStepId,
  WalkthroughContext,
  WalkthroughTarget,
} from '@/lib/trainBotCopy';
import { prefersReducedMotion } from '@/lib/confetti';
import { animateScrollTop } from '@/lib/animatedScroll';
import type { TrainSettingsResponse } from '@/types/train';
import type { OnboardingStep, RevealTourStep } from '@/hooks/useTrainOnboarding';

/** The onboarding step stamped when a part is finished (Phase 240 D-09): part N
 * advances the server's stage to N + 1. */
const REVEAL_TOUR_STAMP: Record<TourPart, RevealTourStep> = {
  0: 'reveal_tour_1',
  1: 'reveal_tour_2',
  2: 'reveal_tour_3',
};

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
  /** What the action bar's Analyze opens: the own source game, or just the puzzle position. */
  analyzeOpens: WalkthroughContext['analyzeOpens'];
  /** Desktop skips the phone-only scroll-to-target; of the copy, only the result
   * step branches on it (the phone strip opens on tap). */
  isDesktop: boolean;
  /** True when the reveal on screen was restored after the Analyze round trip: it
   * never starts a part (the user already saw this reveal). */
  isRestored: boolean;
  /** The solve screen root — the tour targets are looked up inside it. */
  screenRef: RefObject<HTMLDivElement | null>;
  /** The phone-pinned progress + board block. */
  pinnedRef: RefObject<HTMLDivElement | null>;
  stamp: (step: OnboardingStep) => void;
}

export interface UseTrainWalkthroughResult {
  /** Non-null exactly while a tour part is showing. */
  activeStep: TourStepId | null;
  /** Index of the active step within its part (D-23: the counter is per part). */
  stepIndex: number;
  /** Number of steps in the active part, 0 while inactive. */
  stepCount: number;
  /** The part on screen, or null while inactive. */
  part: TourPart | null;
  /** The active step's spotlight target, or null while inactive. */
  target: WalkthroughTarget | null;
  /** The copy context the active step was resolved with (screen conditions). */
  context: WalkthroughContext;
  /** Clears the part latch, the step index and the hidden flag: call on every
   * puzzle transition (D-12). */
  reset: () => void;
  /** The reveal bar's Next while a part runs: on any step but the part's last it
   * advances the part (showing the overlay again) and returns true, so the
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
   * Analyze): stamps `reveal_tour_{part + 1}` if the part is on its last step,
   * else a no-op (an abandoned part stamps nothing and replays, D-08). */
  leave: () => void;
}

/**
 * The part due on this reveal: null while settings are not loaded, the reveal is
 * a restored one, or the whole tour is done; else the part for the stage.
 */
function resolveLivePart(settings: TrainSettingsResponse | undefined, isRestored: boolean): TourPart | null {
  if (settings === undefined) return null;
  if (isRestored) return null;
  if (isRevealTourDone(settings.reveal_tour_stage)) return null;
  return tourPartForStage(settings.reveal_tour_stage);
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
  const { settings, hasVerdict, analyzeOpens, isDesktop, isRestored } = input;
  const { screenRef, pinnedRef, stamp } = input;
  // The part latched for this reveal (see the module docstring); cleared per puzzle.
  const [latchedPart, setLatchedPart] = useState<TourPart | null>(null);
  // Index within the latched part. The caller resets it per puzzle so an
  // abandoned part replays on the next reveal (D-08).
  const [stepIndex, setStepIndex] = useState(0);
  // Phase 237 UAT (G-01): the phone overlay hides on any reveal interaction so
  // the arrows and moves it covers are readable; Next or Hilda's badge shows it
  // again. Reset per puzzle with the step.
  const [overlayHidden, setOverlayHidden] = useState(false);

  const livePart = hasVerdict ? resolveLivePart(settings, isRestored) : null;
  // Latch once (only while empty), so the leave stamp's cache write can never
  // switch the part mid-reveal.
  useEffect(() => {
    if (livePart !== null && latchedPart === null) setLatchedPart(livePart);
  }, [livePart, latchedPart]);
  const part = hasVerdict ? (latchedPart ?? livePart) : null;
  const steps = part === null ? null : tourPartSteps(part);
  const stepCount = steps?.length ?? 0;
  const activeStep: TourStepId | null = steps?.[stepIndex] ?? null;
  const context: WalkthroughContext = { analyzeOpens, isDesktop };
  const target = activeStep === null ? null : tourStepCopy(activeStep, context).spotlightTarget;
  const isLastStep = activeStep !== null && stepIndex === stepCount - 1;
  const consumesNext = activeStep !== null && !isLastStep;

  const reset = useCallback(() => {
    setLatchedPart(null);
    setStepIndex(0);
    setOverlayHidden(false);
  }, []);
  const consumeNext = useCallback((): boolean => {
    if (!consumesNext) return false;
    setStepIndex((current) => current + 1);
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

  // D-08 (Phase 240; D-12 UAT round 3 before it): a part is stamped as done when
  // the user LEAVES the reveal through its last step's action row (Next or
  // Analyze). Guarded on the LAST step so an abandoned part (unmount, reload)
  // still replays next time; the stamp's `onSuccess` writes the settings cache,
  // which moves the live part on (the latch keeps this reveal on its own part).
  // Rewind stays inside the reveal and never completes it.
  const leave = useCallback(() => {
    if (!isLastStep || part === null) return;
    stamp(REVEAL_TOUR_STAMP[part]);
  }, [isLastStep, part, stamp]);

  return { activeStep, stepIndex, stepCount, part, target, context, reset, consumeNext, overlayHidden, hide, reopen, leave };
}
