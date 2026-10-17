/**
 * TrainScoreScreen — the session-end score screen. Renders once the final
 * puzzle's reveal reports the session complete: the total out of
 * `TRAIN_POINTS_PER_PUZZLE` times the session size, the floored percentage
 * beneath it, and a green/yellow/red rating band — all derived from the pure
 * `lib/trainScore.ts` module so the displayed number and the awarded band
 * can never contradict each other.
 *
 * The green band gets a fire-once confetti burst on mount, reusing
 * `fireWinConfetti`/`prefersReducedMotion` verbatim from the bot-game win
 * celebration (`useBotGame.ts`'s `finalizeGame`) rather than a new palette or
 * effect.
 *
 * The percentage is the screen's hero: it renders inside a band-colored
 * circular badge that pops in on arrival, with the raw points line demoted
 * to supporting text beneath it. Each band also gets a result sound: green =
 * WinChime (reserved for this verdict and bot-game wins), yellow =
 * PartialScore, red = Defeat. Yellow additionally gets the smaller
 * `firePartialConfetti` burst — acknowledged, not celebrated.
 *
 * The screen ends on the next-session date, which states when training
 * resumes, and "Done" (primary, right of the Remind me control), which
 * returns to the landing so the session ends on the streak card's new tick.
 * There is no "Train again" button: sessions are once-per-day with no
 * same-day resume path, so a primary button that can never enable would read
 * as broken.
 *
 * The screen OPENS on a bot bubble, BEFORE the Remind me ask, so it opens a
 * loop instead of closing one. Hosted by a random smart bot regardless of
 * the session's rating band, memoised once per mount so a re-render never
 * recasts mid-read. The bubble's copy comes from `scoreBubbleCopy`, fed by
 * the miss count derived from `solvedOutcomes` — the same array is correct
 * whether the session was played straight through or resumed/reloaded/handed
 * off. The bubble does not say what returns or when.
 *
 * The first-completed-session copy (the practice rationale in line 1) shows
 * exactly once, gated on `useTrainSettings().data.sr_explained_at === null`
 * and stamped in ANY branch that rendered it: without that, an
 * all-warm-up guest would read the rationale every session.
 */

import { useEffect, useMemo, useRef, useState, type ReactElement } from 'react';
import { format, parseISO } from 'date-fns';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { useTrainReminderSlot } from '@/components/train/useTrainReminderSlot';
import { useInstallPrompt } from '@/hooks/useInstallPrompt';
import { fireWinConfetti, firePartialConfetti, prefersReducedMotion } from '@/lib/confetti';
import { playSound, type SoundEvent } from '@/lib/sounds';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import { ImportAskActions } from '@/components/train/ImportAskActions';
import { SignupAskActions } from '@/components/train/SignupAskActions';
import { TrainScoreRankLines } from '@/components/train/TrainScoreRankLines';
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

/** Result sound per band. `green` keeps WinChime, which is reserved for this
 * session verdict and bot-game wins — the per-puzzle reveal's full-score case
 * has its own `score-full` clip, so the session end does not sound like just
 * one more solved puzzle. The other two bands share the reveal's clips. */
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

/** The bubble and button column. 384px (max-w-sm) on phones, which
 * fills the screen anyway; 512px from md up, where the narrow column wrapped
 * the bubble into a tall block next to empty space. */
const SCORE_COLUMN_MAX_W = 'max-w-sm md:max-w-lg';

