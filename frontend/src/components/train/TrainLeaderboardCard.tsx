/**
 * TrainLeaderboardCard — the one "This week" card on the Train landing
 * (Phase 230, D-07, D-08): a Points | Accuracy tab toggle (the choice is
 * remembered in localStorage, D-09), the top 5 plus the viewer's own row
 * (highlighted) and its neighbours with a gap marker between the two, one
 * viewer hint line under the board, a "Not yet qualified (20+ puzzles)" divider
 * before the first unranked (tentative) Accuracy row, and for guests a "Sign up
 * to claim your spot" nudge (D-14). Each row's puzzle count is a Puzzle icon
 * plus the number, and an info popover next to the title explains what each
 * board rewards (quick 261006-75v).
 *
 * Phase 231 adds the "Last week:" podium above each board and a lifetime medal
 * tally in every row's name block.
 *
 * `TrainLeaderboardCard` is the thin container, self-contained apart from
 * `isGuest`: it calls `useTrainLeaderboard()` itself, exactly like
 * `TrainStatsCard` calls `useTrainProgress()`, and owns the countdown, tab
 * state and the Umami tab-switch. `TrainLeaderboardCardView` renders the whole
 * card from props, so the admin "Leaderboard medals demo" shows production
 * markup from fixtures. Names are
 * other users' self-typed platform usernames, so they only ever render as
 * React text children (never HTML, never an href/src; T-230-08).
 */
import { useEffect, useRef, useState } from 'react';
import type { ReactElement } from 'react';
import { Puzzle, Settings as SettingsIcon } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { InfoPopover } from '@/components/ui/info-popover';
import { LoadError } from '@/components/ui/load-error';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { SignupAskActions } from '@/components/train/SignupAskActions';
import { LastWeekPodium } from '@/components/train/medals/LastWeekPodium';
import { MedalTally } from '@/components/train/medals/MedalTally';
import { lastWeekFinishCopy } from '@/lib/trainMedals';
import { useQueryClient } from '@tanstack/react-query';
import { TRAIN_LEADERBOARD_QUERY_KEY, useTrainLeaderboard } from '@/hooks/useTrainLeaderboard';
import { trackFeature } from '@/lib/analytics';
import type { LeaderboardTabId } from '@/lib/analytics';
import {
  ACCURACY_EMPTY_COPY,
  COUNTDOWN_TICK_MS,
  EMPTY_WEEK_COPY,
  GUEST_CLAIM_SPOT_COPY,
  GUEST_ROW_LABEL,
  HIDDEN_FROM_OTHERS_LABEL,
  LEADERBOARD_INFO_ACCURACY_COPY,
  LEADERBOARD_INFO_POINTS_COPY,
  NOT_YET_QUALIFIED_DIVIDER_COPY,
  ROLLOVER_MAX_RETRIES,
  ROLLOVER_RETRY_MS,
  boardValueLabel,
  firstUnrankedRowIndex,
  formatCountdown,
  parseLeaderboardTab,
  puzzleCountLabel,
  readLeaderboardTab,
  remainingSeconds,
  viewerHint,
  writeLeaderboardTab,
} from '@/lib/trainLeaderboard';
import { cn } from '@/lib/utils';
import type { LeaderboardBoardKind, LeaderboardRow, TrainLeaderboardResponse } from '@/types/train';

/** Umami `tab-switch` target per board; a fixed map, so nothing user-derived is ever sent (T-230-09). */
const LEADERBOARD_TAB_TARGET: Record<LeaderboardBoardKind, LeaderboardTabId> = {
  points: 'leaderboard-points',
  accuracy: 'leaderboard-accuracy',
};

const EMPTY_BOARD_COPY: Record<LeaderboardBoardKind, string> = {
  points: EMPTY_WEEK_COPY,
  accuracy: ACCURACY_EMPTY_COPY,
};

export interface TrainLeaderboardCardProps {
  /** From `useUserProfile().data`, threaded by `TrainStartScreen`. */
  isGuest: boolean;
}

