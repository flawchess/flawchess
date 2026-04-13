import { useState, useCallback, useMemo } from 'react';
import { InfoPopover } from '@/components/ui/info-popover';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import { GAUGE_SUCCESS } from '@/lib/theme';
import { createDateTickFormatter, formatDateWithYear } from '@/lib/utils';
import { MATERIAL_ADVANTAGE_POINTS, PERSISTENCE_MOVES } from '@/components/charts/EndgamePerformanceSection';
import type { ConvRecovTimelineResponse } from '@/types/endgames';

interface EndgameConvRecovTimelineChartProps {
  data: ConvRecovTimelineResponse;
}

const chartConfig = {
  conversion: { label: 'Conversion', color: GAUGE_SUCCESS },
  // Same blue as EndgameConvRecovChart — distinct from WDL_DRAW, represents "saved" outcome
  recovery: { label: 'Recovery', color: 'oklch(0.55 0.18 260)' },
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

  // Merge conversion and recovery series by date into a single data array.
  // Each unique date gets conversion_rate, recovery_rate, and game counts.
  const { mergedData, sortedDates } = useMemo(() => {
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

    const merged = [...dateMap.values()].sort((a, b) =>
      (a.date as string).localeCompare(b.date as string),
    );
    return { mergedData: merged, sortedDates: merged.map((d) => d.date as string) };
  }, [data.conversion, data.recovery]);

  const formatDateTick = useMemo(() => createDateTickFormatter(sortedDates), [sortedDates]);

  // Empty state: both series empty — don't render
  if (mergedData.length === 0) {
    return null;
  }

  return (
    <div>
      <div className="mb-3">
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Conversion & Recovery Over Time
            <InfoPopover ariaLabel="Conversion recovery chart info" testId="conv-recov-timeline-info" side="top">
              <div className="space-y-2">
                <p>
                  <strong>Conversion</strong>: rolling percentage of the last {data.window} endgame sequences
                  with a material advantage of at least {MATERIAL_ADVANTAGE_POINTS} point (persisted for
                  at least {PERSISTENCE_MOVES} moves) where you went on to win the game.
                </p>
                <p>
                  <strong>Recovery</strong>: rolling percentage of the last {data.window} endgame sequences
                  with a material deficit of at least {MATERIAL_ADVANTAGE_POINTS} point (persisted for
                  at least {PERSISTENCE_MOVES} moves) where you went on to draw or win the game.
                </p>
              </div>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Rolling {data.window}-sequence trend — is your endgame play improving?
        </p>
      </div>
      <ChartContainer config={chartConfig} className="w-full h-72" data-testid="conv-recov-timeline-chart">
        <LineChart data={mergedData}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="date" tickFormatter={formatDateTick} />
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
                              (past {gameCount} sequences)
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
