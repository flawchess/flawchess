/**
 * LastWeekPodium — the "Last week:" line at the top of each leaderboard tab
 * (Phase 231, D-07, D-08, D-09). Lists every server-sent podium entry (ties
 * included, server order gold to bronze) as a medal icon plus the name, and
 * wraps on narrow screens. Renders nothing when there is no podium: no empty
 * state and no older-week fallback.
 *
 * Presentational only. Names are other users' self-typed platform usernames,
 * so they only ever render as React text children (T-230-08, T-231-14).
 */
import type { ReactElement } from 'react';
import { MedalIcon } from '@/components/train/medals/MedalIcon';
import { LAST_WEEK_PODIUM_LABEL, MEDAL_LABEL } from '@/lib/trainMedals';
import type { LeaderboardLastWeek } from '@/types/train';

export function LastWeekPodium({ lastWeek }: { lastWeek: LeaderboardLastWeek | null }): ReactElement | null {
  if (lastWeek === null || lastWeek.podium.length === 0) return null;
  return (
    <p data-testid="train-leaderboard-podium" className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
      <span className="text-muted-foreground">{LAST_WEEK_PODIUM_LABEL}</span>
      {lastWeek.podium.map((entry, index) => (
        // Entries carry no id (the wire format exposes no user id), so index is the key.
        <span
          key={index}
          data-testid={`train-leaderboard-podium-entry-${index}`}
          className="inline-flex min-w-0 max-w-full items-center gap-1"
        >
          <MedalIcon kind={entry.medal} className="shrink-0" />
          <span className="sr-only">{MEDAL_LABEL[entry.medal]}</span>
          <span className="min-w-0 truncate">{entry.name}</span>
        </span>
      ))}
    </p>
  );
}
