import type { WDLStats } from '@/types/api';

// Shared WDL colors — must match WDLBarChart.tsx
export const WDL_WIN = 'oklch(0.55 0.12 145)';
export const WDL_DRAW = 'oklch(0.65 0.01 260)';
export const WDL_LOSS = 'oklch(0.55 0.13 25)';

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
            style={{ width: `${stats.win_pct}%`, backgroundColor: WDL_WIN }}
            title={`Wins: ${stats.wins} (${stats.win_pct.toFixed(1)}%)`}
          />
        )}
        {stats.draw_pct > 0 && (
          <div
            className="transition-all"
            style={{ width: `${stats.draw_pct}%`, backgroundColor: WDL_DRAW }}
            title={`Draws: ${stats.draws} (${stats.draw_pct.toFixed(1)}%)`}
          />
        )}
        {stats.loss_pct > 0 && (
          <div
            className="transition-all"
            style={{ width: `${stats.loss_pct}%`, backgroundColor: WDL_LOSS }}
            title={`Losses: ${stats.losses} (${stats.loss_pct.toFixed(1)}%)`}
          />
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-sm">
        <span>
          <span className="font-medium" style={{ color: WDL_WIN }}>W:</span>{' '}
          {stats.wins} ({stats.win_pct.toFixed(1)}%)
        </span>
        <span>
          <span className="font-medium" style={{ color: WDL_DRAW }}>D:</span>{' '}
          {stats.draws} ({stats.draw_pct.toFixed(1)}%)
        </span>
        <span>
          <span className="font-medium" style={{ color: WDL_LOSS }}>L:</span>{' '}
          {stats.losses} ({stats.loss_pct.toFixed(1)}%)
        </span>
      </div>
    </div>
  );
}
