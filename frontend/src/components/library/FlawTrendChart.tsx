import { useId } from 'react';
import { Area, AreaChart, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { SEV_BLUNDER } from '@/lib/theme';
import type { FlawTrendPoint } from '@/types/library';

// ─── Props ───────────────────────────────────────────────────────────────────

interface FlawTrendChartProps {
  /** Rolling-window blunders/game datapoints from FlawStatsResponse.trend. */
  trend: FlawTrendPoint[];
  /** The rolling window size (games per window), e.g. 20. Shown in subheading. */
  windowSize: number;
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Zone 2: blunders/game rolling trend (UI-SPEC §Zone 2).
 *
 * Uses the existing Recharts AreaChart pattern (EndgameScoreOverTimeChart):
 * - SEV_BLUNDER stroke (width 2.5) + linearGradient fill 32%→0 opacity.
 * - No CartesianGrid (charcoal surface).
 * - isAnimationActive={false}.
 * - X-axis tick fill via var(--color-text-muted).
 *
 * When trend has fewer than 2 datapoints, renders the text fallback
 * ("Not enough games to show a trend") instead of the chart.
 */
export function FlawTrendChart({ trend, windowSize }: FlawTrendChartProps) {
  const rawId = useId();
  // Sanitize for use as an SVG id attribute (no colons or special chars).
  const gradientId = `blunder-gradient-${rawId.replace(/[^a-zA-Z0-9]/g, '_')}`;

  return (
    <div
      className="rounded border border-border p-4 mt-4"
      style={{ background: 'var(--color-charcoal)' }}
      data-testid="flaw-trend-chart"
      aria-label="Blunders per game trend chart"
    >
      {/* Chart heading row */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold" style={{ color: SEV_BLUNDER }}>
          Blunders / game
        </span>
        <span className="text-sm text-muted-foreground">
          last {windowSize} games · rolling window
        </span>
      </div>

      {/* Empty / insufficient-data state */}
      {trend.length < 2 ? (
        <p className="text-sm text-muted-foreground text-center py-4">
          Not enough games to show a trend
        </p>
      ) : (
        <ChartContainer
          config={{}}
          className="w-full h-48"
        >
          <AreaChart data={trend} margin={{ top: 5, right: 10, left: 0, bottom: 10 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={SEV_BLUNDER} stopOpacity={0.32} />
                <stop offset="100%" stopColor={SEV_BLUNDER} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis hide />
            <ChartTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const point = payload[0]?.payload as FlawTrendPoint | undefined;
                if (!point) return null;
                return (
                  <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-sm shadow-xl space-y-1">
                    <div className="font-bold text-muted-foreground">{label as string}</div>
                    <div style={{ color: SEV_BLUNDER }}>
                      {point.rate.toFixed(2)} blunders / game
                    </div>
                    <div className="text-muted-foreground text-sm">
                      {point.game_count} games in window
                    </div>
                  </div>
                );
              }}
            />
            <Area
              type="monotone"
              dataKey="rate"
              stroke={SEV_BLUNDER}
              strokeWidth={2.5}
              fill={`url(#${gradientId})`}
              dot={{ r: 3, fill: SEV_BLUNDER, strokeWidth: 0 }}
              activeDot={{ r: 4, fill: SEV_BLUNDER, strokeWidth: 0 }}
              isAnimationActive={false}
            />
          </AreaChart>
        </ChartContainer>
      )}
    </div>
  );
}
