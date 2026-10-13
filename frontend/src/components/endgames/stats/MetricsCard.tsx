import { Card, CardBody, CardHeader } from '@/components/ui/card';
import type {
  CdfMetricId,
  MaterialBucket,
  RankedBucketOut,
  RankedTcStats,
} from '@/types/endgames';
import { BracketedWdlBar, type WdlShares } from './BracketedWdlBar';
import { RankedMetricRow } from './RankedMetricRow';
import { formatMetricValue } from './rankedMetrics';

const NO_VALUE = '—';
const PERCENT_SCALE = 100;


interface BucketCopy {
  title: string;
  definition: string;
  rateMetric: CdfMetricId;
  gapMetric: CdfMetricId;
}

const BUCKET_COPY: Record<MaterialBucket, BucketCopy> = {
  conversion: {
    title: 'Conversion',
    definition: 'Endgames you entered clearly ahead. How often you won.',
    rateMetric: 'conversion_rate',
    gapMetric: 'score_gap_conv',
  },
  parity: {
    title: 'Parity',
    definition: 'Endgames you entered roughly equal. Your score.',
    rateMetric: 'parity_rate',
    gapMetric: 'score_gap_parity',
  },
  recovery: {
    title: 'Recovery',
    definition: 'Endgames you entered clearly behind. How often you saved them.',
    rateMetric: 'recovery_rate',
    gapMetric: 'recovery_score_gap',
  },
};

/** W/D/L as percent of the bucket's games; null for an empty bucket. */
function bucketShares(bucket: RankedBucketOut | undefined): WdlShares | null {
  if (!bucket || bucket.games === 0) return null;
  const toPct = (count: number): number => (count / bucket.games) * PERCENT_SCALE;
  return { win: toPct(bucket.wins), draw: toPct(bucket.draws), loss: toPct(bucket.losses) };
}

/**
 * How much of the bar the rate counts, in percent of the bar width. Parity's score
 * counts half of each draw, so its span ends halfway through the draw segment (238 UAT:
 * the parity bracket spans its score like the other two cards instead of only labelling it).
 */
function coveredPct(bucket: MaterialBucket, shares: WdlShares): number {
  if (bucket === 'conversion') return shares.win;
  if (bucket === 'recovery') return shares.win + shares.draw;
  return shares.win + shares.draw / 2;
}

interface MetricsCardProps {
  tcStats: RankedTcStats;
  bucket: MaterialBucket;
}

/**
 * One material bucket (Conversion, Parity or Recovery) for the selected time
 * control (D-00d). The big rate, the WDL bar and the percentile rows all come
 * from the same ranked sample, so they always describe the same games (D-00b).
 * No gauge: the bracket over the bar shows what the rate counts instead.
 */
export function MetricsCard({ tcStats, bucket }: MetricsCardProps) {
  const copy = BUCKET_COPY[bucket];
  const rate = tcStats.metrics[copy.rateMetric];
  const gap = tcStats.metrics[copy.gapMetric];
  const shares = bucketShares(tcStats.buckets.find((b) => b.bucket === bucket));
  const testId = `metrics-card-${bucket}`;
  // D-11: while entry evals are missing the rate is not computable, so the
  // pending line (inside the rate row) stands in for the big number and the bar.
  const showHeadline = rate.status !== 'pending';
  const rateText = rate.value === null ? NO_VALUE : formatMetricValue(copy.rateMetric, rate.value);

  return (
    <Card data-testid={testId}>
      <CardHeader>{copy.title}</CardHeader>
      <CardBody className="flex flex-col gap-4">
        {/* Reserve two lines so the rows below line up across the three cards
            when one definition wraps to a second line (238 UAT). */}
        <p className="min-h-[2lh] text-sm text-muted-foreground">{copy.definition}</p>
        {showHeadline && (
          <div className="flex flex-col gap-2">
            <div className="flex items-baseline gap-2">
              {/* Uncolored on purpose: the verdict is the percentile row below. */}
              <span className="text-2xl font-bold tabular-nums" data-testid={`${testId}-rate`}>
                {rateText}
              </span>
              <span className="text-sm text-muted-foreground" data-testid={`${testId}-games`}>
                {rate.n.toLocaleString()} games
              </span>
            </div>
            {shares !== null && (
              <BracketedWdlBar
                shares={shares}
                covered={coveredPct(bucket, shares)}
                testId={testId}
              />
            )}
          </div>
        )}
        <RankedMetricRow
          metric={rate}
          tcStats={tcStats}
          testId={`${testId}-rate-row`}
          label={`${copy.title} vs. peers`}
        />
        <RankedMetricRow
          metric={gap}
          tcStats={tcStats}
          testId={`${testId}-gap-row`}
          label="vs. expected"
        />
      </CardBody>
    </Card>
  );
}