interface LeaderboardRowItemProps {
  row: LeaderboardRow;
  kind: LeaderboardBoardKind;
  index: number;
  /** True on the first unranked row: the "Not yet qualified" divider renders before it. */
  qualifyDividerBefore: boolean;
}

function LeaderboardRowItem({
  row,
  kind,
  index,
  qualifyDividerBefore,
}: LeaderboardRowItemProps): ReactElement {
  return (
    <>
      {row.gap_before && (
        <li
          aria-hidden="true"
          data-testid="train-leaderboard-gap"
          className="py-0.5 text-center text-sm leading-none text-muted-foreground"
        >
          …
        </li>
      )}
      {/* Order: the gap says rows were skipped; the divider labels the section the
          next row opens. Not aria-hidden: unlike the gap marker it carries meaning. */}
      {qualifyDividerBefore && (
        <li
          data-testid="train-leaderboard-qualify-divider"
          className="mt-1 border-t border-border px-2 pt-1.5 text-sm text-muted-foreground"
        >
          {NOT_YET_QUALIFIED_DIVIDER_COPY}
        </li>
      )}
      <li
        data-testid={`train-leaderboard-row-${index}`}
        data-viewer={row.is_viewer ? 'true' : undefined}
        aria-current={row.is_viewer ? 'true' : undefined}
        className={cn(
          'flex items-baseline gap-2 px-2 py-1.5 text-sm',
          row.is_viewer && 'rounded-md bg-muted font-semibold',
        )}
      >
        <span className="w-9 shrink-0 tabular-nums">
          {row.rank === null ? '' : `#${row.rank}`}
        </span>
        {/* IN-02 (phase 230 review): only the name truncates. The privacy cue is
            its own nowrap item and wraps below the name when the row is too
            narrow, instead of being the first text cut off. */}
        <span className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-1">
          <span className="min-w-0 max-w-full truncate">
            {row.visibility === 'guest' ? GUEST_ROW_LABEL : row.name}
          </span>
          <MedalTally medals={row.medals} board={kind} testId={`train-leaderboard-row-${index}-medals`} />
          {row.visibility === 'hidden' && (
            <span className="whitespace-nowrap font-normal text-muted-foreground">
              {HIDDEN_FROM_OTHERS_LABEL}
            </span>
          )}
        </span>
        <span className="shrink-0 font-semibold tabular-nums">{boardValueLabel(kind, row.value)}</span>
        {/* The count text carries the row baseline; only the icon is centred (a lone
            SVG in an items-baseline row has no text baseline and gets lifted). */}
        <span
          role="img"
          aria-label={puzzleCountLabel(row.puzzles)}
          data-testid={`train-leaderboard-row-${index}-puzzles`}
          className="inline-flex shrink-0 items-baseline gap-1 text-muted-foreground"
        >
          <Puzzle aria-hidden="true" className="size-3.5 self-center" />
          <span className="tabular-nums">{row.puzzles}</span>
        </span>
      </li>
    </>
  );
}

function LeaderboardRows({
  rows,
  kind,
}: {
  rows: LeaderboardRow[];
  kind: LeaderboardBoardKind;
}): ReactElement {
  const firstUnranked = firstUnrankedRowIndex(rows);
  return (
    <ol data-testid="train-leaderboard-rows" className="flex flex-col">
      {rows.map((row, index) => (
        // Rows carry no id (the wire format exposes no user id), so index is the key.
        <LeaderboardRowItem
          key={index}
          row={row}
          kind={kind}
          index={index}
          qualifyDividerBefore={index === firstUnranked}
        />
      ))}
    </ol>
  );
}

interface LeaderboardTabsProps {
  tab: LeaderboardBoardKind;
  onChange: (next: string) => void;
}

function LeaderboardTabs({ tab, onChange }: LeaderboardTabsProps): ReactElement {
  return (
    <ToggleGroup
      type="single"
      value={tab}
      onValueChange={onChange}
      variant="outline"
      size="sm"
      className="mb-2 w-full"
      aria-label="Leaderboard"
      data-testid="train-leaderboard-tabs"
    >
      <ToggleGroupItem
        value="points"
        data-testid="train-leaderboard-tab-points"
        className="min-h-11 flex-1 text-sm sm:min-h-0"
      >
        Points
      </ToggleGroupItem>
      <ToggleGroupItem
        value="accuracy"
        data-testid="train-leaderboard-tab-accuracy"
        className="min-h-11 flex-1 text-sm sm:min-h-0"
      >
        Accuracy
      </ToggleGroupItem>
    </ToggleGroup>
  );
}

