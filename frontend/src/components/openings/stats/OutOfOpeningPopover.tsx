/**
 * The popover of one out-of-the-opening rate, on the shared MetricInfoPopover shell
 * (Search trigger right of the label). Follows RankedMetricPopover with no chart (D-09):
 * a WHAT sentence, the percentile statement in words plus the disclosures (D-12), the
 * per-time-control breakdown (D-10), a separator and a greyed 95% footer (D-11). Statistics
 * vocabulary appears only in that footer.
 *
 * The testId becomes the Umami popover-open target, so it is a fixed literal per side with
 * no colour or time-control segment (one analytics row per explanation).
 */

import { MetricInfoPopover } from '@/components/ui/metric-info-popover';
import { RankStatusLine } from '@/components/endgames/stats/PercentileBar';
import type { Color } from '@/types/api';
import type { TimeControlBucket } from '@/types/endgames';
import type { OpeningOutRateOut, OpeningOutSide } from '@/types/openingOut';
import {
  OUT_OF_OPENING_DISCLOSURES,
  OUT_OF_OPENING_LABELS,
  chanceCopy,
  footerCopy,
  statementCopy,
  tcLineCopy,
  whatCopy,
} from './outOfOpeningCopy';

/** Fastest to slowest; the API already sends this order, the popover does not rely on it. */
const TC_ORDER: readonly TimeControlBucket[] = ['bullet', 'blitz', 'rapid', 'classical'];

interface OutOfOpeningPopoverProps {
  side: OpeningOutSide;
  color: Color;
  rate: OpeningOutRateOut;
  /** `out-of-opening-worse-rate` or `out-of-opening-better-rate`. */
  testId: string;
}

function DisclosureList() {
  return (
    <ul className="list-disc space-y-0.5 pl-4">
      {OUT_OF_OPENING_DISCLOSURES.map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ul>
  );
}

function OutOfOpeningPopoverBody({ side, color, rate, testId }: OutOfOpeningPopoverProps) {
  const percentile = rate.status === 'ranked' ? rate.percentile_favorable : null;
  const chance = percentile === null ? null : chanceCopy(percentile, rate.significant);
  const tcs = TC_ORDER.flatMap((tc) => rate.tcs.filter((entry) => entry.tc === tc));
  return (
    <div className="space-y-1.5">
      <p>
        <strong>{OUT_OF_OPENING_LABELS[side]}:</strong> {whatCopy(side, color)}
      </p>
      {percentile === null ? (
        <RankStatusLine
          status={rate.status}
          floorN={rate.floor_n}
          floorRequired={rate.floor_required}
          className="text-xs text-background"
        />
      ) : (
        <p className="font-semibold">
          {statementCopy(side, percentile)}
          {chance !== null && ` ${chance}`}
        </p>
      )}
      <DisclosureList />
      {tcs.length > 0 && (
        <ul className="list-disc space-y-0.5 pl-4" data-testid={`${testId}-tcs`}>
          {tcs.map((entry) => (
            <li key={entry.tc}>{tcLineCopy(entry)}</li>
          ))}
        </ul>
      )}
      <hr className="border-background/25" />
      <p className="italic text-background/60" data-testid={`${testId}-footer`}>
        {footerCopy(rate)}
      </p>
    </div>
  );
}

export function OutOfOpeningPopover(props: OutOfOpeningPopoverProps) {
  return (
    <MetricInfoPopover
      testId={props.testId}
      ariaLabel={`About ${OUT_OF_OPENING_LABELS[props.side]}`}
    >
      <OutOfOpeningPopoverBody {...props} />
    </MetricInfoPopover>
  );
}
