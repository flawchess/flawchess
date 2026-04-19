import { useState, useCallback, useMemo, useEffect } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { ComposedChart, Bar, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import { InfoPopover } from '@/components/ui/info-popover';
import { ENDGAME_VOLUME_BAR_COLOR } from '@/lib/theme';
import { createDateTickFormatter, formatDateWithYear, niceWinRateAxis } from '@/lib/utils';
import type { EndgameTimelineResponse } from '@/types/endgames';

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

interface EndgameTimelineChartProps {
  data: EndgameTimelineResponse;
}

// Color mapping for endgame types — matches the type classification in the backend
const TYPE_COLORS: Record<string, string> = {
  rook: 'oklch(0.55 0.17 145)',
  minor_piece: 'oklch(0.60 0.16 260)',
  pawn: 'oklch(0.65 0.18 80)',
  queen: 'oklch(0.55 0.20 25)',
  mixed: 'oklch(0.60 0.14 320)',
  pawnless: 'oklch(0.55 0.12 200)',
};

// Human-readable labels for endgame types
const TYPE_LABELS: Record<string, string> = {
  rook: 'Rook',
  minor_piece: 'Minor Piece',
  pawn: 'Pawn',
  queen: 'Queen',
  mixed: 'Mixed',
  pawnless: 'Pawnless',
};

export function EndgameTimelineChart({ data }: EndgameTimelineChartProps) {
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

  // ── Win Rate by Endgame Type ──────────────────────────────────────────────

  const typeKeys = Object.keys(data.per_type);

  // Collect all unique dates across all per-type series, sorted chronologically
  const allTypeDates = useMemo(() => [
    ...new Set(
      // safe: typeKeys comes from Object.keys(data.per_type), so each key exists
      typeKeys.flatMap((key) => (data.per_type[key] ?? []).map((p) => p.date))
    ),
  ].sort(), [data.per_type, typeKeys]);

  const formatDateTick = useMemo(() => createDateTickFormatter(allTypeDates), [allTypeDates]);

  const yAxis = useMemo(() => niceWinRateAxis(
    // safe: typeKeys comes from Object.keys(data.per_type), so each key exists
    typeKeys.flatMap((key) => (data.per_type[key] ?? []).map((p) => p.win_rate))
  ), [data.per_type, typeKeys]);

  // Empty state: no overall data
  if (data.overall.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        Not enough game data for timeline charts.
      </div>
    );
  }

  // Build merged data array: one row per date with a win_rate value per type (or undefined if no data)
  const perTypeData = allTypeDates.map((date) => {
    const point: Record<string, string | number | undefined> = { date };
    for (const key of typeKeys) {
      // safe: typeKeys comes from Object.keys(data.per_type), so each key exists
      const found = (data.per_type[key] ?? []).find((p) => p.date === date);
      if (found) {
        point[key] = found.win_rate;
        point[`${key}_game_count`] = found.game_count;
        point[`${key}_per_week_game_count`] = found.per_week_game_count;
      }
      // undefined produces a gap bridged by connectNulls
    }
    return point;
  });

  // Per-row aggregate of per_week_game_count across currently-visible types.
  // Recomputes on legend toggle so hidden types are excluded from the bar.
  // Mirrors the Endgame ELO Timeline pattern (Phase 57.1).
  const perTypeBarData = perTypeData.map((row) => {
    let total = 0;
    for (const key of typeKeys) {
      if (hiddenKeys.has(key)) continue;
      const n = row[`${key}_per_week_game_count`];
      if (typeof n === 'number') total += n;
    }
    return { ...row, per_week_total_visible: total };
  });

  // Volume-bar Y-axis envelope. domain={[0, barMax * 5]} pins the tallest
  // bar to the bottom 20% of the chart canvas (Pattern 3 from 57.1-RESEARCH.md).
  // Math.max(..., 1) avoids a [0, 0] domain when no week has any games.
  const barMax = Math.max(1, ...perTypeBarData.map((r) => r.per_week_total_visible));

  // Build per-type chart config from types present in data
  const perTypeChartConfig = Object.fromEntries(
    typeKeys.map((key) => [
      key,
      {
        label: TYPE_LABELS[key] ?? key,
        color: TYPE_COLORS[key] ?? 'oklch(0.55 0.15 200)',
      },
    ])
  );

  if (typeKeys.length === 0) {
    return null;
  }

  return (
    <div>
      <div className="mb-3">
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Win Rate by Endgame Type
            <InfoPopover ariaLabel="Win Rate by Endgame Type info" testId="timeline-per-type-info" side="top">
              Rolling win rate over the last 100 games for each endgame type, sampled once per week. Early weeks with fewer than 10 games in the window are hidden. Click legend items to toggle individual series.
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Win rate trend over time, per endgame type.
        </p>
      </div>
      <div className={isMobile ? '' : 'flex items-stretch'}>
        {!isMobile && (
          <div
            className="flex items-center text-xs text-muted-foreground shrink-0 pt-35 -mr-1"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
          >
            Win Rate %
          </div>
        )}
        <ChartContainer
          config={perTypeChartConfig}
          className="w-full h-72"
          data-testid="timeline-per-type-chart"
        >
          <ComposedChart
            data={perTypeBarData}
            margin={{ top: 5, right: 10, left: isMobile ? 0 : 10, bottom: 10 }}
          >
            <CartesianGrid vertical={false} />
            <XAxis dataKey="date" tickFormatter={formatDateTick} />
            <YAxis
              yAxisId="value"
              domain={yAxis.domain}
              ticks={yAxis.ticks}
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
              width={44}
            />
          {/* Hidden right Y-axis dedicated to volume bars.
              domain={[0, barMax * 5]} pins the tallest bar to the bottom 20%
              of the chart canvas (Pattern 3 in 57.1-RESEARCH.md). */}
          <YAxis yAxisId="bars" orientation="right" hide domain={[0, barMax * 5]} />
          <ChartTooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              const perWeekTotal =
                ((payload[0]?.payload as Record<string, unknown> | undefined)?.[
                  'per_week_total_visible'
                ] as number | undefined) ?? 0;
              return (
                <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                  <div className="font-medium">{formatDateWithYear(label as string)}</div>
                  <div className="text-muted-foreground">
                    Games this week: {perWeekTotal}
                  </div>
                  {payload
                    .filter((item) => item.dataKey !== 'per_week_total_visible' && item.value !== undefined)
                    .map((item) => {
                      const cfg = perTypeChartConfig[item.dataKey as string];
                      const gameCount = item.payload[`${item.dataKey}_game_count`] as number | undefined;
                      return (
                        <div key={item.dataKey} className="flex items-center gap-1.5">
                          <div
                            className="h-2 w-2 shrink-0 rounded-[2px]"
                            style={{ backgroundColor: item.color }}
                          />
                          <span>
                            {cfg?.label ?? item.dataKey}: {Math.round((item.value as number) * 100)}%
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
          <Bar
            yAxisId="bars"
            dataKey="per_week_total_visible"
            fill={ENDGAME_VOLUME_BAR_COLOR}
            legendType="none"
            isAnimationActive={false}
            data-testid="timeline-per-type-volume-bars"
          />
          {typeKeys.map((key) => (
            <Line
              yAxisId="value"
              key={key}
              type="monotone"
              dataKey={key}
              stroke={`var(--color-${key})`}
              strokeWidth={2}
              dot={false}
              connectNulls={true}
              hide={hiddenKeys.has(key)}
            />
          ))}
          </ComposedChart>
        </ChartContainer>
      </div>
    </div>
  );
}
