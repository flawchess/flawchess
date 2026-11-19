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
 * Every state renders the same Today card (`TrainStreakCard`, with one launcher
 * row per mode), with the settings column beside it (desktop) or below it (phones):
 * one collapsed settings row per mode (`TrainModeSettings`), then the schedule card.
 * All of them edit ONE settings draft (`useTrainSettingsDraft`) owned here, which a
 * launcher row's "Turn on" writes to as well. The session state drives the
 * puzzles row (Start, Resume or done with today's Points). The weekly
 * leaderboard lives on its own tab, not here (the card's rank line links to it).
 *
 * The medal dialog is not rendered here: the Train page layout owns
 * `TrainMedalDialogHost`, outside the immersive views, so it opens on any tab
 * and never over a session.
 *
 * `isVisible` is false while the Today panel is mounted but hidden (the player
 * is on another tab). `TrainLandingHost` (a feedback-ask view POST on mount)
 * and `TrainStreakCard` (reads and rewrites the streak arrival snapshot on
 * mount) are one-shot consumers, so they mount only while visible; a landing
 * the player cannot see must record nothing. `TrainScheduleSettings` stays
 * mounted at a stable child position so its debounced save survives a tab
 * switch.
 */

import type { ReactElement } from 'react';
import { format, parseISO } from 'date-fns';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { FeedbackAskBubble } from '@/components/feedback/FeedbackAskBubble';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadError } from '@/components/ui/load-error';
import { TRAIN_CTA_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { ImportAskActions } from '@/components/train/ImportAskActions';
import { SignupAskActions } from '@/components/train/SignupAskActions';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import { TrainReminderResurfaceBanner } from '@/components/train/TrainReminderResurfaceBanner';
import { DEFAULT_MODE_SIZE, TrainModeSettings } from '@/components/train/TrainModeSettings';
import type { TrainLauncherMode } from '@/components/train/TrainModeLauncherRow';
import { TrainScheduleSettings } from '@/components/train/TrainScheduleSettings';
import { TrainStreakCard } from '@/components/train/TrainStreakCard';
import type { PuzzlesLanding } from '@/components/train/TrainStreakCard';
import { useTrainProgress } from '@/hooks/useTrainProgress';
import { useTrainSettings } from '@/hooks/useTrainSettings';
import { useTrainSettingsDraft } from '@/hooks/useTrainSettingsDraft';
import {
  GUEST_SIGNUP_ASK_SCORE,
  IMPORT_ASK_LANDING,
  REMINDER_INSTALL_ASK,
  isRevealTourDone,
  landingHost,
} from '@/lib/trainBotCopy';
import { trackFeature } from '@/lib/analytics';
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
  /**
   * False while the Today panel is hidden behind another tab. The one-shot
   * landing children (`TrainLandingHost`, `TrainStreakCard`) mount only while
   * this is true, so a landing the player cannot see records no feedback-ask
   * view and consumes no streak arrival. The schedule card ignores it, to keep
   * its pending debounced save.
   */
  isVisible: boolean;
  /**
   * D-21 / D-03: whether the Train step's feature-route dot sits on the start
   * button (Start, Warmup and Resume share it). Decided by the page and passed
   * as a prop so this component stays hook-free for its provider-less tests.
   */
  showRouteDot: boolean;
}

/**
 * The landing page is the same content column as the Import page —
 * `mx-auto w-full max-w-2xl` on top of the page-level `px-4 py-6 md:px-6`
 * (see Import.tsx's `<main>` and Train.tsx). Without the max-width the
 * settings chips stretch edge-to-edge on a wide window while the text sits
 * flush against the left gutter. Text stays left-aligned inside the column.
 *
 * The column widens from lg so the Today card and the settings column fit side by
 * side. Only the landing states use this — `TrainSolveScreen` is a two-column lg
 * layout that must keep the full page width.
 *
 * There is no top padding: the Today panel's `mt-4` supplies the gap under the
 * tabs. Bottom padding is `pb-6 md:pb-8`.
 */
const LANDING_CONTAINER_CLASS =
  'mx-auto flex w-full max-w-2xl flex-col items-start gap-4 pb-6 text-left md:pb-8 lg:max-w-4xl';

/** One column on phones (host bubble, Today card, mode rows, schedule row); from lg the Today
 * card sits on the left and the settings column on the right. */
const LANDING_GRID_CLASS = 'grid w-full grid-cols-1 items-start gap-4 lg:grid-cols-2';


type LandingState =
  | { kind: 'loading' }
  | { kind: 'error' }
  | { kind: 'empty' }
  | { kind: 'completed'; score: number; nextSessionDate: string }
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
  // then unmounted the whole landing mid-edit. The old session keeps
  // rendering instead, with Start disabled until the fresh one lands.
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
    return { kind: 'completed', score: sessionScore, nextSessionDate: session.expires_on };
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
}: {
  progress: ReturnType<typeof useTrainProgress>;
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
      <div data-testid="train-empty-exhausted">
        <EmptyState layout="page" title="All caught up!" subtitle={`${mastered_count} mastered. ${nextDueCopy}`} />
      </div>
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

/**
 * What today's puzzle session tells the puzzles launcher row. The session response, not the
 * server's per-mode estimate, decides whether Start or Resume shows and how many puzzles are
 * left. 'empty' and the load states carry none, so the row falls back to the server mode.
 */
function puzzlesLandingFor(state: LandingState): PuzzlesLanding | undefined {
  switch (state.kind) {
    case 'completed':
      return { state: 'done', left: 0, pointsToday: state.score };
    case 'resume':
      return { state: 'in_progress', left: state.total - state.solved, pointsToday: 0 };
    case 'warmup':
    case 'fresh':
      return { state: 'pending', left: state.puzzleCount, pointsToday: 0 };
    default:
      return undefined;
  }
}

export function TrainStartScreen({
  session,
  isLoading,
  isError,
  sessionScore,
  onSettingsSaved,
  isGuest,
  hasGames,
  feedbackAskDays,
  isVisible,
  showRouteDot,
}: TrainStartScreenProps): ReactElement {
  const state = resolveLandingState(session, isLoading, isError, sessionScore);
  const progress = useTrainProgress();
  // The one settings draft: the mode rows and the schedule card all edit it, so a debounced
  // save never overwrites another edit. It lives here (above the early returns) so a pending
  // save survives the loading state and a tab switch.
  const settingsDraft = useTrainSettingsDraft({ onSaved: onSettingsSaved });

  // An off launcher row's Turn on writes the default size into the shared draft, so it rides
  // the same debounced PUT as the sliders (D-09). Nothing happens until settings have loaded.
  const handleTurnOn = (mode: TrainLauncherMode): void => {
    if (settingsDraft.draft === null) return;
    if (mode === 'puzzles') {
      trackFeature('action', { target: 'train-mode-turn-on-puzzles' });
      settingsDraft.update({ puzzlesPerSession: DEFAULT_MODE_SIZE });
      return;
    }
    trackFeature('action', { target: 'train-mode-turn-on-blunder-check' });
    settingsDraft.update({ blunderCheckPerSession: DEFAULT_MODE_SIZE });
  };

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

  // The Today card (flame, freezes and one launcher row per mode) renders in every landing
  // state, so both modes stay reachable. A re-fetch after a schedule save may replace the
  // session, so the puzzles Start is disabled while loading, and while there is no session.
  const todayCard = isVisible && (
    <TrainStreakCard
      puzzlesLanding={puzzlesLandingFor(state)}
      puzzlesStartDisabled={isLoading || state.kind === 'empty'}
      showRouteDot={showRouteDot}
      onTurnOn={handleTurnOn}
    />
  );
  const completed = state.kind === 'completed';

  if (state.kind === 'empty') {
    // With puzzles off, "no puzzles available" copy would be wrong (the user chose zero);
    // the mode rows and schedule beside the card are where they turn the mode back on.
    const puzzlesOff = progress.data?.modes.puzzles.state === 'off';
    return (
      <div className={LANDING_CONTAINER_CLASS} data-testid="train-start-screen">
        <TrainReminderResurfaceBanner />
        <div className={LANDING_GRID_CLASS} data-testid="train-landing-grid">
          {todayCard}
          <div className="flex min-w-0 flex-col gap-4">
            <TrainModeSettings settingsDraft={settingsDraft} />
            <TrainScheduleSettings settingsDraft={settingsDraft} isGuest={isGuest} />
          </div>
        </div>
        {!puzzlesOff && <TrainEmptyBody progress={progress} />}
      </div>
    );
  }

  return (
    <div className={LANDING_CONTAINER_CLASS} data-testid="train-start-screen">
      <TrainReminderResurfaceBanner />
      {isVisible && (
        <TrainLandingHost
          session={session}
          isGuest={isGuest}
          hasGames={hasGames}
          feedbackAskDays={feedbackAskDays}
          sessionCompleted={completed}
        />
      )}
      <div className={LANDING_GRID_CLASS} data-testid="train-landing-grid">
        {todayCard}
        <div className="flex min-w-0 flex-col gap-4">
          <TrainModeSettings settingsDraft={settingsDraft} />
          <TrainScheduleSettings
            settingsDraft={settingsDraft}
            nextSessionDate={state.kind === 'completed' ? state.nextSessionDate : undefined}
            isGuest={isGuest}
          />
        </div>
      </div>
    </div>
  );
}
