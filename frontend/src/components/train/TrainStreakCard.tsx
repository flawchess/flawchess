/**
 * TrainStreakCard — the Train landing's hero card: the session streak drawn
 * inside a 3-layer flame on the left; on the right the weekly tally, the 0-7
 * freeze meter and, when the session is startable, the Start/Resume button
 * passed in as `action`. Under the weekly tally sits the rank line: the
 * viewer's Points rank this week (`#4 this week`) as a link to the Leaderboard
 * tab, left out with no rank. Self-contained: calls `useTrainProgress()` and
 * `useTrainLeaderboard()` internally.
 *
 * The streak buffer is shown as snowflake "freezes" (cold color family,
 * distinct from the flame, which is reserved for the streak). The
 * `shield_level` API field and the `train-shield-*` testids keep the older
 * name; don't rename them.
 *
 * The flame and meter play a one-shot animation only when the numbers changed
 * since this device last showed them (`lib/streakArrival.ts`).
 */
import { useLayoutEffect, useRef, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { Link } from 'react-router';
import { Card, CardBody } from '@/components/ui/card';
import { InfoPopover } from '@/components/ui/info-popover';
import { LoadError } from '@/components/ui/load-error';
import { FreezeMeter } from '@/components/train/FreezeMeter';
import { StreakFlame } from '@/components/train/StreakFlame';
import { useTrainLeaderboard } from '@/hooks/useTrainLeaderboard';
import { useTrainProgress } from '@/hooks/useTrainProgress';
import { useUserProfile } from '@/hooks/useUserProfile';
import {
  FREEZE_CAP,
  FREEZE_CRACK_STAGGER_MS,
  readStreakLastSeen,
  resolveStreakArrival,
  writeStreakLastSeen,
} from '@/lib/streakArrival';
import type { StreakArrival } from '@/lib/streakArrival';
import { trackFeature } from '@/lib/analytics';
import { TRAIN_TAB_PATHS } from '@/lib/trainRoute';
import type { TrainProgressResponse } from '@/types/train';

/** A freeze earned together with a streak tick pops in once the ignite settles. */
const EARNED_AFTER_IGNITE_DELAY_MS = 1300;
/** The frost sweep or extinguish starts just after the last spent freeze has cracked. */
const FROST_AFTER_CRACKS_PAD_MS = 100;

/**
 * Mirrors `app.services.train_scheduler._judge_one_day`'s four outcomes:
 * "fulfilled" is +1 streak +1 freeze, "credit_only" (an off-day session) is
 * +1 freeze and NO streak change, "missed" is -1 freeze with the streak held
 * until the freezes hit 0 and it resets, "neutral" changes nothing. Prose only — the client holds no
 * copy of that arithmetic beyond the cap, which is interpolated.
 */
const STREAK_EXPLAINER =
  `Complete a session on a scheduled training day and your streak goes up by 1. Sessions on other days don't count toward it. ` +
  `Every completed session earns a freeze (${FREEZE_CAP} max). Each missed scheduled day uses one; when you have none left, your streak resets to 0.`;

/** The weekly tally under the "Session streak" heading. */
function thisWeekCaption(completed: number, required: number | null): string {
  if (required !== null) return `${completed} of ${required} this week`;
  // "Train anytime" mode has no denominator to show.
  return `${completed} this week`;
}

/**
 * The viewer's Points rank this week as a link to the Leaderboard tab. Reads
 * the Points board only: Accuracy stays tentative and unranked until 20
 * puzzles. Hidden and guest viewers carry an integer rank too (pinned
 * server-side), so their line reads like anyone else's. With no rank, or on a
 * query error, there is no line; the Leaderboard tab shows its own LoadError
 * and the global QueryCache reports the failure to Sentry.
 */
function TrainRankLine(): ReactElement | null {
  const { data, isPending, isError } = useTrainLeaderboard();
  if (isPending) {
    // Reserve the row while loading, so nothing shifts when a rank arrives. The
    // reservation only holds for viewers who have a rank: with no rank (or on
    // error) this returns null below and the row collapses once the query
    // resolves, which is intended (the line is simply left out).
    return (
      <span className="text-sm" aria-hidden="true" data-testid="train-rank-line-pending">
        {'\u00a0'}
      </span>
    );
  }
  const rank = isError ? null : (data?.points.viewer?.rank ?? null);
  if (rank === null) return null;
  return (
    <Link
      to={TRAIN_TAB_PATHS.leaderboard}
      data-testid="train-rank-line"
      className="w-fit text-sm text-brand-brown-light transition-colors hover:text-brand-brown-highlight"
      // Not data-umami-event: on a router Link it downgrades the client-side
      // navigation into a full page reload.
      onClick={() => trackFeature('nav-click', { target: 'train', value: 'train-rank-line' })}
    >
      {`#${rank} this week`}
    </Link>
  );
}

/**
 * Resolves the arrival animation once per mount, BEFORE paint (layout
 * effect), so the flame never flashes its final state and then re-ignites.
 * The ref survives StrictMode's effect double-invoke, which would otherwise
 * re-read the snapshot this effect just wrote and resolve "no change".
 * Later progress refetches only refresh the stored snapshot.
 */
function useStreakArrival(
  streak: number | undefined,
  freezes: number | undefined,
  ownerKey: string | null,
  ownerResolved: boolean,
): StreakArrival | null {
  const [arrival, setArrival] = useState<StreakArrival | null>(null);
  const resolvedRef = useRef(false);

  useLayoutEffect(() => {
    if (!ownerResolved || streak === undefined || freezes === undefined) return;
    const next = { streak, freezes };
    if (!resolvedRef.current) {
      resolvedRef.current = true;
      setArrival(resolveStreakArrival(readStreakLastSeen(ownerKey), next));
    }
    writeStreakLastSeen(ownerKey, next);
  }, [streak, freezes, ownerKey, ownerResolved]);

  return arrival;
}

/** The populated flame + freeze row, mounted once the arrival is known so the
 * animations start from their first frame. */
function buildStreakVisuals({
  data,
  arrival,
}: {
  data: TrainProgressResponse;
  arrival: StreakArrival;
}): { flame: ReactElement; meter: ReactElement } {
  const changed = arrival.kind === 'changed' ? arrival : null;
  const ignite = changed?.ignite ?? false;
  const usedCount = changed?.freezesUsed ?? 0;
  // Frost (streak held) or extinguish (streak reset) waits for the cracks.
  const afterCracksMs = usedCount * FREEZE_CRACK_STAGGER_MS + FROST_AFTER_CRACKS_PAD_MS;
  const frostDelayMs = usedCount > 0 ? afterCracksMs : null;
  return {
    flame: (
      <StreakFlame
        count={data.session_streak_count}
        ignite={ignite}
        countFrom={changed?.prev.streak ?? data.session_streak_count}
        frostDelayMs={frostDelayMs}
        extinguishFrom={changed?.extinguish ? changed.prev.streak : null}
        extinguishDelayMs={usedCount > 0 ? afterCracksMs : 0}
        className="w-full"
      />
    ),
    meter: (
      <FreezeMeter
        freezes={data.shield_level}
        usedCount={usedCount}
        earnedCount={changed?.freezesEarned ?? 0}
        earnedDelayMs={ignite ? EARNED_AFTER_IGNITE_DELAY_MS : 0}
      />
    ),
  };
}

export interface TrainStreakCardProps {
  /** The Start/Resume button, in the states where a session is startable. */
  action?: ReactNode;
  /**
   * Today's score, passed only by the completed landing. The label says
   * "Points" because a bare `5/9` next to "Puzzles per session" reads as a
   * puzzle count.
   */
  pointsToday?: { total: number; max: number };
}

export function TrainStreakCard({ action, pointsToday }: TrainStreakCardProps): ReactElement {
  const { data, isPending, isError } = useTrainProgress();
  const profile = useUserProfile();
  const arrival = useStreakArrival(
    data?.session_streak_count,
    data?.shield_level,
    profile.data?.email ?? null,
    !profile.isPending,
  );
  const visuals = data !== undefined && arrival !== null ? buildStreakVisuals({ data, arrival }) : null;

  let details: ReactNode;
  if (isPending) {
    details = (
      <div
        data-testid="train-progress-loading"
        className="h-6 w-full animate-pulse rounded bg-muted"
        aria-hidden="true"
      />
    );
  } else if (isError || data === undefined) {
    details = <LoadError resource="your progress" variant="inline" data-testid="train-progress-error" />;
  } else {
    details = (
      <>
        <div className="flex items-center gap-2 text-sm text-muted-foreground" data-testid="train-shield-row">
          Freezes
          {visuals?.meter}
        </div>
        {data.streak_reset_notice && (
          <p data-testid="train-streak-reset-notice" className="text-sm text-muted-foreground">
            Streak reset. Complete a session to start a new one.
          </p>
        )}
      </>
    );
  }

  // Phone: flame | details on one row, the action full card width beneath it
  // (a ~200px column cannot hold "Resume session — 3 of 6 done" at the mobile
  // type bump). From sm: up the flame spans both rows and the action sits in
  // the right column, beside the flame.
  return (
    <Card as="section" className="w-full" data-testid="train-streak-card">
      <CardBody className="grid grid-cols-[6rem_minmax(0,1fr)] items-center gap-x-4 gap-y-3">
        <div className={action !== undefined ? 'sm:row-span-2' : undefined}>
          {visuals?.flame ?? <div className="aspect-[100/122] w-full" aria-hidden="true" />}
        </div>
        <div className="flex min-w-0 flex-col gap-1.5">
          <div className="flex items-center gap-1.5 text-sm font-semibold">
            Session streak
            <InfoPopover
              ariaLabel="How the streak and freezes work"
              testId="train-shield-explainer"
              side="bottom"
            >
              {STREAK_EXPLAINER}
            </InfoPopover>
          </div>
          {data !== undefined && (
            <span className="text-sm text-muted-foreground" data-testid="train-this-week">
              {thisWeekCaption(data.current_week_completed, data.current_week_required)}
            </span>
          )}
          <TrainRankLine />
          {pointsToday !== undefined && (
            <span className="text-sm text-muted-foreground" data-testid="train-points-today">
              {`Points today: ${pointsToday.total}/${pointsToday.max}`}
            </span>
          )}
          {details}
        </div>
        {action !== undefined && <div className="col-span-2 sm:col-span-1 sm:col-start-2">{action}</div>}
      </CardBody>
    </Card>
  );
}
