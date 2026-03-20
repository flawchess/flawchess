import { useState, useCallback } from 'react';
import { InfoPopover } from '@/components/ui/info-popover';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';
import type { BookmarkTimeSeries } from '@/types/position_bookmarks';

interface WinRateChartProps {
  bookmarks: PositionBookmarkResponse[];
  series: BookmarkTimeSeries[];
}

// Distinct categorical palette — easy to distinguish across lines
const CHART_COLORS = [
  'oklch(0.65 0.20 145)',   // green
  'oklch(0.60 0.22 30)',    // red-orange
  'oklch(0.65 0.20 260)',   // blue
  'oklch(0.70 0.18 80)',    // amber/gold
  'oklch(0.60 0.22 310)',   // purple
  'oklch(0.65 0.15 190)',   // teal
  'oklch(0.55 0.22 350)',   // magenta
  'oklch(0.70 0.15 110)',   // lime
];

const formatDate = (d: string) => {
  const [year, month, day] = d.split('-');
  return new Date(Number(year), Number(month) - 1, Number(day)).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
};

const formatDateWithYear = (d: string) => {
  const [year, month, day] = d.split('-');
  return new Date(Number(year), Number(month) - 1, Number(day)).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

export function WinRateChart({ bookmarks, series }: WinRateChartProps) {
  const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());

  const handleLegendClick = useCallback((dataKey: string) => {
    setHiddenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(dataKey)) {
        next.delete(dataKey);
      } else {
        next.add(dataKey);
      }
      return next;
    });
  }, []);

  // Empty state: no series data
  const hasData = series.some((s) => s.data.length > 0);
  if (!hasData) {
    return (
      <div className="text-center text-muted-foreground py-8">
        No game history available for saved positions yet.
      </div>
    );
  }

  // Build chartConfig
  const chartConfig = Object.fromEntries(
    bookmarks.map((b, i) => [
      `bkm_${b.id}`,
      { label: b.label, color: CHART_COLORS[i % CHART_COLORS.length] },
    ]),
  );

  // Collect all unique dates across series, sorted chronologically
  const allDates = [
    ...new Set(
      series.flatMap((s) => s.data.map((p) => p.date))
    ),
  ].sort();

  // Build data array with win_rate, game_count and window_size per bookmark
  const data = allDates.map((date) => {
    const point: Record<string, string | number | undefined> = { date };
    for (const s of series) {
      const found = s.data.find((p) => p.date === date);
      if (found) {
        point[`bkm_${s.bookmark_id}`] = found.win_rate;
        point[`bkm_${s.bookmark_id}_game_count`] = found.game_count;
        point[`bkm_${s.bookmark_id}_window_size`] = found.window_size;
      }
      // undefined produces a gap in the line
    }
    return point;
  });

  return (
    <div>
      <h2 className="text-lg font-medium mb-3">
        <span className="inline-flex items-center gap-1">
          Win Rate Over Time
          <InfoPopover ariaLabel="Win rate chart info" testId="win-rate-chart-info" side="top">
            Shows your win rate for each saved position over time. Each point is the win rate over your last 30 games through that position. This helps you track and compare your success rate for each opening.
          </InfoPopover>
        </span>
      </h2>
    <ChartContainer config={chartConfig} className="w-full h-72">
      <LineChart data={data}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="date" tickFormatter={formatDate} />
        <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
        <ChartTooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            return (
              <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                <div className="font-medium">{formatDateWithYear(label as string)}</div>
                {payload
                  .filter((item) => item.value !== undefined)
                  .map((item) => {
                    const cfg = chartConfig[item.dataKey as string];
                    const gameCount = item.payload[`${item.dataKey}_game_count`] as number;
                    const windowSize = item.payload[`${item.dataKey}_window_size`] as number;
                    return (
                      <div key={item.dataKey} className="flex items-center gap-1.5">
                        <div
                          className="h-2 w-2 shrink-0 rounded-[2px]"
                          style={{ backgroundColor: item.color }}
                        />
                        <span>
                          {cfg?.label ?? item.dataKey}: {Math.round((item.value as number) * 100)}%
                          <span className="text-muted-foreground ml-1">({gameCount}/{windowSize} games)</span>
                        </span>
                      </div>
                    );
                  })}
              </div>
            );
          }}
        />
        <ChartLegend
          content={<ChartLegendContent hiddenKeys={hiddenKeys} onClickItem={handleLegendClick} />}
        />
        {bookmarks.map((b) => {
          const key = `bkm_${b.id}`;
          return (
            <Line
              key={b.id}
              type="monotone"
              dataKey={key}
              stroke={`var(--color-${key})`}
              strokeWidth={2}
              dot={false}
              connectNulls={true}
              hide={hiddenKeys.has(key)}
            />
          );
        })}
      </LineChart>
    </ChartContainer>
    </div>
  );
}
