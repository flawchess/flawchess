import type { RankedMetricOut, RankedTcStats } from '@/types/endgames';
import { PercentileBar } from './PercentileBar';
import { RankedMetricPopover } from './RankedMetricPopover';
import { METRIC_LABELS, formatMetricValue, metricSlug } from './rankedMetrics';

const NO_VALUE = '—';

interface RankedMetricRowProps {
  metric: RankedMetricOut;
  tcStats: RankedTcStats;
  /** Row root testid; the value is `{testId}-value` and the bar slot `{testId}-bar`. */
  testId: string;
  /** Overrides the default metric label. */
  label?: string;
}

/**
 * One peer-ranked metric: the label with its Search popover trigger to the right, the
 * uncolored value, then the percentile bar (or its status slot). The bar is no
 * trigger. A pending cell shows only its analyzing line in place of
 * value and bar; the trigger stays so the popover still explains why.
 */
export function RankedMetricRow({ metric, tcStats, testId, label }: RankedMetricRowProps) {
  const showValue = metric.status !== 'pending';
  return (
    <div className="flex flex-col gap-1" data-testid={testId}>
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5">
          <span className="font-semibold">{label ?? METRIC_LABELS[metric.metric]}</span>
          <RankedMetricPopover
            metric={metric}
            tcStats={tcStats}
            testId={`ranked-metric-${metricSlug(metric.metric)}-tc-${tcStats.tc}`}
          />
        </span>
        {showValue && (
          <span className="font-bold tabular-nums" data-testid={`${testId}-value`}>
            {metric.value === null ? NO_VALUE : formatMetricValue(metric.metric, metric.value)}
          </span>
        )}
      </div>
      <PercentileBar
        status={metric.status}
        percentile={metric.percentile}
        floorN={metric.floor_n}
        floorRequired={metric.floor_required}
        significant={metric.significant}
        testId={`${testId}-bar`}
      />
    </div>
  );
}
