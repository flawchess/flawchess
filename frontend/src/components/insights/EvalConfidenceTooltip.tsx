import type { ReactNode } from 'react';

type ConfidenceLevel = 'low' | 'medium' | 'high';

const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  low: 'Low confidence',
  medium: 'Medium confidence',
  high: 'High confidence',
};

interface EvalConfidenceTooltipProps {
  level: ConfidenceLevel;
  pValue: number;
  gameCount: number;
  /** Average eval at phase entry, in pawns (signed, user perspective). */
  evalMeanPawns: number;
  /** 95% CI lower bound for the eval mean (pawns). */
  evalCiLowPawns?: number | null;
  /** 95% CI upper bound for the eval mean (pawns). */
  evalCiHighPawns?: number | null;
}

function fmtSigned(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
}

/**
 * Tooltip body for the MG-entry eval bullet chart (one-sample z-test against
 * 0 cp). Used by BulletConfidencePopover. Shows the raw eval and CI in pawns.
 *
 * The chart is centered on 0 cp regardless of color; the per-color engine
 * baseline is a tick on the chart, not subtracted from the displayed mean
 * (260504-rvh).
 */
export function EvalConfidenceTooltip({
  level,
  pValue,
  gameCount,
  evalMeanPawns,
  evalCiLowPawns,
  evalCiHighPawns,
}: EvalConfidenceTooltipProps): ReactNode {
  const pValuePct = (pValue * 100).toFixed(1);
  const effectType = evalMeanPawns >= 0 ? 'advantage' : 'disadvantage';
  const verdictMap: Record<ConfidenceLevel, string> = {
    low: 'Could plausibly be chance',
    medium: 'Possibly a significant ' + effectType,
    high: 'Likely a significant ' + effectType,
  };

  const hasCi =
    evalCiLowPawns !== undefined &&
    evalCiLowPawns !== null &&
    evalCiHighPawns !== undefined &&
    evalCiHighPawns !== null;

  const evalLine = hasCi
    ? `${fmtSigned(evalMeanPawns)} pawns, 95% CI [${fmtSigned(evalCiLowPawns)}, ${fmtSigned(evalCiHighPawns)}]`
    : `${fmtSigned(evalMeanPawns)} pawns`;

  return (
    <div className="text-left">
      <ul className="list-disc pl-4 space-y-0.5">
        <li>Average eval: {evalLine}</li>
        <li>Number of games reaching middlegame: {gameCount}</li>
        <li>
          Probability: {pValuePct}% of such a difference from zero resulting from pure chance (p ={' '}
          {pValue.toFixed(3)})
        </li>
        <li>
          {CONFIDENCE_LABEL[level]}: {verdictMap[level]}
        </li>
      </ul>
      <p className="mt-1 opacity-70">* two-sided z-test vs 0 cp; no correction for multiple comparisons</p>
    </div>
  );
}
