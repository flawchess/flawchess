/**
 * Shared vocabulary for the percentile-first Endgame Stats tab (Phase 238):
 * metric labels and WHAT + sign copy, value formatting, the section ids, and the
 * percentile helpers every bar and popover uses. A non-component module so fast refresh stays happy in the components.
 */

import { GAUGE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import type { CdfMetricId, TimeControlBucket } from '@/types/endgames';

// ── Percentile bar geometry and bands (D-00a) ────────────────────────────────

export const PERCENTILE_TYPICAL_LOW = 25;
export const PERCENTILE_TYPICAL_HIGH = 75;
export const PERCENTILE_MEDIAN = 50;
/** The dot never sits on the very edge: no "0th" or "100th" percentile. */
export const MIN_PERCENT = 1;
export const MAX_PERCENT = 99;

/**
 * The one displayed percentile: rounded, then clamped into 1..99. The bar's dot,
 * ordinal and band color and the popover's "Better than N%" all use it, so they
 * never disagree. Phase 238 review (FE-WR-03 / FE-IN-01): the backend returns exact
 * 0.0 / 100.0 tail percentiles, and the bar clamped only the dot ("0th" label next to
 * a 1% dot); the color also used the raw value, so 24.6 read "25th" in red.
 */
export function displayPercentile(percentile: number): number {
  return Math.max(MIN_PERCENT, Math.min(MAX_PERCENT, Math.round(percentile)));
}

/** Dot and number color: red below 25, blue from 25 to 75 inclusive, green above 75. */
export function percentileBandColor(percentile: number): string {
  if (percentile < PERCENTILE_TYPICAL_LOW) return ZONE_DANGER;
  if (percentile > PERCENTILE_TYPICAL_HIGH) return ZONE_SUCCESS;
  return GAUGE_NEUTRAL;
}

const ORDINAL_TEEN_START = 11;
const ORDINAL_TEEN_END = 13;
const ORDINAL_SUFFIXES: Record<number, string> = { 1: 'st', 2: 'nd', 3: 'rd' };

/** 46 -> "46th", 21 -> "21st", 12 -> "12th". The input is rounded first. */
export function formatOrdinal(value: number): string {
  const n = Math.round(value);
  const lastTwo = n % 100;
  const isTeen = lastTwo >= ORDINAL_TEEN_START && lastTwo <= ORDINAL_TEEN_END;
  const suffix = isTeen ? 'th' : (ORDINAL_SUFFIXES[n % 10] ?? 'th');
  return `${n}${suffix}`;
}

// ── Time controls ────────────────────────────────────────────────────────────

export const TC_LABELS: Record<TimeControlBucket, string> = {
  bullet: 'Bullet',
  blitz: 'Blitz',
  rapid: 'Rapid',
  classical: 'Classic',
};

// ── Metric labels and copy ───────────────────────────────────────────────────

export const METRIC_LABELS: Record<CdfMetricId, string> = {
  score_gap: 'Endgame Score Gap',
  achievable_score_gap: 'Eval Score Gap',
  conversion_rate: 'Conversion',
  parity_rate: 'Parity',
  recovery_rate: 'Recovery',
  score_gap_conv: 'Conversion vs. eval',
  score_gap_parity: 'Parity vs. eval',
  recovery_score_gap: 'Recovery vs. eval',
  clock_gap: 'Clock Gap',
  net_flag_rate: 'Net Flag Rate',
  time_pressure_score_gap: 'Score under time pressure',
};

const BUCKET_GAP_WHAT =
  'your score minus the score the engine expected from your eval at endgame entry, for these games.';

/** One plain sentence per metric: WHAT it measures plus the sign convention. */
export const METRIC_WHAT: Record<CdfMetricId, string> = {
  score_gap:
    'your score in games that reach an endgame minus your score in games that end before. Negative = you do worse once an endgame is reached.',
  achievable_score_gap:
    'your endgame score minus the score the engine expected from your eval at endgame entry. Negative = you lose ground in the endgame.',
  conversion_rate: 'how often you win endgames you entered clearly ahead.',
  parity_rate: 'your score in endgames you entered roughly equal.',
  recovery_rate: 'how often you save (win or draw) endgames you entered clearly behind.',
  score_gap_conv: BUCKET_GAP_WHAT,
  score_gap_parity: BUCKET_GAP_WHAT,
  recovery_score_gap: BUCKET_GAP_WHAT,
  clock_gap:
    "your clock minus your opponent's clock at endgame entry, as % of the base time. Negative = you arrive with less time.",
  net_flag_rate:
    'how often you win on time minus how often you lose on time. Negative = you flag more than you flag opponents.',
  time_pressure_score_gap:
    "your score minus your opponents' score when you were the one under time pressure.",
};

// Rates are plain percents; every other metric is a gap and carries its sign.
const RATE_METRICS: ReadonlySet<CdfMetricId> = new Set<CdfMetricId>([
  'conversion_rate',
  'parity_rate',
  'recovery_rate',
]);

const PERCENT_SCALE = 100;

/** "+5%" / "-3%" for gaps and clock metrics, "75%" for rates. Values arrive as fractions. */
export function formatMetricValue(metric: CdfMetricId, value: number): string {
  const pct = Math.round(value * PERCENT_SCALE);
  if (RATE_METRICS.has(metric)) return `${pct}%`;
  return `${pct >= 0 ? '+' : ''}${pct}%`;
}

const CI_DECIMALS = 1;
const P_VALUE_DECIMALS = 3;
const P_VALUE_FLOOR = 0.001;

/** One bound of the 95% CI in the popover footer: signed for gaps, plain for rates. */
export function formatCiBound(metric: CdfMetricId, value: number): string {
  const pct = (value * PERCENT_SCALE).toFixed(CI_DECIMALS);
  if (RATE_METRICS.has(metric)) return `${pct}%`;
  return `${value >= 0 ? '+' : ''}${pct}%`;
}

/** "p = 0.032", or "p < 0.001" for the tiny ones. */
export function formatPValue(p: number): string {
  return p < P_VALUE_FLOOR ? 'p < 0.001' : `p = ${p.toFixed(P_VALUE_DECIMALS)}`;
}

/** kebab-case slug of a metric id, for data-testids. */
export function metricSlug(metric: CdfMetricId): string {
  return metric.replace(/_/g, '-');
}

// ── Sections ─────────────────────────────────────────────────────────────────

export const SECTION_ID_OVERALL = 'endgame-section-overall';
export const SECTION_ID_METRICS = 'endgame-section-metrics';
export const SECTION_ID_TIME_PRESSURE = 'endgame-section-time-pressure';
