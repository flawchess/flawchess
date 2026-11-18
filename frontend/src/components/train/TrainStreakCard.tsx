/**
 * TrainStreakCard — the Train landing's Today card (sketch 014 variant B): the
 * session streak drawn inside a 3-layer flame on the left; on the right the
 * weekly tally and the 0-7 freeze meter; beneath them one launcher row per mode
 * (`TrainModeLauncherRow`), which are the both-required streak checklist (D-08).
 * Under the weekly tally sits the rank line: the viewer's Points rank this week
 * (`#4 this week`) as a link to the Leaderboard tab, left out with no rank.
 * Self-contained: calls `useTrainProgress()` and `useTrainLeaderboard()`
 * internally.
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
import { TrainModeLauncherRow } from '@/components/train/TrainModeLauncherRow';
import type { TrainLauncherMode } from '@/components/train/TrainModeLauncherRow';
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
import type { TrainModeProgress, TrainModeState, TrainProgressResponse } from '@/types/train';

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

/**
 * What the landing knows about today's puzzle session. The session response is the
 * authority for what the Start button does (fresh, resume or done) and for the count
 * left, so it overrides the server's per-mode estimate for the puzzles row. A server
 * `off` (session size 0) always wins.
 */
export interface PuzzlesLanding {
  state: TrainModeState;
  /** Puzzles left in today's session. */
  left: number;
  /** Points scored in today's session, shown once it is done. */
  pointsToday: number;
}

export interface TrainStreakCardProps {
  puzzlesLanding?: PuzzlesLanding;
  /** Disables the puzzles Start / Resume (the session is loading or has no puzzles). */
  puzzlesStartDisabled?: boolean;
  /** Puts the feature-route dot on the puzzles Start / Resume button. */
  showRouteDot?: boolean;
  /** Called by an off row's Turn on button; no button renders without it. */
  onTurnOn?: (mode: TrainLauncherMode) => void;
}

/**
 * The puzzles row's progress. Without a landing the count left is the server's
 * `waiting_count` estimate, an upper bound that can exceed one session, so it is capped
 * at the session size.
 */
function puzzlesRowProgress(
  server: TrainModeProgress,
  landing: PuzzlesLanding | undefined,
): TrainModeProgress {
  if (server.state === 'off') return server;
  if (landing === undefined) return { ...server, remaining: Math.min(server.remaining, server.size) };
  return { ...server, state: landing.state, remaining: landing.left };
}

/** The two launcher rows, the streak checklist (D-08). */
function TrainLauncherRows({
  data,
  puzzlesLanding,
  puzzlesStartDisabled,
  showRouteDot,
  onTurnOn,
}: { data: TrainProgressResponse } & TrainStreakCardProps): ReactElement {
  return (
    <div className="col-span-2 flex flex-col gap-3" data-testid="train-launcher-rows">
      <TrainModeLauncherRow
        mode="puzzles"
        progress={puzzlesRowProgress(data.modes.puzzles, puzzlesLanding)}
        pointsToday={puzzlesLanding?.pointsToday ?? 0}
        disabled={puzzlesStartDisabled}
        showRouteDot={showRouteDot}
        onTurnOn={onTurnOn}
      />
      <TrainModeLauncherRow
        mode="blunder_check"
        progress={data.modes.blunder_check}
        pointsToday={data.modes.blunder_check.points_today}
        onTurnOn={onTurnOn}
      />
    </div>
  );
}

export function TrainStreakCard({
  puzzlesLanding,
  puzzlesStartDisabled = false,
  showRouteDot = false,
  onTurnOn,
}: TrainStreakCardProps): ReactElement {
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

  // Flame | details on one row, the launcher rows full card width beneath
  // (both Start buttons sit above the phone fold on this one card).
  return (
    <Card as="section" className="w-full" data-testid="train-streak-card">
      <CardBody className="grid grid-cols-[6rem_minmax(0,1fr)] items-center gap-x-4 gap-y-3">
        <div>{visuals?.flame ?? <div className="aspect-[100/122] w-full" aria-hidden="true" />}</div>
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
          {details}
        </div>
        {data !== undefined && (
          <TrainLauncherRows
            data={data}
            puzzlesLanding={puzzlesLanding}
            puzzlesStartDisabled={puzzlesStartDisabled}
            showRouteDot={showRouteDot}
            onTurnOn={onTurnOn}
          />
        )}
      </CardBody>
    </Card>
  );
}
