import { useState, useCallback } from 'react';
import { ChartContainer, ChartTooltip, ChartTooltipContent, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import type { BookmarkResponse } from '@/types/bookmarks';
import type { BookmarkTimeSeries } from '@/types/bookmarks';

interface WinRateChartProps {
  bookmarks: BookmarkResponse[];
  series: BookmarkTimeSeries[];
}

const CHART_COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
];

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
  const hasData = series.some((s) => s.data.length > 0);
  if (!hasData) {
    return (
      <div className="text-center text-muted-foreground py-8">
        No game history available for saved positions yet.
      </div>
    );
  }

  // Build chartConfig: one entry per bookmark using chart CSS variables (cycling 1-5)
  const chartConfig = Object.fromEntries(
    bookmarks.map((b, i) => [
      `bkm_${b.id}`,
      { label: b.label, color: CHART_COLORS[i % CHART_COLORS.length] },
    ]),
  );

  // Collect all unique months across all series, sorted chronologically
  const allMonths = [
    ...new Set(series.flatMap((s) => s.data.map((p) => p.month))),
  ].sort();

  // Build data array: one object per month, with win_rate per bookmark (undefined = gap)
  const data = allMonths.map((month) => {
    const point: Record<string, string | number | undefined> = { month };
    for (const s of series) {
      const found = s.data.find((p) => p.month === month);
      point[`bkm_${s.bookmark_id}`] = found?.win_rate; // undefined produces a gap
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
          content={
            <ChartTooltipContent
              labelFormatter={(label) => formatMonth(label as string)}
              formatter={(value, name) => {
                const cfg = chartConfig[name as string];
                return (
                  <span>
                    {cfg?.label ?? name}: {Math.round((value as number) * 100)}%
                  </span>
                );
              }}
            />
          }
        />
        <ChartLegend
          content={
            <ChartLegendContent />
          }
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
