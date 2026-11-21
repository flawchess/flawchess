/**
 * Metadata for the Library Stats you-vs-opponents views.
 *
 * Holds FLAW_GAP_META (label, hint, definition, noun for the 12 gap metrics),
 * FACEPALM_METRICS / FACEPALM_GAP_META / facepalmMetricCell (the three neutral facepalm rows),
 * CONTEXT_TAG_CARDS (the four cards over the 10 context tags), flawBulletToGapCell /
 * flawMetricCell / tempoPhaseGapCell (API bullet or crossed tempo x phase cell ->
 * gap-bar view model), TEMPO_PHASE_TEMPOS / TEMPO_PHASE_PHASES (the heatmap axes), libraryBasisText /
 * librarySampleBasisText / libraryFreshImportBasisText (the Flaw Stats basis lines),
 * isQuietTc / libraryNoRecentGamesText / NO_RECENT_GAMES_HINT (the time control with games but
 * none in the recent window, 258 D-15 to D-17), and the FlawIcon type shared with the Flaws
 * filter panel.
 *
 * Read by the Library Stats tiles (FlawTiles), the context-tag cards,
 * and FlawFilterControl (FlawIcon only).
 *
 * Definitions reuse TAG_DEFINITIONS (the Game / Flaw card tag tooltips) wherever a gap
 * metric maps onto a FlawTag; blunder and mistake carry their own threshold sentence.
 */

import type { ComponentType, CSSProperties } from 'react';
import { format, parseISO } from 'date-fns';

