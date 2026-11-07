/**
 * LastWeekPodium — the "Last week:" line below each leaderboard board.
 * Lists every server-sent podium entry (ties included, server order gold to
 * bronze) as a medal icon plus the name, then the viewer's own finish when they
 * have a non-medal row, and wraps on narrow screens. Renders nothing when there
 * is neither: no empty state and no older-week fallback. The viewer's own podium
 * entry (server-set `is_viewer`) is semibold so a medal finisher spots
 * themselves, since the finish is suppressed for medals.
 *
 * Presentational only. Names are other users' self-typed platform usernames,
 * so they only ever render as React text children.
 */
import type { ReactElement } from 'react';
import { MedalIcon } from '@/components/train/medals/MedalIcon';
import { LAST_WEEK_PODIUM_LABEL, MEDAL_LABEL, lastWeekFinishCopy } from '@/lib/trainMedals';
import { cn } from '@/lib/utils';
import type { LeaderboardLastWeek } from '@/types/train';

export function LastWeekPodium({ lastWeek }: { lastWeek: LeaderboardLastWeek | null }): ReactElement | null {
  if (lastWeek === null) return null;
  const { podium, viewer_final_rank: finalRank } = lastWeek;
  if (podium.length === 0 && finalRank === null) return null;
  return (
    <div
      data-testid="train-leaderboard-last-week"
      className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-border pt-3 text-sm"
    >
      <span className="text-muted-foreground">{LAST_WEEK_PODIUM_LABEL}</span>
      {/* `contents`: the entries wrap one by one in the line's own flex flow. */}
      {podium.length > 0 && (
        <span data-testid="train-leaderboard-podium" className="contents">
          {podium.map((entry, index) => (
            // Entries carry no id (the wire format exposes no user id), so index is the key.
            <span
              key={index}
              data-testid={`train-leaderboard-podium-entry-${index}`}
              data-viewer={entry.is_viewer ? 'true' : undefined}
              aria-current={entry.is_viewer ? 'true' : undefined}
              className="inline-flex min-w-0 max-w-full items-center gap-1"
            >
              <MedalIcon kind={entry.medal} className="shrink-0" />
              <span className="sr-only">{MEDAL_LABEL[entry.medal]}</span>
              <span className={cn('min-w-0 truncate', entry.is_viewer && 'font-semibold text-foreground')}>
                {entry.name}
              </span>
            </span>
          ))}
        </span>
      )}
      {finalRank !== null && (
        <span data-testid="train-leaderboard-last-week-finish" className="ml-auto text-muted-foreground">
          {lastWeekFinishCopy(finalRank)}
        </span>
      )}
    </div>
  );
}