export interface TrainScoreScreenProps {
  score: TrainSessionScore;
  /**
   * ISO date string for the next available session (`TrainSessionResponse.
   * expires_on`). Sessions are once-per-day with no same-day resume path, so
   * this states when the user can train again. There is deliberately no
   * "Train again" CTA above it: a primary button that can never enable reads
   * as broken rather than as "you're done for today".
   */
  nextSessionDate: string;
  /**
   * Leaves the score screen for the Train landing. The landing is
   * where the streak card lives, so the session ends on the tick it just
   * earned rather than on a screen with no way forward.
   *
   * Done shares a row with the "Remind me" opt-in (`useTrainReminderSlot`), so
   * it is `variant="default"` on the right as the row's primary action.
   */
  onDone: () => void;
  /**
   * Every item solved this session — `useTrainSession().solvedOutcomes`,
   * correct whether the session was played straight through or
   * resumed/reloaded/handed off. The score bubble's source for the miss count.
   */
  solvedOutcomes: SolvedResult[];
  /** `TrainSessionResponse.is_warmup` — a warm-up session (zero surviving
   * SR items) gets its own bubble variant regardless of `sr_explained_at`. */
  isWarmup: boolean;
  /** True when the account has at least one imported game
   * (`hasImportedGames`, the shared user-profile hook's data), passed down
   * from `Train.tsx`. Selects the warm-up bubble's zero-game copy variant. */
  hasGames: boolean;
  /** Sourced from the shared user-profile hook's data
   * via `Train.tsx`, never the auth hook's user object (FLAWCHESS-64), and
   * never read here directly — this component takes props only, so it
   * gains no complexity from the profile query. Replaces the warm-up
   * reminder ask with the sign-up ask (`GUEST_SIGNUP_ASK_SCORE`: a guest
   * gets no reminder slot). */
  isGuest: boolean;
  /** `TrainSessionResponse.session_id`: the rank lines ask the server for this
   * session's rank change. Null while unknown; the
   * lines then render nothing. */
  sessionId: number | null;
}

/** The score bubble's action row: guests get the sign-up ask; a registered
 * zero-game account gets the import ask; everyone else gets none. */
function scoreBubbleActions(isGuest: boolean, hasGames: boolean): ReactElement | undefined {
  if (isGuest) return <SignupAskActions source="train-score" />;
  if (!hasGames) return <ImportAskActions source="train-score" />;
  return undefined;
}

