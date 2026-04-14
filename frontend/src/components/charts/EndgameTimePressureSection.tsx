/**
 * Time Pressure vs Performance section:
 * Two-line Recharts LineChart comparing user's score (blue) vs opponents' score (red)
 * across 10 time-pressure buckets (0-10% through 90-100%), aggregated across all time controls.
 * Answers: "Do I crack under time pressure more than my opponents?"
 */

import { useState, useCallback, useEffect } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import { InfoPopover } from '@/components/ui/info-popover';
import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY, MY_SCORE_COLOR, OPP_SCORE_COLOR } from '@/lib/theme';
import type { TimePressureChartResponse, TimePressureBucketPoint } from '@/types/endgames';

const chartConfig = {
  my_score: { label: 'My score', color: MY_SCORE_COLOR },
  opp_score: { label: "Opponent's score", color: OPP_SCORE_COLOR },
};

const Y_AXIS_DOMAIN: [number, number] = [0.2, 0.8];
const Y_AXIS_TICKS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8];
const X_AXIS_DOMAIN: [number, number] = [0, 100];
const X_AXIS_TICKS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
const BUCKET_WIDTH = 10;
const MOBILE_BREAKPOINT_PX = 768;

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}

interface ChartDataPoint {
  bucket_center: number; // bucket center on the 0-100 axis (5, 15, ..., 95)
  bucket_label: string; // "0-10%" ... "90-100%" for tooltip
  // Recharts with type="number" XAxis computes NaN scales when series values are
  // `undefined`; null renders cleanly with connectNulls=true.
  my_score: number | null;
  opp_score: number | null;
  my_game_count: number;
  opp_game_count: number;
}

/**
 * Aggregate per-time-control series into a single weighted-average series per bucket.
 * Weighted by game_count so buckets with more data dominate, consistent with what a
 * pooled backend query would return.
 */
function aggregateSeries(
  rowsSeries: TimePressureBucketPoint[][],
): { score: number | undefined; game_count: number; bucket_label: string }[] {
  const firstSeries = rowsSeries[0];
  if (!firstSeries) return [];
  return firstSeries.map((_, bucketIdx) => {
    let scoreSum = 0;
    let countSum = 0;
    let scoredCount = 0;
    let bucketLabel = '';
    for (const series of rowsSeries) {
      const pt = series[bucketIdx];
      if (!pt) continue;
      bucketLabel = pt.bucket_label;
      countSum += pt.game_count;
      if (pt.score !== null && pt.game_count > 0) {
        scoreSum += pt.score * pt.game_count;
        scoredCount += pt.game_count;
      }
    }
    return {
      bucket_label: bucketLabel,
      score: scoredCount > 0 ? scoreSum / scoredCount : undefined,
      game_count: countSum,
    };
  });
}

function buildChartData(data: TimePressureChartResponse): ChartDataPoint[] {
  const userAgg = aggregateSeries(data.rows.map((r) => r.user_series));
  const oppAgg = aggregateSeries(data.rows.map((r) => r.opp_series));
  return userAgg.map((userPt, i) => {
    const oppPt = oppAgg[i];
    // Place each data point at the center of its bucket on the 0-100 axis, so
    // ticks (0%, 10%, ..., 100%) sit at bucket boundaries and points fall between.
    const bucket_center = i * BUCKET_WIDTH + BUCKET_WIDTH / 2;
    return {
      bucket_center,
      bucket_label: userPt.bucket_label,
      my_score: userPt.score ?? null,
      opp_score: oppPt?.score ?? null,
      my_game_count: userPt.game_count,
      opp_game_count: oppPt?.game_count ?? 0,
    };
  });
}

interface EndgameTimePressureSectionProps {
  data: TimePressureChartResponse;
}

