/**
 * Phase 88.2 / Plan 88-15 (CONTEXT §2 A-2) — restored "Average Clock Difference
 * over Time" line chart. Plots the rolling-window mean of
 * (user_clock - opp_clock) / base_clock at endgame entry, per ISO Monday,
 * with per-week game volume rendered as muted bars behind the line. Three zone
 * bands tint regions above / inside / below ±NEUTRAL_PCT_THRESHOLD.
 *
 * Restored after the Phase 88-07 cleanup deleted the pre-existing chart —
 * user-approved scope amendment to ROADMAP Phase 88 SC #1 (bullet cards
 * STAY, line chart RETURNS alongside).
 *
 * Unit lock: avg_clock_diff_pct is in PERCENT (50.0, not 0.5).
 * NEUTRAL_PCT_THRESHOLD is in PERCENT (5.0). Chart Y-axis is in PERCENT.
 * All three share the same unit — NO conversion at the chart layer (B-5 lock).
 *
 * Visual design re-aligned with the pre-deletion chart (main branch reference):
 *   - vertical "Clock diff %" Y-axis label on desktop, hidden on mobile
 *   - dynamic Y domain expands past ±30% to include any point that would
 *     otherwise be clipped (Math.max/Math.min around the data extremes)
 *   - three zone bands: danger (red), neutral (blue), success (green)
 *   - white line with zone-colored dots, dot radius 2.5
 *   - detailed info-popover copy mirroring the previous component
 */

import { useEffect, useState } from 'react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  XAxis,
  YAxis,
} from 'recharts';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { InfoPopover } from '@/components/ui/info-popover';
import { NEUTRAL_PCT_THRESHOLD } from '@/generated/endgameZones';
import {
  ENDGAME_VOLUME_BAR_COLOR,
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
} from '@/lib/theme';
import { createDateTickFormatter, formatDateWithYear } from '@/lib/utils';
import { inactivityGapReferenceLines } from './InactivityGapReferenceLines';
import type { ClockDiffTimelinePoint } from '@/types/endgames';

// Y axis baseline envelope. Real values can exceed this — see
// `computeYDomain` below, which expands the domain to include outliers
// instead of silently clipping them to the ±30% edge.
const Y_DOMAIN_BASE: [number, number] = [-30, 30];
const Y_TICKS_BASE = [-30, -20, -10, 0, 10, 20, 30];

// Muted opacity for the zone-tinted ReferenceArea bands. Lower than the bullet
// chart's 0.35 because the chart area is much larger and a denser tint would
// dominate the line. Pre-deletion convention.
const ZONE_OPACITY = 0.15;

