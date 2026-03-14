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

const formatTs = (ts: number) =>
  new Date(ts).toLocaleDateString('en-US', { month: 'short', year: '2-digit' });

/** Compute equally-spaced first-of-month timestamps across the data range. */
function computeXTicks(minTs: number, maxTs: number): number[] {
  const spanMs = maxTs - minTs;
  const spanMonths = spanMs / (1000 * 60 * 60 * 24 * 30.44);

  let intervalMonths: number;
  if (spanMonths <= 6) {
    intervalMonths = 1;
  } else if (spanMonths <= 18) {
    intervalMonths = 2;
  } else if (spanMonths <= 36) {
    intervalMonths = 3;
  } else if (spanMonths <= 72) {
    intervalMonths = 6;
  } else {
    intervalMonths = 12;
  }

  const minDate = new Date(minTs);
  // Start at the first month boundary at or before minTs
  let cur = new Date(Date.UTC(minDate.getUTCFullYear(), minDate.getUTCMonth(), 1));

  const ticks: number[] = [];
  const maxDate = new Date(maxTs);
  const endTs = Date.UTC(maxDate.getUTCFullYear(), maxDate.getUTCMonth() + 1, 1);

  while (cur.getTime() <= endTs) {
    ticks.push(cur.getTime());
    cur = new Date(Date.UTC(cur.getUTCFullYear(), cur.getUTCMonth() + intervalMonths, 1));
  }

  return ticks;
}

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

    // Build a flat array where each entry is { date, dateTs, [tc]: rating }
    // One row per data point (each game is its own data point)
    const rows: Record<string, string | number>[] = data.map((point) => ({
      date: point.date,
      dateTs: new Date(point.date).getTime(),
      [point.time_control_bucket]: point.rating,
    }));

    return rows;
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

  const { xTicks, xDomain } = useMemo(() => {
    if (chartData.length === 0) {
      return { xTicks: undefined, xDomain: undefined };
    }
    const timestamps = chartData.map((row) => row.dateTs as number);
    const minTs = Math.min(...timestamps);
    const maxTs = Math.max(...timestamps);
    return {
      xTicks: computeXTicks(minTs, maxTs),
      xDomain: [minTs, maxTs] as [number, number],
    };
  }, [chartData]);

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
          dataKey="dateTs"
          type="number"
          scale="time"
          domain={xDomain}
          ticks={xTicks}
          tickFormatter={formatTs}
          tick={{ fontSize: 12 }}
          allowDuplicatedCategory={false}
        />
        <YAxis domain={yDomain} ticks={yTicks} />
        <ChartTooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            // label is dateTs (number); format it to a readable date
            const dateLabel = new Date(label as number).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            });
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
