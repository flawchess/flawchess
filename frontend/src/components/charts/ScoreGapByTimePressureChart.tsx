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
  CartesianGrid,
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
  clampDeltaCi,
  computeScoreGapYAxis,
  pressureDeltaZoneColor,
} from '@/lib/pressureBulletConfig';
import type { PressureQuintileBullet } from '@/types/endgames';
import { deriveLevel } from './EndgameOverallShared';

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

// Y-axis domain + 10%-spaced tick logic lives in pressureBulletConfig
// (computeScoreGapYAxis) so this component file only exports React
// components — keeps Fast Refresh / react-refresh lint happy.

// Q4 (80-100% clock remaining) is a low-signal tail — hidden per Plan 88-13 A-4.
// The chart displays only Q0–Q3 (4 datapoints).
const MAX_VISIBLE_QUINTILE_INDEX = 3;

// Ordinal x-axis labels for the 4 displayed quintile buckets.
// Post-UAT (88.4): bucket *center* values (the midpoint of each 20%-wide
// clock-remaining band), no "Time" suffix — the section/axis already conveys
// "Remaining Time". Redeclared here (not imported from EndgameTimePressureCard)
// to keep this chart self-contained per the "build independently" guidance.
const PRESSURE_LABELS: Record<0 | 1 | 2 | 3, string> = {
  0: '10%',
  1: '30%',
  2: '50%',
  3: '70%',
};

// Full bucket *range* — shown in the tooltip header ("Time Bucket: 0-20%")
// where there's room for the precise band, while the x-axis stays compact
// with the center value (post-UAT 88.4).
const PRESSURE_RANGE_LABELS: Record<0 | 1 | 2 | 3, string> = {
  0: '0-20%',
  1: '20-40%',
  2: '40-60%',
  3: '60-80%',
};

/**
 * Build the conclusion line, e.g. "Likely a real strength (p < 0.001)".
 * Verdict noun + Likely/Possibly lead mirror MetricStatTooltip (score
 * vocabulary, 0% baseline); the confidence-label clause is intentionally
 * dropped per UAT — the parenthesised p-value already conveys strength of
 * evidence. The neutral band is the chart's TC-collapsed ±0.06 so the verdict
 * matches the colored zone the dot sits in.
 */
function conclusionText(
  delta: number,
  pValue: number | null,
  n: number,
): string {
  const level = deriveLevel(pValue, n);
  let headline: string;
  if (level === 'low') {
    headline = 'Inconclusive';
  } else {
    const lead = level === 'high' ? 'Likely' : 'Possibly';
    if (delta >= PRESSURE_SCORE_GAP_NEUTRAL_MAX) {
      headline = `${lead} a real strength`;
    } else if (delta <= PRESSURE_SCORE_GAP_NEUTRAL_MIN) {
      headline = `${lead} a real weakness`;
    } else {
      headline = `${lead} a real difference from the 0% baseline`;
    }
  }
  return pValue !== null ? `${headline} (${formatPValue(pValue)})` : headline;
}

// Post-UAT (88.4): inset the first/last datapoints from the chart edges so the
// line doesn't touch the y-axis / right border. Recharts category-axis padding.
const X_AXIS_EDGE_PADDING = 24;

// Datapoint marker size encodes how many games YOU had in the bucket
// relative to your opponent (n / n_opp): a bigger dot means more of the
// bucket's games were yours, so the user-side score is the better-sampled
// of the two. DOT_RADIUS is the base radius at parity (n == n_opp); the
// scaled radius is clamped to [MIN, MAX] so a lopsided bucket can't produce
// an invisible or oversized marker.
// Post-UAT (88.4): base radius bumped for readability (was 2.5).
const DOT_RADIUS = 4.5;
const DOT_RADIUS_MIN = 3;
const DOT_RADIUS_MAX = 7;

/**
 * Scale the marker radius by the user/opponent sample-size ratio, capped to
 * [DOT_RADIUS_MIN, DOT_RADIUS_MAX]. n_opp == 0 with n > 0 means you played
 * every game in the bucket — max the marker rather than divide by zero.
 */
