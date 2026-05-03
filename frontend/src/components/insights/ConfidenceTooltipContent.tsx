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
  /**
   * When provided, renders an eval-context tooltip instead of WDL score context.
   * Value is the average eval at phase entry in pawns (signed, user perspective).
   */
  evalMeanPawns?: number | null;
}

/**
 * Tooltip body for confidence indicators.
 *
 * Two rendering modes:
 * - WDL mode (evalMeanPawns not provided): shows score, game count, p-value, and
 *   strength/weakness verdict. Used by OpeningFindingCard.
 * - Eval mode (evalMeanPawns provided): shows the Stockfish mean eval, game count,
 *   p-value, and a neutral "significant/not significant" verdict. Used by
 *   MostPlayedOpeningsTable eval-confidence pills.
 */
export function ConfidenceTooltipContent({
  level,
  pValue,
  score,
  gameCount,
  evalMeanPawns,
}: ConfidenceTooltipContentProps): ReactNode {
  const pValuePct = (pValue * 100).toFixed(1);

  if (evalMeanPawns !== undefined && evalMeanPawns !== null) {
    // Eval context: one-sample t-test against zero (avg eval != 0 at phase entry).
    const sign = evalMeanPawns >= 0 ? '+' : '';
    const evalLine = `${sign}${evalMeanPawns.toFixed(2)} pawns (avg at phase entry)`;
    const verdictMap: Record<ConfidenceLevel, string> = {
      low: 'Could plausibly be chance',
      medium: 'Possibly a significant eval advantage/disadvantage',
      high: 'Likely a significant eval advantage/disadvantage',
    };
    return (
      <div className="text-left">
        <ul className="list-disc pl-4 space-y-0.5">
          <li>Avg eval: {evalLine}</li>
          <li>Number of games: {gameCount}</li>
          <li>
            Probability: {pValuePct}% that this differs from 0 by chance (p ={' '}
            {pValue.toFixed(3)})
          </li>
          <li>
            {CONFIDENCE_LABEL[level]}: {verdictMap[level]}
          </li>
        </ul>
        <p className="mt-1 opacity-70">* one-sample t-test vs 0; no correction for multiple comparisons</p>
      </div>
    );
  }

  // WDL context: binomial-style confidence against 50% baseline.
  const noun: 'strength' | 'weakness' = score >= 0.5 ? 'strength' : 'weakness';
  const scorePct = Math.round(score * 100);
  const diffPct = Math.round(Math.abs(score * 100 - 50));
  const scoreLine =
    diffPct === 0
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
