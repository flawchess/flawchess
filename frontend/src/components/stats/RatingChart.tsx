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

const formatDate = (dateStr: string) => {
  const [year, month] = dateStr.split('-');
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

    // Build a flat array where each entry is { date, [tc]: rating }
    // One row per data point (each game is its own data point)
    const rows: Record<string, string | number>[] = data.map((point) => ({
      date: point.date,
      [point.time_control_bucket]: point.rating,
    }));

    return rows;
  }, [data]);

  const yDomain = useMemo(() => {
    const visibleTcs = TIME_CONTROLS.filter((tc) => !hiddenKeys.has(tc));
    if (visibleTcs.length === 0 || chartData.length === 0) return ['auto', 'auto'] as [string, string];

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

    if (!isFinite(min) || !isFinite(max)) return ['auto', 'auto'] as [string, string];

    return [Math.floor(min / 100) * 100, Math.ceil(max / 100) * 100] as [number, number];
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
          dataKey="date"
          tickFormatter={formatDate}
          interval="preserveStartEnd"
        />
        <YAxis domain={yDomain} />
        <ChartTooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            return (
              <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                <div className="font-medium">{label as string}</div>
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
          content={<ChartLegendContent />}
          onClick={(e) => {
            if (e?.dataKey) handleLegendClick(e.dataKey as string);
          }}
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
