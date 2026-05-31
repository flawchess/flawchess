import { useState, useCallback, useEffect, useMemo } from 'react';
import { BookMarked } from 'lucide-react';
import { InfoPopover } from '@/components/ui/info-popover';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import { createDateTickFormatter, formatDateWithYear, niceWinRateAxis } from '@/lib/utils';
import { inactivityGapReferenceLines } from './InactivityGapReferenceLines';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';
import type { BookmarkTimeSeries } from '@/types/position_bookmarks';

interface ScoreChartProps {
  bookmarks: PositionBookmarkResponse[];
  series: BookmarkTimeSeries[];
}

// Distinct categorical palette — easy to distinguish across lines
const CHART_COLORS = [
  'oklch(0.65 0.20 145)',   // green
  'oklch(0.60 0.22 30)',    // red-orange
  'oklch(0.65 0.20 260)',   // blue
  'oklch(0.70 0.18 80)',    // amber/gold
  'oklch(0.60 0.22 310)',   // purple
  'oklch(0.65 0.15 190)',   // teal
  'oklch(0.55 0.22 350)',   // magenta
  'oklch(0.70 0.15 110)',   // lime
];

// Mirrors EndgameScoreOverTimeChart: hide the rotated Y-axis label on
// narrow screens so the chart keeps its full width.
const MOBILE_BREAKPOINT_PX = 768;

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

export function ScoreChart({ bookmarks, series }: ScoreChartProps) {
  const isMobile = useIsMobile();
  const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());

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

  // Collect all unique dates across series, sorted chronologically
  const allDates = useMemo(() => [
    ...new Set(
      series.flatMap((s) => s.data.map((p) => p.date))
    ),
  ].sort(), [series]);

  const formatDateTick = useMemo(() => createDateTickFormatter(allDates), [allDates]);

  const yAxis = useMemo(() => niceWinRateAxis(
    series.flatMap((s) => s.data.map((p) => p.score))
  ), [series]);

  // Empty state: no series data
  if (allDates.length === 0) {
    return (
      <>
        <h3
          className="flex items-center gap-2 px-4 py-3 bg-black/20 border-b border-border/40 text-base font-semibold"
          data-testid="score-chart-header"
        >
          <BookMarked className="h-5 w-5" />
          Bookmarked Openings: Score over Time
          <InfoPopover ariaLabel="Score chart info" testId="score-chart-info" side="top">
            Shows your chess score (W + 0.5·D) / N for each saved or most played position over time. Each point is the score over your last 50 games through that position. Only data points with at least 10 games are shown to avoid noisy early values.
          </InfoPopover>
        </h3>
        <div className="p-4 text-center text-muted-foreground py-8">
          No game history available for saved positions yet.
        </div>
      </>
    );
  }

  // Build chartConfig
  const chartConfig = Object.fromEntries(
    bookmarks.map((b, i) => [
      `bkm_${b.id}`,
      { label: b.label, color: CHART_COLORS[i % CHART_COLORS.length] },
    ]),
  );

  // Build data array with score and game_count per bookmark
  const data = allDates.map((date) => {
    const point: Record<string, string | number | undefined> = { date };
    for (const s of series) {
      const found = s.data.find((p) => p.date === date);
      if (found) {
        point[`bkm_${s.bookmark_id}`] = found.score;
        point[`bkm_${s.bookmark_id}_game_count`] = found.game_count;
      }
      // undefined produces a gap in the line
    }
    return point;
  });

  return (
    <>
      <h3
        className="flex items-center gap-2 px-4 py-3 bg-black/20 border-b border-border/40 text-base font-semibold"
        data-testid="score-chart-header"
      >
        <BookMarked className="h-5 w-5" />
        Bookmarked Openings: Score over Time
        <InfoPopover ariaLabel="Score chart info" testId="score-chart-info" side="top">
          Shows your chess score (W + 0.5·D) / N for each saved or most played position over time. Each point is the score over your last 50 games through that position. Only data points with at least 10 games are shown to avoid noisy early values.
        </InfoPopover>
      </h3>
      <div className="p-4">
      <div className={isMobile ? '' : 'flex items-stretch'}>
        {!isMobile && (
          <div
            className="flex items-center text-xs text-muted-foreground shrink-0 pt-40 -mr-1"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
          >
            Score
          </div>
        )}
        <ChartContainer config={chartConfig} className="w-full h-72">
          <LineChart data={data}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="date" tickFormatter={formatDateTick} />
            <YAxis domain={yAxis.domain} ticks={yAxis.ticks} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
            {/* Inactivity-gap annotations via shared helper: Palmtree glyph + label per
                >90-day gap. Placed BEFORE the bookmark Line series so annotations
                sit behind the data in SVG z-order. allDates is pre-sorted
                (ascending) — no yAxisId (single default axis). */}
            {inactivityGapReferenceLines({ dates: allDates })}
            <ChartTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                return (
                  <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                    <div className="font-medium">{formatDateWithYear(label as string)}</div>
                    {payload
                      .filter((item) => item.value !== undefined)
                      .map((item) => {
                        // recharts 3: dataKey is DataKey<any> = string | number | function;
                        // narrow to string for use as a React key and lookup key.
                        const dataKey = typeof item.dataKey === 'string' || typeof item.dataKey === 'number'
                          ? String(item.dataKey)
                          : 'value';
                        const cfg = chartConfig[dataKey];
                        const gameCount = item.payload[`${dataKey}_game_count`] as number | undefined;
                        return (
                          <div key={dataKey} className="flex items-center gap-1.5">
                            <div
                              className="h-2 w-2 shrink-0 rounded-[2px]"
                              style={{ backgroundColor: item.color }}
                            />
                            <span>
                              {cfg?.label ?? dataKey}: {Math.round((item.value as number) * 100)}%
                              {gameCount !== undefined && (
                                <span className="text-muted-foreground ml-1">(past {gameCount} games)</span>
                              )}
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
            {bookmarks.map((b) => {
              const key = `bkm_${b.id}`;
              return (
                <Line
                  key={b.id}
                  type="monotone"
                  dataKey={key}
                  stroke={`var(--color-${key})`}
                  strokeWidth={2}
                  dot={false}
                  connectNulls={true}
                  hide={hiddenKeys.has(key)}
                />
              );
            })}
          </LineChart>
        </ChartContainer>
      </div>
      </div>
    </>
  );
}
