/**
 * TrainScoreScreen — the session-end score screen (SOLV-07, Phase 190 Plan
 * 05 Task 3). Renders once the final puzzle's reveal reports the session
 * complete: the total out of twice the session size, the floored
 * percentage beneath it, and a green/yellow/red rating band — all derived
 * from the pure `lib/trainScore.ts` module so the displayed number and the
 * awarded band can never contradict each other (SOLV-07 edge probe:
 * precision).
 *
 * Phase 191 (D-15/PROG-02) adds the green-band celebration: a fire-once
 * confetti burst on mount, reusing `fireWinConfetti`/`prefersReducedMotion`
 * verbatim from the bot-game win celebration (`useBotGame.ts`'s
 * `finalizeGame`) rather than a new palette or effect.
 *
 * The percentage is the screen's hero: it renders inside a band-colored
 * circular badge that pops in on arrival, with the raw points line demoted
 * to supporting text beneath it. Each band also gets a result sound, reusing
 * the exact per-puzzle mapping `TrainSolveScreen`'s reveal already fires
 * (green = WinChime, yellow = PartialScore, red = Defeat) so the session verdict
 * sounds like a louder version of the per-puzzle verdicts rather than a new
 * vocabulary. Yellow additionally gets the smaller `firePartialConfetti`
 * burst — acknowledged, not celebrated.
 *
 * SEED-122 settles how the screen ends. It used to end on a permanently-
 * disabled "Train again" CTA (nothing could enable it — sessions are
 * once-per-day and there is no same-day resume path), which read as a broken
 * feature. That button is gone; the next-session date states when training
 * resumes, and a secondary "Done" returns to the landing so the session
 * finishes on the streak card showing the tick it just earned.
 *
 * Phase 222 (D-25, SC4): the screen now OPENS on a bot bubble stating what
 * returns and when, BEFORE the Remind me ask — SEED-166's second leak was
 * that this screen closed a loop instead of opening one. Hosted by a random
 * smart bot regardless of the session's rating band (D-04), memoised once
 * per mount so a re-render never recasts mid-read. The bubble's copy comes
 * from `scoreBubbleCopy` (plan 01, D-18/D-21/D-25) fed by `solvedOutcomes`
 * (plan 05 task 1, RESEARCH Finding C) — the same array is correct whether
 * the session was played straight through or resumed/reloaded/handed off.
 *
 * The full spaced-repetition explanation shows exactly once, gated on
 * `useTrainSettings().data.sr_explained_at === null` (D-12) — but ONLY when
 * that variant actually renders: `scoreBubbleCopy`'s own precedence puts the
 * warm-up and nothing-missed variants ahead of the full explanation, so
 * `showsFullExplanation` mirrors that same precedence here before firing the
 * one-shot stamp. An explanation that was never shown must never be stamped
 * (D-12) — it would silently downgrade a future first-timer to the one-liner.
 */

import { useEffect, useMemo, useRef, useState, type ReactElement } from 'react';
import { format, parseISO } from 'date-fns';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { useTrainReminderSlot } from '@/components/train/TrainReminderButton';
import { useInstallPrompt } from '@/hooks/useInstallPrompt';
import { fireWinConfetti, firePartialConfetti, prefersReducedMotion } from '@/lib/confetti';
import { playSound, type SoundEvent } from '@/lib/sounds';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import { SignupAskActions } from '@/components/train/SignupAskActions';
import { pickBot, scoreBubbleCopy, type ReminderAsk, type TrainCopyAudience } from '@/lib/trainBotCopy';
import { useTrainSettings } from '@/hooks/useTrainSettings';
import { useTrainOnboarding } from '@/hooks/useTrainOnboarding';
import type { SolvedResult } from '@/types/train';
import {
  TRAIN_RATING_GREEN,
  TRAIN_RATING_YELLOW,
  TRAIN_RATING_RED,
} from '@/lib/theme';
import {
  resolveRatingBand,
  displaySessionPercentage,
  type TrainRatingBand,
  type TrainSessionScore,
} from '@/lib/trainScore';

const RATING_BAND_COLOR: Record<TrainRatingBand, string> = {
  green: TRAIN_RATING_GREEN,
  yellow: TRAIN_RATING_YELLOW,
  red: TRAIN_RATING_RED,
};

/** Result sound per band. Quick 260814-b: `green` keeps WinChime, which is now
 * reserved for this session verdict and bot-game wins — the per-puzzle reveal
 * moved its full-score case to its own `score-full` clip, so the session end no
 * longer sounds like just one more solved puzzle. The other two bands still
 * share the reveal's clips. */
