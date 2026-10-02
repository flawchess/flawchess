/**
 * TrainStatsCard — the drill-pool numbers on the Train landing screen, as a
 * row of stat tiles (SEED-181, sketch 006 A: the streak hero above carries the
 * page's one big moment, so the pool reads as a quick glance underneath it).
 *
 * History: 193 UAT round 2 gave mastered/parked their own card ("Puzzle
 * pool") rather than sharing the streak row; round 3 gave both terms an
 * `InfoPopover` — "mastered" and "parked" are Train's SR vocabulary and are
 * defined nowhere else on the page. The popovers stay on the tile labels.
 *
 * `todayScore` is only passed by the 'completed' landing state (the session
 * is over and there IS a score to report) — every other state renders
 * without that tile rather than showing a meaningless 0.
 *
 * Self-contained apart from that one prop: calls `useTrainProgress()`
 * internally, exactly like `TrainStreakCard`.
 */
import type { ReactElement } from 'react';
import { Card } from '@/components/ui/card';
import { InfoPopover } from '@/components/ui/info-popover';
import { LoadError } from '@/components/ui/load-error';
import { useTrainProgress } from '@/hooks/useTrainProgress';
import { cn } from '@/lib/utils';

export interface TrainStatsCardProps {
  /**
   * Points scored in today's completed session, or undefined when no
   * session has been completed in the current window. `max` is
   * `puzzle_count * TRAIN_POINTS_PER_PUZZLE` — resolved by the caller,
   * never recomputed here.
   */
  todayScore?: { total: number; max: number };
}

/**
 * Copy mirrors `app.services.train_scheduler`'s `MASTERY_STREAK_THRESHOLD`
 * (3), `PARK_FAIL_THRESHOLD` (3), and `LEECH_FAIL_THRESHOLD` (6). Prose only
 * — no client-side logic reads these thresholds, so there is nothing here to
 * keep numerically in sync beyond the wording.
 */
const MASTERED_EXPLAINER = 'Solved correctly 3 times in a row. Mastered puzzles stop coming back.';
const PARKED_EXPLAINER =
  'Missed 6 times in total, or 3 times without ever solving it. Parked puzzles are set aside so they stop resurfacing.';

interface StatTileProps {
  value: string;
  label: string;
  testId: string;
  info?: { body: string; ariaLabel: string; testId: string };
}

function StatTile({ value, label, testId, info }: StatTileProps): ReactElement {
  return (
    <Card className="w-full px-4 py-3" data-testid={testId}>
      <div className="text-xl leading-tight font-bold tabular-nums">{value}</div>
      <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
        {label}
        {info !== undefined && (
          <InfoPopover ariaLabel={info.ariaLabel} testId={info.testId}>
            {info.body}
          </InfoPopover>
        )}
      </div>
    </Card>
  );
}

export function TrainStatsCard({ todayScore }: TrainStatsCardProps): ReactElement {
  const { data, isPending, isError } = useTrainProgress();

  if (isPending) {
    return (
      <div
        data-testid="train-stats-loading"
        className="h-16 w-full animate-pulse rounded-md bg-muted"
        aria-hidden="true"
      />
    );
  }

  if (isError || data === undefined) {
    return (
      <Card as="section" className="w-full p-4" data-testid="train-stats-card">
        <LoadError resource="your progress" variant="inline" data-testid="train-stats-error" />
      </Card>
    );
  }

  return (
    <section
      aria-label="Puzzle pool"
      data-testid="train-stats-card"
      className={cn('grid w-full gap-4', todayScore !== undefined ? 'grid-cols-3' : 'grid-cols-2')}
    >
      {todayScore !== undefined && (
        <StatTile
          // The label says "Points": with "Puzzles per session" on the same
          // screen, a bare "0/9" reads as a puzzle count (193 UAT round 2).
          value={`${todayScore.total}/${todayScore.max}`}
          label="Points today"
          testId="train-stats-today-score"
        />
      )}
      <StatTile
        value={String(data.mastered_count)}
        label="Mastered"
        testId="train-stats-mastered"
        info={{ body: MASTERED_EXPLAINER, ariaLabel: 'What mastered means', testId: 'train-mastered-info' }}
      />
      <StatTile
        value={String(data.parked_count)}
        label="Parked"
        testId="train-stats-parked"
        info={{ body: PARKED_EXPLAINER, ariaLabel: 'What parked means', testId: 'train-parked-info' }}
      />
    </section>
  );
}
