import type { ReactNode } from 'react';

type ConfidenceLevel = 'low' | 'medium' | 'high';

const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  low: 'Low confidence',
  medium: 'Medium confidence',
  high: 'High confidence',
};

const CONFIDENCE_VERDICT: Record<ConfidenceLevel, (noun: string) => string> = {
  low: () => 'Could plausibly be chance',
  medium: (noun) => `Possibly a real ${noun}`,
  high: (noun) => `Likely a real ${noun}`,
};

interface ConfidenceTooltipContentProps {
  level: ConfidenceLevel;
  pValue: number;
  score: number;
  gameCount: number;
}

/**
 * Tooltip body for confidence indicators — renders a 4-bullet breakdown of the
 * score, sample size, p-value, and verdict. The verdict noun ("strength" vs
 * "weakness") is derived from the score's side of the 50% baseline.
 */
export function ConfidenceTooltipContent({
  level,
  pValue,
  score,
  gameCount,
}: ConfidenceTooltipContentProps): ReactNode {
  const noun: 'strength' | 'weakness' = score >= 0.5 ? 'strength' : 'weakness';
  const scorePct = Math.round(score * 100);
  const diffPct = Math.round(Math.abs(score * 100 - 50));
  const scoreLine =
    diffPct === 0
      ? `${scorePct}% (at 50% baseline)`
      : `${scorePct}% (${diffPct}% difference from 50% baseline)`;
  const pValuePct = (pValue * 100).toFixed(1);
  return (
    <div className="text-left">
      <ul className="list-disc pl-4 space-y-0.5">
        <li>Score: {scoreLine}</li>
        <li>Number of games: {gameCount}</li>
        <li>
          Probability: {pValuePct}% of such a difference resulting from pure chance (p ={' '}
          {pValue.toFixed(3)})
        </li>
        <li>
          {CONFIDENCE_LABEL[level]}: {CONFIDENCE_VERDICT[level](noun)}
        </li>
      </ul>
      <p className="mt-1 opacity-70">* no correction for multiple comparisons</p>
    </div>
  );
}