const RATING_BAND_SOUND: Record<TrainRatingBand, SoundEvent> = {
  green: 'game-win',
  yellow: 'score-partial',
  red: 'game-loss',
};

/** Opacity of the badge's band-colored fill, as a color-mix percentage. Low
 * enough that the large percentage text stays legible on both themes. */
const BADGE_TINT_PERCENT = 14;

/** Thickness of the badge ring, in px. */
const BADGE_RING_WIDTH_PX = 4;

export interface TrainScoreScreenProps {
  score: TrainSessionScore;
  /**
   * ISO date string for the next available session (`TrainSessionResponse.
   * expires_on`). Sessions are once-per-day (Phase 189) and Phase 190 has no
   * same-day resume path, so this states when the user can train again —
   * SEED-122 removed the permanently-disabled "Train again" CTA that used to
   * sit above it, because a primary button that can never enable reads as
   * broken rather than as "you're done for today".
   */
  nextSessionDate: string;
  /**
   * Leaves the score screen for the Train landing (SEED-122). The landing is
   * where the streak card lives, so the session ends on the tick it just
   * earned rather than on a screen with no way forward.
   *
   * Phase 202 D-04 OVERRIDES the original SEED-122 rationale recorded here:
   * Done used to be `brand-outline` ("it is an exit, not a call to action")
   * while it was the screen's only button. Now that it shares a row with the
   * "Remind me" opt-in (`TrainReminderButton`), Done is promoted to
   * `variant="default"` and moves to the right as the row's primary action.
   */
  onDone: () => void;
  /**
   * Phase 222 (D-17/D-18, RESEARCH Finding C): every item solved this
   * session — `useTrainSession().solvedOutcomes`, correct whether the
   * session was played straight through or resumed/reloaded/handed off.
   * The score bubble's sole source for "what returns and when".
   */
  solvedOutcomes: SolvedResult[];
  /** `TrainSessionResponse.session_date` — the day-arithmetic base for the
   * "in N days" phrasing (D-15, no client clock math anywhere). */
  sessionDate: string;
  /** `TrainSessionResponse.expires_on` — the boundary between "next
   * session" and "in N days" (D-15). Same value as `nextSessionDate` above,
   * threaded separately because the two props serve different call sites
   * (the existing "Next session:" line vs. the new bubble copy). */
  expiresOn: string;
  /** `TrainSessionResponse.is_warmup` — a warm-up session (zero surviving
   * SR items) gets its own D-25 variant regardless of `sr_explained_at`. */
  isWarmup: boolean;
  /** D-03 (Phase 224): true when the account has at least one imported game
   * (`hasImportedGames`, the shared user-profile hook's data), passed down
   * from `Train.tsx`. Selects the warm-up bubble's zero-game copy variant. */
  hasGames: boolean;
  /** D-03/S-3 (Phase 224): sourced from the shared user-profile hook's data
   * via `Train.tsx`, never the auth hook's user object (FLAWCHESS-64), and
   * never read here directly — this component takes props only, so it
   * gains no complexity from the profile query. Replaces the warm-up
   * reminder ask with the sign-up ask (`GUEST_SIGNUP_ASK_SCORE`, D-13: a
   * guest gets no reminder slot). */
  isGuest: boolean;
}

