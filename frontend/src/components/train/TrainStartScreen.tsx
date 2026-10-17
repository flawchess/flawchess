/**
 * TrainStartScreen: the pre-loop landing states for /train. `Train.tsx`
 * fetches session status automatically on mount (a status fetch, not a
 * "start": visiting must not jump straight into the solve loop) and renders
 * this component whenever the loop is not active.
 *
 * State selection is a single ordered branch chain (`resolveLandingState`),
 * not scattered inline ternaries — the states are mutually exclusive and
 * exactly one always matches.
 *
 * Wherever a `TrainStreakCard` renders, the weekly `TrainLeaderboardCard`
 * follows it (before `TrainStatsCard`). The schedule card sits between the
 * streak card and the leaderboard on the completed and start/resume landings.
 *
 * `TrainMedalDialogHost` is the first child of the empty, completed and
 * fresh/resume/warmup landings (not loading or error). Train.tsx renders this
 * component only outside the solve loop and the score screen is separate, so
 * the medal dialog never appears mid-session.
 */

import type { ReactElement } from 'react';
import { format, parseISO } from 'date-fns';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { FeedbackAskBubble } from '@/components/feedback/FeedbackAskBubble';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadError } from '@/components/ui/load-error';
import { TRAIN_BUTTON_CLASS, TRAIN_CTA_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { ImportAskActions } from '@/components/train/ImportAskActions';
import { SignupAskActions } from '@/components/train/SignupAskActions';
import { TrainLeaderboardCard } from '@/components/train/TrainLeaderboardCard';
import { TrainMedalDialogHost } from '@/components/train/medals/TrainMedalDialogHost';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import { TrainReminderResurfaceBanner } from '@/components/train/TrainReminderResurfaceBanner';
import { TrainScheduleSettings } from '@/components/train/TrainScheduleSettings';
import { TrainStatsCard } from '@/components/train/TrainStatsCard';
import { TrainStreakCard } from '@/components/train/TrainStreakCard';
import { useTrainProgress } from '@/hooks/useTrainProgress';
import { useTrainSettings } from '@/hooks/useTrainSettings';
import {
  GUEST_SIGNUP_ASK_SCORE,
  IMPORT_ASK_LANDING,
  REMINDER_INSTALL_ASK,
  isRevealTourDone,
  landingHost,
} from '@/lib/trainBotCopy';
import { TRAIN_POINTS_PER_PUZZLE } from '@/lib/trainScore';
import { cn } from '@/lib/utils';
import type { TrainSessionResponse } from '@/types/train';

export interface TrainStartScreenProps {
  session: TrainSessionResponse | null;
  isLoading: boolean;
  isError: boolean;
  /**
   * The session's score, seeded server-side from `TrainSessionResponse.solved_results`
   * — see `useTrainSession`'s `sessionScore` docstring. Only consumed by the
   * 'completed' state.
   */
  sessionScore: number;
  /** Enter the solve loop at the already-seeded resume index. Does not
   * re-fetch — the session/puzzles were already loaded by the status fetch. */
  onEnterLoop: () => void;
  /**
   * Re-fires the session status fetch after a
   * `TrainScheduleSettings` save actually persists, so an untouched session
   * composed under a now-stale `puzzles_per_session` (or `weekday_mask`) is
   * corrected on THIS visit rather than staying frozen until the next page
   * load — see `TrainScheduleSettings`'s `onSaved` prop docstring.
   */
  onSettingsSaved: () => void;
  /** From `useUserProfile().data`, never `useAuth().user` (FLAWCHESS-64). Puts the sign-up ask (sentence +
   * "What changes?"/"Sign up free" buttons) into the host bubble and hides
   * the reminder/QR section on `TrainScheduleSettings`. */
  isGuest: boolean;
  /** `hasImportedGames(useUserProfile().data)`. A registered account without games gets the import ask + "Import games"
   * button in the host bubble instead of the reminder ask. */
  hasGames: boolean;
  /** Non-null while the server says the milestone feedback ask is active:
   * the user's active days for Hilda's copy. From
   * `feedbackAskDays(useUserProfile().data)`. */
  feedbackAskDays: number | null;
}

/**
 * The landing page is the same content column as the Import page —
 * `mx-auto w-full max-w-2xl` on top of the page-level `px-4 py-6 md:px-6`
 * (see Import.tsx's `<main>` and Train.tsx). Without the max-width the
 * settings chips stretch edge-to-edge on a wide window while the text sits
 * flush against the left gutter. Text stays left-aligned inside the column.
 *
 * Only the landing states use this — `TrainSolveScreen` is a two-column lg
 * layout that must keep the full page width.
 *
 * Vertical padding is `py-6 md:py-8`, not `py-12`: stacked on the page's own
 * `py-6` that would put 72px of dead space above the first card on a phone.
 * The phone host bubble is hidden for returning users, so `max-sm:pt-0`
 * leaves just the page's 24px above the streak card.
 */
const LANDING_CONTAINER_CLASS =
  'mx-auto flex w-full max-w-2xl flex-col items-start gap-4 py-6 text-left max-sm:pt-0 md:py-8';


type LandingState =
  | { kind: 'loading' }
  | { kind: 'error' }
  | { kind: 'empty' }
  | { kind: 'completed'; score: number; totalPoints: number; nextSessionDate: string }
  | { kind: 'resume'; solved: number; total: number; isWarmup: boolean }
  | { kind: 'warmup'; puzzleCount: number }
  | { kind: 'fresh'; puzzleCount: number };
// 'warmup' and 'fresh' (and `resume.isWarmup`) render identically. The
// discriminant is kept because the server flag is still the documented
// contract and the warm-up copy lives on in the intro stepper and the score
// screen.

/**
 * Single explicit resolution of the landing states. Order matters:
 * loading/error must be checked first; empty (no session_id) before any
 * puzzle-count math; completed/resume (both require solved_count > 0, or
 * solved_count === puzzle_count) before warmup/fresh (both require
 * solved_count === 0).
 *
 * The 'warmup' discriminant is the server-persisted
 * TrainSessionResponse.is_warmup boolean — a single equality check, no
 * client arithmetic over counts. (There is no 'short' kind: a sharp-filler
 * backfill keeps a session full, so puzzle_count < requested_count never
 * legitimately fires.) is_warmup is ALSO carried on the 'resume' variant (not only
 * a standalone 'warmup' kind): a partially-solved session resolves to
 * 'resume', never 'warmup', so without isWarmup on 'resume' too the label
 * would be dropped the moment the user solves one puzzle — contradicting
 * the "the label survives leaving and resuming the session" contract.
 */
function resolveLandingState(
  session: TrainSessionResponse | null,
  isLoading: boolean,
  isError: boolean,
  sessionScore: number,
): LandingState {
  // Only the FIRST load blanks the landing. A schedule save re-fetches the
  // session while the old one is still in hand; showing "Loading…"
  // then unmounted the whole landing and snapped the schedule card shut
  // mid-edit. The old session keeps rendering instead, with Start disabled
  // until the fresh one lands.
  if (isLoading && session === null) return { kind: 'loading' };
  if (isError) return { kind: 'error' };
  // Per TrainSessionResponse's own contract, session_id is null exactly when
  // no eligible puzzle was found (puzzle_count is then always 0 too).
  if (session === null || session.session_id === null) return { kind: 'empty' };
  // A session with progress but NO puzzles left to serve is also completed:
  // the backend marks a session 'completed' excluding lazily-evicted rows,
  // so a completed-in-window response can legitimately carry
  // solved_count < puzzle_count with an empty puzzles array. Without this
  // clause that shape fell through to 'resume', rendering a Resume button
  // with nothing behind it.
  const nothingLeftToServe = session.puzzles.length === 0 && session.solved_count > 0;
  if (
    session.puzzle_count > 0 &&
    (session.solved_count >= session.puzzle_count || nothingLeftToServe)
  ) {
    return {
      kind: 'completed',
      score: sessionScore,
      // Use the shared per-puzzle max (3: 1 guess + 0-2 move tier), not a
      // hardcoded `* 2`: a 3-puzzle session would report "0/6" while the
      // in-loop score screen, which reads the same constant, reports "0/9".
      totalPoints: session.puzzle_count * TRAIN_POINTS_PER_PUZZLE,
      nextSessionDate: session.expires_on,
    };
  }
  if (session.solved_count > 0 && session.solved_count < session.puzzle_count) {
    return {
      kind: 'resume',
      solved: session.solved_count,
      total: session.puzzle_count,
      isWarmup: session.is_warmup,
    };
  }
  if (session.is_warmup) {
    return { kind: 'warmup', puzzleCount: session.puzzle_count };
  }
  return { kind: 'fresh', puzzleCount: session.puzzle_count };
}

/**
 * The landing page's opener: a bot speaking a greeting in the same
 * `TrainBotBubble` the solve loop and score screen use. Tank the Ox hosts
 * until the intro stepper has been completed (he also opens intro
 * step 1, so the landing page introduces the same host the first puzzle
 * does); afterwards the host rotates daily through all 24 personas, keyed
 * on the server-supplied `session_date` (see `landingHost`). Only the
 * session date is read, so the header renders identically for every
 * landing state on a given day.
 *
 * There is no page heading: the bubble already says what the page is, and
 * the nav tab carries the "Train" label.
 *
 * For a guest the bubble also carries the sign-up ask, the SAME sentence and
 * action pair the guest score screen ends on (`GUEST_SIGNUP_ASK_SCORE` +
 * `SignupAskActions`), so the one prompt a guest sees on landing and on
 * finishing are literally the same words. It is hidden until the guest has
 * completed a session (today's, or an earlier one stamped `sr_explained_at`),
 * and shown on phones too.
 *
 * A registered account with no push subscription from a phone
 * (`has_mobile_subscription === false`, account-wide) gets the reminder ask
 * instead. Desktop subscriptions deliberately don't count: the ask is about
 * the phone app. Strict `=== false`: while settings are still loading the
 * sentence stays hidden rather than flashing in and out. Guests never see it
 * (they get the sign-up ask, and a guest has no reminder slot). It is hidden
 * until the reveal tour is completed.
 *
 * Once the intro stepper is completed and the
 * milestone feedback ask is active, Hilda's `FeedbackAskBubble` replaces the
 * whole host bubble (daily rotating host plus the sign-up/import/reminder
 * asks), on phones too. Tank's intro is never displaced.
 */
function TrainLandingHost({
  session,
  isGuest,
  hasGames,
  feedbackAskDays,
  sessionCompleted,
}: {
  session: TrainSessionResponse | null;
  isGuest: boolean;
  hasGames: boolean;
  feedbackAskDays: number | null;
  /** Today's session is done (the 'completed' landing state). */
  sessionCompleted: boolean;
}): ReactElement {
  const { data: settings } = useTrainSettings();
  const host = landingHost({
    sessionDate: session?.session_date ?? null,
    introSeenAt: settings?.intro_seen_at,
  });
  // A registered zero-game account gets the import ask in place of the
  // reminder ask, the first step before Train has anything of its own to
  // serve.
  const showImportAsk = !isGuest && !hasGames;
  // The install/reminder ask waits until onboarding is over, so a first visit
  // only reads Tank's welcome. That means the whole three-part reveal tour is
  // done, not just its first part.
  const onboardingDone = settings !== undefined && isRevealTourDone(settings.reveal_tour_stage);
  const showReminderAsk =
    !isGuest && !showImportAsk && onboardingDone && settings?.has_mobile_subscription === false;
  // The guest sign-up ask (sentence and buttons) waits until the
  // guest has completed a session, so they try Train before being asked to
  // sign up. `sr_explained_at` is stamped by the first completed session's
  // score screen, warm-up sessions included, but a reload around the end of
  // the session skips that screen (and its stamp), so today's completed
  // landing counts on its own.
  const showSignupAsk = isGuest && (sessionCompleted || settings?.sr_explained_at != null);
  // On a phone the avatar + bubble pushed the streak card and
  // its Start button below the fold, so the bubble is phone-hidden. Tank's intro
  // (intro stepper not yet completed) keeps it there, and so do the sign-up and
  // import asks (their buttons are the next step for a guest or a
  // zero-game account, worth the push-down). The reminder-install ask stays
  // desktop-only. Gated on loaded settings so a returning user's bubble never
  // flashes in before hiding.
  const isIntroHost = settings != null && settings.intro_seen_at == null;
  const keepOnPhone = isIntroHost || showSignupAsk || showImportAsk;
  // Tank's intro wins; Hilda takes the host only once the intro stepper is
  // completed. Requiring LOADED settings also means no view is counted on a
  // render that would flip to Tank a moment later.
  const introDone = settings?.intro_seen_at != null;
  const askDays = introDone ? feedbackAskDays : null;
  return (
    <div
      // The feedback ask shows on phones while active, accepting that it
      // pushes the streak card down; otherwise the phone-hiding rule is unchanged.
      className={cn('w-full', !keepOnPhone && askDays == null && 'max-sm:hidden')}
      data-testid="train-landing-host"
    >
      {askDays != null ? (
        // The ask takes the whole bubble, so it outranks the
        // reminder-install ask (shown indefinitely to anyone without a phone
        // push subscription) and the import ask.
        <FeedbackAskBubble surface="train-landing" activeDays={askDays} avatarSize="large" />
      ) : (
        <TrainBotBubble
          persona={host.persona}
          state="prompt"
          avatarSize="large"
          actions={landingActions(showSignupAsk, showImportAsk)}
        >
          <p data-testid="train-tagline">{host.copy}</p>
          {showSignupAsk && (
            <p data-testid="train-landing-signup-ask">{GUEST_SIGNUP_ASK_SCORE}</p>
          )}
          {showImportAsk && <p data-testid="train-landing-import-ask">{IMPORT_ASK_LANDING}</p>}
          {showReminderAsk && (
            <p data-testid="train-landing-reminder-ask">{REMINDER_INSTALL_ASK}</p>
          )}
        </TrainBotBubble>
      )}
    </div>
  );
}

function landingActions(showSignupAsk: boolean, showImportAsk: boolean): ReactElement | undefined {
  if (showSignupAsk) return <SignupAskActions source="train-landing" />;
  if (showImportAsk) return <ImportAskActions source="train-landing" />;
  return undefined;
}

/**
 * The two tailored empty-state bodies (cold-start / exhausted)
 * plus the generic fallback — chosen purely from the server-computed
 * `pool_state` discriminant. The client performs no arithmetic over
 * `mastered_count`/`waiting_count`/`blob_pending_count` to pick between them;
 * a pending or errored progress query falls back to the generic copy rather
 * than guessing.
 */
function TrainEmptyBody({
  progress,
  isGuest,
}: {
  progress: ReturnType<typeof useTrainProgress>;
  isGuest: boolean;
}): ReactElement {
  const poolState = progress.isPending || progress.isError ? undefined : progress.data?.pool_state;

  if (poolState === 'no_material') {
    return (
      <div data-testid="train-empty-no-material">
        <EmptyState
          layout="page"
          title="Import & analyze your games to start training"
          subtitle="Train drills your own blunders once they're analyzed."
          action={
            <Button variant="brand-outline" asChild className={TRAIN_CTA_BUTTON_CLASS}>
              <Link to="/library/import" data-testid="btn-train-import-games">
                Import games
              </Link>
            </Button>
          }
        />
      </div>
    );
  }

  if (poolState === 'exhausted' && progress.data) {
    const { mastered_count, next_due_date } = progress.data;
    const nextDueCopy =
      next_due_date !== null
        ? `Next review: ${format(parseISO(next_due_date), 'MMM d, yyyy')}.`
        : 'Nothing due right now — nice work.';
    return (
      <>
        <TrainStreakCard />
        <TrainLeaderboardCard isGuest={isGuest} />
        <div data-testid="train-empty-exhausted">
          <EmptyState layout="page" title="All caught up!" subtitle={`${mastered_count} mastered. ${nextDueCopy}`} />
        </div>
      </>
    );
  }

  // Fallback (available / pending / errored): guessing between the two
  // tailored states without a resolved discriminant is the failure this
  // fallback exists to prevent.
  return (
    <EmptyState
      layout="page"
      title="No puzzles available yet"
      subtitle="Analyze more games to build your training pool."
    />
  );
}

export function TrainStartScreen({
  session,
  isLoading,
  isError,
  sessionScore,
  onEnterLoop,
  onSettingsSaved,
  isGuest,
  hasGames,
  feedbackAskDays,
}: TrainStartScreenProps): ReactElement {
  const state = resolveLandingState(session, isLoading, isError, sessionScore);
  const progress = useTrainProgress();

  // Matches the existing muted text-only route-loading pattern
  // (`import-required-loading` / `bots-loading`) rather than a new skeleton.
  if (state.kind === 'loading') {
    return (
      <div className="p-6 text-sm text-muted-foreground" data-testid="train-session-loading">
        Loading…
      </div>
    );
  }

  if (state.kind === 'error') {
    return (
      <div data-testid="train-start-screen">
        <LoadError resource="your training session" variant="centered" />
      </div>
    );
  }

  if (state.kind === 'empty') {
    return (
      <div className={LANDING_CONTAINER_CLASS} data-testid="train-start-screen">
        <TrainMedalDialogHost isGuest={isGuest} />
        <TrainReminderResurfaceBanner />
        <TrainEmptyBody progress={progress} isGuest={isGuest} />
      </div>
    );
  }

  if (state.kind === 'completed') {
    return (
      <div className={LANDING_CONTAINER_CLASS} data-testid="train-start-screen">
        <TrainMedalDialogHost isGuest={isGuest} />
        <TrainReminderResurfaceBanner />
        <TrainLandingHost
          session={session}
          isGuest={isGuest}
          hasGames={hasGames}
          feedbackAskDays={feedbackAskDays}
          sessionCompleted
        />
        <TrainStreakCard />
        <TrainScheduleSettings
          onSaved={onSettingsSaved}
          nextSessionDate={state.nextSessionDate}
          isGuest={isGuest}
        />
        <TrainLeaderboardCard isGuest={isGuest} />
        <TrainStatsCard todayScore={{ total: state.score, max: state.totalPoints }} />
      </div>
    );
  }

  // The fresh/warmup puzzle count lives in the label, matching the shape
  // 'resume' uses, so the two states describing the same button agree on where
  // the number lives and no loose line sits above the CTA.
  const buttonLabel =
    state.kind === 'resume'
      ? `Resume session — ${state.solved} of ${state.total} done`
      : `Start session — ${state.puzzleCount} ${state.puzzleCount === 1 ? 'puzzle' : 'puzzles'}`;

  // The CTA lives INSIDE the streak hero, beside the flame, so the one action
  // on the page and the number it feeds share a glance above the fold on a
  // phone.
  return (
    <div className={LANDING_CONTAINER_CLASS} data-testid="train-start-screen">
      <TrainMedalDialogHost isGuest={isGuest} />
      <TrainReminderResurfaceBanner />
      <TrainLandingHost
        session={session}
        isGuest={isGuest}
        hasGames={hasGames}
        feedbackAskDays={feedbackAskDays}
        sessionCompleted={false}
      />
      <TrainStreakCard
        action={
          <Button
            variant="default"
            className={`${TRAIN_BUTTON_CLASS} w-full`}
            data-testid={state.kind === 'resume' ? 'btn-train-resume' : 'btn-train-start'}
            // A re-fetch after a schedule save may replace this session.
            disabled={isLoading}
            onClick={onEnterLoop}
          >
            {buttonLabel}
          </Button>
        }
      />
      <TrainScheduleSettings onSaved={onSettingsSaved} isGuest={isGuest} />
      <TrainLeaderboardCard isGuest={isGuest} />
      <TrainStatsCard />
    </div>
  );
}
