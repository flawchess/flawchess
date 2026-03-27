import type { WDLStats } from '@/types/api';
import { WDL_WIN, WDL_DRAW, WDL_LOSS, GLASS_OVERLAY } from '@/lib/theme';

interface WDLBarProps {
  stats: WDLStats;
}

export function WDLBar({ stats }: WDLBarProps) {
  if (stats.total === 0) {
    return (
      <div className="space-y-2">
        <div className="h-6 w-full rounded bg-muted" />
        <p className="text-center text-sm text-muted-foreground">No games matched</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Stacked bar */}
      <div className="flex h-6 w-full overflow-hidden rounded">
        {stats.win_pct > 0 && (
          <div
            className="transition-all"
            style={{ width: `${stats.win_pct}%`, backgroundColor: WDL_WIN, backgroundImage: GLASS_OVERLAY }}
          />
        )}
        {stats.draw_pct > 0 && (
          <div
            className="transition-all"
            style={{ width: `${stats.draw_pct}%`, backgroundColor: WDL_DRAW, backgroundImage: GLASS_OVERLAY }}
          />
        )}
        {stats.loss_pct > 0 && (
          <div
            className="transition-all"
            style={{ width: `${stats.loss_pct}%`, backgroundColor: WDL_LOSS, backgroundImage: GLASS_OVERLAY }}
          />
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-sm">
        <span style={{ color: WDL_WIN }}>W: {stats.wins} ({stats.win_pct.toFixed(0)}%)</span>
        <span style={{ color: WDL_DRAW }}>D: {stats.draws} ({stats.draw_pct.toFixed(0)}%)</span>
        <span style={{ color: WDL_LOSS }}>L: {stats.losses} ({stats.loss_pct.toFixed(0)}%)</span>
      </div>
    </div>
  );
}
