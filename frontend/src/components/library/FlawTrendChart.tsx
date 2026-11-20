import { useCallback, useMemo, useState } from 'react';
import { Area, Bar, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from 'recharts';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { ChartTooltipBox } from '@/components/ui/chart-tooltip-box';
import { InfoPopover } from '@/components/ui/info-popover';
import { inactivityGapReferenceLines } from '@/components/charts/InactivityGapReferenceLines';
import {
  FACEPALM_BAND_FILL,
  FACEPALM_BAND_SWATCH,
  OTHER_BLUNDER_BAND_FILL,
  VOLUME_BAR_COLOR,
  SEV_BLUNDER,
  SEV_INACCURACY,
  SEV_MISTAKE,
} from '@/lib/theme';
import { FACEPALM_TIMELINE_INFO } from '@/lib/facepalm';
import { createDateTickFormatter, formatDateWithYear } from '@/lib/utils';
import { onOff, trackFeature } from '@/lib/analytics';
import type { FlawTrendPoint } from '@/types/library';
import { toChartPoint } from './flawTrendBands';

// ─── Series definitions ────────────────────────────────────────────────────────

type SeriesKey = 'blunder_rate' | 'mistake_rate' | 'inaccuracy_rate';

/** Legend entries: the three severity lines plus the facepalm split of the Blunders area. */
type LegendKey = SeriesKey | 'facepalm';

interface SeriesConfig {
  key: SeriesKey;
  label: string;
  color: string;
}

const BLUNDER_SERIES: SeriesConfig = { key: 'blunder_rate', label: 'Blunders', color: SEV_BLUNDER };
const OTHER_SERIES: SeriesConfig[] = [
  { key: 'mistake_rate', label: 'Mistakes', color: SEV_MISTAKE },
  { key: 'inaccuracy_rate', label: 'Inacc.', color: SEV_INACCURACY },
];
const SERIES: SeriesConfig[] = [BLUNDER_SERIES, ...OTHER_SERIES];

/** Legend in severity order: Facepalm (the split of the Blunders area) leads, then the lines. */
const LEGEND: { key: LegendKey; label: string; color: string }[] = [
  { key: 'facepalm', label: 'Facepalm', color: FACEPALM_BAND_SWATCH },
  BLUNDER_SERIES,
  ...OTHER_SERIES,
];

/**
 * Mistakes and inaccuracies are hidden by default: they sit above the blunder rate and push the
 * blunder / facepalm signal down the y-axis. The legend toggles them back on.
 */
const DEFAULT_HIDDEN_KEYS: readonly LegendKey[] = ['mistake_rate', 'inaccuracy_rate'];

const PCT_SCALE = 100;
const BLUNDER_STACK_ID = 'blunders';

// ─── Props ───────────────────────────────────────────────────────────────────

interface FlawTrendChartProps {
  /** ISO-week per-100-moves trend datapoints from FlawStatsResponse.trend. */
  trend: FlawTrendPoint[];
  /** Rolling window size (games per window). Shown in the caption below the axis. */
  windowSize: number;
}

// ─── Tooltip ─────────────────────────────────────────────────────────────────

function TooltipRow({ color, swatch, children }: { color: string; swatch?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-1.5" style={{ color }}>
      <span className="h-2 w-2 shrink-0 rounded-[2px]" style={{ backgroundColor: swatch ?? color }} />
      {children}
    </div>
  );
}

/** The facepalm line under Blunders: rate per 100 moves plus the share of scored blunders. */
function facepalmTooltipText(point: FlawTrendPoint): string | null {
  if (point.facepalm_rate === null) return null;
  const share =
    point.facepalm_share === null
      ? ''
      : ` (${Math.round(point.facepalm_share * PCT_SCALE)}% of blunders)`;
  return `Facepalm: ${point.facepalm_rate.toFixed(2)} / 100${share}`;
}

export function TrendTooltipBody({
  point,
  label,
  hiddenKeys,
}: {
  point: FlawTrendPoint;
  label: string;
  hiddenKeys: Set<LegendKey>;
}) {
  const facepalmText = hiddenKeys.has('facepalm') ? null : facepalmTooltipText(point);
  return (
    <ChartTooltipBox className="text-sm">
      <div className="font-bold text-muted-foreground">{formatDateWithYear(label)}</div>
      {SERIES.filter((s) => !hiddenKeys.has(s.key)).map((s) => (
        <div key={s.key}>
          <TooltipRow color={s.color}>
            {s.label}: {point[s.key].toFixed(2)} / 100
          </TooltipRow>
          {s.key === 'blunder_rate' && facepalmText !== null && (
            <TooltipRow color={SEV_BLUNDER} swatch={FACEPALM_BAND_SWATCH}>
              {facepalmText}
            </TooltipRow>
          )}
        </div>
      ))}
      <div className="text-muted-foreground text-sm">
        {point.per_week_games} games this week · {point.games_in_window} in window
      </div>
    </ChartTooltipBox>
  );
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
 * 257 D-17: the Blunders series also fills its area with two stacked transparent bands,
 * facepalm blunders at the bottom (darker red) and the other blunders above, so the top of the
 * stack is the Blunders line. The Facepalm legend entry toggles the split; hiding Blunders
 * hides both bands.
 *
 * Renders a text fallback when fewer than 2 datapoints are available.
 */
export function FlawTrendChart({ trend, windowSize }: FlawTrendChartProps) {
  const [hiddenKeys, setHiddenKeys] = useState<Set<LegendKey>>(
    () => new Set<LegendKey>(DEFAULT_HIDDEN_KEYS),
  );

  const handleLegendClick = useCallback((key: LegendKey) => {
    setHiddenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const chartData = useMemo(() => trend.map(toChartPoint), [trend]);
  const allDates = useMemo(() => trend.map((p) => p.date), [trend]);
  const formatDateTick = useMemo(() => createDateTickFormatter(allDates), [allDates]);
  const barMax = Math.max(1, ...trend.map((p) => p.per_week_games));
  const bandsHidden = hiddenKeys.has('blunder_rate') || hiddenKeys.has('facepalm');

  return (
    <Card
      className="mt-4"
      data-testid="flaw-trend-chart"
      aria-label="Flaws per 100 moves trend chart"
    >
      <CardHeader size="compact" className="flex items-center gap-2">
        Flaws Timeline
        <InfoPopover ariaLabel="About facepalm blunders" testId="flaw-trend-facepalm-info">
          <p>{FACEPALM_TIMELINE_INFO}</p>
        </InfoPopover>
      </CardHeader>
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
              <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 10 }}>
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
                      <TrendTooltipBody point={point} label={label as string} hiddenKeys={hiddenKeys} />
                    );
                  }}
                />
                {/* Inactivity markers BEFORE the data series so they sit behind in z-order. */}
                {inactivityGapReferenceLines({ dates: allDates, yAxisId: 'rate' })}
                <Bar
                  yAxisId="bars"
                  dataKey="per_week_games"
                  fill={VOLUME_BAR_COLOR}
                  legendType="none"
                  isAnimationActive={false}
                  data-testid="flaw-trend-volume-bars"
                />
                {/* 257 D-17: the two stacked bands of the Blunders area, under the lines. */}
                <Area
                  yAxisId="rate"
                  stackId={BLUNDER_STACK_ID}
                  type="monotone"
                  dataKey="facepalm_band"
                  fill={FACEPALM_BAND_FILL}
                  fillOpacity={1}
                  stroke="none"
                  activeDot={false}
                  isAnimationActive={false}
                  hide={bandsHidden}
                  data-testid="flaw-trend-facepalm-band"
                />
                <Area
                  yAxisId="rate"
                  stackId={BLUNDER_STACK_ID}
                  type="monotone"
                  dataKey="other_band"
                  fill={OTHER_BLUNDER_BAND_FILL}
                  fillOpacity={1}
                  stroke="none"
                  activeDot={false}
                  isAnimationActive={false}
                  hide={bandsHidden}
                />
                {SERIES.map((s) => (
                  <Line
                    key={s.key}
                    yAxisId="rate"
                    type="monotone"
                    dataKey={s.key}
                    stroke={s.color}
                    strokeWidth={2}
                    dot={false}
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
              {LEGEND.map((s) => {
                const isHidden = hiddenKeys.has(s.key);
                return (
                  <button
                    key={s.key}
                    type="button"
                    onClick={() => {
                      handleLegendClick(s.key);
                      // A hidden series becomes shown (on), a shown one hidden (off). No series key.
                      trackFeature('toggle', { target: 'flaw-trend-legend', value: onOff(isHidden) });
                    }}
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
