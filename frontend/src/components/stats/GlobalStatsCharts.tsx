import { InfoPopover } from '@/components/ui/info-popover';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
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

function WDLCategoryChart({ data, title, testId, infoTooltip }: WDLCategoryChartProps) {
  return (
    <div className="charcoal-texture rounded-md overflow-hidden">
      <h3
        className="flex items-center gap-2 px-4 py-3 bg-black/20 border-b border-border/40 text-base font-semibold"
        data-testid={`${testId}-header`}
      >
        {title}
        <InfoPopover ariaLabel={`${title} info`} testId={`${testId}-info`} side="top">
          {infoTooltip}
        </InfoPopover>
      </h3>
      <div className="p-4">
        {data.length === 0 ? (
          <div data-testid={testId} className="text-center text-muted-foreground py-8">
            No data available.
          </div>
        ) : (
          <div className="space-y-2" data-testid={testId}>
            {data.map((cat) => (
              <WDLChartRow
                key={cat.label}
                data={cat}
                label={cat.label}
                maxTotal={Math.max(...data.map((d) => d.total))}
                testId={`${testId}-${cat.label.toLowerCase()}`}
              />
            ))}
          </div>
        )}
      </div>
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
