import type { WDLStats } from '@/types/api';

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
            className="bg-green-600 transition-all"
            style={{ width: `${stats.win_pct}%` }}
            title={`Wins: ${stats.wins} (${stats.win_pct.toFixed(1)}%)`}
          />
        )}
        {stats.draw_pct > 0 && (
          <div
            className="bg-gray-500 transition-all"
            style={{ width: `${stats.draw_pct}%` }}
            title={`Draws: ${stats.draws} (${stats.draw_pct.toFixed(1)}%)`}
          />
        )}
        {stats.loss_pct > 0 && (
          <div
            className="bg-red-600 transition-all"
            style={{ width: `${stats.loss_pct}%` }}
            title={`Losses: ${stats.losses} (${stats.loss_pct.toFixed(1)}%)`}
          />
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-sm">
        <span>
          <span className="font-medium text-green-500">W:</span>{' '}
          {stats.wins} ({stats.win_pct.toFixed(1)}%)
        </span>
        <span>
          <span className="font-medium text-gray-400">D:</span>{' '}
          {stats.draws} ({stats.draw_pct.toFixed(1)}%)
        </span>
        <span>
          <span className="font-medium text-red-500">L:</span>{' '}
          {stats.losses} ({stats.loss_pct.toFixed(1)}%)
        </span>
      </div>
    </div>
  );
}
