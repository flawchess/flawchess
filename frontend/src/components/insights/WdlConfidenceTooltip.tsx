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

interface WdlConfidenceTooltipProps {
  level: ConfidenceLevel;
  pValue: number;
  score: number;
  gameCount: number;
}

/**
 * Tooltip body for WDL-context confidence indicators (binomial-style test
 * against the 50% baseline). Used by OpeningFindingCard and the move-explorer
 * confidence column.
 */
export function WdlConfidenceTooltip({
  level,
  pValue,
  score,
  gameCount,
}: WdlConfidenceTooltipProps): ReactNode {
  const pValuePct = (pValue * 100).toFixed(1);
  const noun: 'strength' | 'weakness' = score >= 0.5 ? 'strength' : 'weakness';
  const scorePct = (score * 100).toFixed(1);
  const diffPct = Math.abs(score * 100 - 50).toFixed(1);
  const scoreLine =
    diffPct === '0.0'
      ? `${scorePct}% (at 50% baseline)`
      : `${scorePct}% (${diffPct}% difference from 50% baseline)`;
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
