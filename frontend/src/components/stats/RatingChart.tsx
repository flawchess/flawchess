import { useState, useMemo, useCallback } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import type { RatingDataPoint } from '@/types/stats';

interface RatingChartProps {
  data: RatingDataPoint[];
  platform: string;
}

const TIME_CONTROLS = ['bullet', 'blitz', 'rapid', 'classical'];

const chartConfig = {
  bullet: { label: 'Bullet', color: 'oklch(0.60 0.22 30)' },
  blitz: { label: 'Blitz', color: 'oklch(0.65 0.20 260)' },
  rapid: { label: 'Rapid', color: 'oklch(0.70 0.18 80)' },
  classical: { label: 'Classical', color: 'oklch(0.60 0.22 310)' },
};

const formatMonth = (m: string) => {
  const [year, month] = m.split('-');
  return new Date(Number(year), Number(month) - 1).toLocaleDateString('en-US', {
    month: 'short',
    year: '2-digit',
  });
};

export function RatingChart({ data, platform }: RatingChartProps) {
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

  const testId = `rating-chart-${platform.toLowerCase().replace(/[.\s]/g, '-')}`;

  const chartData = useMemo(() => {
    if (data.length === 0) return [];
    // data is sorted by played_at (backend guarantees chronological order)
    // Group by month, keep last rating per (month, time_control_bucket)
    const map = new Map<string, Record<string, string | number>>();
    for (const pt of data) {
      const month = pt.date.slice(0, 7); // "YYYY-MM"
      const row = map.get(month) ?? { month };
      row[pt.time_control_bucket] = pt.rating; // last game in month wins
      map.set(month, row);
    }
    return Array.from(map.values());
    // Already sorted because source data is sorted by played_at
  }, [data]);

  const { yDomain, yTicks } = useMemo(() => {
    const visibleTcs = TIME_CONTROLS.filter((tc) => !hiddenKeys.has(tc));
    if (visibleTcs.length === 0 || chartData.length === 0) {
      return { yDomain: ['auto', 'auto'] as [string, string], yTicks: undefined };
    }

    let min = Infinity;
    let max = -Infinity;
    for (const row of chartData) {
      for (const tc of visibleTcs) {
        const val = row[tc];
        if (typeof val === 'number') {
          if (val < min) min = val;
          if (val > max) max = val;
        }
      }
    }

    if (!isFinite(min) || !isFinite(max)) {
      return { yDomain: ['auto', 'auto'] as [string, string], yTicks: undefined };
    }

    // If all ratings are identical, use a small range so ticks are meaningful
    if (min === max) {
      min = min - 50;
      max = max + 50;
    }

    const range = max - min;

    // Pick the largest step where range/step >= 4 (aim for 4-8 ticks)
    const STEP_CANDIDATES = [10, 20, 50, 100, 200, 500];
    let step = STEP_CANDIDATES[0];
    for (const candidate of STEP_CANDIDATES) {
      if (range / candidate >= 4) {
        step = candidate;
      }
    }

    const domainMin = Math.floor(min / step) * step;
    const domainMax = Math.ceil(max / step) * step;

    const ticks: number[] = [];
    for (let t = domainMin; t <= domainMax; t += step) {
      ticks.push(t);
    }

    return {
      yDomain: [domainMin, domainMax] as [number, number],
      yTicks: ticks,
    };
  }, [chartData, hiddenKeys]);

  if (data.length === 0) {
    return (
      <div
        data-testid={testId}
        className="text-center text-muted-foreground py-8"
      >
        No {platform} games imported.
      </div>
    );
  }

  return (
    <ChartContainer config={chartConfig} className="w-full h-72" data-testid={testId}>
      <LineChart data={chartData}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="month"
          tickFormatter={formatMonth}
          tick={{ fontSize: 12 }}
        />
        <YAxis domain={yDomain} ticks={yTicks} />
        <ChartTooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            const dateLabel = formatMonth(label as string);
            return (
              <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                <div className="font-medium">{dateLabel}</div>
                {payload
                  .filter((item) => item.value !== undefined)
                  .map((item) => {
                    const tc = item.dataKey as string;
                    const cfg = chartConfig[tc as keyof typeof chartConfig];
                    return (
                      <div key={tc} className="flex items-center gap-1.5">
                        <div
                          className="h-2 w-2 shrink-0 rounded-[2px]"
                          style={{ backgroundColor: item.color }}
                        />
                        <span>
                          {cfg?.label ?? tc}: {item.value as number}
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
        {TIME_CONTROLS.map((tc) => (
          <Line
            key={tc}
            type="monotone"
            dataKey={tc}
            stroke={`var(--color-${tc})`}
            strokeWidth={2}
            dot={false}
            connectNulls={true}
            hide={hiddenKeys.has(tc)}
          />
        ))}
      </LineChart>
    </ChartContainer>
  );
}
