/**
 * Shared metadata for the 15 you-vs-opponent flaw-comparison bullets (Phase 115 UAT).
 *
 * Single source of truth consumed by both FlawComparisonGrid (family cards +
 * rows) and FlawBulletPopover (the magnifying-glass metric tooltip). Per tag it
 * carries the display label, family (→ colored icon), a lucide icon, a natural
 * plural noun for the "you vs opponent" sentence, and a one-line definition.
 *
 * Definitions reuse TAG_DEFINITIONS (the Game / Flaw card tag tooltips) wherever
 * the comparison tag maps onto a FlawTag; the five tags with no chip equivalent
 * (flaw_rate, mistake, blunder, hasty_miss, low_clock_miss) carry their own
 * one-liner here.
 */

import type { ComponentType, CSSProperties } from 'react';
import {
  AlertTriangle,
  Clock,
  Zap,
  Brain,
  Target,
  Clover,
  Swords,
  ArrowDownUp,
  BookOpen,
  Trophy,
  TrendingDown,
} from 'lucide-react';

import { BlunderIcon, MistakeIcon } from '@/components/icons/SeverityGlyphIcon';

/**
 * Icon shape shared by lucide icons and our custom severity-glyph badges
 * (BlunderIcon / MistakeIcon). Both accept className + style + aria-hidden, so
 * the grid and the tooltip can render either without branching.
 */
export type FlawIcon = ComponentType<{
  className?: string;
  style?: CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}>;

import {
  FAM_SEVERITY,
  FAM_SEVERITY_BG,
  FAM_TEMPO,
  FAM_TEMPO_BG,
  FAM_PHASE,
  FAM_PHASE_BG,
  FAM_OPPORTUNITY,
  FAM_OPPORTUNITY_BG,
  FAM_IMPACT,
  FAM_IMPACT_BG,
  FAM_COMBO,
  FAM_COMBO_BG,
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
} from '@/lib/theme';
import { TAG_DEFINITIONS } from '@/lib/tagDefinitions';
import { BLUNDER_DROP, MISTAKE_DROP, TIME_PRESSURE_CLOCK_FRACTION } from '@/generated/flawThresholds';
import type { GapCell } from '@/lib/gapBar';
import type { ConfidenceLevel } from '@/lib/scoreConfidence';
import type { FlawBullet, FlawDeltaMetric } from '@/types/library';
import type { TimeControlBucket } from '@/types/endgames';

// ─── Families ──────────────────────────────────────────────────────────────────

export type FlawComparisonFamily =
  | 'severity'
  | 'tempo'
  | 'phase'
  | 'opportunity'
  | 'impact'
  | 'combo';

export interface FlawFamilyColors {
  /** Icon + bold-label foreground color. */
  color: string;
  /** Soft background tint (currently unused by the grid, kept for parity with TagChip). */
  bg: string;
}

export const FLAW_FAMILY_COLORS: Record<FlawComparisonFamily, FlawFamilyColors> = {
  severity: { color: FAM_SEVERITY, bg: FAM_SEVERITY_BG },
  tempo: { color: FAM_TEMPO, bg: FAM_TEMPO_BG },
  phase: { color: FAM_PHASE, bg: FAM_PHASE_BG },
  opportunity: { color: FAM_OPPORTUNITY, bg: FAM_OPPORTUNITY_BG },
  impact: { color: FAM_IMPACT, bg: FAM_IMPACT_BG },
  combo: { color: FAM_COMBO, bg: FAM_COMBO_BG },
};

export interface FlawFamilyDef {
  /** Card-header title. */
  name: string;
  family: FlawComparisonFamily;
  /** Bullet tags in display order. */
  tags: string[];
}

/** Registry order per phase 115 plan: Severity → Tempo → Phase → Opportunity → Impact → Combos. */
export const FLAW_COMPARISON_FAMILIES: FlawFamilyDef[] = [
  { name: 'Severity', family: 'severity', tags: ['flaw_rate', 'blunder', 'mistake'] },
  { name: 'Tempo', family: 'tempo', tags: ['low_clock', 'hasty', 'unrushed'] },
  { name: 'Phase', family: 'phase', tags: ['opening', 'middlegame', 'endgame_phase'] },
  { name: 'Opportunity', family: 'opportunity', tags: ['miss', 'lucky'] },
  { name: 'Impact', family: 'impact', tags: ['reversed', 'squandered'] },
  { name: 'Combos', family: 'combo', tags: ['hasty_miss', 'low_clock_miss'] },
];

// ─── Per-tag metadata ────────────────────────────────────────────────────────

export interface FlawComparisonTagMeta {
  /** Title-case label for the row + tooltip heading. */
  label: string;
  family: FlawComparisonFamily;
  icon: FlawIcon;
  /** Natural plural noun for the "you vs opponent" sentence (e.g. "missed opportunities"). */
  noun: string;
  /** One-line definition for the tooltip's first paragraph. */
  definition: string;
}

