import { useMemo } from 'react';
import { TreePalm } from 'lucide-react';
import { Bar, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from 'recharts';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { ChartTooltipBox } from '@/components/ui/chart-tooltip-box';
import { inactivityGapReferenceLines } from '@/components/charts/InactivityGapReferenceLines';
import { FACEPALM_HIGH_CUTOFF } from '@/lib/facepalm';
import { FACEPALM_SHARE_LINE, VOLUME_BAR_COLOR } from '@/lib/theme';
import { createDateTickFormatter, formatDateWithYear } from '@/lib/utils';
import type { FlawTrendPoint } from '@/types/library';

// ─── Named constants (no magic numbers) ──────────────────────────────────────

/** A line needs at least this many plotted shares; fewer shows the text fallback. */
const MIN_PLOTTED_SHARES = 2;

/** Padding (share units, 0.05 = 5 points) added above and below the plotted shares. */
const Y_DOMAIN_PADDING = 0.05;

/** Multiplier turning a 0..1 share into a percent. */
const PERCENT_SCALE = 100;

/** Hidden bars axis runs to barMax times this, pinning the tallest bar to the bottom 20%. */
const BAR_AXIS_HEADROOM = 5;

/** Width of the percent axis labels (px). */
const Y_AXIS_WIDTH = 40;

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Percent axis domain fitted to the plotted shares, padded and clamped to [0, 1].
 * Only called with at least MIN_PLOTTED_SHARES shares.
 */
function shareDomain(shares: number[]): [number, number] {
  const low = Math.max(0, Math.min(...shares) - Y_DOMAIN_PADDING);
  const high = Math.min(1, Math.max(...shares) + Y_DOMAIN_PADDING);
  return [low, high];
}

function formatSharePercent(share: number): string {
  // The share is deliberately rounded to the nearest whole percent: 257 D-07's round-down rule
  // covers the facepalm score itself, not this pooled share, which is a different number.
  return `${Math.round(share * PERCENT_SCALE)}%`;
}

// ─── Tooltip ─────────────────────────────────────────────────────────────────

interface FacepalmShareTooltipBodyProps {
  point: FlawTrendPoint;
  /** The hovered date label (ISO yyyy-mm-dd). */
  label: string;
}

/** Tooltip box: the share and the two counts behind it, then the per-week volume line. */
export function FacepalmShareTooltipBody({ point, label }: FacepalmShareTooltipBodyProps) {
  return (
    <ChartTooltipBox className="text-sm" data-testid="facepalm-share-tooltip">
      <div className="font-bold text-muted-foreground">{formatDateWithYear(label)}</div>
      {point.facepalm_share === null ? (
        <div>Too few scored blunders in this window</div>
      ) : (
        <>
          <div style={{ color: FACEPALM_SHARE_LINE }}>
            Facepalm share: {formatSharePercent(point.facepalm_share)}
          </div>
          <div className="text-muted-foreground">
            {point.facepalm_in_window} of {point.scored_blunders_in_window} scored blunders
          </div>
        </>
      )}
      <div className="text-muted-foreground">
        {point.per_week_games} games this week · {point.games_in_window} in window
      </div>
    </ChartTooltipBox>
  );
}

// ─── Chart ───────────────────────────────────────────────────────────────────

interface FacepalmShareChartProps {
  /** The selected time control's Flaws Timeline points (same points as FlawTrendChart). */
  trend: FlawTrendPoint[];
  /** Rolling window size (games per window). Shown in the caption below the axis. */
  windowSize: number;
}

/**
 * Facepalm share of the player's blunders over time (257 D-03), directly below the Flaws
 * Timeline: facepalm blunders / scored blunders pooled over the same rolling window, on the
 * same dates, with the same volume bars, inactivity markers and caption. One neutral line,
 * not split by type (D-04). A null share (too few scored blunders) is a gap in the line.
 */
export function FacepalmShareChart({ trend, windowSize }: FacepalmShareChartProps) {
  const allDates = useMemo(() => trend.map((p) => p.date), [trend]);
  const formatDateTick = useMemo(() => createDateTickFormatter(allDates), [allDates]);
  const plottedShares = useMemo(
    () => trend.flatMap((p) => (p.facepalm_share === null ? [] : [p.facepalm_share])),
    [trend],
  );
  const barMax = Math.max(1, ...trend.map((p) => p.per_week_games));

  return (
    <Card
      className="mt-4"
      data-testid="facepalm-share-chart"
      aria-label="Facepalm share of blunders chart"
    >
      <CardHeader size="compact" className="flex items-center gap-2">
        <TreePalm className="h-4 w-4" aria-hidden="true" />
        Facepalm share of blunders
      </CardHeader>
      <CardBody>
        <p className="text-sm text-muted-foreground pb-2">
          Blunders with a facepalm score of {FACEPALM_HIGH_CUTOFF}% or more, out of your scored
          blunders.
        </p>
        {plottedShares.length < MIN_PLOTTED_SHARES ? (
          <p
            className="text-sm text-muted-foreground text-center py-4"
            data-testid="facepalm-share-empty"
          >
            Not enough scored blunders to show a trend
          </p>
        ) : (
          <>
            <ChartContainer
              config={{}}
              className="w-full h-48"
              data-testid="facepalm-share-composed-chart"
            >
              <ComposedChart data={trend} margin={{ top: 5, right: 10, left: 0, bottom: 10 }}>
                <CartesianGrid vertical={false} yAxisId="share" stroke="var(--color-border)" />
                <XAxis dataKey="date" tickFormatter={formatDateTick} tick={{ fontSize: 12 }} />
                <YAxis
                  yAxisId="share"
                  domain={shareDomain(plottedShares)}
                  tickFormatter={formatSharePercent}
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={Y_AXIS_WIDTH}
                />
                {/* Hidden right axis for volume bars (mirrors the Flaws Timeline). */}
                <YAxis
                  yAxisId="bars"
                  orientation="right"
                  hide
                  domain={[0, barMax * BAR_AXIS_HEADROOM]}
                />
                <ChartTooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    const point = payload[0]?.payload as FlawTrendPoint | undefined;
                    if (!point) return null;
                    return <FacepalmShareTooltipBody point={point} label={label as string} />;
                  }}
                />
                {/* Inactivity markers BEFORE the data series so they sit behind in z-order. */}
                {inactivityGapReferenceLines({ dates: allDates, yAxisId: 'share' })}
                <Bar
                  yAxisId="bars"
                  dataKey="per_week_games"
                  fill={VOLUME_BAR_COLOR}
                  legendType="none"
                  isAnimationActive={false}
                  data-testid="facepalm-share-volume-bars"
                />
                <Line
                  yAxisId="share"
                  type="monotone"
                  dataKey="facepalm_share"
                  stroke={FACEPALM_SHARE_LINE}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: FACEPALM_SHARE_LINE, strokeWidth: 0 }}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ChartContainer>

            {/* Rolling-window caption, directly below the x-axis label. */}
            <p className="text-sm text-muted-foreground text-center mt-1">
              last {windowSize} games · rolling window
            </p>
          </>
        )}
      </CardBody>
    </Card>
  );
}
