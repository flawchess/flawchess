/**
 * Phase 88.4 / Plan 88.4-01 (SC-3) — Score Gap by Time Pressure line chart.
 *
 * Replaces the four stacked QuintileRow bullet charts inside EndgameTimePressureCard
 * with a single horizontal ComposedChart over the 4 ordinal pressure-bucket labels
 * (Q0–Q3; Q4 filtered as per Plan 88-13 A-4). Three ReferenceArea zone bands use
 * the TC-collapsed neutral zone [-0.06, +0.06] derived from benchmarks-latest.md
 * §3.3.3.b (opp-quintile rerun, 2026-05-17). CI whiskers render via Recharts ErrorBar.
 *
 * Visual pattern: mirrors EndgameClockDiffOverTimeChart (zone bands, white line,
 * zone-colored dots, 0-line reference). Built as a self-contained component — not
 * a fork — so it can be updated independently.
 */

import {
  ComposedChart,
  ErrorBar,
  Line,
  ReferenceArea,
  ReferenceLine,
  XAxis,
  YAxis,
} from 'recharts';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
import {
  PRESSURE_DELTA_DOMAIN,
  clampDeltaCi,
  pressureDeltaZoneColor,
} from '@/lib/pressureBulletConfig';
import type { PressureQuintileBullet } from '@/types/endgames';

// Muted opacity for zone-tinted ReferenceArea bands. Matches EndgameClockDiffOverTimeChart.
// Not exported from theme.ts — local constant per chart.
const ZONE_OPACITY = 0.15;

// TC-collapsed neutral band for the score-gap line chart.
// Derived from PRESSURE_BIN_SCORE_NEUTRAL_ZONES TC-collapse: all 20 (TC, quintile)
// cells cap at ±0.06 under opp-quintile semantics.
// Source: reports/benchmarks-latest.md §3.3.3.b (opp-quintile rerun, 2026-05-17).
// The PRESSURE_BIN_NEUTRAL_CAP = 0.06 fully dominates; raw IQR widths (0.166–0.370)
// are swamped by the cap, so TC differences in the neutral band cannot be observed.
export const PRESSURE_SCORE_GAP_NEUTRAL_MIN = -0.06;
export const PRESSURE_SCORE_GAP_NEUTRAL_MAX = 0.06;

// Fixed Y domain matching the existing bullet chart axis from pressureBulletConfig.ts.
const Y_DOMAIN: [number, number] = [-PRESSURE_DELTA_DOMAIN, PRESSURE_DELTA_DOMAIN];

// Q4 (80-100% clock remaining) is a low-signal tail — hidden per Plan 88-13 A-4.
// The chart displays only Q0–Q3 (4 datapoints).
const MAX_VISIBLE_QUINTILE_INDEX = 3;

// Ordinal x-axis labels for the 4 displayed quintile buckets.
// Redeclared here (not imported from EndgameTimePressureCard) to keep this
// chart self-contained per the "build independently" guidance (RESEARCH.md line 450).
const PRESSURE_LABELS: Record<0 | 1 | 2 | 3, string> = {
  0: '0-20% Time',
  1: '20-40% Time',
  2: '40-60% Time',
  3: '60-80% Time',
};

interface ChartPoint {
  label: string;
  delta: number;
  n: number;
  opp_score: number | null;
  p_value: number | null;
  ciError?: [number, number]; // [downward_offset, upward_offset] for ErrorBar
}

/** Pick zone color for a score-gap dot relative to the TC-collapsed neutral band. */
function zoneDotColor(delta: number): string {
  return pressureDeltaZoneColor(
    delta,
    PRESSURE_SCORE_GAP_NEUTRAL_MIN,
    PRESSURE_SCORE_GAP_NEUTRAL_MAX,
  );
}

/** Transform quintile bins into chart points, filtering Q4 and zero-n bins. */
function toChartData(quintiles: PressureQuintileBullet[]): ChartPoint[] {
  return quintiles
    .filter((bin) => bin.quintile_index <= MAX_VISIBLE_QUINTILE_INDEX)
    .filter((bin) => bin.n > 0)
    .map((bin) => {
      // ciError: [distance_below_value, distance_above_value] — both non-negative
      // when CI properly brackets the point. clampDeltaCi prevents extreme CIs
      // from escaping the visible axis ([-1, 1] clamp).
      const ciError: [number, number] | undefined =
        bin.ci_low != null && bin.ci_high != null
          ? [
              bin.delta - clampDeltaCi(bin.ci_low),
              clampDeltaCi(bin.ci_high) - bin.delta,
            ]
          : undefined;

      return {
        label: PRESSURE_LABELS[bin.quintile_index as 0 | 1 | 2 | 3] ?? '',
        delta: bin.delta,
        n: bin.n,
        opp_score: bin.opp_score,
        p_value: bin.p_value,
        ciError,
      };
    });
}

