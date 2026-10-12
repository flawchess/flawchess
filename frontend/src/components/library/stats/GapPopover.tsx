/**
 * One popover per you-vs-opponents gap (D-00c), on the shared MetricInfoPopover shell:
 * a plain definition + "Fewer is better.", the You/Opponents rates with their unit, the
 * typical gap range in words with the verdict, the basis, then the counts, 95% CI and
 * p-value greyed below a separator. It says flaws, blunders or mistakes, never "events"
 * (D-00d). A zoneless cell has no range line (D-11); a low-sample cell says "Too few
 * flaws to call it." instead of a verdict (D-12). The benchmark basis (including the
 * D-08 stopgap) is deliberately silent here (D-09).
 */

import { MetricInfoPopover } from '@/components/ui/metric-info-popover';
import { formatPValue } from '@/components/endgames/stats/rankedMetrics';
import {
  effectiveVerdict,
  formatSignedGap,
  gapWords,
  type GapCell,
  type GapVerdict,
} from '@/lib/gapBar';

const FOOTER_SEPARATOR = ' · ';
/** Rates read to two decimals, like the tiles ("5.46 per 100 moves"). */
const RATE_DECIMALS = 2;
const COPY_TOO_FEW = 'Too few flaws to call it.';
const COPY_SAME = 'The same as the players you faced.';

export type GapUnit = 'per 100 moves' | 'per 100 games';

const VERDICT_SENTENCE: Record<GapVerdict, string> = {
  better: 'You are better than typical.',
  typical: 'You are typical.',
  worse: 'You are worse than typical.',
};

interface GapPopoverProps {
  /** `library-gap-{metric-key}-tc-{tc}`: only metric keys and the TC segment, never free values. */
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
}

function formatCount(value: number): string {
  return value.toLocaleString('en-US');
}

/** "That is 0.66 fewer than the players you faced." or the same-gap sentence. */
function gapSentence(delta: number): string {
  const words = gapWords(delta);
  return words === 'same' ? COPY_SAME : `That is ${words} than the players you faced.`;
}

/** The typical-range line; null for a zoneless cell with a normal sample (D-11). */
function rangeLine(cell: GapCell): string | null {
  if (!cell.hasZone) return cell.lowSample ? COPY_TOO_FEW : null;
  const range = `Typical gap for players at your level: ${gapWords(cell.zoneLo)} to ${gapWords(cell.zoneHi)}.`;
  const verdict = effectiveVerdict(cell);
  if (cell.lowSample) return `${range} ${COPY_TOO_FEW}`;
  return verdict === null ? range : `${range} ${VERDICT_SENTENCE[verdict]}`;
}

/** Greyed statistics line: counts, gap 95% CI and p-value, each only when present. */
function footerText(cell: GapCell, noun: string): string {
  const parts = [`${formatCount(cell.youEvents)} vs. ${formatCount(cell.oppEvents)} ${noun}`];
  if (cell.ciLow !== null && cell.ciHigh !== null) {
    parts.push(`gap 95% CI ${formatSignedGap(cell.ciLow)} to ${formatSignedGap(cell.ciHigh)}`);
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
}: GapPopoverProps) {
  const range = rangeLine(cell);
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
