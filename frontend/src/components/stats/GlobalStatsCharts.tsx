import { InfoPopover } from '@/components/ui/info-popover';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { WDL_WIN, WDL_DRAW, WDL_LOSS } from '@/lib/theme';
import type { WDLByCategory } from '@/types/stats';

interface GlobalStatsChartsProps {
  byTimeControl: WDLByCategory[];
  byColor: WDLByCategory[];
}

interface WDLCategoryChartProps {
  data: WDLByCategory[];
  title: string;
  testId: string;
  infoTooltip: string;
}

const chartConfig = {
  win_pct: { label: 'Wins', color: WDL_WIN },
  draw_pct: { label: 'Draws', color: WDL_DRAW },
  loss_pct: { label: 'Losses', color: WDL_LOSS },
};

function ChartTitle({ title, infoTooltip, testId }: { title: string; infoTooltip: string; testId: string }) {
  return (
    <h2 className="text-lg font-medium mb-3">
      <span className="inline-flex items-center gap-1">
        {title}
        <InfoPopover ariaLabel={`${title} info`} testId={`${testId}-info`} side="top">
          {infoTooltip}
        </InfoPopover>
      </span>
    </h2>
  );
}

function WDLCategoryChart({ data, title, testId, infoTooltip }: WDLCategoryChartProps) {
  if (data.length === 0) {
    return (
      <div>
        <ChartTitle title={title} infoTooltip={infoTooltip} testId={testId} />
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
      <ChartTitle title={title} infoTooltip={infoTooltip} testId={testId} />
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
        infoTooltip="Your win/draw/loss breakdown for each time control: bullet, blitz, rapid, and classical."
      />
      <WDLCategoryChart
        data={byColor}
        title="Results by Color"
        testId="global-stats-by-color"
        infoTooltip="Your win/draw/loss breakdown when playing as white vs black."
      />
    </div>
  );
}
