/**
 * One popover per peer-ranked metric: a plain WHAT + sign sentence, the
 * percentile statement with its disclosures (cohort, recent-games basis, anchor
 * composition), then the statistics (n, 99% CI, p-value) greyed below a separator.
 * An out-of-range percentile that is not significant adds a could-be-chance line.
 * The Stats tab has no filters, so no filter-independence line. Stats vocabulary
 * appears only in that footer; the prose stays plain (popover copy minimalism).
 *
 * The shell (Search trigger right of the metric name, hover-open delay, Radix Portal
 * content) lives in the shared MetricInfoPopover; the bar itself is no trigger.
 */

import { MetricInfoPopover } from '@/components/ui/metric-info-popover';
import type { RankedMetricOut, RankedTcStats, RatingAnchorOut } from '@/types/endgames';
import { RankStatusLine } from './PercentileBar';
import {
  METRIC_LABELS,
  METRIC_WHAT,
  PERCENTILE_TYPICAL_HIGH,
  PERCENTILE_TYPICAL_LOW,
  COPY_CHANCE,
  displayPercentile,
  formatCiBound,
  formatPValue,
} from './rankedMetrics';

const FOOTER_SEPARATOR = ' · ';

/** The anchor-composition disclosure: mixed, lichess-only or chess.com-only (feedback contract). */
function anchorCompositionCopy(anchor: RatingAnchorOut): string {
  const { anchor_rating, n_chesscom_games, n_lichess_games } = anchor;
  const chesscomMedian = anchor.chesscom_median_native;
  const lichessMedian = anchor.lichess_median_native;
  if (n_chesscom_games > 0 && n_lichess_games > 0) {
    return `Anchored at ~${anchor_rating} Elo, blending ${n_chesscom_games} chess.com games (median ${chesscomMedian}, converted) with ${n_lichess_games} lichess games (median ${lichessMedian}).`;
  }
  if (n_chesscom_games === 0) {
    return `Anchored at ~${anchor_rating} Elo from ${n_lichess_games} lichess games (native rating).`;
  }
  return `Anchored at ~${anchor_rating} Elo from ${n_chesscom_games} chess.com games (median ${chesscomMedian}, converted to Lichess-equivalent).`;
}

/** Greyed statistics line: n, 99% CI and p-value, each only when the metric has it. */
function footerText(metric: RankedMetricOut): string {
  const parts = [`n = ${metric.n}`];
  if (metric.ci_low !== null && metric.ci_high !== null) {
    parts.push(
      `99% CI ${formatCiBound(metric.metric, metric.ci_low)} to ${formatCiBound(metric.metric, metric.ci_high)}`,
    );
  }
  if (metric.p_value !== null) parts.push(formatPValue(metric.p_value));
  return parts.join(FOOTER_SEPARATOR);
}

interface PopoverBodyProps {
  metric: RankedMetricOut;
  tcStats: RankedTcStats;
  testId: string;
}

/** Percentile statement plus its disclosures; ranked cells only. */
function RankedDisclosures({ metric, tcStats }: Omit<PopoverBodyProps, 'testId'>) {
  const { tc, anchor } = tcStats;
  const percentile = displayPercentile(metric.percentile ?? 0);
  const outOfRange = percentile < PERCENTILE_TYPICAL_LOW || percentile > PERCENTILE_TYPICAL_HIGH;
  const peers = anchor ? `~${anchor.anchor_rating}-rated ${tc} players` : `similarly-rated ${tc} players`;
  return (
    <>
      <p className="font-semibold">
        Better than {percentile}% of {peers}.
        {outOfRange && !metric.significant && ` ${COPY_CHANCE}`}
      </p>
      <ul className="list-disc space-y-0.5 pl-4">
        <li>Compared against benchmarked Lichess players at your rating.</li>
        <li>
          Based on {metric.n} of your {tc} games from the last 36 months, opponents within ±100
          Elo.
        </li>
        {anchor && <li>{anchorCompositionCopy(anchor)}</li>}
      </ul>
    </>
  );
}

function RankedMetricPopoverBody({ metric, tcStats, testId }: PopoverBodyProps) {
  const ranked = metric.status === 'ranked' && metric.percentile !== null;
  return (
    <div className="space-y-1.5">
      <p>
        <strong>{METRIC_LABELS[metric.metric]}:</strong> {METRIC_WHAT[metric.metric]}
      </p>
      {ranked ? (
        <RankedDisclosures metric={metric} tcStats={tcStats} />
      ) : (
        <RankStatusLine
          status={metric.status}
          floorN={metric.floor_n}
          floorRequired={metric.floor_required}
          className="text-xs text-background"
        />
      )}
      <hr className="border-background/25" />
      <p className="italic text-background/60" data-testid={`${testId}-footer`}>
        {footerText(metric)}
      </p>
    </div>
  );
}

interface RankedMetricPopoverProps {
  metric: RankedMetricOut;
  tcStats: RankedTcStats;
  /** `ranked-metric-{metric-kebab}-tc-{tc}`: the TC segment collapses into one analytics row. */
  testId: string;
}

export function RankedMetricPopover({
  metric,
  tcStats,
  testId,
}: RankedMetricPopoverProps) {
  return (
    <MetricInfoPopover testId={testId} ariaLabel={`About ${METRIC_LABELS[metric.metric]}`}>
      <RankedMetricPopoverBody metric={metric} tcStats={tcStats} testId={testId} />
    </MetricInfoPopover>
  );
}
