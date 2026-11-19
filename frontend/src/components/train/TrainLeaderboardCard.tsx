/**
 * TrainLeaderboardCard — the one "This week" card on the Train Leaderboard tab
 * under a Puzzles | Blunder check mode switch (D-14, underline tabs above the card)
 * with that mode's two boards (Points | Accuracy, or Points | Score %) as a segmented
 * control in the card header. Both choices are remembered in
 * localStorage only (D-24). Shows the top 5 plus the viewer's own row (highlighted) and its
 * neighbours with a gap marker between the two (and a trailing one when lower
 * ranks are cut), a hint line under the board for a viewer not on it yet, a "Not yet qualified
 * (20+ puzzles)" divider before the first unranked (tentative) Accuracy row
 * ("18+ sequences" on Score %), and for guests a "Sign up to claim your spot"
 * nudge (guests see the Blunder check standings like the puzzle ones, D-25). Each
 * row's count is an icon plus the number (puzzles, or sequences on Blunder check),
 * and an info popover next to the title explains what each board rewards.
 *
 * Each board has the "Last week:" line below it (the podium plus the viewer's
 * own finish) and a lifetime medal tally in every row's name block.
 *
 * `TrainLeaderboardCard` is the thin container, self-contained apart from
 * `isGuest`: it calls `useTrainLeaderboard()` itself, exactly like
 * `TrainStreakCard` calls `useTrainProgress()`, and owns the countdown, tab
 * state and the Umami tab-switch. `TrainLeaderboardCardView` renders the whole
 * card from props, so the admin "Leaderboard medals demo" shows production
 * markup from fixtures. Names are other users' self-typed platform usernames,
 * so they only ever render as React text children (never HTML, never an
 * href/src).
 */
import { useEffect, useRef, useState } from 'react';
import type { ReactElement } from 'react';
import { Puzzle, Settings as SettingsIcon, ShieldCheck } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { InfoPopover } from '@/components/ui/info-popover';
import { LoadError } from '@/components/ui/load-error';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { TRAIN_SEGMENT_CLASS, TRAIN_UNDERLINE_TAB_CLASS } from '@/components/train/buttonStyles';
import { SignupAskActions } from '@/components/train/SignupAskActions';
import { LastWeekPodium } from '@/components/train/medals/LastWeekPodium';
import { MedalTally } from '@/components/train/medals/MedalTally';
import { useQueryClient } from '@tanstack/react-query';
import { TRAIN_LEADERBOARD_QUERY_KEY, useTrainLeaderboard } from '@/hooks/useTrainLeaderboard';
import { trackFeature } from '@/lib/analytics';
import type { LeaderboardTabId } from '@/lib/analytics';
import {
  BOARD_TAB_LABEL,
  COUNTDOWN_TICK_MS,
  EMPTY_BOARD_COPY,
  GUEST_CLAIM_SPOT_COPY,
  GUEST_ROW_LABEL,
  HIDDEN_FROM_OTHERS_LABEL,
  LEADERBOARD_INFO_ACCURACY_COPY,
  LEADERBOARD_INFO_BLUNDER_CHECK_POINTS_COPY,
  LEADERBOARD_INFO_BLUNDER_CHECK_SCORE_COPY,
  LEADERBOARD_INFO_MEDALS_COPY,
  LEADERBOARD_INFO_POINTS_COPY,
  MODE_LABEL,
  ROLLOVER_MAX_RETRIES,
  ROLLOVER_RETRY_MS,
  boardCountLabel,
  boardKindFor,
  boardValueLabel,
  firstUnrankedRowIndex,
  formatCountdown,
  parseLeaderboardMode,
  parseLeaderboardTab,
  qualifyDividerCopy,
  readLeaderboardMode,
  readLeaderboardTab,
  remainingSeconds,
  viewerHint,
  writeLeaderboardMode,
  writeLeaderboardTab,
} from '@/lib/trainLeaderboard';
import type { LeaderboardMode, LeaderboardTab } from '@/lib/trainLeaderboard';
import { cn } from '@/lib/utils';
import type { LeaderboardBoardKind, LeaderboardRow, TrainLeaderboardResponse } from '@/types/train';

