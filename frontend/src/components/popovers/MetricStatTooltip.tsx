/**
 * MetricStatTooltip — pure-markup tooltip BODY shared by the 6 tooltips in the
 * "Endgame Overall Performance" section. The Radix popover shell lives in
 * MetricStatPopover.tsx; this file owns the 4-paragraph anatomy only:
 *
 *   1. Bold name + inline explanation.
 *   2. Value line: "{maybe-signed value} {name} over {N} games, {distance} {direction} the {baselineLabel} baseline."
 *      (pawns variant: "{signed} pawns over {N} games." — no baseline-distance text)
 *   3. Headline verdict + Confidence + optional p-value: e.g. "Likely a real strength. High confidence (p = 0.001)."
 *   4. Optional "Last played: …" line, then italic methodology footer.
 *
 * Vocabulary switch:
 *   - 'score' → strength / weakness / difference (score-based metrics, 5/6 tooltips)
 *   - 'eval'  → advantage / disadvantage / deviation (eval-based metric, 1/6: Endgame Entry Eval)
 *
 * Sign convention:
 *   - percent unit + baseline === 0 (gap metrics) → signed value (+7.0%, -5.0%)
 *   - percent unit + baseline === 0.5 (score-vs-50%) → unsigned (62.0%)
 *   - pawns unit → always signed (+0.42, -1.00)
 *
 * Quick task 260514-i3l.
 *
 * Font-size note: this body uses inherited sizing — the wrapping
 * PopoverPrimitive.Content in MetricStatPopover sets text-xs to match the
 * existing hover-popover convention (ScoreGapPopover, AchievableScorePopover,
 * BulletConfidencePopover all use text-xs). This is a deliberate exception to
 * the CLAUDE.md "minimum text-sm" rule for the popover layer only — the rule
 * is honored everywhere else in the section (Endgames page body copy is
 * text-sm or larger).
 */

import type { ReactNode } from 'react';

import { formatAbsoluteDate, formatRelativeDate } from '@/lib/relativeDate';
import type { ConfidenceLevel } from '@/lib/scoreConfidence';

const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
};

const ZERO_DIFF_PCT_STRING = '0.0%';
const GAP_BASELINE = 0;

type ScoreVerdict = 'strength' | 'weakness' | 'difference';
type EvalVerdict = 'advantage' | 'disadvantage' | 'deviation';
type Verdict = ScoreVerdict | EvalVerdict;

export type MetricVocabulary = 'score' | 'eval';
export type MetricUnit = 'percent' | 'pawns';

export interface MetricStatTooltipProps {
  /** Bold metric name in paragraph 1 (e.g. "Endgame Score"). */
  name: string;
  /** 1-2 sentence inline explanation rendered next to the bold name. */
  explanation: ReactNode;
  /** The metric's measured value (percent: fraction in [0, 1] or [-1, 1] for gaps;
   *  pawns: signed pawn units). */
  value: number;
  /** Reference baseline for the verdict / direction text. Common values:
   *  0.5 (score-vs-50%), 0 (gap metrics / eval-vs-0-pawns). */
  baseline: number;
  /** Display unit for the value line. */
  unit: MetricUnit;
  /** Sample size for the test. */
  gameCount: number;
  /** Confidence bucket derived from p-value + n gate. */
  level: ConfidenceLevel;
  /** Raw p-value from the backend. Null when below the reliability gate —
   *  the " (p = X.XXX)" segment is omitted then. */
  pValue: number | null;
  /** Vocabulary switch for the verdict noun. */
  vocabulary: MetricVocabulary;
  /** Lower edge of the neutral band (e.g. 0.45 for score, -0.75 for endgame
   *  entry eval). Values < neutralLower → weakness/disadvantage. */
  neutralLower: number;
  /** Upper edge of the neutral band. Values > neutralUpper → strength/advantage. */
  neutralUpper: number;
  /** Human-readable baseline reference (e.g. "50%", "0%", "0 pawns"). */
  baselineLabel: string;
  /** Italic methodology footer (test name + CI method). */
  methodology: ReactNode;
  /** Optional ISO 8601 timestamp; when set, renders a "Last played: …" line. */
  lastPlayedAt?: string | null;
  /** When true, qualifies score-vocabulary verdicts as "relative strength" /
   *  "relative weakness". Used by Endgame Score Gap (0% baseline): the gap is
   *  relative to the player's own non-endgame score, not an absolute win
   *  rate, so unqualified "strength"/"weakness" overclaims for players whose
   *  absolute scores are uniformly high or low. */
  relative?: boolean;
  /** When true (and pendingCount > 0), shows a one-line pending-analysis caveat
   * at the bottom of the tooltip body. Default false — backwards-compatible. */
  isPending?: boolean;
  /** Number of games still pending Stockfish analysis. Used in caveat copy. */
  pendingCount?: number;
}

