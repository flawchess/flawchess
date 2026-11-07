/**
 * Train — the /train layout.
 *
 * Default export (required by React.lazy in App.tsx, mirroring Bots.tsx /
 * Analysis.tsx's divergence from the app's named-export convention).
 *
 * `/train/*` is one route, so this page parses the pathname
 * (`lib/trainRoute.ts`) and renders URL-routed tabs: Today (the landing, the
 * solve loop and the score screen), Leaderboard and Archive. An unknown `/train/*` path
 * redirects to `/train`. The session, the grading Worker and the loop flags
 * live in `useTrainLoop` (see its docstring for the session and loop rules
 * and the Today latch that keeps a Leaderboard-only visit from creating a
 * session or loading the engine).
 *
 * The tab bar shows everywhere except the immersive states (the solve loop,
 * the score screen and a cached restored reveal, from the first paint), where
 * the solve screen needs the full page height. The wrapper keeps the same element across tabs and only swaps
 * its class, so nothing remounts.
 */

import { Navigate, useLocation } from 'react-router';
import type { ReactElement } from 'react';
import { useTrainLoop } from '@/hooks/useTrainLoop';
import type { UseTrainLoopResult } from '@/hooks/useTrainLoop';
import { hasImportedGames, useUserProfile } from '@/hooks/useUserProfile';
import { TrainStartScreen } from '@/components/train/TrainStartScreen';
import { TrainSolveScreen } from '@/components/train/TrainSolveScreen';
import { TrainScoreScreen } from '@/components/train/TrainScoreScreen';
import { TrainDevClock } from '@/components/train/TrainDevClock';
import { TrainLeaderboardCard } from '@/components/train/TrainLeaderboardCard';
import { TrainMedalDialogHost } from '@/components/train/medals/TrainMedalDialogHost';
import { TrainSubnav } from '@/components/train/TrainSubnav';
import { TrainArchiveTab } from '@/components/train/TrainArchiveTab';
import { DEV_CLOCK_ENABLED } from '@/lib/devClock';
import { feedbackAskDays } from '@/lib/feedbackAsk';
import { parseTrainRoute, TRAIN_TAB_PATHS } from '@/lib/trainRoute';
import { TRAIN_POINTS_PER_PUZZLE } from '@/lib/trainScore';
import { cn } from '@/lib/utils';

/** The page wrapper's classes while a session view is on screen (the loop or a
 * restored reveal); it drops the phone top padding (see the comment at the
 * call site). Module-level so the branching stays out of `TrainPage`'s own
 * gated complexity. */
function trainPageClass(showLoop: boolean, restoredActive: boolean): string {
  return cn('px-4 py-6 md:px-6', (showLoop || restoredActive) && 'max-sm:pt-0');
}

/** The wrapper's classes on the tab views: the same max-w-7xl on every tab. */
const TRAIN_TAB_PAGE_CLASS = 'mx-auto w-full max-w-7xl px-4 py-2 md:px-6 md:py-6';

/** The solve loop, restored reveal and score screen. They render only on
 * Today, so one `isToday` gate covers all three. */
function TrainSessionViews({
  isToday,
  loop,
  isGuest,
  hasGames,
}: {
  isToday: boolean;
  loop: UseTrainLoopResult;
  isGuest: boolean;
  hasGames: boolean;
}): ReactElement | null {
  const { trainSession, gradingEngine, restoredActive, restoredReveal, showLoop, showScoreScreen } =
    loop;
  if (!isToday) return null;
  return (
    <>
      {restoredActive && restoredReveal && (
        <TrainSolveScreen
          puzzle={restoredReveal.puzzle}
          trainSession={trainSession}
          gradingEngine={gradingEngine}
          restoredSolve={restoredReveal}
          onNext={loop.handleRestoredNext}
        />
      )}
      {showLoop && trainSession.currentPuzzle && (
        <TrainSolveScreen
          puzzle={trainSession.currentPuzzle}
          trainSession={trainSession}
          gradingEngine={gradingEngine}
          onNext={loop.handleNext}
        />
      )}
      {showScoreScreen && trainSession.session && (
        <TrainScoreScreen
          score={{
            total: trainSession.sessionScore,
            max: trainSession.session.puzzle_count * TRAIN_POINTS_PER_PUZZLE,
          }}
          nextSessionDate={trainSession.session.expires_on}
          onDone={loop.returnToLanding}
          solvedOutcomes={trainSession.solvedOutcomes}
          isWarmup={trainSession.session.is_warmup}
          hasGames={hasGames}
          isGuest={isGuest}
          sessionId={trainSession.session.session_id}
        />
      )}
    </>
  );
}

