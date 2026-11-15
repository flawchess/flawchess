import { useMemo } from 'react';
import { ChartTooltipBox } from '@/components/ui/chart-tooltip-box';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { Bar, CartesianGrid, ComposedChart, Line, ReferenceLine, XAxis, YAxis } from 'recharts';
import { InfoPopover } from '@/components/ui/info-popover';
import { createDateTickFormatter, formatDateWithYear, niceWinRateAxis } from '@/lib/utils';
import {
  SCORE_OVER_TIME_ACTUAL_LINE,
  SCORE_OVER_TIME_EXPECTED_LINE,
  VOLUME_BAR_COLOR,
} from '@/lib/theme';
import { inactivityGapReferenceLines } from './InactivityGapReferenceLines';
import type { BookmarkTimeSeries, TimeSeriesPoint } from '@/types/position_bookmarks';

interface ScoreChartProps {
  /** One opening's rolling score series (the expanded repertoire row). */
  series: BookmarkTimeSeries;
  /** Adds grey weekly bars of games in the opening, tallest bar = bottom 20% of the canvas. */
  showVolume?: boolean;
  testId?: string;
}

/** The hidden bar axis runs [0, barMax * 5], which pins the tallest bar to the bottom 20%. */
const VOLUME_BAR_DOMAIN_FACTOR = 5;
const PERCENT_SCALE = 100;
const EXPECTED_LINE_WIDTH = 2;
const ACTUAL_LINE_WIDTH = 1.5;
const BASELINE_DASH = '4 3';
const BASELINE_OPACITY = 0.3;
const CHART_HEIGHT_CLASS = 'h-52';
const EMPTY_MESSAGE = 'Not enough games in this opening for a score line yet.';
const EXPECTED_LINE_NAME = 'Expected score from eval after opening';
const ACTUAL_LINE_NAME = 'Actual score';
// No left margin: with an auto-width value axis the plot starts right after the tick labels
// instead of behind Recharts' fixed 60px axis gutter.
const CHART_MARGIN = { top: 5, right: 5, bottom: 5, left: 0 };

function ScoreTooltipBody({ point, showVolume }: { point: TimeSeriesPoint; showVolume: boolean }) {
  return (
    <ChartTooltipBox>
      <div className="font-medium">Week of {formatDateWithYear(point.date)}</div>
      <div>
        {EXPECTED_LINE_NAME}:{' '}
        {point.expected_score === null ? (
          <span className="text-muted-foreground">not enough games with an eval</span>
        ) : (
          <>
            {Math.round(point.expected_score * PERCENT_SCALE)}%
            <span className="text-muted-foreground ml-1">
              ({point.eval_game_count} games with an eval)
            </span>
          </>
        )}
      </div>
      <div>
        {ACTUAL_LINE_NAME}: {Math.round(point.score * PERCENT_SCALE)}%
        <span className="text-muted-foreground ml-1">(past {point.game_count} games)</span>
      </div>
      {showVolume && (
        <div className="text-muted-foreground">
          {point.per_week_games} {point.per_week_games === 1 ? 'game' : 'games'} that week
        </div>
      )}
    </ChartTooltipBox>
  );
}

function ScoreChartLegend({ testId, windowSize }: { testId: string; windowSize: number }) {
  return (
    <div
      className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm"
      data-testid={`${testId}-legend`}
    >
      <span className="flex items-center gap-2" data-testid={`${testId}-legend-expected`}>
        <span
          className="h-0.5 w-4"
          style={{ backgroundColor: SCORE_OVER_TIME_EXPECTED_LINE }}
          aria-hidden="true"
        />
        {EXPECTED_LINE_NAME}
      </span>
      <span className="flex items-center gap-2 text-muted-foreground" data-testid={`${testId}-legend-actual`}>
        <span
          className="h-0.5 w-4"
          style={{ backgroundColor: SCORE_OVER_TIME_ACTUAL_LINE }}
          aria-hidden="true"
        />
        {ACTUAL_LINE_NAME}
      </span>
      <InfoPopover ariaLabel="Score over time info" testId={`${testId}-info`} side="top">
        <p>
          <strong>{EXPECTED_LINE_NAME}:</strong> the score the engine eval of the position you
          reach out of the opening predicts, averaged over your last {windowSize} games in this
          opening. The dashed line is the typical expected score for your colour.
        </p>
        <p className="mt-1">
          <strong>{ACTUAL_LINE_NAME}:</strong> your real results over the same games.
        </p>
        <p className="mt-1">
          The expected line reflects only the position reached out of the opening, so your actual
          score can sit above or below it.
        </p>
      </InfoPopover>
    </div>
  );
}

