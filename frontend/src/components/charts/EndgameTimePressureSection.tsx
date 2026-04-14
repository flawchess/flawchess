/**
 * Time Pressure vs Performance section:
 * Two-line Recharts LineChart comparing user's score (blue) vs opponents' score (red)
 * across 10 time-pressure buckets (0-10% through 90-100%), tabbed by time control.
 * Answers: "Do I crack under time pressure more than my opponents?"
 */

import { useState, useCallback } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import { InfoPopover } from '@/components/ui/info-popover';
import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY, MY_SCORE_COLOR, OPP_SCORE_COLOR } from '@/lib/theme';
import type { TimePressureChartResponse, TimePressureChartRow } from '@/types/endgames';

const chartConfig = {
  my_score: { label: 'My score', color: MY_SCORE_COLOR },
  opp_score: { label: "Opponent's score", color: OPP_SCORE_COLOR },
};

interface ChartDataPoint {
  bucket_label: string;
  my_score: number | undefined;
  opp_score: number | undefined;
  my_game_count: number;
  opp_game_count: number;
}

function buildChartData(row: TimePressureChartRow): ChartDataPoint[] {
  return row.user_series.map((userPt, i) => {
    const oppPt = row.opp_series[i];
    return {
      bucket_label: userPt.bucket_label,
      my_score: userPt.score ?? undefined,
      opp_score: oppPt?.score ?? undefined,
      my_game_count: userPt.game_count,
      opp_game_count: oppPt?.game_count ?? 0,
    };
  });
}

interface ChartForRowProps {
  row: TimePressureChartRow;
  hiddenKeys: Set<string>;
  handleLegendClick: (dataKey: string) => void;
}

function ChartForRow({ row, hiddenKeys, handleLegendClick }: ChartForRowProps) {
  const chartData = buildChartData(row);

  return (
    <ChartContainer config={chartConfig} className="w-full h-72" data-testid="time-pressure-chart">
      <LineChart data={chartData}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="bucket_label"
          tickFormatter={(v: string) => v.split('-')[0] ?? v}
        />
        <YAxis
          domain={[0, 1]}
          ticks={[0, 0.2, 0.4, 0.6, 0.8, 1.0]}
          tickFormatter={(v: number) => v.toFixed(1)}
        />
        <ChartTooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            return (
              <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                <div className="font-medium">{label as string}</div>
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
            if (cx === undefined || cy === undefined || !payload) return <></>;
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
            if (cx === undefined || cy === undefined || !payload) return <></>;
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
  );
}

interface EndgameTimePressureSectionProps {
  data: TimePressureChartResponse;
}

export function EndgameTimePressureSection({ data }: EndgameTimePressureSectionProps) {
  const [activeTab, setActiveTab] = useState<string>(
    data.rows[0]?.time_control ?? 'bullet',
  );
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

  if (data.rows.length === 0) return null;

  const sectionHeader = (
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
              <p>Only endgames that span at least 6 plies (3 moves) are included.</p>
              <p className="text-xs text-muted-foreground">Dimmed dots indicate fewer than 10 games in that bucket.</p>
            </div>
          </InfoPopover>
        </span>
      </h3>
      <p className="text-sm text-muted-foreground mt-1">
        Does your score drop faster than your opponent&apos;s as the clock winds down?
      </p>
    </div>
  );

  // Single time control — render chart directly without tabs
  if (data.rows.length === 1) {
    const row = data.rows[0]!;
    return (
      <div data-testid="time-pressure-section">
        {sectionHeader}
        <ChartForRow row={row} hiddenKeys={hiddenKeys} handleLegendClick={handleLegendClick} />
      </div>
    );
  }

  // Multiple time controls — render with tabs
  return (
    <div data-testid="time-pressure-section">
      {sectionHeader}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList variant="default" data-testid="time-pressure-tabs">
          {data.rows.map((row) => (
            <TabsTrigger
              key={row.time_control}
              value={row.time_control}
              data-testid={`tab-time-pressure-${row.time_control}`}
            >
              {row.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {data.rows.map((row) => (
          <TabsContent key={row.time_control} value={row.time_control}>
            <ChartForRow row={row} hiddenKeys={hiddenKeys} handleLegendClick={handleLegendClick} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