import { TAG_DEFINITIONS } from '@/lib/tagDefinitions';
import { BLUNDER_DROP, MISTAKE_DROP, TIME_PRESSURE_CLOCK_FRACTION } from '@/generated/flawThresholds';
import { FACEPALM_HIGH_CUTOFF } from '@/lib/facepalm';
import type { GapCell } from '@/lib/gapBar';
import type {
  FacepalmBullet,
  FacepalmMetric,
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

// ─── Facepalm rows (257) ────────────────────────────────────────────────────────

/** The three facepalm rows in display order: the total, then the two types. */
export const FACEPALM_METRICS: readonly FacepalmMetric[] = [
  'facepalm',
  'facepalm_missed_win',
  'facepalm_allowed_loss',
];

/**
 * Label, hint, definition and noun of the facepalm rows (257 D-14, D-15). The 70% comes from
 * FACEPALM_HIGH_CUTOFF so it cannot drift from the High preset.
 */
export const FACEPALM_GAP_META: Record<FacepalmMetric, FlawGapMeta> = {
  facepalm: {
    label: 'Facepalm blunders',
    hint: `Blunders with a facepalm score of ${FACEPALM_HIGH_CUTOFF}% or more`,
    definition: `Blunders with a facepalm score of ${FACEPALM_HIGH_CUTOFF}% or more`,
    noun: 'facepalm blunders',
  },
  facepalm_missed_win: {
    label: 'Missed wins',
    hint: 'Facepalm blunders that passed up winning material or checkmate',
    definition: 'Facepalm blunders that passed up winning material or checkmate',
    noun: 'missed-win facepalm blunders',
  },
  facepalm_allowed_loss: {
    label: 'Allowed losses',
    hint: 'Facepalm blunders that gave away material or allowed checkmate',
    definition: 'Facepalm blunders that gave away material or allowed checkmate',
    noun: 'allowed-loss facepalm blunders',
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
export function metricTestIdSegment(metric: FlawDeltaMetric | FacepalmMetric): string {
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

/**
 * The neutral gap-bar cell of one facepalm row (257 D-13): significance is carried for the
 * popover but `noVerdict` keeps the bar free of any verdict colour. Null when the payload
 * carries no such row.
 */
export function facepalmMetricCell(
  bullets: readonly FacepalmBullet[],
  metric: FacepalmMetric,
): GapCell | null {
  const bullet = bullets.find((b) => b.tag === metric);
  return bullet ? { ...flawBulletToGapCell(bullet), noVerdict: true } : null;
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
  return `your ${analyzedN.toLocaleString('en-US')} analyzed ${tc} games in the recent sample.`;
}

/**
 * The popover basis line: "Based on your 1,841 analyzed rapid games in the recent sample."
 * analyzedN is the windowed count (258); the Flaw Stats basis line above the tiles spells the
 * sample out, so a popover only names it.
 */
export function libraryBasisText(analyzedN: number, tc: TimeControlBucket): string {
  return `Based on ${scopeText(analyzedN, tc)}`;
}

/** Inputs of the Flaw Stats basis line (the recent-window sample of one time control). */
interface SampleBasis {
  tc: TimeControlBucket;
  /** Games of the TC in the recent window. */
  totalN: number;
  /** Analyzed games among them. */
  analyzedN: number;
  /** True when the window hit the games cap. */
  capReached: boolean;
  /** ISO date of the oldest game in the window. */
  sampleSince: string | null;
  /** True when an explicit period (recency filter) replaced the default window bound. */
  recencyFiltered: boolean;
  /** True when a sidebar filter other than recency is active. */
  otherFiltersActive: boolean;
  /** Default window length in months. */
  windowMonths: number;
}

function samplePlaceText(recencyFiltered: boolean, otherFiltersActive: boolean): string {
  if (recencyFiltered && otherFiltersActive) return ' in the selected period and the current filters';
  if (recencyFiltered) return ' in the selected period';
  if (otherFiltersActive) return ' in the current filters';
  return '';
}

/**
 * The Flaw Stats basis line: names the bound that cut the sample (258 D-13).
 *  - at the cap: "Based on your most recent 1,000 blitz games (since Mar 2025), 640 analyzed."
 *  - under the cap: "Based on your 412 blitz games from the last 36 months, 300 analyzed."
 * With a recency filter the "from the last N months" clause becomes "in the selected period";
 * " in the current filters" is added only when a sidebar filter other than recency is active.
 */
export function librarySampleBasisText(b: SampleBasis): string {
  const fmt = (n: number): string => n.toLocaleString('en-US');
  const games = `${b.tc} ${b.totalN === 1 ? 'game' : 'games'}`;
  const place = samplePlaceText(b.recencyFiltered, b.otherFiltersActive);
  const analyzed = `${fmt(b.analyzedN)} analyzed`;
  if (b.capReached) {
    const since = b.sampleSince ? ` (since ${format(parseISO(b.sampleSince), 'MMM yyyy')})` : '';
    return `Based on your most recent ${fmt(b.totalN)} ${games}${place}${since}, ${analyzed}.`;
  }
  if (b.recencyFiltered) return `Based on your ${fmt(b.totalN)} ${games}${place}, ${analyzed}.`;
  return `Based on your ${fmt(b.totalN)} ${games} from the last ${b.windowMonths} months${place}, ${analyzed}.`;
}

/**
 * The basis line before any game is analyzed: "0 of 523 games analyzed in the current
 * filters." There is no TC on the switch yet and so no window to describe; totalN is the
 * unwindowed count of the filtered games.
 */
export function libraryFreshImportBasisText(totalN: number): string {
  return `0 of ${totalN.toLocaleString('en-US')} games analyzed in the current filters.`;
}

/**
 * True for a time control that has games in the filters but none in the recent window (258
 * D-15): the flaw comparison keeps it on the switch with `total_n` 0. The tactic payload never
 * lists a quiet TC and so carries no `total_n`; such an entry is not quiet.
 */
export function isQuietTc(tcStats: { total_n?: number }): boolean {
  return tcStats.total_n === 0;
}

/**
 * The quiet-TC message, first sentence: "No blitz games in the last 36 months." With a sidebar
 * filter other than recency active it ends "... in the current filters." (258 D-13), the same
 * qualifier the basis line uses.
 */
export function libraryNoRecentGamesText(
  tc: TimeControlBucket,
  windowMonths: number,
  otherFiltersActive: boolean,
): string {
  // recencyFiltered is always false here: a quiet TC only exists under the default window,
  // because an explicit recency also bounds the offered time controls.
  const place = samplePlaceText(false, otherFiltersActive);
  return `No ${tc} games in the last ${windowMonths} months${place}.`;
}

/**
 * The quiet-TC message, second sentence. It names Recency in general rather than one preset:
 * the five-year preset bounds the offered time controls too, so a TC whose newest matching game
 * is older than five years leaves the switch under that preset (258 UAT test 2, user 7 Classic),
 * while a custom range reaches any date. Plain text, never a button: 258 D-17 forbids an action
 * that would change the shared filter store.
 */
export const NO_RECENT_GAMES_HINT =
  'Choose a longer period or a custom range under Recency to include older games.';
