import type { ReactNode } from 'react';
import { EVAL_NEUTRAL_MAX_PAWNS, EVAL_NEUTRAL_MIN_PAWNS } from '@/lib/openingStatsZones';

type ConfidenceLevel = 'low' | 'medium' | 'high';

const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
};

type Verdict = 'advantage' | 'disadvantage' | 'deviation';

function pickVerdict(evalMeanPawns: number): Verdict {
  if (evalMeanPawns >= EVAL_NEUTRAL_MAX_PAWNS) return 'advantage';
  if (evalMeanPawns <= EVAL_NEUTRAL_MIN_PAWNS) return 'disadvantage';
  return 'deviation';
}

function headline(level: ConfidenceLevel, evalMeanPawns: number): string {
  if (level === 'low') return 'Inconclusive.';
  const verdict = pickVerdict(evalMeanPawns);
  const lead = level === 'high' ? 'Likely' : 'Possibly';
  if (verdict === 'deviation') return `${lead} a real deviation from 0 pawns.`;
  return `${lead} a real ${verdict}.`;
}

function fmtSigned(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
}

interface EvalConfidenceTooltipProps {
  level: ConfidenceLevel;
  pValue: number;
  gameCount: number;
  /** Average eval at endgame entry, in pawns (signed, user perspective). */
  evalMeanPawns: number;
}

/**
 * Tooltip body for the Endgames entry-eval bullet chart (z-test against 0 cp).
 * Used by EvalConfidencePopover. Finding-first layout: signed-pawn metric
 * with inline explainer, then bold verdict + confidence, then italic footer
 * for the test legend. CI numbers are not shown in text — the bullet's whisker
 * carries that. The Openings End Eval uses EvalVerdictPopover instead.
 */
export function EvalConfidenceTooltip({
  level,
  pValue,
  gameCount,
  evalMeanPawns,
}: EvalConfidenceTooltipProps): ReactNode {
  return (
    <div className="text-left space-y-1">
      <p>
        <strong>{fmtSigned(evalMeanPawns)} pawns</strong> over {gameCount} games (average
        Stockfish eval at the position where the <em>endgame begins</em>).
      </p>
      <p>
        <strong>{headline(level, evalMeanPawns)}</strong> {CONFIDENCE_LABEL[level]} confidence
        (p = {pValue.toFixed(3)}).
      </p>
      <p className="opacity-70 italic">
        Test: two-sided Wald z vs 0 pawns.<br />
        Confidence interval: Wald 95% (whiskers).
      </p>
    </div>
  );
}
