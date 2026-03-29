import { useState, useMemo, useCallback } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import type { RatingDataPoint } from '@/types/stats';

interface RatingChartProps {
  data: RatingDataPoint[];
  platform: string;
}

type Granularity = 'day' | 'week' | 'month';

const DAYS_ONE_YEAR = 365;
const DAYS_THREE_YEARS = 3 * 365;

const TIME_CONTROLS = ['bullet', 'blitz', 'rapid', 'classical'];

const chartConfig = {
  bullet: { label: 'Bullet', color: 'oklch(0.60 0.22 30)' },
  blitz: { label: 'Blitz', color: 'oklch(0.65 0.20 260)' },
  rapid: { label: 'Rapid', color: 'oklch(0.70 0.18 80)' },
  classical: { label: 'Classic', color: 'oklch(0.60 0.22 310)' },
};

function determineGranularity(data: RatingDataPoint[]): Granularity {
  if (data.length < 2) return 'day';
  const first = new Date(data[0].date).getTime();
  const last = new Date(data[data.length - 1].date).getTime();
  const spanDays = (last - first) / (1000 * 60 * 60 * 24);
  if (spanDays < DAYS_ONE_YEAR) return 'day';
  if (spanDays < DAYS_THREE_YEARS) return 'week';
  return 'month';
}

function getBucketKey(dateStr: string, granularity: Granularity): string {
  if (granularity === 'day') return dateStr;
  if (granularity === 'month') return dateStr.slice(0, 7);
  // 'week': compute ISO week start (Monday)
  const d = new Date(dateStr);
  const day = d.getUTCDay(); // 0=Sun, 1=Mon, ..., 6=Sat
  const diff = day === 0 ? -6 : 1 - day; // adjust to Monday
  d.setUTCDate(d.getUTCDate() + diff);
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(d.getUTCDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function formatBucketLabel(key: string, granularity: Granularity): string {
  if (granularity === 'month') {
    const [year, month] = key.split('-');
    return new Date(Number(year), Number(month) - 1).toLocaleDateString('en-US', {
      month: 'short',
      year: '2-digit',
    });
  }
  // 'day' and 'week': show "Mar 15"
  const [year, month, day] = key.split('-');
  return new Date(Number(year), Number(month) - 1, Number(day)).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
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

  const { chartData, granularity } = useMemo(() => {
    if (data.length === 0) return { chartData: [], granularity: 'day' as Granularity };
    const gran = determineGranularity(data);
    // data is sorted by played_at (backend guarantees chronological order)
    // Group by bucket, keep last rating per (bucket, time_control_bucket)
    const map = new Map<string, Record<string, string | number>>();
    for (const pt of data) {
      const bucket = getBucketKey(pt.date, gran);
      const row = map.get(bucket) ?? { bucket };
      row[pt.time_control_bucket] = pt.rating; // last game in bucket wins
      map.set(bucket, row);
    }
    return { chartData: Array.from(map.values()), granularity: gran };
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
          dataKey="bucket"
          tickFormatter={(key: string) => formatBucketLabel(key, granularity)}
          tick={{ fontSize: 12 }}
        />
        <YAxis domain={yDomain} ticks={yTicks} />
        <ChartTooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            const dateLabel = formatBucketLabel(label as string, granularity);
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
