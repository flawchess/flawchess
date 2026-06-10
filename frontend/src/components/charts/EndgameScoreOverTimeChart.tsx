/**
 * EndgameScoreOverTimeChart: two-line absolute Score timeline (endgame +
 * non-endgame) with a sign-aware shaded band in between.
 *
 * Extracted from EndgamePerformanceSection.tsx in Phase 85 (D-09) so the
 * legacy section file can be deleted cleanly in Plan 04 without entangling
 * this unrelated timeline chart.
 */

import { useEffect, useId, useMemo, useState } from 'react';
import { Area, Bar, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { InfoPopover } from '@/components/ui/info-popover';
import { CardHeader } from '@/components/ui/card';
import { ChartTooltipBox } from '@/components/ui/chart-tooltip-box';
import {
  ENDGAME_VOLUME_BAR_COLOR,
  SCORE_TIMELINE_FILL_ABOVE,
  SCORE_TIMELINE_FILL_BELOW,
  SCORE_TIMELINE_LINE_ENDGAME,
  SCORE_TIMELINE_LINE_NON_ENDGAME,
} from '@/lib/theme';
import { signedBandGradient, type GradientStop } from '@/lib/signedBandGradient';
import { inactivityGapReferenceLines } from './InactivityGapReferenceLines';
import { createDateTickFormatter, formatDateWithYear } from '@/lib/utils';
import type { ScoreGapTimelinePoint } from '@/types/endgames';

// Endgame vs Non-Endgame Score timeline (Phase 68). Absolute scores on a
// clamped Y-axis: typical score values sit in 20-80%; 0-100 wastes vertical
// space and flattens the lines. Matches the Time Pressure vs Performance
// chart's Y_AXIS_DOMAIN treatment.
const SCORE_TIMELINE_Y_DOMAIN: [number, number] = [20, 80];
const SCORE_TIMELINE_Y_TICKS = [20, 30, 40, 50, 60, 70, 80];
const MOBILE_BREAKPOINT_PX = 768;

// Class used to identify the band <Area> element in tests and DOM inspection.
// See the diagnosis comment on EndgameScoreOverTimeChart for why we do not
// use a `<g data-testid>` wrapper.
export const SCORE_BAND_CLASS = 'score-band';

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined'
      && window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}

export interface EndgameScoreOverTimeChartProps {
  timeline: ScoreGapTimelinePoint[];
  window: number;
}

interface ScoreOverTimeChartPoint {
  date: string;
  endgame: number;       // 0-100 whole-number percentage
  non_endgame: number;   // 0-100 whole-number percentage
  endgame_game_count: number;
  non_endgame_game_count: number;
  per_week_total_games: number;
  // Ranged tuple [low, high] — Recharts renders an <Area> as a band between
  // the two values. Always populated so the Area path is continuous; color
  // switching is handled by the horizontal linearGradient fill.
  band: [number, number];
}

/**
 * Phase 68: two-line absolute Score timeline (endgame + non-endgame) with a
 * sign-aware shaded band in between.
 *
 * Shading strategy (Phase 68 UAT fix): a single <Area> renders the band
 * between min(endgame, non_endgame) and max(endgame, non_endgame) and is
 * filled by a horizontal <linearGradient> whose stop offsets are computed at
 * each crossover x-position. At every sign flip two stops with identical
 * offset but different stopColor produce an instant color switch, so the
 * green and red regions meet exactly at the crossover with no gap. This
 * replaces an earlier two-Area approach that used null masking plus an ±1 pp
 * epsilon — that combination left a visible unshaded band across every
 * crossover, which was the bug this wiring fixes.
 *
 * UAT diagnosis (Phase 68, 260424-pc6): the earlier `<g data-testid=...>`
 * wrapper around each `<Area>` silently broke rendering. Recharts'
 * `findAllByType` in `generateCategoricalChart` only inspects DIRECT
 * children's `type.displayName`; a plain `<g>` wrapper hides the `<Area>`
 * from that scan, so the area never registers with the chart axes and no
 * `<path>` is emitted. The `<Area>` must remain a direct child of
 * ComposedChart — tests now query by the `SCORE_BAND_CLASS` className.
 */