function dotRadius(n: number, nOpp: number): number {
  if (nOpp <= 0) return DOT_RADIUS_MAX;
  const scaled = DOT_RADIUS * (n / nOpp);
  return Math.min(DOT_RADIUS_MAX, Math.max(DOT_RADIUS_MIN, scaled));
}

interface ChartPoint {
  label: string;
  /** Full bucket range for the tooltip header (e.g. "0-20%"). */
  rangeLabel: string;
  delta: number;
  n: number;
  n_opp: number;
  opp_score: number | null;
  p_value: number | null;
  ci_low: number | null;
  ci_high: number | null;
  ciError?: [number, number]; // [downward_offset, upward_offset] for ErrorBar
}

/** Signed percentage, one decimal, explicit leading +/−. e.g. -0.17 → "-17.0%". */
function formatSignedPct(frac: number): string {
  const pct = frac * 100;
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
}

/** Plain percentage, one decimal (no forced sign). e.g. 0.55 → "55.0%". */
function formatPct(frac: number | null): string {
  return frac != null ? `${(frac * 100).toFixed(1)}%` : 'n/a';
}

/** p-value display matching MetricStatTooltip: 3 decimals, "< 0.001" floor. */
function formatPValue(p: number): string {
  return p < 0.001 ? 'p < 0.001' : `p = ${p.toFixed(3)}`;
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
        rangeLabel:
          PRESSURE_RANGE_LABELS[bin.quintile_index as 0 | 1 | 2 | 3] ?? '',
        delta: bin.delta,
        n: bin.n,
        n_opp: bin.n_opp,
        opp_score: bin.opp_score,
        p_value: bin.p_value,
        ci_low: bin.ci_low,
        ci_high: bin.ci_high,
        ciError,
      };
    });
}

/**
 * Tooltip body for a single bucket. Exported so the test renders the REAL
 * production tooltip instead of a reimplementation (REVIEW.md IN-01 tautology
 * fix). Post-UAT 88.4: header is the full bucket range ("Time Bucket: 0-20%");
 * You/Opp/Games collapse to one muted line; the app-standard verdict sentence
 * (conclusionText) plus the statistical test + CI methodology we had behind
 * the old per-bucket info icons render below.
 *
 * Font-size note: this Recharts hover tooltip deliberately uses `text-xs` to
 * match the sibling "Clock Gap at Endgame Entry"
 * (EndgameClockDiffOverTimeChart)
 * tooltip — a compact, transient, opt-in hover surface, the same rationale as
 * the CLAUDE.md popover-layer exception. User-directed (post-UAT 88.4),
 * superseding the earlier WR-01 text-sm bump; do not re-flag.
 */
