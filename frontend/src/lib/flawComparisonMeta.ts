/**
 * Metadata for the Library Stats you-vs-opponents views (Phase 239, sketch 010 round 5).
 *
 * Holds FLAW_GAP_META (label, hint, definition, noun for the 12 gap metrics),
 * CONTEXT_TAG_CARDS (the four cards over the 10 context tags), flawBulletToGapCell /
 * flawMetricCell (API bullet -> gap-bar view model), libraryBasisText / librarySectionBasisText (the basis lines), and the FlawIcon
 * type shared with the Flaws filter panel.
 *
 * Read by the Library Stats tiles (FlawTiles), the context-tag cards,
 * and FlawFilterControl (FlawIcon only). The Phase 115 comparison-grid metadata (family
 * colours, per-tag icons, confidence/significance helpers) was retired with the grid.
 *
 * Definitions reuse TAG_DEFINITIONS (the Game / Flaw card tag tooltips) wherever a gap
 * metric maps onto a FlawTag; blunder and mistake carry their own threshold sentence.
 */

import type { ComponentType, CSSProperties } from 'react';

import { TAG_DEFINITIONS } from '@/lib/tagDefinitions';
import { BLUNDER_DROP, MISTAKE_DROP, TIME_PRESSURE_CLOCK_FRACTION } from '@/generated/flawThresholds';
import type { GapCell } from '@/lib/gapBar';
import type { FlawBullet, FlawComparisonTc, FlawDeltaMetric } from '@/types/library';
import type { TimeControlBucket } from '@/types/endgames';

/**
 * Icon shape shared by lucide icons and our custom severity-glyph badges
 * (BlunderIcon / MistakeIcon). Both accept className + style + aria-hidden, so
 * the Flaws filter panel can render either without branching.
 */
export type FlawIcon = ComponentType<{
  className?: string;
  style?: CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}>;

// ─── Gap metadata per metric ──────────────────────────────────────────────────

const PERCENT_POINTS = 100;
const BLUNDER_POINTS = Math.round(BLUNDER_DROP * PERCENT_POINTS);
const MISTAKE_POINTS = Math.round(MISTAKE_DROP * PERCENT_POINTS);
const LOW_CLOCK_PERCENT = Math.round(TIME_PRESSURE_CLOCK_FRACTION * PERCENT_POINTS);

export interface FlawGapMeta {
  label: string;
  /** The one-line plain hint under a row label (sketch META). */
  hint: string;
  /** The popover's first sentence, from the tag definitions (D-00c). */
  definition: string;
  /** Plural noun for the popover counts (D-00d: flaws, never events). */
  noun: string;
}

const BLUNDER_HINT = `Moves that dropped your expected score by ${BLUNDER_POINTS}+ points`;
const MISTAKE_HINT = `Moves that dropped your expected score by ${MISTAKE_POINTS} to ${BLUNDER_POINTS} points`;

/** Label, hint, definition and noun for each of the 12 gap metrics. */
export const FLAW_GAP_META: Record<FlawDeltaMetric, FlawGapMeta> = {
  blunder: { label: 'Blunders', hint: BLUNDER_HINT, definition: BLUNDER_HINT, noun: 'blunders' },
  mistake: { label: 'Mistakes', hint: MISTAKE_HINT, definition: MISTAKE_HINT, noun: 'mistakes' },
  low_clock: {
    label: 'Low-clock',
    hint: `Flaws with under ${LOW_CLOCK_PERCENT}% of your time left`,
    definition: TAG_DEFINITIONS['low-clock'],
    noun: 'low-clock flaws',
  },
  hasty: {
    label: 'Hasty',
    hint: 'Flaws played fast while you still had time',
    definition: TAG_DEFINITIONS['hasty'],
    noun: 'hasty flaws',
  },
  unrushed: {
    label: 'Unrushed',
    hint: 'Flaws despite taking your time',
    definition: TAG_DEFINITIONS['unrushed'],
    noun: 'unrushed flaws',
  },
  opening: {
    label: 'Opening',
    hint: 'Flaws in the opening',
    definition: TAG_DEFINITIONS['opening'],
    noun: 'opening flaws',
  },
  middlegame: {
    label: 'Middlegame',
    hint: 'Flaws in the middlegame',
    definition: TAG_DEFINITIONS['middlegame'],
    noun: 'middlegame flaws',
  },
  endgame_phase: {
    label: 'Endgame',
    hint: 'Flaws in the endgame',
    definition: TAG_DEFINITIONS['endgame'],
    noun: 'endgame flaws',
  },
  miss: {
    label: 'Miss',
    hint: 'Your opponent erred and you missed it',
    definition: TAG_DEFINITIONS['miss'],
    noun: 'misses',
  },
  lucky: {
    label: 'Lucky',
    hint: 'Your flaw went unpunished',
    definition: TAG_DEFINITIONS['lucky'],
    noun: 'lucky flaws',
  },
  reversed: {
    label: 'Reversed',
    hint: 'Winning position turned into a losing one',
    definition: TAG_DEFINITIONS['reversed'],
    noun: 'reversals',
  },
  squandered: {
    label: 'Squandered',
    hint: 'Winning position thrown back to equal',
    definition: TAG_DEFINITIONS['squandered'],
    noun: 'squandered wins',
  },
};

