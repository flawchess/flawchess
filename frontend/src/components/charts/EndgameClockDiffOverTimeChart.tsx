/**
 * Phase 88.2 / Plan 88-15 (CONTEXT §2 A-2) — restored "Average Clock Difference
 * over Time" line chart. Plots the rolling-window mean of
 * (user_clock - opp_clock) / base_clock at endgame entry, per ISO Monday,
 * with per-week game volume rendered as muted bars behind the line. Zone bands
 * tint regions above/below NEUTRAL_PCT_THRESHOLD.
 *
 * Restored after the Phase 88-07 cleanup deleted the pre-existing chart —
 * user-approved scope amendment to ROADMAP Phase 88 SC #1 (bullet cards
 * STAY, line chart RETURNS alongside).
 *
 * Unit lock: avg_clock_diff_pct is in PERCENT (50.0, not 0.5).
 * NEUTRAL_PCT_THRESHOLD is in PERCENT (5.0). Chart Y-axis is in PERCENT
 * ([-30, 30]). All three share the same unit — NO conversion at the chart
 * layer (B-5 lock).
 */

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
  MY_SCORE_COLOR,
  ZONE_DANGER,
  ZONE_SUCCESS,
} from '@/lib/theme';
import { createDateTickFormatter, formatDateWithYear } from '@/lib/utils';
import type { ClockDiffTimelinePoint } from '@/types/endgames';

// Y axis configuration. Fixed ±30 percent envelope; ticks at every 10 points
// for legibility. Restored from the pre-deletion chart's TIMELINE_Y_DOMAIN /
// TIMELINE_Y_TICKS values (Plan 88-15 plan, <interfaces> section).
const Y_DOMAIN: [number, number] = [-30, 30];
const Y_TICKS = [-30, -20, -10, 0, 10, 20, 30];

// Muted opacity for the zone-tinted ReferenceArea bands. Lower than the bullet
// chart's 0.35 because the chart area is much larger and a denser tint would
// dominate the line. Pre-deletion convention.
const ZONE_OPACITY = 0.15;

// REVIEW.md WR-05: the original implementation scaffolded a `useIsMobile`
// hook with a media-query listener just to set `margin.left` to 0 on mobile.
// That listener cost wasn't worth a single layout tweak, so we drop the hook
// and shave the left margin via a Tailwind responsive class on the wrapper
// instead (`-ml-2 sm:ml-0`). If a future change needs richer mobile awareness
// (tick density, height, label rotation), reach for `useIsMobile` from
// `EndgameScoreOverTimeChart` rather than reintroducing a one-line listener.

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

  const dates = data.map((p) => p.date);
  const formatDateTick = createDateTickFormatter(dates);

  return (
    <div
      data-testid="clock-diff-over-time-chart"
      role="img"
      aria-label="Average clock difference over time"
    >
      <div className="mb-3">
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Average Clock Difference over Time
            <InfoPopover
              ariaLabel="Average clock difference over time info"
              testId="clock-diff-over-time-info"
              side="top"
            >
              <p>
                Rolling average of (your clock minus opponent's clock) at
                endgame entry, as a percent of base clock. Each point is the
                average across the trailing 100 games up to the last game of
                that ISO week.
              </p>
              <p className="mt-1">
                Bars show how many games you played in each week. Positive
                values mean you entered endgames with more clock than your
                opponent.
              </p>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Are you banking time into the endgame or burning it down?
        </p>
      </div>
      <ChartContainer
        config={{}}
        className="w-full h-72 -ml-2 sm:ml-0"
        data-testid="clock-diff-over-time-chart-container"
      >
        <ComposedChart
          data={data}
          margin={{ top: 5, right: 10, left: 10, bottom: 10 }}
        >
          <CartesianGrid vertical={false} />
          <XAxis dataKey="date" tickFormatter={formatDateTick} />
          <YAxis
            yAxisId="value"
            domain={Y_DOMAIN}
            ticks={Y_TICKS}
            // REVIEW.md WR-02: allow values outside ±30% to render past the
            // envelope rather than silently clipping to the edge. Mirrors the
            // bullet-chart "open-ended whisker" convention (clampDeltaCi). Real
            // rapid/classical users routinely bank >30% more clock than their
            // opponents at endgame entry; clipping turned that into a flat line
            // at the axis edge.
            allowDataOverflow={true}
            tickFormatter={(v: number) => `${v}%`}
            width={44}
          />
          {/* Hidden right Y-axis dedicated to volume bars. Same pinning trick
              as EndgameScoreOverTimeChart — barMax * 5 keeps bars in the
              bottom 20% of the canvas so they don't fight the line for
              vertical real estate. */}
          <YAxis yAxisId="bars" orientation="right" hide domain={[0, barMax * 5]} />
          {/* Zone bands. NEUTRAL_PCT_THRESHOLD and Y_DOMAIN are both PERCENT
              units — no conversion. The neutral middle stays unshaded. */}
          <ReferenceArea
            yAxisId="value"
            y1={NEUTRAL_PCT_THRESHOLD}
            y2={Y_DOMAIN[1]}
            fill={ZONE_SUCCESS}
            fillOpacity={ZONE_OPACITY}
            ifOverflow="visible"
          />
          <ReferenceArea
            yAxisId="value"
            y1={Y_DOMAIN[0]}
            y2={-NEUTRAL_PCT_THRESHOLD}
            fill={ZONE_DANGER}
            fillOpacity={ZONE_OPACITY}
            ifOverflow="visible"
          />
          <ReferenceLine
            yAxisId="value"
            y={0}
            stroke="currentColor"
            strokeDasharray="3 3"
            strokeOpacity={0.4}
          />
          <ChartTooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              const point = payload.find(
                (p) => (p.payload as ChartPoint | undefined)?.date !== undefined,
              )?.payload as ChartPoint | undefined;
              if (!point) return null;
              const sign = point.avg_clock_diff_pct > 0 ? '+' : '';
              return (
                <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                  <div className="font-medium">
                    Week of {formatDateWithYear(label as string)}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div
                      className="h-2 w-2 shrink-0 rounded-[2px]"
                      style={{ backgroundColor: MY_SCORE_COLOR }}
                    />
                    <span>
                      Clock difference: {sign}
                      {point.avg_clock_diff_pct.toFixed(1)}%
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
            stroke={MY_SCORE_COLOR}
            strokeWidth={2}
            dot={{ r: 3, fill: MY_SCORE_COLOR }}
            connectNulls={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ChartContainer>
      {/* REVIEW.md IN-04: bumped from text-xs to text-sm — CLAUDE.md sets
          text-sm as the floor for non-tooltip copy; the popover-body
          exception does not extend to plain chart captions. */}
      <p className="text-sm text-muted-foreground text-center mt-1">
        Week (rolling average of the last 100 games)
      </p>
    </div>
  );
}
