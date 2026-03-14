import { useState, useCallback } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import type { BookmarkResponse } from '@/types/bookmarks';

interface WDLStats {
  wins: number;
  draws: number;
  losses: number;
  total: number;
}

interface WDLBarChartProps {
  bookmarks: BookmarkResponse[];
  wdlStatsMap: Record<number, WDLStats>;
}

const chartConfig = {
  win_pct: { label: 'Wins', color: 'oklch(0.55 0.18 145)' },
  draw_pct: { label: 'Draws', color: 'oklch(0.65 0.01 260)' },
  loss_pct: { label: 'Losses', color: 'oklch(0.55 0.2 25)' },
};

export function WDLBarChart({ bookmarks, wdlStatsMap }: WDLBarChartProps) {
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

  const data = bookmarks
    .filter((b) => wdlStatsMap[b.id] && wdlStatsMap[b.id].total > 0)
    .map((b) => {
      const s = wdlStatsMap[b.id];
      const t = s.total;
      return {
        label: b.label,
        win_pct: t > 0 ? (s.wins / t) * 100 : 0,
        draw_pct: t > 0 ? (s.draws / t) * 100 : 0,
        loss_pct: t > 0 ? (s.losses / t) * 100 : 0,
        wins: s.wins,
        draws: s.draws,
        losses: s.losses,
        total: t,
      };
    });

  if (data.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        No stats available for saved positions yet.
      </div>
    );
  }

  return (
    <ChartContainer config={chartConfig} className="w-full" style={{ height: Math.max(120, data.length * 48 + 60) }}>
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
          type="number"
          domain={[0, 100]}
          ticks={[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]}
          tickFormatter={(v) => `${v}%`}
          tick={{ fontSize: 11 }}
        />
        <ChartTooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0].payload;
            return (
              <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                <div className="font-medium">{d.label}</div>
                <div className="text-green-500">Wins: {d.wins} ({d.win_pct.toFixed(1)}%)</div>
                <div className="text-gray-400">Draws: {d.draws} ({d.draw_pct.toFixed(1)}%)</div>
                <div className="text-red-500">Losses: {d.losses} ({d.loss_pct.toFixed(1)}%)</div>
                <div className="text-muted-foreground pt-0.5 border-t border-border/50">Total: {d.total} games</div>
              </div>
            );
          }}
        />
        <ChartLegend
          content={<ChartLegendContent hiddenKeys={hiddenKeys} />}
          onClick={(e) => {
            if (e?.dataKey) handleLegendClick(e.dataKey as string);
          }}
        />
        <Bar dataKey="win_pct" stackId="wdl" fill="var(--color-win_pct)" radius={[0, 0, 0, 0]} hide={hiddenKeys.has('win_pct')} />
        <Bar dataKey="draw_pct" stackId="wdl" fill="var(--color-draw_pct)" hide={hiddenKeys.has('draw_pct')} />
        <Bar dataKey="loss_pct" stackId="wdl" fill="var(--color-loss_pct)" radius={[0, 0, 0, 0]} hide={hiddenKeys.has('loss_pct')} />
      </BarChart>
    </ChartContainer>
  );
}
