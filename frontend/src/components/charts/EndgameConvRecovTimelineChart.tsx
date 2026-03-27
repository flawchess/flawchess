import { useState, useCallback } from 'react';
import { InfoPopover } from '@/components/ui/info-popover';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import { CHART_CONVERSION, CHART_RECOVERY } from '@/lib/theme';
import type { ConvRecovTimelineResponse } from '@/types/endgames';

interface EndgameConvRecovTimelineChartProps {
  data: ConvRecovTimelineResponse;
}

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

const chartConfig = {
  conversion: { label: 'Conversion', color: CHART_CONVERSION },
  recovery: { label: 'Recovery', color: CHART_RECOVERY },
};

export function EndgameConvRecovTimelineChart({ data }: EndgameConvRecovTimelineChartProps) {
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

  // Empty state: both series empty — don't render
  if (data.conversion.length === 0 && data.recovery.length === 0) {
    return null;
  }

  // Merge conversion and recovery series by date into a single data array.
  // Each unique date gets conversion_rate, recovery_rate, and game counts.
  const dateMap = new Map<string, Record<string, string | number | undefined>>();

  for (const point of data.conversion) {
    if (!dateMap.has(point.date)) {
      dateMap.set(point.date, { date: point.date });
    }
    const entry = dateMap.get(point.date)!;
    entry.conversion = point.rate;
    entry.conversion_game_count = point.game_count;
    entry.conversion_window_size = point.window_size;
  }

  for (const point of data.recovery) {
    if (!dateMap.has(point.date)) {
      dateMap.set(point.date, { date: point.date });
    }
    const entry = dateMap.get(point.date)!;
    entry.recovery = point.rate;
    entry.recovery_game_count = point.game_count;
    entry.recovery_window_size = point.window_size;
  }

  // Sort by date chronologically
  const mergedData = [...dateMap.values()].sort((a, b) =>
    (a.date as string).localeCompare(b.date as string),
  );

  return (
    <div>
      <h3 className="text-base font-semibold mb-3">
        <span className="inline-flex items-center gap-1">
          Conversion & Recovery Over Time
          <InfoPopover ariaLabel="Conversion recovery chart info" testId="conv-recov-timeline-info" side="top">
            <strong>Conversion rate</strong>: your win rate in the last {data.window} games where you
            entered the endgame with a significant material advantage ({'>'}=3 pawns).{' '}
            <strong>Recovery rate</strong>: your save rate (wins + draws) in the last {data.window} games
            where you entered the endgame at a significant material disadvantage ({'>'}=3 pawns down).
          </InfoPopover>
        </span>
      </h3>
      <ChartContainer config={chartConfig} className="w-full h-72" data-testid="conv-recov-timeline-chart">
        <LineChart data={mergedData}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="date" tickFormatter={formatDate} />
          <YAxis domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
          <ChartTooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                  <div className="font-medium">{formatDateWithYear(label as string)}</div>
                  {payload
                    .filter((item) => item.value !== undefined)
                    .map((item) => {
                      const cfg = chartConfig[item.dataKey as keyof typeof chartConfig];
                      const gameCount = item.payload[`${item.dataKey}_game_count`] as number;
                      return (
                        <div key={item.dataKey} className="flex items-center gap-1.5">
                          <div
                            className="h-2 w-2 shrink-0 rounded-[2px]"
                            style={{ backgroundColor: item.color }}
                          />
                          <span>
                            {cfg?.label ?? item.dataKey}: {Math.round((item.value as number) * 100)}%
                            <span className="text-muted-foreground ml-1">
                              (past {gameCount} games)
                            </span>
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
          <Line
            type="monotone"
            dataKey="conversion"
            stroke={`var(--color-conversion)`}
            strokeWidth={2}
            dot={false}
            connectNulls={true}
            hide={hiddenKeys.has('conversion')}
          />
          <Line
            type="monotone"
            dataKey="recovery"
            stroke={`var(--color-recovery)`}
            strokeWidth={2}
            dot={false}
            connectNulls={true}
            hide={hiddenKeys.has('recovery')}
          />
        </LineChart>
      </ChartContainer>
    </div>
  );
}
