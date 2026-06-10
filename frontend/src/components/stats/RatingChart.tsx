import { useState, useMemo, useCallback, useEffect } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { ChartTooltipBox } from '@/components/ui/chart-tooltip-box';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import { createDateTickFormatter, formatDateWithYear } from '@/lib/utils';
import { inactivityGapReferenceLines } from '@/components/charts/InactivityGapReferenceLines';
import type { RatingDataPoint } from '@/types/stats';
import type { TimeControl } from '@/types/api';

interface RatingChartProps {
  data: RatingDataPoint[];
  platform: string;
  /**
   * Which time-control series to render. null (default) = all four series.
   * When the user disables a TC in the Stats-tab TC filter, that series is
   * excluded from the chart. The legend click hide/show is layered on top.
   */
  enabledTimeControls?: TimeControl[] | null;
}

const TIME_CONTROLS: TimeControl[] = ['bullet', 'blitz', 'rapid', 'classical'];

const MOBILE_BREAKPOINT_PX = 768;

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined'
      && window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}

const chartConfig = {
  bullet: { label: 'Bullet', color: 'oklch(0.60 0.22 30)' },
  blitz: { label: 'Blitz', color: 'oklch(0.65 0.20 260)' },
  rapid: { label: 'Rapid', color: 'oklch(0.70 0.18 80)' },
  classical: { label: 'Classic', color: 'oklch(0.60 0.22 310)' },
};

export function RatingChart({ data, platform, enabledTimeControls }: RatingChartProps) {
  const isMobile = useIsMobile();
  const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());

  // TCs that actually have at least one data point. Omit empty series so a
  // never-played time control (e.g. bullet) shows no line and no legend entry.
  const tcsWithData = useMemo(
    () => TIME_CONTROLS.filter((tc) => data.some((pt) => pt.time_control_bucket === tc)),
    [data],
  );

  // Series to render: intersection of the filter set (all four when null) and the
  // TCs that have data. Drives both the <Line> series and the recharts legend
  // payload (legend items derive from rendered <Line> children).
  const visibleTcs: TimeControl[] = useMemo(
    () => (enabledTimeControls ?? TIME_CONTROLS).filter((tc) => tcsWithData.includes(tc)),
    [enabledTimeControls, tcsWithData],
  );

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

  // Group by date, keep last rating per (date, time_control_bucket).
  // Data is sorted by played_at (backend guarantees chronological order).
  const chartData = useMemo(() => {
    if (data.length === 0) return [];
    const map = new Map<string, Record<string, string | number>>();
    for (const pt of data) {
      const row = map.get(pt.date) ?? { date: pt.date };
      row[pt.time_control_bucket] = pt.rating;
      map.set(pt.date, row);
    }
    return Array.from(map.values());
  }, [data]);

  const allDates = useMemo(() => chartData.map((d) => d.date as string), [chartData]);
  const formatDateTick = useMemo(() => createDateTickFormatter(allDates), [allDates]);

  // computeInactivityGaps requires ascending-sorted dates. allDates derives from a
  // Map keyed by date string (insertion order = backend chronological order), which
  // is generally already sorted. Sort a copy defensively to guarantee the invariant
  // without disturbing allDates (used by the tick formatter for ordinal x-axis).
  const sortedGapDates = useMemo(() => [...allDates].sort(), [allDates]);

  const { yDomain, yTicks } = useMemo(() => {
    // visibleTcs already excludes empty series and filter-disabled TCs.
    // hiddenKeys applies the legend click hide/show on top so hidden series
    // don't inflate the Y-axis scale.
    const effectiveTcs = visibleTcs.filter((tc) => !hiddenKeys.has(tc));
    if (effectiveTcs.length === 0 || chartData.length === 0) {
      return { yDomain: ['auto', 'auto'] as [string, string], yTicks: undefined };
    }

    let min = Infinity;
    let max = -Infinity;
    for (const row of chartData) {
      for (const tc of effectiveTcs) {
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
    // start with a known numeric value to avoid noUncheckedIndexedAccess widening to number | undefined
    let step: number = 10;
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
  }, [chartData, hiddenKeys, visibleTcs]);

  // Narrow the chart config to the visible series so the legend and the generated
  // --color-* CSS vars never reference an omitted/empty series.
  const legendConfig = useMemo(
    () => Object.fromEntries(visibleTcs.map((tc) => [tc, chartConfig[tc as keyof typeof chartConfig]])),
    [visibleTcs],
  );

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
    <ChartContainer config={legendConfig} className="w-full h-72" data-testid={testId}>
      <LineChart
        data={chartData}
        margin={{ top: 5, right: 10, left: isMobile ? 0 : 10, bottom: 10 }}
      >
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDateTick}
          tick={{ fontSize: 12 }}
        />
        <YAxis domain={yDomain} ticks={yTicks} interval={0} tick={{ fontSize: 12 }} width={44} />
        <ChartTooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            return (
              <ChartTooltipBox>
                <div className="font-medium">{formatDateWithYear(label as string)}</div>
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
              </ChartTooltipBox>
            );
          }}
        />
        <ChartLegend
          content={<ChartLegendContent hiddenKeys={hiddenKeys} onClickItem={handleLegendClick} />}
        />
        {/* Inactivity-gap annotations via shared helper: Palmtree glyph + label per
            >90-day gap. Placed BEFORE the TIME_CONTROLS Line series so annotations
            sit behind the data in SVG z-order. sortedGapDates is a defensively
            sorted copy of allDates so computeInactivityGaps' ascending-sort
            requirement is guaranteed even if the backend order shifts. No yAxisId
            (single default axis). Covers both Chess.com and Lichess instances
            (same component, platform prop only affects testid/labels). */}
        {inactivityGapReferenceLines({ dates: sortedGapDates })}
        {visibleTcs.map((tc) => (
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
