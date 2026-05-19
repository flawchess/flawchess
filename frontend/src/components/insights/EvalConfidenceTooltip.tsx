import type { ReactNode } from 'react';
import {
  EVAL_BASELINE_PAWNS_BLACK,
  EVAL_BASELINE_PAWNS_WHITE,
  EVAL_NEUTRAL_MAX_PAWNS,
  EVAL_NEUTRAL_MIN_PAWNS,
} from '@/lib/openingStatsZones';

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
  /** Average eval at phase entry, in pawns (signed, user perspective). */
  evalMeanPawns: number;
  /** User's color for this row — drives which per-color baseline tick is shown. */
  color: 'white' | 'black';
  /** Whether the bullet chart renders a per-color baseline tick. When false
   * (endgame entry eval is color-agnostic), the tick legend line is hidden. */
  showBaselineTick?: boolean;
  /** Which game phase the averaged eval is sampled at. 'opening-end' (default)
   * = end of the openings containing this position (move explorer / Openings).
   * 'endgame-entry' = the position where the endgame begins (Endgames Games
   * subtab), matching the Stats-tab "Endgame Entry Eval" metric. */
  evalContext?: 'opening-end' | 'endgame-entry';
}

/**
 * Tooltip body for the MG-entry eval bullet chart (z-test against 0 cp).
 * Used by BulletConfidencePopover. Finding-first layout: signed-pawn metric
 * with inline explainer, then bold verdict + confidence, then italic footer
 * for the chart-decoration legend. CI numbers are not shown in text — the
 * bullet's whisker carries that.
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
  color,
  showBaselineTick = true,
  evalContext = 'opening-end',
}: EvalConfidenceTooltipProps): ReactNode {
  const baselinePawns =
    color === 'white' ? EVAL_BASELINE_PAWNS_WHITE : EVAL_BASELINE_PAWNS_BLACK;
  const evalPhraseClause =
    evalContext === 'endgame-entry' ? (
      <>
        average Stockfish eval at the position where the <em>endgame begins</em>
      </>
    ) : (
      <>
        average Stockfish eval at the <em>end</em> of your openings which include this position
      </>
    );
  return (
    <div className="text-left space-y-1">
      <p>
        <strong>{fmtSigned(evalMeanPawns)} pawns</strong> over {gameCount} games ({evalPhraseClause}).
      </p>
      <p>
        <strong>{headline(level, evalMeanPawns)}</strong> {CONFIDENCE_LABEL[level]} confidence
        (p = {pValue.toFixed(3)}).
      </p>
      <p className="opacity-70 italic">
        {showBaselineTick && (
          <>
            Dashed tick: typical eval for {color} ({fmtSigned(baselinePawns)} pawns).<br />
          </>
        )}
        Test: two-sided Wald z vs 0 pawns.<br />
        Confidence interval: Wald 95% (whiskers).
      </p>
    </div>
  );
}