function LeaderboardHint({
  tab,
  data,
}: {
  tab: LeaderboardBoardKind;
  data: TrainLeaderboardResponse;
}): ReactElement | null {
  const hint = viewerHint(tab, data);
  const finalRank = data[tab].last_week?.viewer_final_rank ?? null;
  if (hint === null && finalRank === null) return null;
  return (
    <>
      {hint !== null && (
        <p data-testid={`train-leaderboard-${hint.id}`} className="mt-2 text-sm text-muted-foreground">
          {hint.text}
        </p>
      )}
      {/* D-03: a separate line below this week's hint, never replacing it. */}
      {finalRank !== null && (
        <p
          data-testid="train-leaderboard-last-week-finish"
          className={cn('text-sm text-muted-foreground', hint === null ? 'mt-2' : 'mt-1')}
        >
          {lastWeekFinishCopy(finalRank)}
        </p>
      )}
    </>
  );
}

function LeaderboardBoardView({
  tab,
  data,
}: {
  tab: LeaderboardBoardKind;
  data: TrainLeaderboardResponse;
}): ReactElement {
  const rows = data[tab].rows;
  return (
    <>
      <LastWeekPodium lastWeek={data[tab].last_week} />
      {rows.length === 0 ? (
        <p data-testid="train-leaderboard-empty" className="text-sm text-muted-foreground">
          {EMPTY_BOARD_COPY[tab]}
        </p>
      ) : (
        <LeaderboardRows rows={rows} kind={tab} />
      )}
      <LeaderboardHint tab={tab} data={data} />
    </>
  );
}

function LeaderboardGuestCta(): ReactElement {
  return (
    <div data-testid="train-leaderboard-guest-cta" className="mt-3 flex flex-col gap-2">
      <p className="text-sm">{GUEST_CLAIM_SPOT_COPY}</p>
      <div className="flex flex-wrap gap-2">
        <SignupAskActions source="train-leaderboard" />
      </div>
    </div>
  );
}

/**
 * Seconds to the week's deadline (D-02), or null before data arrives.
 *
 * Derived from the server's `seconds_remaining` minus the time since the
 * fetch (`dataUpdatedAt`). The clock is only read inside the interval
 * callback (react-hooks purity: no clock reads during render); until the
 * first tick `nowMs` is null and the fetch time stands in for "now". At zero
 * the leaderboard query is invalidated once per `week_end`, so the board rolls
 * over at the Monday reset. WR-03 fix: a single shot could land just before the
 * server's reset and leave last week stuck on "ending now", so while a fresh
 * response still carries the old `week_end` at zero, retry after
 * ROLLOVER_RETRY_MS, capped at ROLLOVER_MAX_RETRIES (never an unbounded loop).
 */
function useLeaderboardCountdown(
  data: TrainLeaderboardResponse | undefined,
  dataUpdatedAt: number,
): number | null {
  const queryClient = useQueryClient();
  const [nowMs, setNowMs] = useState<number | null>(null);
  const rollover = useRef<{ weekEnd: string; retries: number } | null>(null);

  useEffect(() => {
    const id = setInterval(() => setNowMs(Date.now()), COUNTDOWN_TICK_MS);
    return () => clearInterval(id);
  }, []);

  const remaining =
    data === undefined
      ? null
      : remainingSeconds(data.seconds_remaining, dataUpdatedAt, nowMs ?? dataUpdatedAt);
  const weekEnd = data?.week_end ?? null;

  useEffect(() => {
    if (remaining !== 0 || weekEnd === null) return;
    const state = rollover.current;
    if (state === null || state.weekEnd !== weekEnd) {
      rollover.current = { weekEnd, retries: 0 };
      void queryClient.invalidateQueries({ queryKey: TRAIN_LEADERBOARD_QUERY_KEY });
      return;
    }
    if (state.retries >= ROLLOVER_MAX_RETRIES) return;
    // Re-armed by each fresh response (dataUpdatedAt) that still shows the old week.
    const id = setTimeout(() => {
      state.retries += 1;
      void queryClient.invalidateQueries({ queryKey: TRAIN_LEADERBOARD_QUERY_KEY });
    }, ROLLOVER_RETRY_MS);
    return () => clearTimeout(id);
  }, [remaining, weekEnd, dataUpdatedAt, queryClient]);

  return remaining;
}