export function ScoreGapTooltipContent({ point }: { point: ChartPoint }) {
  const userScore = point.opp_score != null ? point.opp_score + point.delta : null;
  // p-value is already in the conclusion line above — don't repeat it here.
  const testLine = 'Independent two-sample test.';
  const ciLine =
    point.ci_low != null && point.ci_high != null
      ? `95% CI [${formatSignedPct(point.ci_low)}, ${formatSignedPct(point.ci_high)}]`
      : '95% normal-approx CI';

  return (
    <div
      className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1"
      data-testid="score-gap-tooltip"
    >
      <div className="font-medium">Time Bucket: {point.rangeLabel}</div>
      <div className="flex items-center gap-1.5">
        <div
          className="h-2 w-2 shrink-0 rounded-[2px]"
          style={{ backgroundColor: zoneDotColor(point.delta) }}
        />
        <span>Score gap: {formatSignedPct(point.delta)}</span>
      </div>
      {/* Two lines: the user-side and opponent-side splits are independent
          samples from the same game-set, so their game counts can differ —
          show each count next to its own score. */}
      <div className="text-muted-foreground">
        <div>
          You: {formatPct(userScore)} ({point.n} games)
        </div>
        <div>
          Opp: {formatPct(point.opp_score)} ({point.n_opp} games)
        </div>
      </div>
      <div>{conclusionText(point.delta, point.p_value, point.n)}</div>
      <div className="text-muted-foreground italic">{testLine}</div>
      <div className="text-muted-foreground italic">{ciLine}</div>
    </div>
  );
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
  const { domain: yDomain, ticks: yTicks } = computeScoreGapYAxis(data);

  return (
    <div
      data-testid={`score-gap-by-time-pressure-chart-${tc}`}
      role="img"
      aria-label={`Score gap by time pressure - ${tc}`}
    >
      <ChartContainer
        config={{}}
        className="w-full h-64"
        data-testid="score-gap-by-time-pressure-chart-container"
      >
        <ComposedChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 10 }}>
          {/* Horizontal-only fine grid — identical to EndgameClockDiffOverTimeChart. */}
          <CartesianGrid vertical={false} />
          {/* Hidden full-range numeric x-axis the zone bands bind to. The
              visible category axis is padded (datapoints inset off the
              borders), so a category-bound band would inherit that inset and
              leave uncolored gutters. Binding the bands to this unpadded
              [0,1] axis instead makes them full-bleed: flush to the y-axis on
              the left and the chart border on the right (post-UAT 88.4). */}
          <XAxis
            xAxisId="bleed"
            type="number"
            domain={[0, 1]}
            hide
            allowDataOverflow
          />
          {/* Three flat zone bands — full-bleed via xAxisId="bleed" x1=0/x2=1. */}
          <ReferenceArea
            xAxisId="bleed"
            yAxisId="value"
            x1={0}
            x2={1}
            y1={yDomain[0]}
            y2={PRESSURE_SCORE_GAP_NEUTRAL_MIN}
            fill={ZONE_DANGER}
            fillOpacity={ZONE_OPACITY}
            ifOverflow="visible"
          />
          <ReferenceArea
            xAxisId="bleed"
            yAxisId="value"
            x1={0}
            x2={1}
            y1={PRESSURE_SCORE_GAP_NEUTRAL_MIN}
            y2={PRESSURE_SCORE_GAP_NEUTRAL_MAX}
            fill={ZONE_NEUTRAL}
            fillOpacity={ZONE_OPACITY}
            ifOverflow="visible"
          />
          <ReferenceArea
            xAxisId="bleed"
            yAxisId="value"
            x1={0}
            x2={1}
            y1={PRESSURE_SCORE_GAP_NEUTRAL_MAX}
            y2={yDomain[1]}
            fill={ZONE_SUCCESS}
            fillOpacity={ZONE_OPACITY}
            ifOverflow="visible"
          />
          {/* Category x-axis — 4 bucket-center labels. Edge padding insets the
              first/last datapoints off the chart borders (post-UAT 88.4). */}
          <XAxis
            dataKey="label"
            type="category"
            padding={{ left: X_AXIS_EDGE_PADDING, right: X_AXIS_EDGE_PADDING }}
          />
          <YAxis
            yAxisId="value"
            domain={yDomain}
            ticks={yTicks}
            // interval={0} forces every 10% tick (and its CartesianGrid line)
            // to render — Recharts otherwise auto-thins ticks/grid lines when
            // the expanded domain produces many ticks (post-UAT 88.4).
            interval={0}
            width={48}
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
              return <ScoreGapTooltipContent point={point} />;
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
              const n = (payload.n as number) ?? 0;
              const nOpp = (payload.n_opp as number) ?? 0;
              return (
                <circle
                  key={`score-gap-dot-${payload.label as string}`}
                  cx={cx}
                  cy={cy}
                  r={dotRadius(n, nOpp)}
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
      {/* X-axis caption rendered as HTML (not a Recharts SVG <Label>) so it
          matches the "Clock Gap at Endgame Entry" chart's text-sm caption
          exactly on every viewport — SVG label text scales with the
          responsive container and would not match on mobile. */}
      <p className="text-sm text-muted-foreground text-center mt-1">
        Remaining Time
      </p>
    </div>
  );
}