export function EndgameScoreOverTimeChart({ timeline, window }: EndgameScoreOverTimeChartProps) {
  const isMobile = useIsMobile();
  const rawId = useId();
  const gradientId = `score-gap-gradient-${rawId.replace(/[^a-zA-Z0-9]/g, '_')}`;

  const { data, gradientStops } = useMemo(() => {
    const data: ScoreOverTimeChartPoint[] = timeline.map((p) => {
      // Plan 01 guarantees endgame_score / non_endgame_score are present
      // on every point — no fallback needed.
      const endgame = Math.round(p.endgame_score * 100);
      const non_endgame = Math.round(p.non_endgame_score * 100);
      return {
        date: p.date,
        endgame,
        non_endgame,
        endgame_game_count: p.endgame_game_count,
        non_endgame_game_count: p.non_endgame_game_count,
        per_week_total_games: p.per_week_total_games,
        band: [Math.min(endgame, non_endgame), Math.max(endgame, non_endgame)] as [number, number],
      };
    });

    // Phase 87.6: extracted into shared helper signedBandGradient.
    // Verbatim algorithm from EndgameScoreOverTimeChart.tsx:121-163 before extraction.
    // GradientStop type is now imported from the helper module.
    const rows: Array<{ x: number; sign: 1 | -1 | 0 }> = data.map((p, i) => ({
      x: i,
      sign: Math.sign(p.endgame - p.non_endgame) as 1 | -1 | 0,
    }));
    const stops: GradientStop[] = signedBandGradient(
      rows,
      [0, Math.max(0, data.length - 1)],
      { positive: SCORE_TIMELINE_FILL_ABOVE, negative: SCORE_TIMELINE_FILL_BELOW },
    );

    return { data, gradientStops: stops };
  }, [timeline]);

  // Volume-bar Y-axis envelope. domain={[0, barMax * 5]} pins the tallest bar
  // to the bottom 20% of the chart canvas (Pattern 3 in 57.1-RESEARCH.md).
  // Math.max(..., 1) avoids a [0, 0] domain when no week has any games.
  const barMax = Math.max(1, ...data.map((r) => r.per_week_total_games));

  // dates and inactivityGaps are derived from `data` (itself from `timeline`),
  // so they are placed BEFORE the early-return to satisfy the rules-of-hooks
  // constraint (no hooks after a conditional return).
  const dates = data.map((p) => p.date);
  const formatDateTick = createDateTickFormatter(dates);

  if (timeline.length === 0) return null;

  return (
    <div data-testid="endgame-score-timeline-chart">
      <CardHeader data-testid="endgame-score-timeline-header">
        Endgame Score Gap over Time
        <InfoPopover
          ariaLabel="Endgame vs Non-Endgame Score timeline info"
          testId="score-timeline-info"
          side="top"
        >
          <p>
            <strong>Endgame Score Gap over Time:</strong> how your Endgame
            Score compares to your Non-Endgame Score over time, so you can
            see whether the gap is closing or widening.
          </p>
          <p className="mt-1">
            The shaded area between the lines is color-coded: green when
            your Endgame Score leads your Non-Endgame Score, red when it
            trails.
          </p>
        </InfoPopover>
      </CardHeader>
      <div className="p-4">
      <p className="text-sm text-muted-foreground mb-3">
        Are your endgames a weakness or a strength, and is the gap closing?
      </p>
      <div className={isMobile ? '' : 'flex items-stretch'}>
        {!isMobile && (
          <div
            className="flex items-center text-xs text-muted-foreground shrink-0 pt-33 -mr-1"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
          >
            Score
          </div>
        )}
        <ChartContainer
          config={{}}
          className="w-full h-72"
          data-testid="endgame-score-timeline-chart-container"
        >
          <ComposedChart
            data={data}
            margin={{ top: 5, right: 10, left: isMobile ? 0 : 10, bottom: 10 }}
          >
            {/* recharts 3: CartesianGrid must bind to the named primary YAxis via yAxisId */}
            <CartesianGrid vertical={false} yAxisId="value" />
            <XAxis dataKey="date" tickFormatter={formatDateTick} />
            <YAxis
              yAxisId="value"
              domain={SCORE_TIMELINE_Y_DOMAIN}
              ticks={SCORE_TIMELINE_Y_TICKS}
              allowDataOverflow={false}
              tickFormatter={(v: number) => `${v}%`}
              width={44}
            />
            {/* Hidden right Y-axis dedicated to volume bars.
                domain={[0, barMax * 5]} pins the tallest bar to the bottom
                20% of the chart canvas (Pattern 3 in 57.1-RESEARCH.md). */}
            <YAxis yAxisId="bars" orientation="right" hide domain={[0, barMax * 5]} />
            <ChartTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const point = payload.find(
                  (p) => (p.payload as ScoreOverTimeChartPoint | undefined)?.date !== undefined,
                )?.payload as ScoreOverTimeChartPoint | undefined;
                if (!point) return null;
                const gap = point.endgame - point.non_endgame;
                const gapSign = gap > 0 ? '+' : '';
                return (
                  <ChartTooltipBox>
                    <div className="font-medium">
                      Week of {formatDateWithYear(label as string)}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div
                        className="h-2 w-2 shrink-0 rounded-[2px]"
                        style={{ backgroundColor: SCORE_TIMELINE_LINE_ENDGAME }}
                      />
                      <span>
                        Endgame: {point.endgame}%
                        <span className="text-muted-foreground ml-1">
                          (n={point.endgame_game_count})
                        </span>
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div
                        className="h-2 w-2 shrink-0 rounded-[2px]"
                        style={{ backgroundColor: SCORE_TIMELINE_LINE_NON_ENDGAME }}
                      />
                      <span>
                        Non-endgame: {point.non_endgame}%
                        <span className="text-muted-foreground ml-1">
                          (n={point.non_endgame_game_count})
                        </span>
                      </span>
                    </div>
                    <div className="text-muted-foreground">
                      Gap: {gapSign}{gap}%
                    </div>
                    <div className="text-muted-foreground">
                      Games this week: {point.per_week_total_games}
                    </div>
                  </ChartTooltipBox>
                );
              }}
            />
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
                {gradientStops.map((s, i) => (
                  <stop key={i} offset={`${s.offset}%`} stopColor={s.color} />
                ))}
              </linearGradient>
            </defs>
            {/* Inactivity-gap annotations via shared helper: one ReferenceLine + Palmtree
                glyph + label per gap that exceeds INACTIVITY_GAP_THRESHOLD_DAYS.
                Placed BEFORE <Bar> so annotations sit behind the data series in SVG
                z-order. x must exactly match a value from the dates array
                (Recharts Pitfall 1 from 88.3-01-PLAN.md). */}
            {inactivityGapReferenceLines({ dates, yAxisId: 'value' })}
            <Bar
              yAxisId="bars"
              dataKey="per_week_total_games"
              fill={ENDGAME_VOLUME_BAR_COLOR}
              legendType="none"
              isAnimationActive={false}
              data-testid="endgame-score-timeline-volume-bars"
            />
            <Area
              yAxisId="value"
              type="monotone"
              dataKey="band"
              className={SCORE_BAND_CLASS}
              fill={`url(#${gradientId})`}
              stroke="none"
              isAnimationActive={false}
              connectNulls={false}
              legendType="none"
            />
            <Line
              yAxisId="value"
              type="monotone"
              dataKey="endgame"
              stroke={SCORE_TIMELINE_LINE_ENDGAME}
              strokeWidth={2}
              strokeDasharray="6 3"
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Line
              yAxisId="value"
              type="monotone"
              dataKey="non_endgame"
              stroke={SCORE_TIMELINE_LINE_NON_ENDGAME}
              strokeWidth={2}
              strokeDasharray="1 4"
              strokeLinecap="round"
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ChartContainer>
      </div>
      {/* Custom legend rendered outside the chart so we can attach per-item
          data-testid attributes. Recharts' default <Legend> doesn't expose
          hooks for that without a custom `content` render prop, and this
          approach avoids another indirection. */}
      <div
        className="flex flex-wrap items-center justify-center gap-4 mt-1 text-xs text-muted-foreground"
        data-testid="endgame-score-timeline-legend"
      >
        <span className="inline-flex items-center gap-1.5" data-testid="chart-legend-endgame">
          <span
            className="inline-block h-2 w-2 rounded-[2px]"
            style={{ backgroundColor: SCORE_TIMELINE_LINE_ENDGAME }}
            aria-hidden="true"
          />
          Endgame
        </span>
        <span className="inline-flex items-center gap-1.5" data-testid="chart-legend-non-endgame">
          <span
            className="inline-block h-2 w-2 rounded-[2px]"
            style={{ backgroundColor: SCORE_TIMELINE_LINE_NON_ENDGAME }}
            aria-hidden="true"
          />
          Non-endgame
        </span>
      </div>
      <p className="text-xs text-muted-foreground text-center mt-1">
        Week (rolling average of the last {window} games per side)
      </p>
      </div>
    </div>
  );
}