// ─── You vs. your opponents: the four context-tag cards (D-00f, D-13) ──────────

export type ContextTagCardKey = 'clock' | 'phase' | 'opponent_errors' | 'lost_advantages';

/** The 10 context tags; blunder and mistake have tiles, never rows here (D-13). */
export type ContextTagMetric = Exclude<FlawDeltaMetric, 'blunder' | 'mistake'>;

export interface ContextTagCardDef {
  key: ContextTagCardKey;
  title: string;
  /** Muted one-liner next to the title (sketch 010 GROUPS). */
  subtitle: string;
  metrics: readonly ContextTagMetric[];
}

/** The four cards in display order, each with its tag rows in display order (no combo row). */
export const CONTEXT_TAG_CARDS: readonly ContextTagCardDef[] = [
  {
    key: 'clock',
    title: 'Clock',
    subtitle: 'how much time you had',
    metrics: ['low_clock', 'hasty', 'unrushed'],
  },
  {
    key: 'phase',
    title: 'Game phase',
    subtitle: 'where the flaw happened',
    metrics: ['opening', 'middlegame', 'endgame_phase'],
  },
  {
    key: 'opponent_errors',
    title: 'Opponent errors',
    subtitle: 'chances you missed or got',
    metrics: ['miss', 'lucky'],
  },
  {
    key: 'lost_advantages',
    title: 'Lost advantages',
    subtitle: 'what the flaw cost',
    metrics: ['reversed', 'squandered'],
  },
];

/** `low_clock` -> `low-clock`: the metric segment of the gap testids. */
export function metricTestIdSegment(metric: FlawDeltaMetric): string {
  return metric.replace(/_/g, '-');
}

/** Adapt one API bullet to the gap-bar view model (the components never see API types). */
export function flawBulletToGapCell(b: FlawBullet): GapCell {
  return {
    delta: b.delta,
    zoneLo: b.zone_lo,
    zoneHi: b.zone_hi,
    hasZone: b.has_zone,
    lowSample: b.low_sample,
    youRate: b.player_rate,
    oppRate: b.opp_rate,
    ciLow: b.ci_low,
    ciHigh: b.ci_high,
    pValue: b.p_value,
    youEvents: b.player_events,
    oppEvents: b.opp_events,
  };
}

/** The gap-bar cell of one metric in a TC entry; null when the payload carries no such bullet. */
export function flawMetricCell(tcStats: FlawComparisonTc, metric: FlawDeltaMetric): GapCell | null {
  const bullet = tcStats.bullets.find((b) => b.tag === metric);
  return bullet ? flawBulletToGapCell(bullet) : null;
}

function scopeText(analyzedN: number, tc: TimeControlBucket): string {
  return `your ${analyzedN.toLocaleString('en-US')} analyzed ${tc} games in the current filters.`;
}

/** The popover basis line: "Based on your 1,841 analyzed rapid games in the current filters." */
export function libraryBasisText(analyzedN: number, tc: TimeControlBucket): string {
  return `Based on ${scopeText(analyzedN, tc)}`;
}

/** The section basis line under a heading: "Your 1,841 analyzed rapid games in the current filters." */
export function librarySectionBasisText(analyzedN: number, tc: TimeControlBucket): string {
  const text = scopeText(analyzedN, tc);
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
}