/** Umami `tab-switch` target per board; a fixed map, so nothing user-derived is ever sent. */
const LEADERBOARD_TAB_TARGET: Record<LeaderboardBoardKind, LeaderboardTabId> = {
  points: 'leaderboard-points',
  accuracy: 'leaderboard-accuracy',
  blunder_check_points: 'leaderboard-blunder-check-points',
  blunder_check_score: 'leaderboard-blunder-check-score',
};

/** Umami `tab-switch` target per mode. */
const LEADERBOARD_MODE_TARGET: Record<LeaderboardMode, LeaderboardTabId> = {
  puzzles: 'leaderboard-mode-puzzles',
  blunder_check: 'leaderboard-mode-blunder-check',
};

/** Slug used in the testid of each board tab; the mode switch items carry their full testid. */
const BOARD_TESTID_SLUG: Record<LeaderboardBoardKind, string> = {
  points: 'points',
  accuracy: 'accuracy',
  blunder_check_points: 'blunder-check-points',
  blunder_check_score: 'blunder-check-score',
};
const MODE_TESTID: Record<LeaderboardMode, string> = {
  puzzles: 'train-leaderboard-mode-puzzles',
  blunder_check: 'train-leaderboard-mode-blunder-check',
};

/** Row count icon: a puzzle piece for puzzles, the Blunder check tab's shield for sequences. */
const BOARD_COUNT_ICON: Record<LeaderboardBoardKind, LucideIcon> = {
  points: Puzzle,
  accuracy: Puzzle,
  blunder_check_points: ShieldCheck,
  blunder_check_score: ShieldCheck,
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

/** The '…' between non-adjacent ranks, and after the last row when ranks below it are cut. */
function LeaderboardGap({ testId }: { testId: string }): ReactElement {
  return (
    <li
      aria-hidden="true"
      data-testid={testId}
      className="py-0.5 text-center text-sm leading-none text-muted-foreground"
    >
      …
    </li>
  );
}

function LeaderboardRowItem({
  row,
  kind,
  index,
  qualifyDividerBefore,
}: LeaderboardRowItemProps): ReactElement {
  const CountIcon = BOARD_COUNT_ICON[kind];
  return (
    <>
      {row.gap_before && <LeaderboardGap testId="train-leaderboard-gap" />}
      {/* Order: the gap says rows were skipped; the divider labels the section the
          next row opens. Not aria-hidden: unlike the gap marker it carries meaning. */}
      {qualifyDividerBefore && (
        <li
          data-testid="train-leaderboard-qualify-divider"
          className="mt-1 border-t border-border px-2 pt-1.5 text-sm text-muted-foreground"
        >
          {qualifyDividerCopy(kind)}
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
        {/* Only the name truncates. The privacy cue is
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
          aria-label={boardCountLabel(kind, row.puzzles)}
          data-testid={`train-leaderboard-row-${index}-puzzles`}
          // Bug fix: the width followed the digit count, so the values to its left
          // lost their right alignment between rows (424 pts vs 178 pts). Fixed width,
          // icon left and count right, keeps both columns straight.
          className="inline-flex w-12 shrink-0 items-baseline justify-between text-muted-foreground"
        >
          <CountIcon aria-hidden="true" className="size-3.5 self-center" />
          <span className="tabular-nums">{row.puzzles}</span>
        </span>
      </li>
      {/* Without it a top-ranked viewer sees only top 5 plus neighbours and reads that as everyone. */}
      {row.gap_after && <LeaderboardGap testId="train-leaderboard-gap-after" />}
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

interface LeaderboardModeSwitchProps {
  mode: LeaderboardMode;
  onChange: (next: string) => void;
}

/** Puzzles | Blunder check as underline tabs: which game's boards the card shows (D-14). */
function LeaderboardModeSwitch({ mode, onChange }: LeaderboardModeSwitchProps): ReactElement {
  return (
    <ToggleGroup
      type="single"
      value={mode}
      onValueChange={onChange}
      size="sm"
      className="mb-4 w-full rounded-none! border-b border-border"
      aria-label="Leaderboard mode"
      data-testid="train-leaderboard-mode"
    >
      {(Object.keys(MODE_LABEL) as LeaderboardMode[]).map((value) => (
        <ToggleGroupItem
          key={value}
          value={value}
          data-testid={MODE_TESTID[value]}
          className={TRAIN_UNDERLINE_TAB_CLASS}
        >
          {MODE_LABEL[value]}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}

const LEADERBOARD_TABS: readonly LeaderboardTab[] = ['points', 'accuracy'];

interface LeaderboardTabsProps {
  mode: LeaderboardMode;
  tab: LeaderboardTab;
  onChange: (next: string) => void;
}

/** The mode's two boards as a segmented control in the card header: Points | Accuracy, or Points | Score %. */
function LeaderboardTabs({ mode, tab, onChange }: LeaderboardTabsProps): ReactElement {
  return (
    <ToggleGroup
      type="single"
      value={tab}
      onValueChange={onChange}
      variant="outline"
      size="sm"
      className="ml-auto font-normal"
      aria-label="Leaderboard"
      data-testid="train-leaderboard-tabs"
    >
      {LEADERBOARD_TABS.map((value) => {
        const kind = boardKindFor(mode, value);
        return (
          <ToggleGroupItem
            key={value}
            value={value}
            data-testid={`train-leaderboard-tab-${BOARD_TESTID_SLUG[kind]}`}
            className={TRAIN_SEGMENT_CLASS}
          >
            {BOARD_TAB_LABEL[kind]}
          </ToggleGroupItem>
        );
      })}
    </ToggleGroup>
  );
}

function LeaderboardHint({
  kind,
  data,
}: {
  kind: LeaderboardBoardKind;
  data: TrainLeaderboardResponse;
}): ReactElement | null {
  const hint = viewerHint(kind, data);
  if (hint === null) return null;
  return (
    <p data-testid={`train-leaderboard-${hint.id}`} className="mt-2 text-sm text-muted-foreground">
      {hint.text}
    </p>
  );
}

function LeaderboardBoardView({
  kind,
  data,
  isGuest,
}: {
  kind: LeaderboardBoardKind;
  data: TrainLeaderboardResponse;
  isGuest: boolean;
}): ReactElement {
  const rows = data[kind].rows;
  return (
    <>
      {rows.length === 0 ? (
        <p data-testid="train-leaderboard-empty" className="text-sm text-muted-foreground">
          {EMPTY_BOARD_COPY[kind]}
        </p>
      ) : (
        <LeaderboardRows rows={rows} kind={kind} />
      )}
      <LeaderboardHint kind={kind} data={data} />
      {/* The sign-up nudge is about this week's board, so it sits above last week's line. */}
      {isGuest && <LeaderboardGuestCta />}
      <LastWeekPodium lastWeek={data[kind].last_week} />
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
 * Seconds to the week's deadline, or null before data arrives.
 *
 * Derived from the server's `seconds_remaining` minus the time since the
 * fetch (`dataUpdatedAt`). The clock is only read inside the interval
 * callback (react-hooks purity: no clock reads during render); until the
 * first tick `nowMs` is null and the fetch time stands in for "now". At zero
 * the leaderboard query is invalidated once per `week_end`, so the board rolls
 * over at the Monday reset. A single shot could land just before the
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
  secondsRemaining: number | null;
  mode: LeaderboardMode;
  tab: LeaderboardTab;
  onModeChange: (value: string) => void;
  onTabChange: (value: string) => void;
  isGuest: boolean;
}

/**
 * The whole card rendered from props: no fetching, no query client, no
 * analytics beyond the header InfoPopover's own popover-open (trackFeature
 * drops events on /admin). The admin "Leaderboard medals demo" renders this
 * with fixture data so it shows production markup.
 */
export function TrainLeaderboardCardView({
  data,
  isPending,
  isError,
  secondsRemaining,
  mode,
  tab,
  onModeChange,
  onTabChange,
  isGuest,
}: TrainLeaderboardCardViewProps): ReactElement {
  // The selected board is known before the data arrives, so the switches show during
  // loading too. Without data after a failed load there is no board to switch.
  const showTabs = isPending || data !== undefined;

  return (
    <>
      {showTabs && <LeaderboardModeSwitch mode={mode} onChange={onModeChange} />}
      <Card as="section" className="w-full" data-testid="train-leaderboard-card">
        <CardHeader as="h2">
          {/* Title and countdown stack on mobile so the board switch fits beside them. */}
          <span className="flex min-w-0 flex-col gap-x-2 sm:flex-row sm:items-center">
            <span className="flex items-center gap-2">
              This week
              <InfoPopover ariaLabel="About the weekly leaderboards" testId="train-leaderboard-info" side="bottom">
                <div className="space-y-1">
                  {mode === 'puzzles' ? (
                    <>
                      <p>{LEADERBOARD_INFO_POINTS_COPY}</p>
                      <p>{LEADERBOARD_INFO_ACCURACY_COPY}</p>
                    </>
                  ) : (
                    <>
                      <p>{LEADERBOARD_INFO_BLUNDER_CHECK_POINTS_COPY}</p>
                      <p>{LEADERBOARD_INFO_BLUNDER_CHECK_SCORE_COPY}</p>
                    </>
                  )}
                  <p>{LEADERBOARD_INFO_MEDALS_COPY}</p>
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
            </span>
            {secondsRemaining !== null && (
              <span data-testid="train-leaderboard-countdown" className="text-sm font-normal text-muted-foreground">
                {formatCountdown(secondsRemaining)}
              </span>
            )}
          </span>
          {showTabs && <LeaderboardTabs mode={mode} tab={tab} onChange={onTabChange} />}
        </CardHeader>
        <CardBody>
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
            <LeaderboardBoardView kind={boardKindFor(mode, tab)} data={data} isGuest={isGuest} />
          )}
        </CardBody>
      </Card>
    </>
  );
}

export function TrainLeaderboardCard({ isGuest }: TrainLeaderboardCardProps): ReactElement {
  const { data, isPending, isError, dataUpdatedAt } = useTrainLeaderboard();
  const remaining = useLeaderboardCountdown(data, dataUpdatedAt);
  const [mode, setMode] = useState<LeaderboardMode>(readLeaderboardMode);
  const [tab, setTab] = useState<LeaderboardTab>(readLeaderboardTab);

  const handleModeChange = (value: string): void => {
    // Radix single-select emits '' when the active item is re-tapped: keep the
    // current mode and fire nothing (no write, no Umami event).
    if (value === '') return;
    const next = parseLeaderboardMode(value);
    if (next === mode) return;
    setMode(next);
    writeLeaderboardMode(next);
    trackFeature('tab-switch', { target: LEADERBOARD_MODE_TARGET[next] });
  };

  const handleTabChange = (value: string): void => {
    // Same re-tap rule as the mode switch: '' keeps the tab and fires nothing.
    if (value === '') return;
    const next = parseLeaderboardTab(value);
    if (next === tab) return;
    setTab(next);
    writeLeaderboardTab(next);
    trackFeature('tab-switch', { target: LEADERBOARD_TAB_TARGET[boardKindFor(mode, next)] });
  };

  return (
    <TrainLeaderboardCardView
      data={data}
      isPending={isPending}
      isError={isError}
      secondsRemaining={remaining}
      mode={mode}
      tab={tab}
      onModeChange={handleModeChange}
      onTabChange={handleTabChange}
      isGuest={isGuest}
    />
  );
}
