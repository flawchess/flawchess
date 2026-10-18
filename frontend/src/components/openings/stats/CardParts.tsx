import type { ReactNode } from 'react';
import { Archive } from 'lucide-react';
import { EvalCpuPlaceholder } from '@/components/stats/EvalCpuPlaceholder';
import { VerdictBar } from '@/components/openings/stats/VerdictBar';
import { EvalVerdictPopover } from '@/components/openings/stats/VerdictPopover';
import { useReadiness } from '@/hooks/useReadiness';
import { formatSignedGap } from '@/lib/gapBar';
import {
  EVAL_VERDICT_BAND,
  evalBaselinePawns,
  evalVerdictInput,
  formatEvalCompact,
  openingVerdict,
  openingVerdictReason,
  openingVerdictSentence,
  type EvalSample,
  type OpeningVerdictInput,
} from '@/lib/openingVerdict';
import { formatRelativeDate } from '@/lib/relativeDate';

/**
 * Pieces shared by the repertoire and finding cards (Openings Stats), so a layout or verdict
 * change lands on both card kinds at once.
 */

const NOT_PLAYED_RECENTLY = 'Not played recently';
const EVAL_LABEL = 'Eval after opening';
const EVAL_LABEL_SHORT = 'Eval';
const NO_VALUE = '—';

/**
 * "3 weeks ago" plus the archive icon for a card outside the current repertoire (D-27), right
 * of the card header. Nothing when there is neither a date nor the stale flag.
 */
export function LastPlayedIndicator({
  lastPlayedAt,
  stale,
  testId,
}: {
  lastPlayedAt: string | null | undefined;
  stale: boolean;
  testId: string;
}) {
  if (!lastPlayedAt && !stale) return null;
  return (
    <span
      className="ml-auto flex shrink-0 items-center gap-1.5 text-sm font-normal whitespace-nowrap text-muted-foreground"
      data-testid={`${testId}-last-played`}
    >
      {lastPlayedAt && formatRelativeDate(lastPlayedAt)}
      {/* Indicator only, not an action. */}
      {stale && (
        <Archive
          className="h-4 w-4"
          role="img"
          aria-label={NOT_PLAYED_RECENTLY}
          data-testid={`${testId}-stale-icon`}
        >
          <title>{NOT_PLAYED_RECENTLY}</title>
        </Archive>
      )}
    </span>
  );
}

interface EvalVerdictLineProps {
  sample: EvalSample;
  ciLow: number | null;
  ciHigh: number | null;
  pValue: number | null;
  /** Prefix of the testids: `-eval-bar`, `-eval-none` and `-eval-info` (the popover). */
  testId: string;
}

/**
 * "Eval after opening" verdict bar centred on the colour baseline, with its popover; an em dash
 * without eval data and the pending placeholder until Stockfish analysis (tier 2) is done.
 */
export function EvalVerdictLine({ sample, ciLow, ciHigh, pValue, testId }: EvalVerdictLineProps) {
  const { tier2 } = useReadiness();
  if (!tier2) return <EvalCpuPlaceholder />;
  const input = evalVerdictInput(sample);
  if (sample.avgEvalPawns === null || input === null) {
    return (
      <div
        className="flex items-center justify-between text-sm text-muted-foreground"
        data-testid={`${testId}-eval-none`}
      >
        <span>{EVAL_LABEL}</span>
        <span>{NO_VALUE}</span>
      </div>
    );
  }
  const avg = sample.avgEvalPawns;
  const baseline = evalBaselinePawns(sample.color);
  return (
    <VerdictBar
      delta={input.delta}
      band={EVAL_VERDICT_BAND}
      verdict={openingVerdict(input)}
      valueText={formatEvalCompact(avg)}
      zeroTickDelta={-baseline}
      centreSwatch={sample.color}
      testId={`${testId}-eval-bar`}
      ariaLabel={`${EVAL_LABEL} ${formatSignedGap(avg)}, centred on an average ${sample.color} game at ${formatSignedGap(baseline)}`}
      leading={
        // Phones shorten the label so it fits beside the value on one line.
        <span className="text-muted-foreground">
          <span className="sm:hidden">{EVAL_LABEL_SHORT}</span>
          <span className="max-sm:hidden">{EVAL_LABEL}</span>
        </span>
      }
      trailing={
        <EvalVerdictPopover
          testId={`${testId}-eval-info`}
          label={EVAL_LABEL}
          avgEvalPawns={avg}
          evalN={sample.evalN}
          color={sample.color}
          reason={openingVerdictReason(input)}
          ciLow={ciLow}
          ciHigh={ciHigh}
          pValue={pValue}
        />
      }
    />
  );
}

/** The Score and Eval verdicts read together in one muted line; eval counts only once tier 2. */
export function VerdictSentence({
  scoreInput,
  evalSample,
  testId,
}: {
  scoreInput: OpeningVerdictInput;
  evalSample: EvalSample;
  testId: string;
}) {
  const { tier2 } = useReadiness();
  const evalIn = tier2 ? evalVerdictInput(evalSample) : null;
  const sentence = openingVerdictSentence(
    openingVerdictReason(scoreInput),
    evalIn ? openingVerdictReason(evalIn) : null,
  );
  return (
    <p className="text-sm text-muted-foreground" data-testid={`${testId}-sentence`}>
      {sentence}
    </p>
  );
}

/**
 * The card body grid: the board left, the metrics column right, the verdict sentence under the
 * metrics from sm up. Phones are too narrow for that column, so the sentence spans the card.
 */
export function CardVerdictGrid({
  board,
  metrics,
  sentence,
}: {
  board: ReactNode;
  metrics: ReactNode;
  sentence: ReactNode;
}) {
  return (
    <div className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-3 gap-y-3 sm:gap-y-2.5">
      <div className="sm:row-span-2">{board}</div>
      <div className="flex min-w-0 flex-col gap-2.5">{metrics}</div>
      <div className="col-span-2 sm:col-span-1 sm:col-start-2">{sentence}</div>
    </div>
  );
}
