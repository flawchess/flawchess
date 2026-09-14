/**
 * useTrainWalkthrough — Phase 222 (D-24/D-12): the first-reveal walkthrough's
 * step state and everything that moves it, extracted from `TrainSolveScreen`
 * (UAT round 3) so the auto-advance handlers and the scroll-to-cards effect
 * do not push the component over its statement gate.
 *
 * Owns: the step index (reset per puzzle by the caller), the active-step
 * resolution against the settings watermark, Next, the two interaction
 * auto-advances (a spotlit card leaves the tap step, a stepped line leaves
 * the arrows step), the phone scroll-to-cards effect, and the stamp fired
 * when the user leaves the reveal from the last step.
 */
import { useCallback, useEffect, useState } from 'react';
import type { RefObject } from 'react';
import { WALKTHROUGH_STEP_COUNT, walkthroughCopy } from '@/lib/trainBotCopy';
import type { WalkthroughStep, WalkthroughStepCopy } from '@/lib/trainBotCopy';
import { prefersReducedMotion } from '@/lib/confetti';
import { animateScrollTop } from '@/lib/animatedScroll';
import type { TrainSettingsResponse } from '@/types/train';
import type { OnboardingStep } from '@/hooks/useTrainOnboarding';
import type { TrainRevealStep } from '@/components/train/TrainReveal';

/** Walkthrough step indices that auto-advance on the interaction they
 * describe (UAT round 3): tapping a line card, stepping a line. Named so the
 * interaction handlers never carry bare step numbers. */
const WALKTHROUGH_STEP_TAP_CARD: WalkthroughStep = 1;
const WALKTHROUGH_STEP_STEP_LINE: WalkthroughStep = 2;

/** Gap left between the pinned board block and the first line card when the
 * walkthrough scrolls the cards into view on phones. */
const WALKTHROUGH_CARD_SCROLL_GAP_PX = 12;

/**
 * Duration of the phone scroll-to-cards tween. Quick task 260914-uer
 * (QUICK-03): Phase 222 shipped the browser's native `behavior: 'smooth'`,
 * whose duration is UA-owned (~350ms in Chrome for this delta) and not
 * tunable; the ask was half that speed, so the scroll is now an explicit
 * rAF tween (`animateScrollTop`) and this number is the single knob.
 */
const WALKTHROUGH_CARD_SCROLL_DURATION_MS = 700;

/** The reveal's spotlight entry shape (`TrainReveal`'s `onSpotlightChange`). */
export interface SpotlightEntry {
  key: string;
  ucis: string[];
}

export interface UseTrainWalkthroughInput {
  /** `useTrainSettings().data` — undefined while loading or failed. */
  settings: TrainSettingsResponse | undefined;
  /** True once a verdict (`SolveResponse`) has landed for the puzzle on screen. */
  hasVerdict: boolean;
  /** Whether the action row carries Analyze (own-game puzzle). */
  hasAnalyze: boolean;
  /** Whether the action row carries Solution (departed board). */
  hasSolution: boolean;
  isDesktop: boolean;
  /** The solve screen root — the first line card is looked up inside it. */
  screenRef: RefObject<HTMLDivElement | null>;
  /** The phone-pinned progress + board block. */
  pinnedRef: RefObject<HTMLDivElement | null>;
  /** The caller's own spotlight / line-step setters, wrapped by the hook's
   * handlers so the reveal keeps a single channel for each. Must be
   * referentially stable (React state setters are). */
  setSpotlight: (entry: SpotlightEntry | null) => void;
  setLineStep: (step: TrainRevealStep | null) => void;
  stamp: (step: OnboardingStep) => void;
}