export interface ScoreGapByTimePressureChartProps {
  quintiles: PressureQuintileBullet[];
  tc: 'bullet' | 'blitz' | 'rapid' | 'classical';
}

export function ScoreGapByTimePressureChart({
  quintiles,
  tc,
}: ScoreGapByTimePressureChartProps) {
  const data = toChartData(quintiles);

  return (
    <div
      data-testid={`score-gap-by-time-pressure-chart-${tc}`}
      role="img"
      aria-label={`Score gap by time pressure - ${tc}`}
    >
      <ChartContainer
        config={{}}
        className="w-full h-44"
        data-testid="score-gap-by-time-pressure-chart-container"
      >
        <ComposedChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 10 }}>
          {/* Three flat zone bands — same pattern as EndgameClockDiffOverTimeChart. */}
          <ReferenceArea
            yAxisId="value"
            y1={Y_DOMAIN[0]}
            y2={PRESSURE_SCORE_GAP_NEUTRAL_MIN}
            fill={ZONE_DANGER}
            fillOpacity={ZONE_OPACITY}
            ifOverflow="visible"
          />
          <ReferenceArea
            yAxisId="value"
            y1={PRESSURE_SCORE_GAP_NEUTRAL_MIN}
            y2={PRESSURE_SCORE_GAP_NEUTRAL_MAX}
            fill={ZONE_NEUTRAL}
            fillOpacity={ZONE_OPACITY}
            ifOverflow="visible"
          />
          <ReferenceArea
            yAxisId="value"
            y1={PRESSURE_SCORE_GAP_NEUTRAL_MAX}
            y2={Y_DOMAIN[1]}
            fill={ZONE_SUCCESS}
            fillOpacity={ZONE_OPACITY}
            ifOverflow="visible"
          />
          {/* Category x-axis — 4 ordinal labels, no tick formatter needed */}
          <XAxis dataKey="label" type="category" />
          <YAxis
            yAxisId="value"
            domain={Y_DOMAIN}
            width={44}
            tickFormatter={(v: number) =>
              v > 0 ? `+${(v * 100).toFixed(0)}%` : `${(v * 100).toFixed(0)}%`
            }
          />
          {/* 0-line baseline — same props as EndgameClockDiffOverTimeChart */}
          <ReferenceLine
            yAxisId="value"
            y={0}
            stroke="currentColor"
            strokeDasharray="3 3"
            strokeOpacity={0.4}
          />
          <ChartTooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const point = payload[0]?.payload as ChartPoint | undefined;
              if (!point) return null;
              const sign = point.delta >= 0 ? '+' : '';
              const signedDelta = `${sign}${(point.delta * 100).toFixed(1)}%`;
              const oppPct =
                point.opp_score != null
                  ? `${(point.opp_score * 100).toFixed(1)}%`
                  : 'n/a';
              return (
                <div
                  className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1"
                  data-testid="score-gap-tooltip"
                >
                  <div className="font-medium">{point.label}</div>
                  <div className="flex items-center gap-1.5">
                    <div
                      className="h-2 w-2 shrink-0 rounded-[2px]"
                      style={{ backgroundColor: zoneDotColor(point.delta) }}
                    />
                    <span>Score gap: {signedDelta}</span>
                  </div>
                  <div className="text-muted-foreground">vs opponents at {oppPct}</div>
                  <div className="text-muted-foreground">n = {point.n}</div>
                </div>
              );
            }}
          />
          <Line
            yAxisId="value"
            type="monotone"
            dataKey="delta"
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
                return <g key={`nodot-${String(payload?.label ?? cx)}`} />;
              }
              const delta = (payload.delta as number) ?? 0;
              return (
                <circle
                  key={`score-gap-dot-${payload.label as string}`}
                  cx={cx}
                  cy={cy}
                  r={2.5}
                  fill={zoneDotColor(delta)}
                />
              );
            }}
          >
            {/* ErrorBar as child of Line — recharts 2.15.x pattern.
                dataKey="ciError" points to [downOffset, upOffset] pre-computed
                in toChartData(). undefined ciError suppresses the whisker. */}
            <ErrorBar
              dataKey="ciError"
              width={4}
              stroke="currentColor"
              strokeOpacity={0.5}
              direction="y"
            />
          </Line>
        </ComposedChart>
      </ChartContainer>
    </div>
  );
}