export function TrainScoreScreen({
  score,
  nextSessionDate,
  onDone,
  solvedOutcomes,
  isWarmup,
  hasGames,
  isGuest,
  sessionId,
}: TrainScoreScreenProps): ReactElement {
  const percentage = displaySessionPercentage(score);
  const band = score.max > 0 ? resolveRatingBand(score.total / score.max) : null;
  const bandColor = band !== null ? RATING_BAND_COLOR[band] : null;
  // A random smart bot hosts the score bubble regardless of the
  // session's rating band — memoised once per mount so a re-render can never
  // recast mid-read (no deps: pickBot('smart') has no external inputs, so
  // exhaustive-deps raises nothing here).
  const bot = useMemo(() => pickBot('smart'), []);
  // The shared settings cache — already warm app-wide for every non-guest,
  // so this costs no extra request.
  const { data: settings } = useTrainSettings();
  const { stamp } = useTrainOnboarding();
  // The same desktop gate `useTrainReminderSlot` uses
  // to pick the phone block below the row, so the bubble's ask ("scan the
  // code below" / "yours are already on") and what actually renders there
  // can never disagree.
  const { isMobile, isStandalone } = useInstallPrompt();
  const reminderAsk = resolveReminderAsk({
    isDesktop: !isMobile && !isStandalone,
    hasMobileSubscription: settings?.has_mobile_subscription ?? false,
  });

  // ScoreBubbleInput's own docstring: "NOT fully correct" (guess or move
  // wrong).
  const missedCount = useMemo(
    () => solvedOutcomes.filter((outcome) => !(outcome.correct_guess && outcome.move_quality === 'good'))
      .length,
    [solvedOutcomes],
  );

  // Render no bubble copy until `data !== undefined`, so a first-timer never
  // sees the one-liner flash before the full explanation replaces it.
  //
  // BUG FIX: latched on the first resolved settings value, never re-derived. The `stamp('sr_explained')` below writes the
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
          missedCount,
          isFirstCompletedSession: firstExplanation,
          isWarmup,
          reminderAsk,
          band,
          audience: { hasGames, isGuest } satisfies TrainCopyAudience,
        });

  // Stamp whenever the first-completed variant actually rendered,
  // in any branch (warm-up, nothing missed, regular). An explanation that was
  // never rendered must never be stamped (`bubbleCopy` is still null until
  // settings resolve), but one that WAS rendered in a warm-up or perfect
  // session must be, or an all-warm-up guest would see the rationale every
  // session. Accepted trade-off: a user whose first completed session was a
  // warm-up never later sees the "Reminders build the habit" line.
  const showsFirstSessionCopy = bubbleCopy !== null && firstExplanation;
  const stampedRef = useRef(false);
  useEffect(() => {
    if (!showsFirstSessionCopy || stampedRef.current) return;
    stampedRef.current = true;
    stamp('sr_explained');
  }, [showsFirstSessionCopy, stamp]);
  // Called directly here (not via a wrapper component)
  // so `control` and `belowRow` can be placed in two different rows — see
  // useTrainReminderSlot.tsx's module docstring for why the split exists. One
  // hook call, one state instance, for this whole screen.
  const { control: reminderControl, belowRow: reminderBelowRow } = useTrainReminderSlot();
  // Read once per render (not inside the effect) so the badge animation and
  // the confetti decision can never disagree within a single mount.
  const reducedMotion = prefersReducedMotion();

  useEffect(() => {
    // Fire once per mount only — the exact reduced-motion guard shape
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
    // No extra top/bottom padding on phones — stacked
    // on the page's own `py-6` it pushed the bubble (and the score under it)
    // a screenful down; the page padding alone is the gap below the header.
    <div
      className="flex flex-col items-center gap-4 py-0 text-center md:py-12"
      data-testid="train-score-screen"
    >
      {/* The bubble opens the screen, before the Remind me ask. */}
      <div className={cn('w-full text-left', SCORE_COLUMN_MAX_W)} data-testid="train-score-bubble">
        <TrainBotBubble
          persona={bot}
          state="verdict"
          actions={scoreBubbleActions(isGuest, hasGames)}
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
      <TrainScoreRankLines sessionId={sessionId} />
      <p className="text-sm font-semibold text-muted-foreground">
        Next session: {format(parseISO(nextSessionDate), 'MMM d, yyyy')}
      </p>
      {/* Remind me (left, brand-outline) then Done (right, default/primary).
          The column is width-capped because the Train page container has no
          max width, so a bare w-full row would stretch Done across the whole
          desktop viewport.
          The row keeps its two-cell shape no matter
          which reminder-slot state is active — overflow content (error
          copy, the iOS instructions, the Android install offer, the QR
          block) never crowds into this row; it renders on its own full-width
          line below via `reminderBelowRow`, wrapped in this flex-col so both
          pieces stay inside the same max-w-sm column. */}
      <div className={cn('flex w-full flex-col gap-2', SCORE_COLUMN_MAX_W)}>
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

/** Reminders already on a phone leave nothing to ask for, on any device;
 * otherwise desktop points at the QR and mobile/standalone name the row
 * button. Mirrors `useTrainReminderSlot`'s desktop branches.
 *
 * BUG FIX (2026-09-28): mobile used to return `remind_me` unconditionally,
 * so a user whose phone already had reminders on was still told to "Turn on
 * Remind me" in the score bubble on that same phone. */
function resolveReminderAsk({
  isDesktop,
  hasMobileSubscription,
}: {
  isDesktop: boolean;
  hasMobileSubscription: boolean;
}): ReminderAsk {
  if (hasMobileSubscription) return 'none';
  return isDesktop ? 'scan_qr' : 'remind_me';
}

/**
 * GuardedReminderControl / GuardedReminderBelowRow — suppress the reminder
 * row's two pieces entirely for a guest (no reminder slot, no QR/install
 * block). Fragments are transparent in the DOM, so this changes no rendered
 * markup.
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
