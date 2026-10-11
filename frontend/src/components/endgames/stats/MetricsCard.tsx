import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { METRIC_BRACKET_COLOR, METRIC_BRACKET_DIM_OVERLAY } from '@/lib/theme';
import type {
  CdfMetricId,
  MaterialBucket,
  RankedBucketOut,
  RankedTcStats,
} from '@/types/endgames';
import { RankedMetricRow } from './RankedMetricRow';
import { formatMetricValue } from './rankedMetrics';

const NO_VALUE = '—';
const PERCENT_SCALE = 100;

/** The bracket label starts this far past the end of the bracket, in % of the bar width. */
const BRACKET_LABEL_OFFSET_PCT = 2;
/** The label never starts further right than this, so a long label stays inside the bar. */
const BRACKET_LABEL_MAX_LEFT_PCT = 60;

interface BucketCopy {
  title: string;
  definition: string;
  rateMetric: CdfMetricId;
  gapMetric: CdfMetricId;
  /** Prefix of the bracket label; the rate follows after an equals sign. */
  bracketLabel: string;
}

const BUCKET_COPY: Record<MaterialBucket, BucketCopy> = {
  conversion: {
    title: 'Conversion',
    definition: 'Endgames you entered clearly ahead. How often you won.',
    rateMetric: 'conversion_rate',
    gapMetric: 'score_gap_conv',
    bracketLabel: 'wins',
  },
  parity: {
    title: 'Parity',
    definition: 'Endgames you entered roughly equal. Your score.',
    rateMetric: 'parity_rate',
    gapMetric: 'score_gap_parity',
    // Short on purpose: since the 238 UAT the label sits after the span (not at 0),
    // and "score (W + ½D) = 52%" ran past the bar's right edge on a narrow card.
    bracketLabel: 'W + ½D',
  },
  recovery: {
    title: 'Recovery',
    definition: 'Endgames you entered clearly behind. How often you saved them.',
    rateMetric: 'recovery_rate',
    gapMetric: 'recovery_score_gap',
    bracketLabel: 'wins + draws',
  },
};

interface BucketShares {
  win: number;
  draw: number;
  loss: number;
}

/** W/D/L as percent of the bucket's games; null for an empty bucket. */
function bucketShares(bucket: RankedBucketOut | undefined): BucketShares | null {
  if (!bucket || bucket.games === 0) return null;
  const toPct = (count: number): number => (count / bucket.games) * PERCENT_SCALE;
  return { win: toPct(bucket.wins), draw: toPct(bucket.draws), loss: toPct(bucket.losses) };
}

/**
 * How much of the bar the rate counts, in percent of the bar width. Parity's score
 * counts half of each draw, so its span ends halfway through the draw segment (238 UAT:
 * the parity bracket spans its score like the other two cards instead of only labelling it).
 */
function coveredPct(bucket: MaterialBucket, shares: BucketShares): number {
  if (bucket === 'conversion') return shares.win;
  if (bucket === 'recovery') return shares.win + shares.draw;
  return shares.win + shares.draw / 2;
}

interface BracketProps {
  covered: number;
  label: string;
  testId: string;
}

/** Bracket under the WDL bar: spans what the rate counts, labelled with the rate. */
function Bracket({ covered, label, testId }: BracketProps) {
  const labelLeft = Math.min(covered + BRACKET_LABEL_OFFSET_PCT, BRACKET_LABEL_MAX_LEFT_PCT);
  return (
    <div className="relative mt-0.5 h-6" data-testid={testId}>
      <span
        className="absolute left-0 top-0 h-2 rounded-b-md border-x-[1.5px] border-b-[1.5px]"
        style={{ width: `${covered}%`, borderColor: METRIC_BRACKET_COLOR }}
        data-testid={`${testId}-span`}
      />
      <span
        className="absolute top-1 whitespace-nowrap text-sm text-muted-foreground"
        style={{ left: `${labelLeft}%` }}
        data-testid={`${testId}-label`}
      >
        {label}
      </span>
    </div>
  );
}

interface BracketedWdlBarProps {
  shares: BucketShares;
  covered: number;
  label: string;
  testId: string;
}

/** The bucket's WDL bar with everything right of the counted share dimmed, and the bracket below. */
function BracketedWdlBar({ shares, covered, label, testId }: BracketedWdlBarProps) {
  return (
    <div>
      <div className="relative" data-testid={`${testId}-bar`}>
        <MiniWDLBar win_pct={shares.win} draw_pct={shares.draw} loss_pct={shares.loss} />
        <div
          className="pointer-events-none absolute inset-y-0 right-0 rounded-r-sm"
          style={{ left: `${covered}%`, backgroundColor: METRIC_BRACKET_DIM_OVERLAY }}
          data-testid={`${testId}-dim`}
        />
      </div>
      <Bracket covered={covered} label={label} testId={`${testId}-bracket`} />
    </div>
  );
}

interface MetricsCardProps {
  tcStats: RankedTcStats;
  bucket: MaterialBucket;
}

/**
 * One material bucket (Conversion, Parity or Recovery) for the selected time
 * control (D-00d). The big rate, the WDL bar and the percentile rows all come
 * from the same ranked sample, so they always describe the same games (D-00b).
 * No gauge: the bracket under the bar shows what the rate counts instead.
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
              <span className="text-2xl font-semibold tabular-nums" data-testid={`${testId}-rate`}>
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
                label={`${copy.bracketLabel} = ${rateText}`}
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
