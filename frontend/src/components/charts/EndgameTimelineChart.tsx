import { useState, useCallback } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import type { EndgameTimelineResponse } from '@/types/endgames';

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

const formatDate = (d: string) => {
  const [year, month, day] = d.split('-');
  return new Date(Number(year), Number(month) - 1, Number(day)).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
};

const formatDateWithYear = (d: string) => {
  const [year, month, day] = d.split('-');
  return new Date(Number(year), Number(month) - 1, Number(day)).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

export function EndgameTimelineChart({ data }: EndgameTimelineChartProps) {
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

  // Empty state: no overall data
  if (data.overall.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        Not enough game data for timeline charts.
      </div>
    );
  }

  // ── Chart 1: Win Rate Over Time (endgame vs non-endgame) ─────────────────

  const overallChartConfig = {
    endgame: { label: 'Endgame', color: 'oklch(0.55 0.17 145)' },
    non_endgame: { label: 'Non-endgame', color: 'oklch(0.55 0.18 260)' },
  };

  const overallData = data.overall.map((p) => ({
    date: p.date,
    endgame: p.endgame_win_rate,
    non_endgame: p.non_endgame_win_rate,
    endgame_game_count: p.endgame_game_count,
    non_endgame_game_count: p.non_endgame_game_count,
    window_size: p.window_size,
  }));

  // ── Chart 2: Win Rate by Endgame Type ────────────────────────────────────

  const typeKeys = Object.keys(data.per_type);

  // Collect all unique dates across all per-type series, sorted chronologically
  const allTypeDates = [
    ...new Set(
      typeKeys.flatMap((key) => data.per_type[key].map((p) => p.date))
    ),
  ].sort();

  // Build merged data array: one row per date with a win_rate value per type (or undefined if no data)
  const perTypeData = allTypeDates.map((date) => {
    const point: Record<string, string | number | undefined> = { date };
    for (const key of typeKeys) {
      const found = data.per_type[key].find((p) => p.date === date);
      if (found) {
        point[key] = found.win_rate;
        point[`${key}_game_count`] = found.game_count;
        point[`${key}_window_size`] = found.window_size;
      }
      // undefined produces a gap bridged by connectNulls
    }
    return point;
  });

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

  return (
    <div className="flex flex-col gap-6">
      {/* Chart 1: Win Rate Over Time */}
      <div>
        <h3 className="text-base font-semibold mb-3">Win Rate Over Time</h3>
        <ChartContainer
          config={overallChartConfig}
          className="w-full h-72"
          data-testid="timeline-overall-chart"
        >
          <LineChart data={overallData}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="date" tickFormatter={formatDate} />
            <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
            <ChartTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                return (
                  <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                    <div className="font-medium">{formatDateWithYear(label as string)}</div>
                    {payload
                      .filter((item) => item.value !== undefined)
                      .map((item) => {
                        const cfg = overallChartConfig[item.dataKey as keyof typeof overallChartConfig];
                        const gameCountKey = `${item.dataKey}_game_count`;
                        const gameCount = item.payload[gameCountKey] as number | undefined;
                        return (
                          <div key={item.dataKey} className="flex items-center gap-1.5">
                            <div
                              className="h-2 w-2 shrink-0 rounded-[2px]"
                              style={{ backgroundColor: item.color }}
                            />
                            <span>
                              {cfg?.label ?? item.dataKey}: {Math.round((item.value as number) * 100)}%
                              {gameCount !== undefined && (
                                <span className="text-muted-foreground ml-1">({gameCount}/{item.payload.window_size as number} games)</span>
                              )}
                            </span>
                          </div>
                        );
                      })}
                  </div>
                );
              }}
            />
            <ChartLegend content={<ChartLegendContent />} />
            <Line
              type="monotone"
              dataKey="endgame"
              stroke="var(--color-endgame)"
              strokeWidth={2}
              dot={false}
              connectNulls={true}
            />
            <Line
              type="monotone"
              dataKey="non_endgame"
              stroke="var(--color-non_endgame)"
              strokeWidth={2}
              dot={false}
              connectNulls={true}
            />
          </LineChart>
        </ChartContainer>
      </div>

      {/* Chart 2: Win Rate by Endgame Type (only if per_type data is present) */}
      {typeKeys.length > 0 && (
        <div>
          <h3 className="text-base font-semibold mb-3">Win Rate by Endgame Type</h3>
          <ChartContainer
            config={perTypeChartConfig}
            className="w-full h-72"
            data-testid="timeline-per-type-chart"
          >
            <LineChart data={perTypeData}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="date" tickFormatter={formatDate} />
              <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
              <ChartTooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null;
                  return (
                    <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                      <div className="font-medium">{formatDateWithYear(label as string)}</div>
                      {payload
                        .filter((item) => item.value !== undefined)
                        .map((item) => {
                          const cfg = perTypeChartConfig[item.dataKey as string];
                          const gameCount = item.payload[`${item.dataKey}_game_count`] as number | undefined;
                          const windowSize = item.payload[`${item.dataKey}_window_size`] as number | undefined;
                          return (
                            <div key={item.dataKey} className="flex items-center gap-1.5">
                              <div
                                className="h-2 w-2 shrink-0 rounded-[2px]"
                                style={{ backgroundColor: item.color }}
                              />
                              <span>
                                {cfg?.label ?? item.dataKey}: {Math.round((item.value as number) * 100)}%
                                {gameCount !== undefined && windowSize !== undefined && (
                                  <span className="text-muted-foreground ml-1">({gameCount}/{windowSize} games)</span>
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
              {typeKeys.map((key) => (
                <Line
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
            </LineChart>
          </ChartContainer>
        </div>
      )}
    </div>
  );
}
