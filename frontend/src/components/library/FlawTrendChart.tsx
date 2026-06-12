import { useCallback, useMemo, useState } from 'react';
import { Bar, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from 'recharts';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { ChartTooltipBox } from '@/components/ui/chart-tooltip-box';
import { inactivityGapReferenceLines } from '@/components/charts/InactivityGapReferenceLines';
import {
  ENDGAME_VOLUME_BAR_COLOR,
  SEV_BLUNDER,
  SEV_INACCURACY,
  SEV_MISTAKE,
} from '@/lib/theme';
import { createDateTickFormatter, formatDateWithYear } from '@/lib/utils';
import type { FlawTrendPoint } from '@/types/library';

// ─── Series definitions ────────────────────────────────────────────────────────

type SeriesKey = 'blunder_rate' | 'mistake_rate' | 'inaccuracy_rate';

interface SeriesConfig {
  key: SeriesKey;
  label: string;
  color: string;
}

const SERIES: SeriesConfig[] = [
  { key: 'blunder_rate', label: 'Blunders', color: SEV_BLUNDER },
  { key: 'mistake_rate', label: 'Mistakes', color: SEV_MISTAKE },
  { key: 'inaccuracy_rate', label: 'Inacc.', color: SEV_INACCURACY },
];

// ─── Props ───────────────────────────────────────────────────────────────────

interface FlawTrendChartProps {
  /** ISO-week per-100-moves trend datapoints from FlawStatsResponse.trend. */
  trend: FlawTrendPoint[];
  /** Rolling window size (games per window). Shown in the caption below the axis. */
  windowSize: number;
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Zone 2: flaws / 100 moves rolling trend — three severity lines (blunders, mistakes,
 * inaccuracies) over a trailing windowSize-game window, bucketed by ISO week.
 *
 * Mirrors the Endgame ELO Timeline chart style: span-aware date ticks
 * (createDateTickFormatter), per-week volume BARS on a hidden right axis, inactivity-gap
 * markers (Palmtree) on long inactive stretches, and a toggleable legend below the chart.
 * Rates are macro per-100-moves from the games-table oracle columns.
 *
 * Renders a text fallback when fewer than 2 datapoints are available.
 */
export function FlawTrendChart({ trend, windowSize }: FlawTrendChartProps) {
  const [hiddenKeys, setHiddenKeys] = useState<Set<SeriesKey>>(() => new Set());

  const handleLegendClick = useCallback((key: SeriesKey) => {
    setHiddenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const allDates = useMemo(() => trend.map((p) => p.date), [trend]);
  const formatDateTick = useMemo(() => createDateTickFormatter(allDates), [allDates]);
  const barMax = Math.max(1, ...trend.map((p) => p.per_week_games));

  return (
    <Card
      className="mt-4"
      data-testid="flaw-trend-chart"
      aria-label="Flaws per 100 moves trend chart"
    >
      <CardHeader size="compact">Flaws Timeline</CardHeader>
      <CardBody>
        {/* Empty / insufficient-data state */}
        {trend.length < 2 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            Not enough games to show a trend
          </p>
        ) : (
          <>
            <ChartContainer
              config={{}}
              className="w-full h-48"
              data-testid="flaw-trend-composed-chart"
            >
              <ComposedChart data={trend} margin={{ top: 5, right: 10, left: 0, bottom: 10 }}>
                <CartesianGrid vertical={false} yAxisId="rate" stroke="var(--color-border)" />
                <XAxis dataKey="date" tickFormatter={formatDateTick} tick={{ fontSize: 12 }} />
                <YAxis
                  yAxisId="rate"
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={32}
                />
                {/* Hidden right axis for volume bars: domain [0, barMax*5] pins the tallest
                    bar to the bottom 20% of the canvas (mirrors the Endgame ELO Timeline). */}
                <YAxis yAxisId="bars" orientation="right" hide domain={[0, barMax * 5]} />
                <ChartTooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    const point = payload[0]?.payload as FlawTrendPoint | undefined;
                    if (!point) return null;
                    return (
                      <ChartTooltipBox className="text-sm">
                        <div className="font-bold text-muted-foreground">
                          {formatDateWithYear(label as string)}
                        </div>
                        {SERIES.filter((s) => !hiddenKeys.has(s.key)).map((s) => (
                          <div
                            key={s.key}
                            className="flex items-center gap-1.5"
                            style={{ color: s.color }}
                          >
                            <span
                              className="h-2 w-2 shrink-0 rounded-[2px]"
                              style={{ backgroundColor: s.color }}
                            />
                            {s.label}: {point[s.key].toFixed(2)} / 100
                          </div>
                        ))}
                        <div className="text-muted-foreground text-sm">
                          {point.per_week_games} games this week · {point.games_in_window} in window
                        </div>
                      </ChartTooltipBox>
                    );
                  }}
                />
                {/* Inactivity markers BEFORE the data series so they sit behind in z-order. */}
                {inactivityGapReferenceLines({ dates: allDates, yAxisId: 'rate' })}
                <Bar
                  yAxisId="bars"
                  dataKey="per_week_games"
                  fill={ENDGAME_VOLUME_BAR_COLOR}
                  legendType="none"
                  isAnimationActive={false}
                  data-testid="flaw-trend-volume-bars"
                />
                {SERIES.map((s) => (
                  <Line
                    key={s.key}
                    yAxisId="rate"
                    type="monotone"
                    dataKey={s.key}
                    stroke={s.color}
                    strokeWidth={2}
                    dot={{ r: 2.5, fill: s.color, strokeWidth: 0 }}
                    activeDot={{ r: 4, fill: s.color, strokeWidth: 0 }}
                    isAnimationActive={false}
                    hide={hiddenKeys.has(s.key)}
                  />
                ))}
              </ComposedChart>
            </ChartContainer>

            {/* Rolling-window caption, directly below the x-axis label. */}
            <p className="text-sm text-muted-foreground text-center mt-1">
              last {windowSize} games · rolling window
            </p>

            {/* Toggleable legend below the chart (click to show/hide a series). */}
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm pt-2 justify-center">
              {SERIES.map((s) => {
                const isHidden = hiddenKeys.has(s.key);
                return (
                  <button
                    key={s.key}
                    type="button"
                    onClick={() => handleLegendClick(s.key)}
                    className={`inline-flex min-w-0 items-center gap-1.5 cursor-pointer ${isHidden ? 'opacity-50 line-through' : ''}`}
                    data-testid={`flaw-trend-legend-${s.key}`}
                    aria-pressed={!isHidden}
                  >
                    <span
                      className="h-2 w-2 shrink-0 rounded-[2px]"
                      style={{ backgroundColor: s.color }}
                    />
                    <span className="truncate">{s.label}</span>
                  </button>
                );
              })}
            </div>
          </>
        )}
      </CardBody>
    </Card>
  );
}
