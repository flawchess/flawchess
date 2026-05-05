import type { ReactNode } from 'react';

type ConfidenceLevel = 'low' | 'medium' | 'high';

const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
};

// Score-zone boundaries match arrowColor.ts: scores in (0.45, 0.55) are the
// neutral zone; >=0.55 is a strength, <=0.45 a weakness. The strength/weakness
// label only fires when the user's score is outside that band — inside it, a
// statistically significant gap is reported as a "real difference from the
// 50% baseline" without claiming directional advantage.
const NEUTRAL_LOWER = 0.45;
const NEUTRAL_UPPER = 0.55;

type Verdict = 'strength' | 'weakness' | 'difference';

function pickVerdict(score: number): Verdict {
  if (score >= NEUTRAL_UPPER) return 'strength';
  if (score <= NEUTRAL_LOWER) return 'weakness';
  return 'difference';
}

function headline(level: ConfidenceLevel, score: number): string {
  if (level === 'low') return 'Could plausibly be chance.';
  const verdict = pickVerdict(score);
  const lead = level === 'high' ? 'Likely' : 'Possibly';
  if (verdict === 'difference') return `${lead} a real difference from the 50% baseline.`;
  return `${lead} a real ${verdict}.`;
}

function statsLine(score: number, gameCount: number): string {
  const scorePct = (score * 100).toFixed(1);
  const diffPct = Math.abs(score * 100 - 50).toFixed(1);
  if (diffPct === '0.0') {
    return `${scorePct}% score over ${gameCount} games, at the 50% baseline.`;
  }
  const direction = score >= 0.5 ? 'above' : 'below';
  return `${scorePct}% score over ${gameCount} games, ${diffPct}% ${direction} the 50% baseline.`;
}

interface WdlConfidenceTooltipProps {
  level: ConfidenceLevel;
  pValue: number;
  score: number;
  gameCount: number;
}

/**
 * Tooltip body for WDL-context confidence indicators (two-sided Wald test
 * against the 50% baseline). Used by OpeningFindingCard (via ScoreConfidencePopover),
 * the move-explorer Score column, and the stats-board Score bullet popover.
 */
export function WdlConfidenceTooltip({
  level,
  pValue,
  score,
  gameCount,
}: WdlConfidenceTooltipProps): ReactNode {
  return (
    <div className="text-left space-y-1">
      <p>
        <strong>{headline(level, score)}</strong> {CONFIDENCE_LABEL[level]} confidence
        (p = {pValue.toFixed(3)}).
      </p>
      <p>{statsLine(score, gameCount)}</p>
      <p className="opacity-70 italic">Score = wins + ½ draws<br/> Error bars = 95% confidence interval</p>
    </div>
  );
}
