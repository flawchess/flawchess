import { useState, useCallback } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import type { BookmarkResponse } from '@/types/bookmarks';
import type { BookmarkTimeSeries } from '@/types/bookmarks';

interface WinRateChartProps {
  bookmarks: BookmarkResponse[];
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

const MIN_GAMES = 3;

const formatMonth = (m: string) => {
  const [year, month] = m.split('-');
  return new Date(Number(year), Number(month) - 1).toLocaleDateString('en-US', {
    month: 'short',
    year: '2-digit',
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

  // Empty state: no series data or all series have empty data
  const hasData = series.some((s) => s.data.some((p) => p.game_count >= MIN_GAMES));
  if (!hasData) {
    return (
      <div className="text-center text-muted-foreground py-8">
        No game history available for saved positions yet (minimum {MIN_GAMES} games per month).
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

  // Collect all unique months across series (only months with >= MIN_GAMES for at least one bookmark)
  const allMonths = [
    ...new Set(
      series.flatMap((s) =>
        s.data.filter((p) => p.game_count >= MIN_GAMES).map((p) => p.month)
      )
    ),
  ].sort();

  // Build data array with win_rate and game_count per bookmark
  const data = allMonths.map((month) => {
    const point: Record<string, string | number | undefined> = { month };
    for (const s of series) {
      const found = s.data.find((p) => p.month === month);
      // Only include data point if at least MIN_GAMES games
      if (found && found.game_count >= MIN_GAMES) {
        point[`bkm_${s.bookmark_id}`] = found.win_rate;
        point[`bkm_${s.bookmark_id}_games`] = found.game_count;
      }
      // undefined produces a gap in the line
    }
    return point;
  });

  return (
    <ChartContainer config={chartConfig} className="w-full h-72">
      <LineChart data={data}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="month" tickFormatter={formatMonth} />
        <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
        <ChartTooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            return (
              <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                <div className="font-medium">{formatMonth(label as string)}</div>
                {payload
                  .filter((item) => item.value !== undefined)
                  .map((item) => {
                    const cfg = chartConfig[item.dataKey as string];
                    const games = item.payload[`${item.dataKey}_games`];
                    return (
                      <div key={item.dataKey} className="flex items-center gap-1.5">
                        <div
                          className="h-2 w-2 shrink-0 rounded-[2px]"
                          style={{ backgroundColor: item.color }}
                        />
                        <span>
                          {cfg?.label ?? item.dataKey}: {Math.round((item.value as number) * 100)}%
                          <span className="text-muted-foreground ml-1">({games} games)</span>
                        </span>
                      </div>
                    );
                  })}
              </div>
            );
          }}
        />
        <ChartLegend
          content={<ChartLegendContent />}
          onClick={(e) => {
            if (e?.dataKey) handleLegendClick(e.dataKey as string);
          }}
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
              connectNulls={false}
              hide={hiddenKeys.has(key)}
            />
          );
        })}
      </LineChart>
    </ChartContainer>
  );
}
