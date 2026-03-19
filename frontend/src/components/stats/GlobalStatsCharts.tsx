import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import type { WDLByCategory } from '@/types/stats';

interface GlobalStatsChartsProps {
  byTimeControl: WDLByCategory[];
  byColor: WDLByCategory[];
}

interface WDLCategoryChartProps {
  data: WDLByCategory[];
  title: string;
  testId: string;
}

const chartConfig = {
  win_pct: { label: 'Wins', color: 'oklch(0.45 0.16 145)' },
  draw_pct: { label: 'Draws', color: 'oklch(0.65 0.01 260)' },
  loss_pct: { label: 'Losses', color: 'oklch(0.45 0.17 25)' },
};

function WDLCategoryChart({ data, title, testId }: WDLCategoryChartProps) {
  if (data.length === 0) {
    return (
      <div>
        <h2 className="text-lg font-medium mb-3">{title}</h2>
        <div
          data-testid={testId}
          className="text-center text-muted-foreground py-8"
        >
          No data available.
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-medium mb-3">{title}</h2>
      <ChartContainer
        config={chartConfig}
        className="w-full"
        style={{ height: Math.max(120, data.length * 48 + 60) }}
        data-testid={testId}
      >
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
            tickFormatter={(v) => `${v as number}%`}
            tick={{ fontSize: 11 }}
          />
          <ChartTooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload as WDLByCategory;
              return (
                <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                  <div className="font-medium">{d.label}</div>
                  <div className="text-green-600">Wins: {d.wins} ({d.win_pct.toFixed(1)}%)</div>
                  <div className="text-gray-400">Draws: {d.draws} ({d.draw_pct.toFixed(1)}%)</div>
                  <div className="text-red-600">Losses: {d.losses} ({d.loss_pct.toFixed(1)}%)</div>
                  <div className="text-muted-foreground pt-0.5 border-t border-border/50">Total: {d.total} games</div>
                </div>
              );
            }}
          />
          <ChartLegend content={<ChartLegendContent />} />
          <Bar dataKey="win_pct" stackId="wdl" fill="var(--color-win_pct)" radius={[0, 0, 0, 0]} />
          <Bar dataKey="draw_pct" stackId="wdl" fill="var(--color-draw_pct)" />
          <Bar dataKey="loss_pct" stackId="wdl" fill="var(--color-loss_pct)" radius={[0, 0, 0, 0]} />
        </BarChart>
      </ChartContainer>
    </div>
  );
}

export function GlobalStatsCharts({ byTimeControl, byColor }: GlobalStatsChartsProps) {
  return (
    <div className="space-y-8">
      <WDLCategoryChart
        data={byTimeControl}
        title="Results by Time Control"
        testId="global-stats-by-tc"
      />
      <WDLCategoryChart
        data={byColor}
        title="Results by Color"
        testId="global-stats-by-color"
      />
    </div>
  );
}
