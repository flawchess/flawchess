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

  const maxTotal = Math.max(...data.map((d) => d.total));

  return (
    <div>
      <ChartTitle title={title} infoTooltip={infoTooltip} testId={testId} />
      <div className="space-y-2" data-testid={testId}>
        {data.map((cat) => (
          <WDLChartRow
            key={cat.label}
            data={cat}
            label={cat.label}
            maxTotal={maxTotal}
            testId={`${testId}-${cat.label.toLowerCase()}`}
          />
        ))}
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
