/**
 * Grouped vertical bar chart for Conversion & Recovery percentages
 * by endgame type (D-08, D-09).
 */

import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { InfoPopover } from '@/components/ui/info-popover';
import { MATERIAL_ADVANTAGE_POINTS } from '@/components/charts/EndgamePerformanceSection';
import type { EndgameCategoryStats } from '@/types/endgames';
import type { ChartConfig } from '@/components/ui/chart';

const chartConfig: ChartConfig = {
  conversion_pct: { label: 'Conversion', color: 'oklch(0.55 0.17 145)' },
  recovery_pct: { label: 'Recovery', color: 'oklch(0.55 0.18 260)' },
};

interface ConvRecovDataPoint {
  label: string;
  conversion_pct: number;
  recovery_pct: number;
}

interface EndgameConvRecovChartProps {
  categories: EndgameCategoryStats[];
}

export function EndgameConvRecovChart({ categories }: EndgameConvRecovChartProps) {
  const chartData: ConvRecovDataPoint[] = categories
    .filter(c => c.conversion.conversion_games > 0 || c.conversion.recovery_games > 0)
    .map(c => ({
      label: c.label,
      conversion_pct: c.conversion.conversion_pct,
      recovery_pct: c.conversion.recovery_pct,
    }));

  return (
    <div data-testid="conv-recov-chart">
      <h3 className="text-base font-semibold mb-3">
        <span className="inline-flex items-center gap-1">
          Conversion &amp; Recovery by Endgame Type
          <InfoPopover ariaLabel="Conversion and Recovery info" testId="conv-recov-chart-info" side="top">
              <strong>Conversion</strong>: your win rate when you entered the endgame with a material advantage of at least {MATERIAL_ADVANTAGE_POINTS} points. <br/>
              <strong>Recovery</strong>: your draw+win rate when you entered the endgame with a material deficit of at least {MATERIAL_ADVANTAGE_POINTS} points.
          </InfoPopover>
        </span>
      </h3>

      {chartData.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">
          Not enough data for conversion/recovery analysis
        </p>
      ) : (
        <ChartContainer config={chartConfig} className="w-full h-64">
          <BarChart data={chartData} margin={{ left: 4, right: 4, bottom: 20 }}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11 }}
              angle={-30}
              textAnchor="end"
            />
            <YAxis
              domain={[0, 100]}
              tickFormatter={(v: number) => `${v}%`}
            />
            <ChartTooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload as ConvRecovDataPoint;
                return (
                  <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                    <div className="font-medium">{d.label}</div>
                    <div style={{ color: chartConfig.conversion_pct.color }}>
                      Conversion: {d.conversion_pct.toFixed(1)}%
                    </div>
                    <div style={{ color: chartConfig.recovery_pct.color }}>
                      Recovery: {d.recovery_pct.toFixed(1)}%
                    </div>
                  </div>
                );
              }}
            />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar dataKey="conversion_pct" fill="var(--color-conversion_pct)" radius={[2, 2, 0, 0]} />
            <Bar dataKey="recovery_pct" fill="var(--color-recovery_pct)" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ChartContainer>
      )}
    </div>
  );
}
