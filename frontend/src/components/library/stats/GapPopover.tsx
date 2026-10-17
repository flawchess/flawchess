/**
 * One popover per you-vs-opponents gap, on the shared MetricInfoPopover shell:
 * a plain definition + "Fewer is better.", the You/Opponents rates with their unit, the
 * typical gap range in words with the verdict, the basis, then the counts, 99% CI and
 * p-value greyed below a separator. It says flaws, blunders or mistakes, never "events".
 * A zoneless cell has no range line; an out-of-band gap that is not
 * significant says it could be chance instead of a verdict. The benchmark basis
 * (including the blitz/bullet-reads-rapid stopgap) is deliberately silent here.
 */

import { MetricInfoPopover } from '@/components/ui/metric-info-popover';
import { COPY_CHANCE, formatPValue } from '@/components/endgames/stats/rankedMetrics';
import {
  GAP_SAME_WORD,
  effectiveVerdict,
  formatSignedGap,
  isChanceGap,
  gapWords,
  type GapCell,
  type GapVerdict,
} from '@/lib/gapBar';

const FOOTER_SEPARATOR = ' · ';
/** Rates read to two decimals, like the tiles ("5.46 per 100 moves"). */
const RATE_DECIMALS = 2;
const COPY_SAME = 'The same as the players you faced.';
// Defensive: all four shown tactic families have bands today, but a benchmark refresh could drop one.
const COPY_ZONELESS_SIGNIFICANT =
  'There is no typical range for this tactic, but the gap is too large to be chance.';

export type GapUnit = 'per 100 moves' | 'per 100 games';

const VERDICT_SENTENCE: Record<GapVerdict, string> = {
  better: 'You are better than typical.',
  typical: 'You are typical.',
  worse: 'You are worse than typical.',
};

interface GapPopoverProps {
  /** `gap-popover-{metric-key}-tc-{tc}`: only metric keys and the TC segment, never free values. */
  testId: string;
  label: string;
  /** One plain sentence about what the metric counts; "Fewer is better." is appended. */
  definition: string;
  unit: GapUnit;
  /** Plural noun for the footer counts: "blunders", "low-clock flaws". */
  noun: string;
  /** The "Based on your N analyzed rapid games in the current filters." line. */
  basis: string;
  cell: GapCell;
  /** Overrides the significance sentence of a zoneless significant cell (default names the tactic). */
  zonelessSignificantCopy?: string;
}

function formatCount(value: number): string {
  return value.toLocaleString('en-US');
}

/** "That is 0.66 fewer than the players you faced." or the same-gap sentence. */
function gapSentence(delta: number): string {
  const words = gapWords(delta);
  return words === GAP_SAME_WORD ? COPY_SAME : `That is ${words} than the players you faced.`;
}

/** The typical-range line; for a zoneless cell only the significance line. */
function rangeLine(cell: GapCell, zonelessSignificantCopy: string): string | null {
  if (!cell.hasZone) return effectiveVerdict(cell) === null ? null : zonelessSignificantCopy;
  const range = `Typical gap for players at your level: ${gapWords(cell.zoneLo)} to ${gapWords(cell.zoneHi)}.`;
  if (isChanceGap(cell)) return `${range} ${COPY_CHANCE}`;
  const verdict = effectiveVerdict(cell);
  return verdict === null ? range : `${range} ${VERDICT_SENTENCE[verdict]}`;
}

/** Greyed statistics line: counts, gap 99% CI and p-value, each only when present. */
function footerText(cell: GapCell, noun: string): string {
  const parts = [`${formatCount(cell.youEvents)} vs. ${formatCount(cell.oppEvents)} ${noun}`];
  if (cell.ciLow !== null && cell.ciHigh !== null) {
    parts.push(`gap 99% CI ${formatSignedGap(cell.ciLow)} to ${formatSignedGap(cell.ciHigh)}`);
  }
  if (cell.pValue !== null) parts.push(formatPValue(cell.pValue));
  return parts.join(FOOTER_SEPARATOR);
}

function GapPopoverBody({
  testId,
  label,
  definition,
  unit,
  noun,
  basis,
  cell,
  zonelessSignificantCopy = COPY_ZONELESS_SIGNIFICANT,
}: GapPopoverProps) {
  const range = rangeLine(cell, zonelessSignificantCopy);
  return (
    <div className="space-y-1.5">
      <p>
        <strong>{label}:</strong> {definition.replace(/\.$/, '')}. Fewer is better.
      </p>
      <p>
        <strong>
          You: {(cell.youRate ?? 0).toFixed(RATE_DECIMALS)} {unit}. Opponents:{' '}
          {(cell.oppRate ?? 0).toFixed(RATE_DECIMALS)}.
        </strong>{' '}
        {cell.delta !== null && gapSentence(cell.delta)}
      </p>
      <ul className="list-disc space-y-0.5 pl-4">
        {range !== null && <li>{range}</li>}
        <li>{basis}</li>
      </ul>
      <hr className="border-background/25" />
      <p className="italic text-background/60" data-testid={`${testId}-footer`}>
        {footerText(cell, noun)}
      </p>
    </div>
  );
}

export function GapPopover(props: GapPopoverProps) {
  return (
    <MetricInfoPopover testId={props.testId} ariaLabel={`About ${props.label}`}>
      <GapPopoverBody {...props} />
    </MetricInfoPopover>
  );
}
