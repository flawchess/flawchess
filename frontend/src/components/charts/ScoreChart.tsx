import { useMemo } from 'react';
import { ChartTooltipBox } from '@/components/ui/chart-tooltip-box';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { Bar, CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine, XAxis, YAxis } from 'recharts';
import { createDateTickFormatter, formatDateWithYear, niceWinRateAxis } from '@/lib/utils';
import { SCORE_VERDICT_BAND } from '@/lib/openingVerdict';
import { SCORE_OVER_TIME_LINE, TYPICAL_BAND_FILL, VOLUME_BAR_COLOR } from '@/lib/theme';
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
const EVEN_SCORE = 0.5;
const PERCENT_SCALE = 100;
const SCORE_LINE_WIDTH = 2;
const EVEN_SCORE_DASH = '4 3';
const CHART_HEIGHT_CLASS = 'h-52';
const EMPTY_MESSAGE = 'Not enough games in this opening for a score line yet.';
// The grey typical band (the same 45-55% the score verdict bar uses), labelled like the
// Clock Gap at Endgame Entry chart, at the text-sm floor (14px).
const TYPICAL_LOW = EVEN_SCORE - SCORE_VERDICT_BAND;
const TYPICAL_HIGH = EVEN_SCORE + SCORE_VERDICT_BAND;
const TYPICAL_LABEL = 'typical';
const TYPICAL_LABEL_FONT_SIZE = 14;
// No left margin: with an auto-width value axis the plot starts right after the tick labels
// instead of behind Recharts' fixed 60px axis gutter.
const CHART_MARGIN = { top: 5, right: 5, bottom: 5, left: 0 };

function ScoreTooltipBody({ point, showVolume }: { point: TimeSeriesPoint; showVolume: boolean }) {
  return (
    <ChartTooltipBox>
      <div className="font-medium">Week of {formatDateWithYear(point.date)}</div>
      <div>
        Score: {Math.round(point.score * PERCENT_SCALE)}%
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

/**
 * Score over time for one opening: the rolling score line on an ordinal axis over active weeks
 * (inactivity is cut out, >90-day breaks get a palm-tree marker) and, with showVolume, grey
 * bars of the games played in it per week. The first point can be dated up to six days before
 * the filter's from-date because points are keyed by the ISO-week Monday; the ordinal axis
 * takes the series as it comes.
 */
export function ScoreChart({ series, showVolume = false, testId = 'score-chart' }: ScoreChartProps) {
  const points = series.data;
  const dates = useMemo(() => points.map((p) => p.date), [points]);
  const formatDateTick = useMemo(() => createDateTickFormatter(dates), [dates]);
  // The 50% reference line and the typical band have to sit inside the axis even for a
  // one-sided series.
  const yAxis = useMemo(
    () => niceWinRateAxis([...points.map((p) => p.score), TYPICAL_LOW, TYPICAL_HIGH]),
    [points],
  );
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
          <ReferenceArea
            yAxisId="value"
            y1={TYPICAL_LOW}
            y2={TYPICAL_HIGH}
            fill={TYPICAL_BAND_FILL}
            ifOverflow="visible"
            label={{
              value: TYPICAL_LABEL,
              position: 'insideTopLeft',
              style: { fontSize: TYPICAL_LABEL_FONT_SIZE, fill: 'var(--muted-foreground)' },
            }}
          />
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
            y={EVEN_SCORE}
            stroke="currentColor"
            strokeOpacity={0.3}
            strokeDasharray={EVEN_SCORE_DASH}
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
          <Line
            yAxisId="value"
            type="monotone"
            dataKey="score"
            stroke={SCORE_OVER_TIME_LINE}
            strokeWidth={SCORE_LINE_WIDTH}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ChartContainer>
    </div>
  );
}