function pickVerdict(
  vocabulary: MetricVocabulary,
  value: number,
  neutralLower: number,
  neutralUpper: number,
): Verdict {
  if (vocabulary === 'score') {
    if (value >= neutralUpper) return 'strength';
    if (value <= neutralLower) return 'weakness';
    return 'difference';
  }
  if (value >= neutralUpper) return 'advantage';
  if (value <= neutralLower) return 'disadvantage';
  return 'deviation';
}

function headline(
  level: ConfidenceLevel,
  verdict: Verdict,
  baselineLabel: string,
  relative: boolean,
): string {
  if (level === 'low') return 'Inconclusive.';
  const lead = level === 'high' ? 'Likely' : 'Possibly';
  if (verdict === 'difference') {
    return `${lead} a real difference from the ${baselineLabel} baseline.`;
  }
  if (verdict === 'deviation') {
    return `${lead} a real deviation from ${baselineLabel}.`;
  }
  const qualifier = relative ? 'relative ' : '';
  return `${lead} a real ${qualifier}${verdict}.`;
}

function renderPercentValueLine(
  name: string,
  value: number,
  baseline: number,
  baselineLabel: string,
  gameCount: number,
): ReactNode {
  const valuePct = (value * 100).toFixed(1) + '%';
  const diffPct = Math.abs(value * 100 - baseline * 100).toFixed(1) + '%';
  const direction = value >= baseline ? 'above' : 'below';
  // Only sign the value for gap metrics (baseline = 0); score-vs-50% reads as
  // unsigned percentage by convention.
  const sign = baseline === GAP_BASELINE && value >= 0 ? '+' : '';
  if (diffPct === ZERO_DIFF_PCT_STRING) {
    return (
      <>
        <strong>
          {sign}
          {valuePct} {name}
        </strong>{' '}
        over {gameCount} games, at the {baselineLabel} baseline.
      </>
    );
  }
  return (
    <>
      <strong>
        {sign}
        {valuePct} {name}
      </strong>{' '}
      over {gameCount} games, {diffPct} {direction} the {baselineLabel} baseline.
    </>
  );
}

function renderPawnsValueLine(
  value: number,
  gameCount: number,
): ReactNode {
  const sign = value >= 0 ? '+' : '';
  const signed = `${sign}${value.toFixed(2)}`;
  return (
    <>
      <strong>{signed} pawns</strong> over {gameCount} games.
    </>
  );
}

export function MetricStatTooltip({
  name,
  explanation,
  value,
  baseline,
  unit,
  gameCount,
  level,
  pValue,
  vocabulary,
  neutralLower,
  neutralUpper,
  baselineLabel,
  methodology,
  lastPlayedAt,
  relative = false,
  isPending = false,
  pendingCount = 0,
}: MetricStatTooltipProps): ReactNode {
  const verdict = pickVerdict(vocabulary, value, neutralLower, neutralUpper);
  const headlineText = headline(level, verdict, baselineLabel, relative);
  const valueLine =
    unit === 'percent'
      ? renderPercentValueLine(name, value, baseline, baselineLabel, gameCount)
      : renderPawnsValueLine(value, gameCount);

  return (
    <div className="text-left space-y-1">
      <p>
        <strong>{name}:</strong> {explanation}
      </p>
      <p>{valueLine}</p>
      <p>
        <strong>{headlineText}</strong> {CONFIDENCE_LABEL[level]} confidence
        {pValue !== null ? ` (p = ${pValue.toFixed(3)})` : ''}.
      </p>
      {lastPlayedAt && (
        <p>
          <strong>Last played</strong>:{' '}
          <span title={formatAbsoluteDate(lastPlayedAt)}>
            {formatRelativeDate(lastPlayedAt)}
          </span>
        </p>
      )}
      <p className="opacity-70 italic">{methodology}</p>
      {isPending === true && (pendingCount ?? 0) > 0 && (
        <p className="opacity-70">
          Based on currently-evaluated games. {(pendingCount ?? 0).toLocaleString()} more being
          analysed — refresh in a few minutes for updated values.
        </p>
      )}
    </div>
  );
}
