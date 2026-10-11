/**
 * One popover per peer-ranked metric (D-00c): a plain WHAT + sign sentence, the
 * percentile statement with its disclosures (cohort, recent-games basis, anchor
 * composition), then the statistics (n, 95% CI, p-value) greyed below a separator.
 * The Stats tab has no filters, so no filter-independence line (238 UAT). Stats vocabulary appears only in that
 * footer; the prose stays plain (popover copy minimalism).
 *
 * The shell follows the app's other hover/tap info popovers: a lucide Search
 * trigger right of the metric name (238 UAT: the bar itself is no trigger), 100ms
 * hover-open delay, Radix Portal + Content side="top" sideOffset 4, and text-xs, which
 * frontend/CLAUDE.md allows for short, transient, opt-in info surfaces.
 */

import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { Search } from 'lucide-react';
import { useTrackedPopoverOpen } from '@/hooks/useTrackedOpen';
import { cn } from '@/lib/utils';
import type { RankedMetricOut, RankedTcStats, RatingAnchorOut } from '@/types/endgames';
import { RankStatusLine } from './PercentileBar';
import {
  METRIC_LABELS,
  METRIC_WHAT,
  displayPercentile,
  formatCiBound,
  formatPValue,
} from './rankedMetrics';

const HOVER_OPEN_DELAY_MS = 100;
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

/** Greyed statistics line: n, 95% CI and p-value, each only when the metric has it. */
function footerText(metric: RankedMetricOut): string {
  const parts = [`n = ${metric.n}`];
  if (metric.ci_low !== null && metric.ci_high !== null) {
    parts.push(
      `95% CI ${formatCiBound(metric.metric, metric.ci_low)} to ${formatCiBound(metric.metric, metric.ci_high)}`,
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
  const peers = anchor ? `~${anchor.anchor_rating}-rated ${tc} players` : `similarly-rated ${tc} players`;
  return (
    <>
      <p className="font-semibold">
        Better than {percentile}% of {peers}.
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
  const [open, setOpen] = useTrackedPopoverOpen(testId);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear a pending hover-open timer on unmount so it cannot fire setOpen late.
  React.useEffect(() => {
    return () => {
      if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    };
  }, []);

  const handleMouseEnter = (): void => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    hoverTimeout.current = setTimeout(() => setOpen(true), HOVER_OPEN_DELAY_MS);
  };

  const handleMouseLeave = (): void => {
    if (hoverTimeout.current) {
      clearTimeout(hoverTimeout.current);
      hoverTimeout.current = null;
    }
    setOpen(false);
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          role="button"
          tabIndex={0}
          aria-label={`About ${METRIC_LABELS[metric.metric]}`}
          data-testid={testId}
          className="inline-flex cursor-pointer items-center text-brand-brown-light/70 hover:text-brand-brown focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <Search className="h-4 w-4" />
        </span>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="top"
          sideOffset={4}
          onMouseEnter={() => {
            if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
          }}
          onMouseLeave={handleMouseLeave}
          data-testid={`${testId}-popover`}
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          <RankedMetricPopoverBody metric={metric} tcStats={tcStats} testId={testId} />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