export function TrainScoreScreen({
  score,
  nextSessionDate,
  onDone,
  solvedOutcomes,
  sessionDate,
  expiresOn,
  isWarmup,
  hasGames,
  isGuest,
}: TrainScoreScreenProps): ReactElement {
  const percentage = displaySessionPercentage(score);
  const band = score.max > 0 ? resolveRatingBand(score.total / score.max) : null;
  const bandColor = band !== null ? RATING_BAND_COLOR[band] : null;
  // D-04: a random smart bot hosts the score bubble regardless of the
  // session's rating band — memoised once per mount so a re-render can never
  // recast mid-read (no deps: pickBot('smart') has no external inputs, so
  // exhaustive-deps raises nothing here).
  const bot = useMemo(() => pickBot('smart'), []);
  // Phase 222 (D-12): the shared settings cache — already warm app-wide for
  // every non-guest (RESEARCH Finding D), so this costs no extra request.
  const { data: settings } = useTrainSettings();
  const { stamp } = useTrainOnboarding();
  // Phase 222 UAT round 5: the same desktop gate `useTrainReminderSlot` uses
  // to pick the phone block below the row, so the bubble's ask ("scan the
  // code below" / "yours are already on") and what actually renders there
  // can never disagree.
  const { isMobile, isStandalone } = useInstallPrompt();
  const reminderAsk = resolveReminderAsk({
    isDesktop: !isMobile && !isStandalone,
    hasMobileSubscription: settings?.has_mobile_subscription ?? false,
  });

  // ScoreBubbleInput's own docstring: "NOT fully correct" (guess or move
  // wrong) — the same items still return later (D-18), so "returning" and
  // "missed" are independent facts.
  const missedCount = useMemo(
    () => solvedOutcomes.filter((outcome) => !(outcome.correct_guess && outcome.move_quality === 'good'))
      .length,
    [solvedOutcomes],
  );

  // RESEARCH Finding D: render no bubble copy until `data !== undefined`, so
  // a first-timer never sees the one-liner flash before the full explanation
  // replaces it.
  //
  // BUG FIX (Phase 222 UAT round 5): latched on the first resolved settings
  // value, never re-derived. The `stamp('sr_explained')` below writes the
  // stamped row back into the SAME settings cache (`useTrainOnboarding`'s
  // `setQueryData`), so a live read flipped `sr_explained_at` to non-null a
  // moment after mount and the full explanation collapsed into the
  // later-session one-liner on the very screen that was supposed to show it.
  const [firstExplanationLatch, setFirstExplanationLatch] = useState<boolean | null>(() =>
    settings === undefined ? null : settings.sr_explained_at === null,
  );
  useEffect(() => {
    if (firstExplanationLatch !== null || settings === undefined) return;
    setFirstExplanationLatch(settings.sr_explained_at === null);
  }, [firstExplanationLatch, settings]);
  const firstExplanation = firstExplanationLatch === true;
  const bubbleCopy =
    firstExplanationLatch === null
      ? null
      : scoreBubbleCopy({
          outcomes: solvedOutcomes,
          missedCount,
          isFirstCompletedSession: firstExplanation,
          isWarmup,
          reminderAsk,
          band,
          session_date: sessionDate,
          expires_on: expiresOn,
          audience: { hasGames, isGuest } satisfies TrainCopyAudience,
        });

  // D-12: mirrors `scoreBubbleCopy`'s own precedence (isWarmup and
  // missedCount===0 both win over isFirstCompletedSession) — an explanation
  // that was never actually rendered must never be stamped.
  const showsFullExplanation = firstExplanation && !isWarmup && missedCount > 0;
  const stampedRef = useRef(false);
  useEffect(() => {
    if (!showsFullExplanation || stampedRef.current) return;
    stampedRef.current = true;
    stamp('sr_explained');
  }, [showsFullExplanation, stamp]);
  // Plan 04 UAT round 1: called directly here (not via `<TrainReminderButton />`)
  // so `control` and `belowRow` can be placed in two different rows — see
  // TrainReminderButton.tsx's module docstring for why the split exists. One
  // hook call, one state instance, for this whole screen.
  const { control: reminderControl, belowRow: reminderBelowRow } = useTrainReminderSlot();
  // Read once per render (not inside the effect) so the badge animation and
  // the confetti decision can never disagree within a single mount.
  const reducedMotion = prefersReducedMotion();

  useEffect(() => {
    // Fire once per mount only (D-15) — the exact reduced-motion guard shape
    // `useBotGame.ts`'s `finalizeGame` uses for the bot-win burst. The sound
    // is NOT motion-gated: reduced-motion users still get the result sound
    // (playSound honors the shared mute preference on its own), they just
    // lose the confetti.
    if (band === null) return;
    playSound(RATING_BAND_SOUND[band]);
    if (reducedMotion) return;
    if (band === 'green') fireWinConfetti();
    else if (band === 'yellow') firePartialConfetti();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    // Phase 222 UAT round 6: no extra top/bottom padding on phones — stacked
    // on the page's own `py-6` it pushed the bubble (and the score under it)
    // a screenful down; the page padding alone is the gap below the header.
    <div
      className="flex flex-col items-center gap-4 py-0 text-center md:py-12"
      data-testid="train-score-screen"
    >
      {/* Phase 222 (D-25, SC4): the bubble states what returns and when
          BEFORE the Remind me ask below — the whole point of SC4. Replaces
          the old "Session complete" heading, which said nothing about the
          loop this screen is meant to open. */}
      <div className="w-full max-w-sm text-left" data-testid="train-score-bubble">
        <TrainBotBubble
          persona={bot}
          state="verdict"
          actions={isGuest ? <SignupAskActions source="train-score" /> : undefined}
        >
          {bubbleCopy !== null && (
            <div data-testid="train-score-bubble-returns">
              {bubbleCopy.lines.map((line, index) => (
                <p key={index}>{line}</p>
              ))}
            </div>
          )}
        </TrainBotBubble>
      </div>
      {percentage !== null && bandColor !== null && (
        <div
          className={`flex size-36 items-center justify-center rounded-full ${
            reducedMotion ? '' : 'animate-train-score-badge-pop'
          }`}
          data-testid="train-score-badge"
          style={{
            border: `${BADGE_RING_WIDTH_PX}px solid ${bandColor}`,
            backgroundColor: `color-mix(in oklch, ${bandColor} ${BADGE_TINT_PERCENT}%, transparent)`,
          }}
        >
          <span
            className="text-5xl font-bold leading-none"
            data-testid="train-score-percentage"
            style={{ color: bandColor }}
          >
            {percentage}%
          </span>
        </div>
      )}
      <p className="text-lg font-semibold text-muted-foreground" data-testid="train-score-total">
        Points: {score.total}/{score.max}
      </p>
      <p className="text-sm font-semibold text-muted-foreground">
        Next session: {format(parseISO(nextSessionDate), 'MMM d, yyyy')}
      </p>
      {/* Phase 202 (D-01..D-04, UI-SPEC E2): Remind me (left, brand-outline)
          then Done (right, promoted to default/primary). max-w-sm is a
          planner resolution — the Train page container has no max width, so
          a bare w-full row would stretch Done across the whole desktop
          viewport.
          Plan 04 UAT round 1: the row keeps its two-cell shape no matter
          which reminder-slot state is active — overflow content (error
          copy, the iOS instructions, the Android install offer, the QR
          block) never crowds into this row; it renders on its own full-width
          line below via `reminderBelowRow`, wrapped in this flex-col so both
          pieces stay inside the same max-w-sm column. */}
      <div className="flex w-full max-w-sm flex-col gap-2">
        <div className="flex w-full items-center gap-2" data-testid="train-score-button-row">
          <GuardedReminderControl isGuest={isGuest} reminderControl={reminderControl} />
          <Button
            variant="default"
            className={cn('flex-1', TRAIN_BUTTON_CLASS)}
            onClick={onDone}
            data-testid="btn-train-done"
          >
            Done
          </Button>
        </div>
        <GuardedReminderBelowRow isGuest={isGuest} reminderBelowRow={reminderBelowRow} />
      </div>
    </div>
  );
}

/** Desktop with reminders already on a phone has nothing left to ask for;
 * any other desktop points at the QR; mobile and standalone name the row
 * button. Mirrors `useTrainReminderSlot`'s desktop branches. */
function resolveReminderAsk({
  isDesktop,
  hasMobileSubscription,
}: {
  isDesktop: boolean;
  hasMobileSubscription: boolean;
}): ReminderAsk {
  if (!isDesktop) return 'remind_me';
  return hasMobileSubscription ? 'none' : 'scan_qr';
}

/**
 * GuardedReminderControl / GuardedReminderBelowRow — Phase 224 (S-3):
 * suppress the reminder row's two pieces entirely for a guest (no reminder
 * slot, no QR/install block, S-3). Each wraps exactly one guest-guard
 * ternary in its own module-level function so it is measured against ITS
 * OWN complexity, not `TrainScoreScreen`'s — which had only one branch of
 * headroom left against CLAUDE.md's un-baselined complexity cap of 15 after
 * the bubble's guest-guarded `actions` prop ternary above (baseline
 * complexity 13, cap 15: only one more branch fits inline). Fragments are
 * transparent in the DOM, so this changes no rendered markup and no
 * existing TrainScoreScreen.test.tsx assertion.
 */
function GuardedReminderControl({
  isGuest,
  reminderControl,
}: {
  isGuest: boolean;
  reminderControl: ReactElement | null;
}): ReactElement {
  return <>{isGuest ? null : reminderControl}</>;
}

function GuardedReminderBelowRow({
  isGuest,
  reminderBelowRow,
}: {
  isGuest: boolean;
  reminderBelowRow: ReactElement | null;
}): ReactElement {
  return <>{isGuest ? null : reminderBelowRow}</>;
}