export default function TrainPage(): ReactElement {
  const { pathname } = useLocation();
  const route = parseTrainRoute(pathname);
  const isToday = route?.tab === 'today';
  // FLAWCHESS-64: is_guest read from useUserProfile(), never useAuth().user
  // (always null, carries no is_guest; cf. Analysis.tsx's free-play ELO
  // default source comment).
  const { data: profile, isError: profileError } = useUserProfile();
  const isGuest = profile?.is_guest === true;
  // The two orthogonal flags the games-less Train copy
  // branches on. hasImportedGames is the SAME shared zero-game predicate
  // Home.tsx uses — never re-derived here.
  const hasGames = hasImportedGames(profile);
  // No /train/* handler rejects guests, so canTrain only waits for the
  // profile to resolve.
  const canTrain = profile != null;
  const loop = useTrainLoop({ isToday, canTrain });
  const { trainSession, showLoop, showScoreScreen, restoredActive, immersive } = loop;

  // All hooks are above: an unknown /train/* path lands on Today.
  if (route === null) {
    return <Navigate to={TRAIN_TAB_PATHS.today} replace />;
  }

  if (profile == null) {
    return (
      <div className="px-4 py-6 md:px-6" data-testid="train-page">
        {profileError ? (
          <p className="text-sm text-muted-foreground" data-testid="train-profile-error">
            Failed to load your profile. Something went wrong. Please try again in a moment.
          </p>
        ) : (
          <p className="text-sm text-muted-foreground" data-testid="train-profile-loading">
            Loading your profile…
          </p>
        )}
      </div>
    );
  }

  const landingActive = !(showLoop || showScoreScreen || restoredActive);

  return (
    // While a puzzle is on screen the phone header is suppressed
    // (`useMarkPlayActive`), so the top padding would only push the pinned
    // progress row + board down — drop it below `sm`, the header's own
    // breakpoint. Otherwise the tab views share one max-w-7xl wrapper.
    <div
      className={immersive ? trainPageClass(showLoop, restoredActive) : TRAIN_TAB_PAGE_CLASS}
      data-testid="train-page"
    >
      {!immersive && <TrainSubnav active={route.tab} />}
      {/* The layout owns the medal dialog so it opens on any tab (a Leaderboard
          deep link included). It is unmounted in the immersive views, so it
          never covers a session, and it sits at a stable position so a tab
          switch keeps its dismissed state. */}
      {!immersive && <TrainMedalDialogHost isGuest={isGuest} />}
      {/* The landing stays mounted but hidden on the other tabs once Today has
          been visited: `TrainScheduleSettings` debounces saves by 600 ms, so an
          edit followed by a quick tab switch would otherwise lose the save, and
          the return to Today shows no skeleton flash. `isVisible` keeps the
          one-shot effects (feedback-ask view, streak arrival snapshot) from
          firing out of sight: the host bubble and streak card mount only
          while Today is on screen. */}
      {loop.todayVisited && landingActive && (
        <div className={cn('mt-4', !isToday && 'hidden')} data-testid="train-today-panel">
          {/* Landing screen only: the strip is vertical chrome above the solve
              screen's board column, which on mobile is pinned and sized to the
              viewport — every row above it comes straight out of the board. Time
              travel is only ever ARMED from the landing screen anyway (a change
              bounces back here via returnToLanding), so nothing is lost by
              hiding it once a session is running. Today panel only: its handler
              fires a session read. */}
          {DEV_CLOCK_ENABLED && <TrainDevClock onChange={loop.returnToLanding} />}
          <TrainStartScreen
            session={trainSession.session}
            // The session mutation is idle on the first commit, before the mount
            // effect fires it, so `isSessionPending` alone would flash the
            // empty state on every first Today click. No session and no error
            // yet means the first load is still to come.
            isLoading={
              trainSession.isSessionPending ||
              (trainSession.session === null && !trainSession.isSessionError)
            }
            isError={trainSession.isSessionError}
            sessionScore={trainSession.sessionScore}
            onEnterLoop={loop.enterLoop}
            onSettingsSaved={loop.requestSessionReread}
            isGuest={isGuest}
            hasGames={hasGames}
            feedbackAskDays={feedbackAskDays(profile)}
            isVisible={isToday}
          />
        </div>
      )}
      <TrainSessionViews isToday={isToday} loop={loop} isGuest={isGuest} hasGames={hasGames} />
      {route.tab === 'leaderboard' && (
        <div className="mx-auto mt-4 w-full max-w-2xl" data-testid="train-leaderboard-panel">
          <TrainLeaderboardCard isGuest={isGuest} />
        </div>
      )}
      {route.tab === 'archive' && (
        <div className="mt-4" data-testid="train-archive-panel">
          <TrainArchiveTab list={route.list} />
        </div>
      )}
    </div>
  );
}
