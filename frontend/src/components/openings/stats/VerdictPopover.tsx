/**
 * Info popovers for the Openings verdict cells (End Eval bar, repertoire card Score and Eval), on the shared MetricInfoPopover shell:
 * what the metric is and that higher is better, the raw value against an average game of the
 * colour, the typical range around that baseline with the verdict reason, then the 99% CI,
 * p-value (with its reference) and n greyed below a separator. Plain words only: no unit name,
 * no statistics jargon (popover copy minimalism).
 */

import { MetricInfoPopover } from '@/components/ui/metric-info-popover';
import { COPY_CHANCE, formatPValue } from '@/components/endgames/stats/rankedMetrics';
import { formatSignedGap } from '@/lib/gapBar';
import {
  EVAL_VERDICT_BAND,
  SCORE_VERDICT_BAND,
  evalBaselinePawns,
  formatScorePercent,
  type OpeningVerdictReason,
} from '@/lib/openingVerdict';

const FOOTER_SEPARATOR = ' · ';
/** A distance that rounds to 0.00 reads "about the same as an average game". */
const DISTANCE_DECIMALS = 2;
const DISTANCE_SAME_BELOW = 0.005;

const COPY_TOO_FEW = 'Too few games to call it.';
const COPY_TYPICAL = 'That is typical.';
const COPY_BASELINE =
  'White moves first, so an average game reaches the middlegame at about +0.25 for White and −0.25 for Black. The bar is centred there; the faint tick is 0 (equal).';

const REASON_SENTENCE: Record<OpeningVerdictReason, (side: string) => string> = {
  'too-few': () => COPY_TOO_FEW,
  typical: () => COPY_TYPICAL,
  chance: () => COPY_CHANCE,
  better: (side) => `You come out of the opening clearly better than an average ${side} game.`,
  worse: (side) => `You come out of the opening clearly worse than an average ${side} game.`,
};

const SCORE_REASON_SENTENCE: Record<OpeningVerdictReason, string> = {
  'too-few': COPY_TOO_FEW,
  typical: COPY_TYPICAL,
  chance: COPY_CHANCE,
  better: 'You score clearly above 50%.',
  worse: 'You score clearly below 50%.',
};
const SCORE_REFERENCE_TEXT = '50%';

interface EvalVerdictPopoverProps {
  /** Trigger testid (a fixed literal; it becomes the Umami popover-open target). */
  testId: string;
  label: string;
  avgEvalPawns: number;
  evalN: number;
  color: 'white' | 'black';
  reason: OpeningVerdictReason;
  ci99Low: number | null;
  ci99High: number | null;
  /** p-value of the mean against the colour baseline. */
  pValue: number | null;
}

/** "0.41 better than an average White game (+0.25)" or the same-as sentence. */
function distanceText(delta: number, side: string, baselineText: string): string {
  const distance = Math.abs(delta);
  if (distance < DISTANCE_SAME_BELOW) return `about the same as an average ${side} game`;
  const direction = delta > 0 ? 'better' : 'worse';
  return `${distance.toFixed(DISTANCE_DECIMALS)} ${direction} than an average ${side} game (${baselineText})`;
}

/** Greyed statistics line: 99% CI, p-value vs the baseline, n; each only when present. */
function footerText(
  ci99Low: number | null,
  ci99High: number | null,
  pValue: number | null,
  baselineText: string,
  evalN: number,
): string {
  const parts: string[] = [];
  if (ci99Low !== null && ci99High !== null) {
    parts.push(`99% CI ${formatSignedGap(ci99Low)} to ${formatSignedGap(ci99High)}`);
  }
  if (pValue !== null) parts.push(`${formatPValue(pValue)} vs ${baselineText}`);
  parts.push(`n = ${evalN.toLocaleString('en-US')}`);
  return parts.join(FOOTER_SEPARATOR);
}

export function EvalVerdictPopover({
  testId,
  label,
  avgEvalPawns,
  evalN,
  color,
  reason,
  ci99Low,
  ci99High,
  pValue,
}: EvalVerdictPopoverProps) {
  const side = color === 'black' ? 'Black' : 'White';
  const baseline = evalBaselinePawns(color);
  const baselineText = formatSignedGap(baseline);
  const typicalRange = `${formatSignedGap(baseline - EVAL_VERDICT_BAND)} to ${formatSignedGap(baseline + EVAL_VERDICT_BAND)}`;
  return (
    <MetricInfoPopover testId={testId} ariaLabel={`About ${label}`}>
      <div className="space-y-1.5">
        <p>
          <strong>{label}:</strong> the average engine evaluation when your games reach the
          middlegame, from your side. Higher is better.
        </p>
        <p>
          <strong>You: {formatSignedGap(avgEvalPawns)}</strong>,{' '}
          {distanceText(avgEvalPawns - baseline, side, baselineText)}.
        </p>
        <ul className="list-disc space-y-0.5 pl-4">
          <li>{COPY_BASELINE}</li>
          <li>
            Typical: {typicalRange}. {REASON_SENTENCE[reason](side)}
          </li>
        </ul>
        <hr className="border-background/25" />
        <p className="italic text-background/60" data-testid={`${testId}-footer`}>
          {footerText(ci99Low, ci99High, pValue, baselineText, evalN)}
        </p>
      </div>
    </MetricInfoPopover>
  );
}

interface ScoreVerdictPopoverProps {
  /** Trigger testid (numeric indices only; it becomes the Umami popover-open target). */
  testId: string;
  score: number;
  games: number;
  wins: number;
  draws: number;
  losses: number;
  reason: OpeningVerdictReason;
  ci99Low: number | null;
  ci99High: number | null;
  /** p-value of the score against 50%. */
  pValue: number | null;
}

/** Greyed statistics line for the score: 99% CI as percentages, p-value vs 50%, n. */
function scoreFooterText(
  ci99Low: number | null,
  ci99High: number | null,
  pValue: number | null,
  games: number,
): string {
  const parts: string[] = [];
  if (ci99Low !== null && ci99High !== null) {
    parts.push(`99% CI ${formatScorePercent(ci99Low)} to ${formatScorePercent(ci99High)}`);
  }
  if (pValue !== null) parts.push(`${formatPValue(pValue)} vs ${SCORE_REFERENCE_TEXT}`);
  parts.push(`n = ${games.toLocaleString('en-US')}`);
  return parts.join(FOOTER_SEPARATOR);
}

export function ScoreVerdictPopover({
  testId,
  score,
  games,
  wins,
  draws,
  losses,
  reason,
  ci99Low,
  ci99High,
  pValue,
}: ScoreVerdictPopoverProps) {
  const typicalRange = `${formatScorePercent(0.5 - SCORE_VERDICT_BAND)} to ${formatScorePercent(0.5 + SCORE_VERDICT_BAND)}`;
  return (
    <MetricInfoPopover testId={testId} ariaLabel="About Score">
      <div className="space-y-1.5">
        <p>
          <strong>Score:</strong> wins plus half the draws, as a percentage of your games. 50% means
          you break even.
        </p>
        <p>
          <strong>You: {formatScorePercent(score)}</strong> over {games.toLocaleString('en-US')}{' '}
          games ({wins}W {draws}D {losses}L).
        </p>
        <ul className="list-disc space-y-0.5 pl-4">
          <li>
            Typical: {typicalRange}. {SCORE_REASON_SENTENCE[reason]}
          </li>
        </ul>
        <hr className="border-background/25" />
        <p className="italic text-background/60" data-testid={`${testId}-footer`}>
          {scoreFooterText(ci99Low, ci99High, pValue, games)}
        </p>
      </div>
    </MetricInfoPopover>
  );
}
