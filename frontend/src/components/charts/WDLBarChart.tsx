import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';

interface WDLStats {
  wins: number;
  draws: number;
  losses: number;
  total: number;
}

interface WDLBarChartProps {
  bookmarks: PositionBookmarkResponse[];
  wdlStatsMap: Record<number, WDLStats>;
}

const chartConfig = {
  win_pct: { label: 'Wins', color: 'oklch(0.55 0.18 145)' },
  draw_pct: { label: 'Draws', color: 'oklch(0.65 0.01 260)' },
  loss_pct: { label: 'Losses', color: 'oklch(0.55 0.2 25)' },
  game_count: { label: 'Games', color: 'transparent' },
};

export function WDLBarChart({ bookmarks, wdlStatsMap }: WDLBarChartProps) {
  const data = bookmarks
    .filter((b) => wdlStatsMap[b.id] && wdlStatsMap[b.id].total > 0)
    .map((b) => {
      const s = wdlStatsMap[b.id];
      const t = s.total;
      const colorPrefix = b.color === 'white' ? '● ' : b.color === 'black' ? '○ ' : '';
      return {
        label: colorPrefix + b.label,
        color: b.color,
        win_pct: t > 0 ? (s.wins / t) * 100 : 0,
        draw_pct: t > 0 ? (s.draws / t) * 100 : 0,
        loss_pct: t > 0 ? (s.losses / t) * 100 : 0,
        wins: s.wins,
        draws: s.draws,
        losses: s.losses,
        total: t,
        game_count: t,
      };
    })
    .sort((a, b) => b.total - a.total);

  if (data.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        No stats available for saved positions yet.
      </div>
    );
  }

  return (
    <ChartContainer config={chartConfig} className="w-full" style={{ height: Math.max(120, data.length * 64 + 60) }}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
        <CartesianGrid horizontal={false} />
        <YAxis
          dataKey="label"
          type="category"
          width={120}
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
        />
        <XAxis
          xAxisId="pct"
          type="number"
          domain={[0, 100]}
          ticks={[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]}
          tickFormatter={(v) => `${v}%`}
          tick={{ fontSize: 11 }}
        />
        <XAxis
          xAxisId="count"
          type="number"
          orientation="top"
          hide={true}
        />
        <ChartTooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0].payload;
            return (
              <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                <div className="font-medium">{d.label.replace(/^[○●] /, '')}</div>
                <div className="text-green-500">Wins: {d.wins} ({d.win_pct.toFixed(1)}%)</div>
                <div className="text-gray-400">Draws: {d.draws} ({d.draw_pct.toFixed(1)}%)</div>
                <div className="text-red-500">Losses: {d.losses} ({d.loss_pct.toFixed(1)}%)</div>
                <div className="text-muted-foreground pt-0.5 border-t border-border/50">Total: {d.total} games</div>
              </div>
            );
          }}
        />
        <ChartLegend content={<ChartLegendContent />} />
        <Bar xAxisId="pct" dataKey="win_pct" stackId="wdl" fill="var(--color-win_pct)" radius={[0, 0, 0, 0]} />
        <Bar xAxisId="pct" dataKey="draw_pct" stackId="wdl" fill="var(--color-draw_pct)" />
        <Bar xAxisId="pct" dataKey="loss_pct" stackId="wdl" fill="var(--color-loss_pct)" radius={[0, 0, 0, 0]} />
        <Bar
          xAxisId="count"
          dataKey="game_count"
          name="Games"
          fill="transparent"
          shape={(props: unknown) => {
            const { x, y, width, height } = props as { x: number; y: number; width: number; height: number };
            return (
              <rect x={x} y={y} width={width} height={height}
                fill="transparent" stroke="oklch(0.6 0 0)" strokeWidth={1} />
            );
          }}
        />
      </BarChart>
    </ChartContainer>
  );
}