export const FLAW_COMPARISON_META: Record<string, FlawComparisonTagMeta> = {
  // ── Severity ──
  flaw_rate: {
    label: 'Flaw rate',
    family: 'severity',
    icon: AlertTriangle,
    noun: 'mistakes & blunders',
    definition: 'Your overall mistake + blunder rate, compared to your opponents.',
  },
  blunder: {
    label: 'Blunder',
    family: 'severity',
    icon: BlunderIcon,
    noun: 'blunders',
    definition: 'Moves that dropped your Expected Score by at least 15 percentage points.',
  },
  mistake: {
    label: 'Mistake',
    family: 'severity',
    icon: MistakeIcon,
    noun: 'mistakes',
    definition: 'Moves that dropped your Expected Score by at least 10 but less than 15 percentage points.',
  },
  // ── Tempo ──
  low_clock: {
    label: 'Low-clock',
    family: 'tempo',
    icon: Clock,
    noun: 'low-clock flaws',
    definition: TAG_DEFINITIONS['low-clock'],
  },
  hasty: {
    label: 'Hasty',
    family: 'tempo',
    icon: Zap,
    noun: 'hasty flaws',
    definition: TAG_DEFINITIONS['hasty'],
  },
  unrushed: {
    label: 'Unrushed',
    family: 'tempo',
    icon: Brain,
    noun: 'unrushed flaws',
    definition: TAG_DEFINITIONS['unrushed'],
  },
  // ── Phase ──
  opening: {
    label: 'Opening',
    family: 'phase',
    icon: BookOpen,
    noun: 'opening flaws',
    definition: TAG_DEFINITIONS['opening'],
  },
  middlegame: {
    label: 'Middlegame',
    family: 'phase',
    icon: Swords,
    noun: 'middlegame flaws',
    definition: TAG_DEFINITIONS['middlegame'],
  },
  endgame_phase: {
    label: 'Endgame',
    family: 'phase',
    icon: Trophy,
    noun: 'endgame flaws',
    definition: TAG_DEFINITIONS['endgame'],
  },
  // ── Opportunity ──
  miss: {
    label: 'Miss',
    family: 'opportunity',
    icon: Target,
    noun: 'missed opportunities',
    definition: TAG_DEFINITIONS['miss'],
  },
  lucky: {
    label: 'Lucky',
    family: 'opportunity',
    icon: Clover,
    noun: 'lucky escapes',
    definition: TAG_DEFINITIONS['lucky'],
  },
  // ── Impact ──
  reversed: {
    label: 'Reversed',
    family: 'impact',
    icon: ArrowDownUp,
    noun: 'reversals',
    definition: TAG_DEFINITIONS['reversed'],
  },
  squandered: {
    label: 'Squandered',
    family: 'impact',
    icon: TrendingDown,
    noun: 'squandered advantages',
    definition: TAG_DEFINITIONS['squandered'],
  },
  // ── Combos ──
  hasty_miss: {
    label: 'Hasty miss',
    family: 'combo',
    icon: Zap,
    noun: 'hasty missed opportunities',
    definition: 'A missed opportunity (gift from opponent) made in under 1% of base time — hasty AND a miss.',
  },
  low_clock_miss: {
    label: 'Low-clock miss',
    family: 'combo',
    icon: Clock,
    noun: 'low-clock missed opportunities',
    definition: 'A missed opportunity made under clock pressure (remaining clock under 5% of base time).',
  },
};

// ─── Stat helpers (shared by the grid + the metric tooltip) ────────────────────

// Same p-value buckets the rest of the app uses (see scoreConfidence.ts):
// high < 0.01, medium < 0.05, low otherwise. The grid uses
// the same threshold to decide when to apply the zone color to the rate_diff —
// the number is tinted only when the result is significant (medium/high), i.e.
// when the 95% CI excludes zero.
const CONFIDENCE_HIGH_MAX_P = 0.01;
const CONFIDENCE_MEDIUM_MAX_P = 0.05;

export function flawConfidenceLevel(pValue: number | null): ConfidenceLevel {
  if (pValue == null) return 'low';
  if (pValue < CONFIDENCE_HIGH_MAX_P) return 'high';
  if (pValue < CONFIDENCE_MEDIUM_MAX_P) return 'medium';
  return 'low';
}

/**
 * Two-sided significance at α = 0.05 — equivalently, the 95% CI excludes zero
 * (the bound the backend Wald-z CI is built on). Used to gate the rate_diff
 * color: significant → zone color, otherwise muted.
 */
export function isFlawDeltaSignificant(bullet: FlawBullet): boolean {
  if (bullet.ci_low == null || bullet.ci_high == null) return false;
  return bullet.ci_low > 0 || bullet.ci_high < 0;
}

/**
 * The zone color the rate_diff lands in. Inverted vs the endgame convention:
 * fewer flaws than opponents (delta below the typical band) is good → green.
 */
export function flawDeltaZoneColor(delta: number, zoneLo: number, zoneHi: number): string {
  if (delta >= zoneHi) return ZONE_DANGER;
  if (delta >= zoneLo) return ZONE_NEUTRAL;
  return ZONE_SUCCESS;
}

/** "p < 0.001" for tiny values, else "p = 0.XXX" (also used by the RankedMetricPopover footer). */
export function formatPValue(pValue: number): string {
  if (pValue < 0.001) return 'p < 0.001';
  return `p = ${pValue.toFixed(3)}`;
}

// ─── Library Stats gap metadata (Phase 239, sketch 010 round 5) ───────────────

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
  /** Plural noun for the popover counts and the standout sentences (D-00d: flaws, never events). */
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
