import type { WDLStats } from '@/types/api';

// Shared WDL colors — must match WDLBarChart.tsx
// Richer base colors — the glass overlay softens them visually
export const WDL_WIN = 'oklch(0.50 0.14 145)';
export const WDL_DRAW = 'oklch(0.60 0.02 260)';
export const WDL_LOSS = 'oklch(0.50 0.15 25)';

// Glass-effect overlay: white highlight fading to transparent
const GLASS_OVERLAY = 'linear-gradient(to bottom, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.05) 60%, rgba(0,0,0,0.05) 100%)';

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
        <span>
          <span className="font-medium" style={{ color: WDL_WIN }}>W:</span>{' '}
          {stats.wins} ({stats.win_pct.toFixed(0)}%)
        </span>
        <span>
          <span className="font-medium" style={{ color: WDL_DRAW }}>D:</span>{' '}
          {stats.draws} ({stats.draw_pct.toFixed(0)}%)
        </span>
        <span>
          <span className="font-medium" style={{ color: WDL_LOSS }}>L:</span>{' '}
          {stats.losses} ({stats.loss_pct.toFixed(0)}%)
        </span>
      </div>
    </div>
  );
}
