/**
 * Grouped vertical bar chart for Conversion & Recovery percentages
 * by endgame type (D-08, D-09).
 */

import { useState, useEffect } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { InfoPopover } from '@/components/ui/info-popover';
import { MATERIAL_ADVANTAGE_POINTS, PERSISTENCE_MOVES } from '@/components/charts/EndgamePerformanceSection';
import { ZONE_SUCCESS } from '@/lib/theme';
import type { EndgameCategoryStats } from '@/types/endgames';
import type { ChartConfig } from '@/components/ui/chart';

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

const chartConfig: ChartConfig = {
  // Conversion uses the success (green) zone color from theme
  conversion_pct: { label: 'Conversion', color: ZONE_SUCCESS },
  // Recovery uses a blue that is intentionally distinct from WDL_DRAW (grey-blue) — it represents a positive "saved" outcome
  recovery_pct: { label: 'Recovery', color: 'oklch(0.55 0.18 260)' },
};

interface ConvRecovDataPoint {
  label: string;
  conversion_pct: number;
  recovery_pct: number;
  conversion_games: number;
  recovery_games: number;
}

interface EndgameConvRecovChartProps {
  categories: EndgameCategoryStats[];
}

export function EndgameConvRecovChart({ categories }: EndgameConvRecovChartProps) {
  const isMobile = useIsMobile();
  const chartData: ConvRecovDataPoint[] = categories
    .filter(c => c.conversion.conversion_games > 0 || c.conversion.recovery_games > 0)
    .map(c => ({
      label: c.label,
      conversion_pct: c.conversion.conversion_pct,
      recovery_pct: c.conversion.recovery_pct,
      conversion_games: c.conversion.conversion_games,
      recovery_games: c.conversion.recovery_games,
    }));

  return (
    <div data-testid="conv-recov-chart">
      <div className="mb-3">
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Conversion &amp; Recovery by Endgame Type
            <InfoPopover ariaLabel="Conversion and Recovery info" testId="conv-recov-chart-info" side="top">
              <div className="space-y-2">
                <p>
                  <strong>Conversion</strong>: percentage of endgame sequences per type with a material advantage of at least {MATERIAL_ADVANTAGE_POINTS} point (persisted for at least {PERSISTENCE_MOVES} moves) where you went on to win the game.
                </p>
                <p>
                  <strong>Recovery</strong>: percentage of endgame sequences per type with a material deficit of at least {MATERIAL_ADVANTAGE_POINTS} point (persisted for at least {PERSISTENCE_MOVES} moves) where you went on to draw or win the game.
                </p>
              </div>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Which endgame types you convert best and which you defend best.
        </p>
      </div>

      {chartData.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">
          Not enough data for conversion/recovery analysis
        </p>
      ) : (
        <div className={isMobile ? '' : 'flex items-stretch'}>
          {!isMobile && (
            <div
              className="flex items-center text-xs text-muted-foreground shrink-0 pt-35 -mr-1"
              style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
            >
              Rate %
            </div>
          )}
          <ChartContainer config={chartConfig} className="w-full h-64">
            <BarChart data={chartData} margin={{ left: isMobile ? 0 : 4, right: 4, bottom: 20 }}>
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
                width={isMobile ? 36 : 44}
              />
            <ChartTooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                // safe: payload.length check above guarantees index 0 exists
                const d = payload[0]!.payload as ConvRecovDataPoint;
                return (
                  <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                    <div className="font-medium">{d.label}</div>
                    {/* safe: chartConfig keys are defined as literal string constants above */}
                    <div style={{ color: chartConfig['conversion_pct']?.color }}>
                      Conversion: {d.conversion_pct.toFixed(1)}% ({d.conversion_games} sequences)
                    </div>
                    <div style={{ color: chartConfig['recovery_pct']?.color }}>
                      Recovery: {d.recovery_pct.toFixed(1)}% ({d.recovery_games} sequences)
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
        </div>
      )}
    </div>
  );
}
