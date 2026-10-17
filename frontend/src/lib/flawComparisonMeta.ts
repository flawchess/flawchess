/**
 * Metadata for the Library Stats you-vs-opponents views.
 *
 * Holds FLAW_GAP_META (label, hint, definition, noun for the 12 gap metrics),
 * CONTEXT_TAG_CARDS (the four cards over the 10 context tags), flawBulletToGapCell /
 * flawMetricCell / tempoPhaseGapCell (API bullet or crossed tempo x phase cell ->
 * gap-bar view model), TEMPO_PHASE_TEMPOS / TEMPO_PHASE_PHASES (the heatmap axes), libraryBasisText /
 * libraryCoverageBasisText (the basis lines), and the FlawIcon type shared with the Flaws
 * filter panel.
 *
 * Read by the Library Stats tiles (FlawTiles), the context-tag cards,
 * and FlawFilterControl (FlawIcon only).
 *
 * Definitions reuse TAG_DEFINITIONS (the Game / Flaw card tag tooltips) wherever a gap
 * metric maps onto a FlawTag; blunder and mistake carry their own threshold sentence.
 */

import type { ComponentType, CSSProperties } from 'react';

import { TAG_DEFINITIONS } from '@/lib/tagDefinitions';
import { BLUNDER_DROP, MISTAKE_DROP, TIME_PRESSURE_CLOCK_FRACTION } from '@/generated/flawThresholds';
import type { GapCell } from '@/lib/gapBar';
import type {
  FlawBullet,
  FlawComparisonTc,
  FlawDeltaMetric,
  FlawPhaseMetric,
  FlawTempoMetric,
} from '@/types/library';
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
  /** The one-line plain hint under a row label. */
  hint: string;
  /** The popover's first sentence, from the tag definitions. */
  definition: string;
  /** Plural noun for the popover counts (flaws, never events). */
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

// ─── You vs. your opponents: the four context-tag cards ─────────────────────────

export type ContextTagCardKey = 'clock' | 'phase' | 'opponent_errors' | 'lost_advantages';

/** The 10 context tags; blunder and mistake have tiles, never rows here. */
export type ContextTagMetric = Exclude<FlawDeltaMetric, 'blunder' | 'mistake'>;

export interface ContextTagCardDef {
  key: ContextTagCardKey;
  title: string;
  /** Muted one-liner next to the title. */
  subtitle: string;
  metrics: readonly ContextTagMetric[];
}

/** The four cards in display order, each with its tag rows in display order (no combo row). */
export const CONTEXT_TAG_CARDS: readonly ContextTagCardDef[] = [
  {
    key: 'phase',
    title: 'Game phase',
    subtitle: 'where the flaw happened',
    metrics: ['opening', 'middlegame', 'endgame_phase'],
  },
  {
    key: 'clock',
    title: 'Clock',
    subtitle: 'how much time you had',
    metrics: ['unrushed', 'hasty', 'low_clock'],
  },
  {
    key: 'lost_advantages',
    title: 'Lost advantages',
    subtitle: 'what the flaw cost',
    metrics: ['reversed', 'squandered'],
  },
  {
    key: 'opponent_errors',
    title: 'Opponent errors',
    subtitle: 'chances you missed or got',
    metrics: ['miss', 'lucky'],
  },
];

/** `low_clock` -> `low-clock`: the metric segment of the gap testids. */
export function metricTestIdSegment(metric: FlawDeltaMetric): string {
  return metric.replace(/_/g, '-');
}

/**
 * Heatmap columns, from most to least time on the clock (unrushed, hasty, low-clock). Cells
 * are looked up by tempo + phase, so this display order is independent of the backend's.
 */
export const TEMPO_PHASE_TEMPOS: readonly FlawTempoMetric[] = ['unrushed', 'hasty', 'low_clock'];

/** Heatmap rows in game order (mirrors backend TEMPO_PHASE_PHASES). */
export const TEMPO_PHASE_PHASES: readonly FlawPhaseMetric[] = [
  'opening',
  'middlegame',
  'endgame_phase',
];

/**
 * Adapt one API bullet or crossed cell to the gap-bar view model (the components never see
 * API types). Takes the shared stat fields only, so both payload shapes fit.
 */
export function flawBulletToGapCell(b: Omit<FlawBullet, 'tag'>): GapCell {
  return {
    delta: b.delta,
    zoneLo: b.zone_lo,
    zoneHi: b.zone_hi,
    hasZone: b.has_zone,
    significant: b.significant,
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

const TEMPO_ADJECTIVE: Record<FlawTempoMetric, string> = {
  low_clock: 'low-clock',
  hasty: 'hasty',
  unrushed: 'unrushed',
};

const PHASE_WORD: Record<FlawPhaseMetric, string> = {
  opening: 'opening',
  middlegame: 'middlegame',
  endgame_phase: 'endgame',
};

/** Popover copy of a crossed cell: the two tag hints combined ("Hasty, middlegame"). */
export function tempoPhaseMeta(tempo: FlawTempoMetric, phase: FlawPhaseMetric): FlawGapMeta {
  const phaseWord = PHASE_WORD[phase];
  const hint = `${FLAW_GAP_META[tempo].hint}, in the ${phaseWord}`;
  return {
    label: `${FLAW_GAP_META[tempo].label}, ${phaseWord}`,
    hint,
    definition: hint,
    noun: `${TEMPO_ADJECTIVE[tempo]} ${phaseWord} flaws`,
  };
}

/** The gap-bar cell of one tempo x phase combination; null when the payload carries no such cell. */
export function tempoPhaseGapCell(
  tcStats: FlawComparisonTc,
  tempo: FlawTempoMetric,
  phase: FlawPhaseMetric,
): GapCell | null {
  const cell = tcStats.tempo_phase_cells.find((c) => c.tempo === tempo && c.phase === phase);
  return cell ? flawBulletToGapCell(cell) : null;
}

function scopeText(analyzedN: number, tc: TimeControlBucket): string {
  return `your ${analyzedN.toLocaleString('en-US')} analyzed ${tc} games in the current filters.`;
}

/** The popover basis line: "Based on your 1,841 analyzed rapid games in the current filters." */
export function libraryBasisText(analyzedN: number, tc: TimeControlBucket): string {
  return `Based on ${scopeText(analyzedN, tc)}`;
}

/**
 * The Flaw Stats basis line, which doubles as the per-TC coverage readout:
 * "1,768 of 1,790 rapid games analyzed in the current filters.", or
 * "All 1,841 rapid games in the current filters are analyzed." once complete.
 */
export function libraryCoverageBasisText(
  analyzedN: number,
  totalN: number,
  tc: TimeControlBucket | null,
): string {
  const fmt = (n: number): string => n.toLocaleString('en-US');
  // tc is null before any game is analyzed (no TC on the switch yet): "0 of 523 games ...".
  const games = tc === null ? 'games' : `${tc} games`;
  if (analyzedN >= totalN) return `All ${fmt(totalN)} ${games} in the current filters are analyzed.`;
  return `${fmt(analyzedN)} of ${fmt(totalN)} ${games} analyzed in the current filters.`;
}
