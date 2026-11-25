/**
 * TrainSubnav — the URL-routed tab bar of the /train layout (Today, Leaderboard and Archive; blunder check has no tab, it runs from the Today card).
 *
 * Nav-only: `Tabs` wraps just the `TabsList`, and the page renders its panels
 * as plain divs rather than `TabsContent`. Two reasons. One responsive list
 * instead of Library's duplicated desktop/mobile pair, because a duplicated
 * pair would mount each panel twice and so double the session and medal
 * hosts. And `TabsContent` applies `flex-1 text-sm` to everything inside it.
 * The trade-off is a dangling `aria-controls` from the Radix triggers, which
 * is harmless.
 *
 * No `tab-switch` Umami event: URL-routed tabs are covered by the pageview
 * (frontend/CLAUDE.md). Non-sticky on mobile, like Library.
 */

import { useEffect, useRef } from 'react';
import type { ReactElement } from 'react';
import { useNavigate } from 'react-router';
import { Archive, CalendarCheck, Trophy } from 'lucide-react';
import { RouteDot } from '@/components/feature-route/RouteDot';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TRAIN_TAB_PATHS } from '@/lib/trainRoute';
import type { TrainTab } from '@/lib/trainRoute';

const TAB_ICON_CLASS = 'mr-1.5 h-4 w-4';

function isTrainTab(value: string): value is TrainTab {
  return Object.hasOwn(TRAIN_TAB_PATHS, value);
}

export function TrainSubnav({
  active,
  showTodayRouteDot,
}: {
  active: TrainTab;
  /** D-03: the Train step's route dot while the user is on another Train tab,
   * decided by the page so this component stays hook-free. */
  showTodayRouteDot: boolean;
}): ReactElement {
  const navigate = useNavigate();

  // Radix fires `onValueChange` on mousedown and again on the trigger's focus,
  // before the router has re-rendered `active`. Without this guard the same
  // path was pushed twice and Back took two presses. The ref tracks the tab
  // last navigated to, re-synced whenever the URL moves (Back, Forward, links).
  const requestedTab = useRef<TrainTab>(active);
  useEffect(() => {
    requestedTab.current = active;
  }, [active]);

  function handleValueChange(value: string): void {
    if (!isTrainTab(value) || value === requestedTab.current) return;
    requestedTab.current = value;
    navigate(TRAIN_TAB_PATHS[value]);
    window.scrollTo({ top: 0 });
  }

  return (
    <Tabs value={active} onValueChange={handleValueChange}>
      <TabsList variant="brand" className="w-full max-lg:!h-10 max-lg:!p-0" data-testid="train-tabs">
        <TabsTrigger value="today" className="flex-1" data-testid="tab-train-today">
          <CalendarCheck className={TAB_ICON_CLASS} />
          Today
          {showTodayRouteDot && <RouteDot testid="train-today-notification-dot" variant="corner" />}
        </TabsTrigger>
        <TabsTrigger value="leaderboard" className="flex-1" data-testid="tab-train-leaderboard">
          <Trophy className={TAB_ICON_CLASS} />
          Leaderboard
        </TabsTrigger>
        <TabsTrigger value="archive" className="flex-1" data-testid="tab-train-archive">
          <Archive className={TAB_ICON_CLASS} />
          Archive
        </TabsTrigger>
      </TabsList>
    </Tabs>
  );
}
