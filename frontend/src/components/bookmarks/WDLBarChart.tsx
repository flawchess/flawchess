import { ChartContainer, ChartTooltip, ChartTooltipContent, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
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
  wins: { label: 'Wins', color: 'oklch(0.55 0.18 145)' },
  draws: { label: 'Draws', color: 'oklch(0.65 0.01 260)' },
  losses: { label: 'Losses', color: 'oklch(0.55 0.2 25)' },
};

export function WDLBarChart({ bookmarks, wdlStatsMap }: WDLBarChartProps) {
  const data = bookmarks
    .filter((b) => wdlStatsMap[b.id] && wdlStatsMap[b.id].total > 0)
    .map((b) => {
      const s = wdlStatsMap[b.id];
      return {
        label: b.label,
        wins: s.wins,
        draws: s.draws,
        losses: s.losses,
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
        <XAxis type="number" hide />
        <ChartTooltip
          content={
            <ChartTooltipContent
              formatter={(value, name) => {
                const cfg = chartConfig[name as keyof typeof chartConfig];
                return (
                  <span>{cfg?.label ?? name}: {value as number}</span>
                );
              }}
            />
          }
        />
        <ChartLegend content={<ChartLegendContent />} />
        <Bar dataKey="wins" stackId="wdl" fill="var(--color-wins)" radius={[0, 0, 0, 0]} />
        <Bar dataKey="draws" stackId="wdl" fill="var(--color-draws)" />
        <Bar dataKey="losses" stackId="wdl" fill="var(--color-losses)" radius={[0, 0, 0, 0]} />
      </BarChart>
    </ChartContainer>
  );
}
