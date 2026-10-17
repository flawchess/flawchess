import { useState, useEffect, useMemo } from 'react';
import { ChartTooltipBox } from '@/components/ui/chart-tooltip-box';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { Bar, CartesianGrid, ComposedChart, Line, ReferenceLine, XAxis, YAxis } from 'recharts';
import { createDateTickFormatter, formatDateWithYear, niceWinRateAxis } from '@/lib/utils';
import { SCORE_OVER_TIME_LINE, VOLUME_BAR_COLOR } from '@/lib/theme';
import { inactivityGapReferenceLines } from './InactivityGapReferenceLines';
import type { BookmarkTimeSeries, TimeSeriesPoint } from '@/types/position_bookmarks';

interface ScoreChartProps {
  /** One opening's rolling score series (the expanded repertoire row). */
  series: BookmarkTimeSeries;
  /** Adds grey weekly bars of games in the opening, tallest bar = bottom 20% of the canvas. */
  showVolume?: boolean;
  testId?: string;
}

// Mirrors EndgameScoreOverTimeChart: hide the rotated Y-axis label on
// narrow screens so the chart keeps its full width.
const MOBILE_BREAKPOINT_PX = 768;

/** The hidden bar axis runs [0, barMax * 5], which pins the tallest bar to the bottom 20%. */
const VOLUME_BAR_DOMAIN_FACTOR = 5;
const EVEN_SCORE = 0.5;
const PERCENT_SCALE = 100;
const SCORE_LINE_WIDTH = 2;
const EVEN_SCORE_DASH = '4 3';
const CHART_HEIGHT_CLASS = 'h-52';
const EMPTY_MESSAGE = 'Not enough games in this opening for a score line yet.';

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    () =>
      typeof window !== 'undefined' &&
      window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}

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
  const isMobile = useIsMobile();
  const points = series.data;
  const dates = useMemo(() => points.map((p) => p.date), [points]);
  const formatDateTick = useMemo(() => createDateTickFormatter(dates), [dates]);
  // The 50% reference line has to sit inside the axis even for a one-sided series.
  const yAxis = useMemo(
    () => niceWinRateAxis([...points.map((p) => p.score), EVEN_SCORE]),
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
    <div className={isMobile ? '' : 'flex items-stretch'} data-testid={testId}>
      {!isMobile && (
        <div
          className="flex shrink-0 items-center text-sm text-muted-foreground -mr-1"
          style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
        >
          Score
        </div>
      )}
      <ChartContainer config={{}} className={`w-full ${CHART_HEIGHT_CLASS}`}>
        <ComposedChart data={points}>
          <CartesianGrid vertical={false} yAxisId="value" />
          <XAxis dataKey="date" tickFormatter={formatDateTick} />
          <YAxis
            yAxisId="value"
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