export interface UseTrainWalkthroughResult {
  /** Non-null exactly while the walkthrough is showing. */
  activeStep: WalkthroughStep | null;
  /** The active step's spotlight target, or null while inactive. */
  target: WalkthroughStepCopy['spotlightTarget'] | null;
  /** Resets the step index — call on every puzzle transition (D-12). */
  reset: () => void;
  /** The stepper's Next control. */
  next: () => void;
  /** Wraps `setSpotlight`; a non-null entry leaves the tap step. */
  handleSpotlightChange: (entry: SpotlightEntry | null) => void;
  /** Wraps `setLineStep`; a non-null step leaves the arrows step. */
  handleLineStep: (step: TrainRevealStep | null) => void;
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

function advanceFrom(from: WalkthroughStep): (step: WalkthroughStep) => WalkthroughStep {
  return (step) => (step === from ? ((step + 1) as WalkthroughStep) : step);
}

export function useTrainWalkthrough(input: UseTrainWalkthroughInput): UseTrainWalkthroughResult {
  const { settings, hasVerdict, hasAnalyze, hasSolution, isDesktop, screenRef, pinnedRef } = input;
  const { setSpotlight, setLineStep, stamp } = input;
  // Only meaningful while `resolveWalkthroughStep` reports it active;
  // otherwise ignored. The caller resets it per puzzle so an abandoned
  // stepper replays on the next reveal (D-12).
  const [step, setStep] = useState<WalkthroughStep>(0);
  const activeStep = resolveWalkthroughStep(settings, hasVerdict, step);
  const target =
    activeStep === null ? null : walkthroughCopy(activeStep, hasAnalyze, hasSolution).spotlightTarget;

  const reset = useCallback(() => setStep(0), []);
  const next = useCallback(() => {
    setStep((current) => Math.min(current + 1, WALKTHROUGH_STEP_COUNT - 1) as WalkthroughStep);
  }, []);

  // UAT round 3: the two line-card steps ALSO advance on the very interaction
  // they describe — a spotlit card (tap on phones, hover on desktop) leaves
  // the tap step, a stepped line leaves the arrows step. On phones the cards
  // sit below the fold, so the user who scrolls down and tries one finds the
  // next instruction waiting instead of a Next click stranded above. Next
  // stays as the fallback on both steps. A functional update keyed on the
  // CURRENT step keeps this a no-op everywhere else (walkthrough inactive,
  // other steps), so the handlers stay referentially stable for
  // `TrainReveal`'s own effect deps.
  const handleSpotlightChange = useCallback(
    (entry: SpotlightEntry | null) => {
      setSpotlight(entry);
      if (entry === null) return;
      setStep(advanceFrom(WALKTHROUGH_STEP_TAP_CARD));
    },
    [setSpotlight],
  );
  const handleLineStep = useCallback(
    (lineStep: TrainRevealStep | null) => {
      setLineStep(lineStep);
      if (lineStep === null) return;
      setStep(advanceFrom(WALKTHROUGH_STEP_STEP_LINE));
    },
    [setLineStep],
  );

  // UAT round 3: entering the tap-a-card step on a phone scrolls the first
  // line card up to just under the pinned board block, so the cards the step
  // talks about are on screen. Desktop already shows them in their own
  // column. Measured from the pinned block's own height (not its current
  // bottom edge) because the block re-anchors to the viewport top as the
  // page scrolls.
  useEffect(() => {
    if (activeStep !== WALKTHROUGH_STEP_TAP_CARD || isDesktop) return;
    const card = screenRef.current?.querySelector('[data-testid^="train-line-box-"]');
    const pinned = pinnedRef.current;
    if (!(card instanceof HTMLElement) || pinned === null) return;
    const delta =
      card.getBoundingClientRect().top -
      pinned.getBoundingClientRect().height -
      WALKTHROUGH_CARD_SCROLL_GAP_PX;
    if (delta <= 0) return;
    // The page itself is the scroller here (the feedback scrolls behind the
    // pinned board); `document.scrollingElement` is the element whose
    // `scrollTop` moves it (`documentElement` is the standards-mode fallback,
    // and what jsdom offers). Reduced motion jumps instantly via a 0ms duration.
    const scroller = document.scrollingElement ?? document.documentElement;
    animateScrollTop(scroller as HTMLElement, delta, prefersReducedMotion() ? 0 : WALKTHROUGH_CARD_SCROLL_DURATION_MS);
  }, [activeStep, isDesktop, screenRef, pinnedRef]);

  // D-12 (UAT round 3): the walkthrough is stamped as seen when the user
  // LEAVES the first reveal through its last step's action row (Next or
  // Analyze) — there is no separate "Got it". Guarded on the LAST step so an
  // abandoned walkthrough (unmount, reload) still replays next time; the
  // stamp's `onSuccess` writes the settings cache, which flips `activeStep`
  // to null (same settings-only-guard pattern plan 04 used for the intro
  // stamp). Solution stays inside the reveal and never completes it.
  const isLastStep = activeStep === WALKTHROUGH_STEP_COUNT - 1;
  const leave = useCallback(() => {
    if (!isLastStep) return;
    stamp('reveal_walkthrough');
  }, [isLastStep, stamp]);

  return { activeStep, target, reset, next, handleSpotlightChange, handleLineStep, leave };
}