// Mobile breakpoint for hiding the vertical Y-axis label (Tailwind `sm:`).
const MOBILE_BREAKPOINT_PX = 640;

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined'
      && window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`).matches,
  );
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}

/** Pick the zone color for a point based on its value vs the neutral threshold. */
function zoneColor(diffPct: number): string {
  if (diffPct > NEUTRAL_PCT_THRESHOLD) return ZONE_SUCCESS;
  if (diffPct < -NEUTRAL_PCT_THRESHOLD) return ZONE_DANGER;
  return ZONE_NEUTRAL;
}

/**
 * Compute a Y-axis domain that expands past the ±30% baseline when needed to
 * include any data point that would otherwise be clipped. Mirrors the pre-
 * deletion chart's behavior (main branch).
 */
function computeYDomain(values: number[]): [number, number] {
  if (values.length === 0) return Y_DOMAIN_BASE;
  const dataMax = Math.max(...values);
  const dataMin = Math.min(...values);
  return [
    Math.min(Y_DOMAIN_BASE[0], Math.floor(dataMin)),
    Math.max(Y_DOMAIN_BASE[1], Math.ceil(dataMax)),
  ];
}

export interface EndgameClockDiffOverTimeChartProps {
  timeline: ClockDiffTimelinePoint[];
}

interface ChartPoint {
  date: string;
  avg_clock_diff_pct: number;
  game_count: number;
  per_week_game_count: number;
}

export function EndgameClockDiffOverTimeChart({
  timeline,
}: EndgameClockDiffOverTimeChartProps) {
  const isMobile = useIsMobile();

  // Belt-and-suspenders: page-level integration also guards on empty, but
  // returning null here keeps the chart fully self-contained.
  if (timeline.length === 0) return null;

  const data: ChartPoint[] = timeline.map((p) => ({
    date: p.date,
    avg_clock_diff_pct: p.avg_clock_diff_pct,
    game_count: p.game_count,
    per_week_game_count: p.per_week_game_count,
  }));

  // Volume-bar Y-axis envelope. domain={[0, barMax * 5]} pins the tallest bar
  // to the bottom 20% of the chart canvas (mirrors EndgameScoreOverTimeChart).
  const barMax = Math.max(1, ...data.map((r) => r.per_week_game_count));

  const yDomain = computeYDomain(data.map((p) => p.avg_clock_diff_pct));

  const dates = data.map((p) => p.date);
  const formatDateTick = createDateTickFormatter(dates);

  return (
    <div
      data-testid="clock-diff-over-time-chart"
      role="img"
      aria-label="Average clock gap over time"
    >
      <div className="mb-3">
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Average Clock Gap over Time
            <InfoPopover
              ariaLabel="Average clock gap over time info"
              testId="clock-diff-over-time-info"
              side="top"
            >
              <p>
                <strong>Average Clock Gap over Time:</strong> whether you
                tend to enter endgames with more or less time on your clock
                than your opponent, tracked over time. Positive means you
                arrived with more time left.
              </p>
              <p className="mt-1">
                Dots are colored by zone: green when your lead exceeds
                +{NEUTRAL_PCT_THRESHOLD}%, red when you're down more than
                −{NEUTRAL_PCT_THRESHOLD}%, blue in between. Bars at the bottom
                show how many games you played.
              </p>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Are you banking time into the endgame or burning it down?
        </p>
      </div>
      <div className={isMobile ? '' : 'flex items-stretch'}>
        {/* Vertical Y-axis label on desktop only. Plain HTML rotated via CSS —
            Recharts' SVG `label` with position='insideLeft' + angle produces
            NaN plot-area rects when the chart is responsive (legacy bug from
            the pre-deletion implementation). */}
        {!isMobile && (
          <div
            className="flex items-center text-sm text-muted-foreground shrink-0 pt-32 -mr-1"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
          >
            Clock Gap
          </div>
        )}
        <ChartContainer
          config={{}}
          className="w-full h-72"
          data-testid="clock-diff-over-time-chart-container"
        >
          <ComposedChart
            data={data}
            margin={{ top: 5, right: 10, left: isMobile ? 0 : 10, bottom: 10 }}
          >
            <CartesianGrid vertical={false} />
            {/* Three zone bands (danger / neutral / success). The pre-deletion
                chart used these to make the verdict readable at a glance. */}
            <ReferenceArea
              yAxisId="value"
              y1={yDomain[0]}
              y2={-NEUTRAL_PCT_THRESHOLD}
              fill={ZONE_DANGER}
              fillOpacity={ZONE_OPACITY}
              ifOverflow="visible"
            />
            <ReferenceArea
              yAxisId="value"
              y1={-NEUTRAL_PCT_THRESHOLD}
              y2={NEUTRAL_PCT_THRESHOLD}
              fill={ZONE_NEUTRAL}
              fillOpacity={ZONE_OPACITY}
              ifOverflow="visible"
            />
            <ReferenceArea
              yAxisId="value"
              y1={NEUTRAL_PCT_THRESHOLD}
              y2={yDomain[1]}
              fill={ZONE_SUCCESS}
              fillOpacity={ZONE_OPACITY}
              ifOverflow="visible"
            />
            <XAxis dataKey="date" tickFormatter={formatDateTick} />
            <YAxis
              yAxisId="value"
              domain={yDomain}
              ticks={Y_TICKS_BASE}
              allowDataOverflow={false}
              tickFormatter={(v: number) => (v > 0 ? `+${v}%` : `${v}%`)}
              width={44}
            />
            {/* Hidden right Y-axis dedicated to volume bars. Same pinning trick
                as EndgameScoreOverTimeChart — barMax * 5 keeps bars in the
                bottom 20% of the canvas so they don't fight the line for
                vertical real estate. */}
            <YAxis yAxisId="bars" orientation="right" hide domain={[0, barMax * 5]} />
            <ReferenceLine
              yAxisId="value"
              y={0}
              stroke="currentColor"
              strokeDasharray="3 3"
              strokeOpacity={0.4}
            />
            {/* Inactivity-gap annotations via shared helper: Palmtree glyph + label per
                >56-day gap. Vertical x= gap lines are independent from the horizontal
                y=0 baseline above — no overlap, no double-annotation. Placed BEFORE
                <Bar> so annotations sit behind data in SVG z-order. */}
            {inactivityGapReferenceLines({ dates, yAxisId: 'value' })}
            <ChartTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const point = payload.find(
                  (p) => (p.payload as ChartPoint | undefined)?.date !== undefined,
                )?.payload as ChartPoint | undefined;
                if (!point) return null;
                const diff = point.avg_clock_diff_pct;
                const sign = diff > 0 ? '+' : '';
                return (
                  <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                    <div className="font-medium">
                      Week of {formatDateWithYear(label as string)}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div
                        className="h-2 w-2 shrink-0 rounded-[2px]"
                        style={{ backgroundColor: zoneColor(diff) }}
                      />
                      <span>
                        Avg clock diff: {sign}
                        {diff.toFixed(1)}%
                        <span className="text-muted-foreground ml-1">
                          (trailing {point.game_count})
                        </span>
                      </span>
                    </div>
                    <div className="text-muted-foreground">
                      Games this week: {point.per_week_game_count}
                    </div>
                  </div>
                );
              }}
            />
            <Bar
              yAxisId="bars"
              dataKey="per_week_game_count"
              fill={ENDGAME_VOLUME_BAR_COLOR}
              legendType="none"
              isAnimationActive={false}
              data-testid="clock-diff-over-time-volume-bars"
            />
            <Line
              yAxisId="value"
              type="monotone"
              dataKey="avg_clock_diff_pct"
              stroke="white"
              strokeWidth={2}
              connectNulls={false}
              isAnimationActive={false}
              dot={(props: {
                cx?: number;
                cy?: number;
                payload?: Record<string, unknown>;
              }) => {
                const { cx, cy, payload } = props;
                if (!payload || !Number.isFinite(cx) || !Number.isFinite(cy)) {
                  return <g key={`nodot-${String(payload?.date ?? cx)}`} />;
                }
                const diff = (payload.avg_clock_diff_pct as number) ?? 0;
                return (
                  <circle
                    key={`clock-diff-dot-${payload.date as string}`}
                    cx={cx}
                    cy={cy}
                    r={2.5}
                    fill={zoneColor(diff)}
                  />
                );
              }}
            />
          </ComposedChart>
        </ChartContainer>
      </div>
      <p className="text-sm text-muted-foreground text-center mt-1">
        Week (rolling average of the last 100 games)
      </p>
    </div>
  );
}