/**
 * Score over time for one opening: the rolling expected score from the opening eval (primary
 * line) and the rolling actual score (fainter line) on one ordinal axis over active weeks
 * (inactivity is cut out, >90-day breaks get a palm-tree marker) and, with showVolume, grey
 * bars of the games played in it per week. The dashed reference line is the colour baseline. The first point can be dated up to six days before
 * the filter's from-date because points are keyed by the ISO-week Monday; the ordinal axis
 * takes the series as it comes.
 */
export function ScoreChart({ series, showVolume = false, testId = 'score-chart' }: ScoreChartProps) {
  const points = series.data;
  const dates = useMemo(() => points.map((p) => p.date), [points]);
  const formatDateTick = useMemo(() => createDateTickFormatter(dates), [dates]);
  // Both lines and the baseline reference line have to sit inside the axis.
  const baseline = series.expected_score_baseline;
  const yAxis = useMemo(() => {
    const expected = points.flatMap((p) => (p.expected_score === null ? [] : [p.expected_score]));
    return niceWinRateAxis([...points.map((p) => p.score), ...expected, baseline]);
  }, [points, baseline]);
  // Math.max(..., 1) avoids a [0, 0] domain when no week has any games.
  const barMax = Math.max(1, ...points.map((p) => p.per_week_games));

  if (points.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-muted-foreground" data-testid={`${testId}-empty`}>
        {EMPTY_MESSAGE}
      </div>
    );
  }

  return (
    <div data-testid={testId}>
      <ChartContainer config={{}} className={`w-full ${CHART_HEIGHT_CLASS}`}>
        <ComposedChart data={points} margin={CHART_MARGIN}>
          <CartesianGrid vertical={false} yAxisId="value" />
          <XAxis dataKey="date" tickFormatter={formatDateTick} />
          <YAxis
            yAxisId="value"
            width="auto"
            domain={yAxis.domain}
            ticks={yAxis.ticks}
            tickFormatter={(v: number) => `${Math.round(v * PERCENT_SCALE)}%`}
          />
          {showVolume && (
            <YAxis yAxisId="bars" orientation="right" hide domain={[0, barMax * VOLUME_BAR_DOMAIN_FACTOR]} />
          )}
          <ChartTooltip
            content={({ active, payload }) => {
              const point = payload?.[0]?.payload as TimeSeriesPoint | undefined;
              if (!active || !point) return null;
              return <ScoreTooltipBody point={point} showVolume={showVolume} />;
            }}
          />
          <ReferenceLine
            yAxisId="value"
            y={baseline}
            stroke="currentColor"
            strokeOpacity={BASELINE_OPACITY}
            strokeDasharray={BASELINE_DASH}
          />
          {/* Inactivity-gap annotations (palm tree + label per >90-day gap) sit BEFORE the data
              series so they render behind it. dates is ascending (backend emits by week). */}
          {inactivityGapReferenceLines({ dates, yAxisId: 'value' })}
          {showVolume && (
            <Bar
              yAxisId="bars"
              dataKey="per_week_games"
              fill={VOLUME_BAR_COLOR}
              legendType="none"
              isAnimationActive={false}
              data-testid="score-chart-volume-bars"
            />
          )}
          {/* Actual score first so the primary expected line draws on top of it. */}
          <Line
            yAxisId="value"
            type="monotone"
            dataKey="score"
            name={ACTUAL_LINE_NAME}
            stroke={SCORE_OVER_TIME_ACTUAL_LINE}
            strokeWidth={ACTUAL_LINE_WIDTH}
            dot={false}
            isAnimationActive={false}
          />
          {/* Null expected points (fewer than 10 games with an eval) leave a gap. */}
          <Line
            yAxisId="value"
            type="monotone"
            dataKey="expected_score"
            name={EXPECTED_LINE_NAME}
            stroke={SCORE_OVER_TIME_EXPECTED_LINE}
            strokeWidth={EXPECTED_LINE_WIDTH}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ChartContainer>
      <ScoreChartLegend testId={testId} windowSize={points[0]?.window_size ?? 0} />
    </div>
  );
}
