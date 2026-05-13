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
import {
  ENDGAME_VOLUME_BAR_COLOR,
  SCORE_TIMELINE_FILL_ABOVE,
  SCORE_TIMELINE_FILL_BELOW,
  SCORE_TIMELINE_LINE_ENDGAME,
  SCORE_TIMELINE_LINE_NON_ENDGAME,
} from '@/lib/theme';
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

interface GradientStop {
  offset: number;  // percentage 0..100 along the gradient's x-axis
  color: string;
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

    const colorFor = (diff: number): string =>
      diff >= 0 ? SCORE_TIMELINE_FILL_ABOVE : SCORE_TIMELINE_FILL_BELOW;

    const stops: GradientStop[] = [];
    const N = data.length;
    if (N > 0) {
      // Bug 260424: initialize the starting color from the first NON-ZERO
      // diff, not `data[0]`. If the first sample rounds to `endgame === non_endgame`
      // (diff=0), `colorFor(0)` returns green. The prior sign-flip detector
      // then missed subsequent negative diffs because `0 * dB = 0` is not
      // strictly `< 0`, so the whole band stayed green even where endgame
      // trailed. Finding the first non-zero diff makes the initial color
      // match the first visible band direction.
      let currentColor = SCORE_TIMELINE_FILL_ABOVE;
      for (const p of data) {
        const d = p.endgame - p.non_endgame;
        if (d !== 0) {
          currentColor = colorFor(d);
          break;
        }
      }
      stops.push({ offset: 0, color: currentColor });
      const denom = N > 1 ? N - 1 : 1;
      for (let i = 0; i < N - 1; i++) {
        const a = data[i]!;
        const b = data[i + 1]!;
        const dA = a.endgame - a.non_endgame;
        const dB = b.endgame - b.non_endgame;
        const colorA = colorFor(dA);
        const colorB = colorFor(dB);
        // Insert an instant color flip whenever the segment endpoints fall
        // on different color sides. Using `colorA !== colorB` instead of the
        // stricter `dA * dB < 0` correctly handles the zero-endpoint case:
        // if dA=0 and dB<0 the linear t lands at 0 (start of segment),
        // producing a coincident flip-stop that switches `currentColor`
        // forward.
        if (colorA !== colorB) {
          const t = dA / (dA - dB); // in [0, 1] when colorA !== colorB
          const offsetPct = ((i + t) / denom) * 100;
          stops.push({ offset: offsetPct, color: currentColor });
          stops.push({ offset: offsetPct, color: colorB });
          currentColor = colorB;
        }
      }
      stops.push({ offset: 100, color: currentColor });
    }

    return { data, gradientStops: stops };
  }, [timeline]);

  // Volume-bar Y-axis envelope. domain={[0, barMax * 5]} pins the tallest bar
  // to the bottom 20% of the chart canvas (Pattern 3 in 57.1-RESEARCH.md).
  // Math.max(..., 1) avoids a [0, 0] domain when no week has any games.
  const barMax = Math.max(1, ...data.map((r) => r.per_week_total_games));

  if (timeline.length === 0) return null;

  const dates = data.map((p) => p.date);
  const formatDateTick = createDateTickFormatter(dates);

  return (
    <div data-testid="endgame-score-timeline-chart">
      <div className="mb-3">
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Endgame Score Gap over Time
            <InfoPopover
              ariaLabel="Endgame vs non-endgame score timeline info"
              testId="score-timeline-info"
              side="top"
            >
              <p>
                Your endgame Score and non-endgame Score over the trailing {window} games,
                sampled once per week.
              </p>
              <p className="mt-1">
                The shaded area between the lines is color-coded: green when your
                endgame Score leads your non-endgame Score, red when it trails.
              </p>
              <p className="mt-1">
                Early weeks where either side has fewer than 10 games in the
                window are hidden.
              </p>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Are your endgames a weakness or a strength, and is the gap closing?
        </p>
      </div>
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
            <CartesianGrid vertical={false} />
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
                  <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
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
                  </div>
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
  );
}