export function EndgameTimePressureSection({ data }: EndgameTimePressureSectionProps) {
  const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());
  const isMobile = useIsMobile();

  const handleLegendClick = useCallback((dataKey: string) => {
    setHiddenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(dataKey)) {
        next.delete(dataKey);
      } else {
        next.add(dataKey);
      }
      return next;
    });
  }, []);

  if (data.rows.length === 0) return null;

  const chartData = buildChartData(data);

  return (
    <div data-testid="time-pressure-section">
      <div className="mb-3">
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Time Pressure vs Performance
            <InfoPopover ariaLabel="Time pressure chart info" testId="time-pressure-chart-info" side="top">
              <div className="space-y-2">
                <p>Compares how you perform under time pressure vs how your opponents perform.</p>
                <p><strong>Blue line (My score):</strong> your average score when <em>you</em> had this much time remaining at endgame entry.</p>
                <p><strong>Red line (Opponent&apos;s score):</strong> average score of your opponents when <em>they</em> had this much time remaining.</p>
                <p>Where the lines diverge reveals who handles time pressure better. If your line drops faster as time decreases, you crack under pressure more than your opponents.</p>
                <p>Includes every game that reached an endgame phase (total of at least 3 full moves / 6 half-moves spent in the endgame, summed across all endgame types), aggregated across all time controls. Each game contributes one data point based on the clocks at the first endgame position reached. Use the filter panel to narrow by time control.</p>
                <p className="text-xs text-muted-foreground">Dimmed dots indicate fewer than 10 games in that bucket.</p>
              </div>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Can you handle time pressure better or worse than your opponents?
        </p>
      </div>
      <div className={isMobile ? '' : 'flex items-stretch gap-2'}>
        {/* Desktop: vertical Y-axis label rendered as plain HTML (SVG `label` with
            position='insideLeft' + angle produced NaN plot-area rects and chart width 0). */}
        {!isMobile && (
          <div
            className="flex items-center text-xs text-muted-foreground shrink-0"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
          >
            Avg Score
          </div>
        )}
        <ChartContainer config={chartConfig} className="w-full h-72" data-testid="time-pressure-chart">
          <LineChart
            data={chartData}
            margin={{ top: 5, right: 10, left: isMobile ? 0 : 10, bottom: 10 }}
          >
            <CartesianGrid vertical={false} horizontal={true} />
            <XAxis
              dataKey="bucket_center"
              type="number"
              scale="linear"
              domain={X_AXIS_DOMAIN}
              ticks={X_AXIS_TICKS}
              tickFormatter={(v: number) => `${v}%`}
              allowDecimals={false}
            />
            <YAxis
              domain={Y_AXIS_DOMAIN}
              ticks={Y_AXIS_TICKS}
              tickFormatter={(v: number) => v.toFixed(1)}
              width={isMobile ? 32 : 40}
            />
          <ChartTooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              // Use the bucket_label from the row payload rather than Recharts' numeric `label`,
              // since the x-axis is now numeric (0-100) but we still want "0-10%"..."90-100%" in the tooltip.
              const bucketLabel = (payload[0]?.payload as ChartDataPoint | undefined)?.bucket_label ?? '';
              return (
                <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                  <div className="font-medium">{bucketLabel}</div>
                  {payload
                    .filter((item) => item.value !== undefined)
                    .map((item) => {
                      const cfg = chartConfig[item.dataKey as keyof typeof chartConfig];
                      const isMyScore = item.dataKey === 'my_score';
                      const gameCount = isMyScore
                        ? (item.payload as ChartDataPoint).my_game_count
                        : (item.payload as ChartDataPoint).opp_game_count;
                      return (
                        <div key={item.dataKey} className="flex items-center gap-1.5">
                          <div
                            className="h-2 w-2 shrink-0 rounded-[2px]"
                            style={{ backgroundColor: item.color }}
                          />
                          <span>
                            {cfg?.label ?? item.dataKey}: {(item.value as number).toFixed(2)}
                            <span className="text-muted-foreground ml-1">
                              ({gameCount} games)
                            </span>
                          </span>
                        </div>
                      );
                    })}
                </div>
              );
            }}
          />
          <ChartLegend
            content={<ChartLegendContent hiddenKeys={hiddenKeys} onClickItem={handleLegendClick} />}
          />
          <Line
            type="monotone"
            dataKey="my_score"
            stroke="var(--color-my_score)"
            strokeWidth={2}
            connectNulls={true}
            hide={hiddenKeys.has('my_score')}
            dot={(props: { cx?: number; cy?: number; payload?: Record<string, unknown> }) => {
              const { cx, cy, payload } = props;
              if (!payload || !Number.isFinite(cx) || !Number.isFinite(cy)) {
                // Return a group with the key Recharts expects on every child of Line.
                return <g key={`nodot-${String(payload?.bucket_label ?? cx)}`} />;
              }
              const gameCount = (payload.my_game_count as number) ?? 0;
              const isDim = gameCount < MIN_GAMES_FOR_RELIABLE_STATS;
              return (
                <circle
                  key={`my-dot-${payload.bucket_label as string}`}
                  cx={cx}
                  cy={cy}
                  r={4}
                  fill={MY_SCORE_COLOR}
                  opacity={isDim ? UNRELIABLE_OPACITY : 1}
                />
              );
            }}
          />
          <Line
            type="monotone"
            dataKey="opp_score"
            stroke="var(--color-opp_score)"
            strokeWidth={2}
            connectNulls={true}
            hide={hiddenKeys.has('opp_score')}
            dot={(props: { cx?: number; cy?: number; payload?: Record<string, unknown> }) => {
              const { cx, cy, payload } = props;
              if (!payload || !Number.isFinite(cx) || !Number.isFinite(cy)) {
                // Return a group with the key Recharts expects on every child of Line.
                return <g key={`nodot-${String(payload?.bucket_label ?? cx)}`} />;
              }
              const gameCount = (payload.opp_game_count as number) ?? 0;
              const isDim = gameCount < MIN_GAMES_FOR_RELIABLE_STATS;
              return (
                <circle
                  key={`opp-dot-${payload.bucket_label as string}`}
                  cx={cx}
                  cy={cy}
                  r={4}
                  fill={OPP_SCORE_COLOR}
                  opacity={isDim ? UNRELIABLE_OPACITY : 1}
                />
              );
            }}
          />
          </LineChart>
        </ChartContainer>
      </div>
      <p className="text-xs text-muted-foreground text-center mt-2">
        % of base time remaining at endgame entry
      </p>
    </div>
  );
}
