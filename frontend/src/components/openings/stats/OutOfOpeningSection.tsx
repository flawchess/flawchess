import type { ReactNode } from 'react';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { LoadError } from '@/components/ui/load-error';
import { PercentileBar, RankStatusLine } from '@/components/endgames/stats/PercentileBar';
import { REPERTOIRE_HEADING_CLASS } from '@/components/openings/stats/headingClasses';
import { OutOfOpeningPopover } from '@/components/openings/stats/OutOfOpeningPopover';
import {
  OUT_OF_OPENING_LABELS,
  OUT_OF_OPENING_RATE_LABEL,
  hintCopy,
} from '@/components/openings/stats/outOfOpeningCopy';
import { useOutOfOpeningStats } from '@/hooks/useOutOfOpeningStats';
import { useReadiness } from '@/hooks/useReadiness';
import type { Color } from '@/types/api';
import type { OpeningOutRateOut, OpeningOutSide } from '@/types/openingOut';

const NO_VALUE = '—';
const PERCENT_SCALE = 100;

/** Same grid as the repertoire cards: stacked on mobile, side by side on desktop (UAT). */
const CARD_GRID_CLASS = 'grid grid-cols-1 items-stretch gap-3 lg:grid-cols-2';

interface OutOfOpeningCardProps {
  side: OpeningOutSide;
  color: Color;
  rate: OpeningOutRateOut;
  /** Card root testid; the value is `{testId}-value`, the hint `{testId}-hint`, the bar `{testId}-bar`. */
  testId: string;
}

/**
 * One rate as its own card (UAT: separate titled cards): the title and popover in the header
 * band, then the labelled pooled rate (uncolored), the percentile bar and the plain-language
 * hint under it. A pending card shows only its analyzing line in place of value and bar.
 */
function OutOfOpeningCard({ side, color, rate, testId }: OutOfOpeningCardProps) {
  const showValue = rate.status !== 'pending';
  const ranked = rate.status === 'ranked' && rate.percentile_favorable !== null;
  return (
    <Card className="flex flex-col" data-testid={testId}>
      <CardHeader>
        {OUT_OF_OPENING_LABELS[side]}
        {/* Fixed literal testid per side: one Umami popover-open row per explanation. */}
        <OutOfOpeningPopover
          side={side}
          color={color}
          rate={rate}
          testId={`out-of-opening-${side}-rate`}
        />
      </CardHeader>
      <CardBody className="flex flex-1 flex-col gap-1">
        {showValue && (
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-sm text-muted-foreground">{OUT_OF_OPENING_RATE_LABEL}</span>
            <span className="text-lg font-bold tabular-nums" data-testid={`${testId}-value`}>
              {rate.rate === null ? NO_VALUE : `${Math.round(rate.rate * PERCENT_SCALE)}%`}
            </span>
          </div>
        )}
        <PercentileBar
          status={rate.status}
          percentile={rate.percentile_favorable}
          floorN={rate.floor_n}
          floorRequired={rate.floor_required}
          significant={rate.significant}
          testId={`${testId}-bar`}
        />
        {/* Under the bar, not beside the value: next to "11%" it read as one sentence (UAT). */}
        {ranked && rate.percentile_favorable !== null && (
          <p className="text-sm text-muted-foreground" data-testid={`${testId}-hint`}>
            {hintCopy(side, rate.percentile_favorable)}
          </p>
        )}
      </CardBody>
    </Card>
  );
}

/**
 * "Out of the opening": how often the selected colour leaves the opening clearly worse (primary)
 * or clearly better (lesser) than a typical position, ranked against rating x time-control peers.
 * Each rate is its own titled card. The heading sits outside the cards so the desktop sticky
 * colour bar overlays it (StatsTab).
 */
export function OutOfOpeningSection({ color }: { color: Color }) {
  const { tier2 } = useReadiness();
  const { data, isError } = useOutOfOpeningStats({ enabled: tier2 });

  // Non-data states keep one untitled card; data renders the two titled cards.
  let status: ReactNode = null;
  if (!tier2) {
    status = (
      <RankStatusLine status="pending" floorN={0} floorRequired={0} testId="out-of-opening-pending" />
    );
  } else if (isError && !data) {
    // Only a failure with nothing cached is an error state: TanStack keeps `data` when a
    // background refetch (import-complete invalidation) fails, and that data is still usable.
    status = <LoadError resource="out-of-the-opening stats" data-testid="out-of-opening-error" />;
  } else if (!data) {
    status = (
      <p className="text-sm text-muted-foreground" data-testid="out-of-opening-loading">
        Loading out-of-the-opening stats...
      </p>
    );
  }

  return (
    <section className="space-y-2" data-testid="out-of-opening-section">
      <h2 className={REPERTOIRE_HEADING_CLASS} data-testid="out-of-opening-heading">
        Out of the opening
      </h2>
      {tier2 && data ? (
        <div className={CARD_GRID_CLASS}>
          <OutOfOpeningCard side="worse" color={color} rate={data[color].worse} testId="out-of-opening-card-worse" />
          <OutOfOpeningCard side="better" color={color} rate={data[color].better} testId="out-of-opening-card-better" />
        </div>
      ) : (
        <div className="charcoal-texture rounded-md p-4" data-testid="out-of-opening-status-card">
          {status}
        </div>
      )}
    </section>
  );
}