export interface TrainLeaderboardCardViewProps {
  data: TrainLeaderboardResponse | undefined;
  isPending: boolean;
  isError: boolean;
  /** Seconds to the deadline, or null before data arrives (header countdown). */
  remaining: number | null;
  tab: LeaderboardBoardKind;
  onTabChange: (value: string) => void;
  isGuest: boolean;
}

/**
 * The whole card rendered from props: no fetching, no query client, no
 * analytics beyond the header InfoPopover's own popover-open (Phase 231;
 * trackFeature drops events on /admin). The admin "Leaderboard medals demo" renders this with
 * fixture data so it shows production markup.
 */
export function TrainLeaderboardCardView({
  data,
  isPending,
  isError,
  remaining,
  tab,
  onTabChange,
  isGuest,
}: TrainLeaderboardCardViewProps): ReactElement {
  return (
    <Card as="section" className="w-full p-4" data-testid="train-leaderboard-card">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <h2 className="text-base font-semibold">This week</h2>
          <InfoPopover ariaLabel="About the weekly leaderboards" testId="train-leaderboard-info" side="bottom">
            <div className="space-y-1">
              <p>{LEADERBOARD_INFO_POINTS_COPY}</p>
              <p>{LEADERBOARD_INFO_ACCURACY_COPY}</p>
              {/* Guests never appear on the boards, so the opt-out hint is for signed-in users only. */}
              {!isGuest && (
                <p data-testid="train-leaderboard-info-opt-out">
                  You can hide yourself from the leaderboards in the{' '}
                  <SettingsIcon className="inline h-3.5 w-3.5 align-text-bottom" aria-label="Settings" />{' '}
                  settings.
                </p>
              )}
            </div>
          </InfoPopover>
        </div>
        {remaining !== null && (
          <span data-testid="train-leaderboard-countdown" className="text-sm text-muted-foreground">
            {formatCountdown(remaining)}
          </span>
        )}
      </div>
      {isPending && (
        <div
          data-testid="train-leaderboard-loading"
          className="h-24 w-full animate-pulse rounded-md bg-muted"
          aria-hidden="true"
        />
      )}
      {!isPending && (isError || data === undefined) && (
        <LoadError resource="the leaderboard" variant="inline" data-testid="train-leaderboard-error" />
      )}
      {data !== undefined && (
        <>
          <LeaderboardTabs tab={tab} onChange={onTabChange} />
          <LeaderboardBoardView tab={tab} data={data} />
          {isGuest && <LeaderboardGuestCta />}
        </>
      )}
    </Card>
  );
}

export function TrainLeaderboardCard({ isGuest }: TrainLeaderboardCardProps): ReactElement {
  const { data, isPending, isError, dataUpdatedAt } = useTrainLeaderboard();
  const remaining = useLeaderboardCountdown(data, dataUpdatedAt);
  const [tab, setTab] = useState<LeaderboardBoardKind>(readLeaderboardTab);

  const handleTabChange = (value: string): void => {
    // Radix single-select emits '' when the active item is re-tapped: keep the
    // current tab and fire nothing (no write, no Umami event).
    if (value === '') return;
    const next = parseLeaderboardTab(value);
    if (next === tab) return;
    setTab(next);
    writeLeaderboardTab(next);
    trackFeature('tab-switch', { target: LEADERBOARD_TAB_TARGET[next] });
  };

  return (
    <TrainLeaderboardCardView
      data={data}
      isPending={isPending}
      isError={isError}
      remaining={remaining}
      tab={tab}
      onTabChange={handleTabChange}
      isGuest={isGuest}
    />
  );
}
