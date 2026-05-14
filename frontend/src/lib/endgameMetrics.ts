/**
 * Shared helpers + constants for Phase 86 Endgame Metrics cards and Phase 87
 * per-type cards. Lifted from `EndgameScoreGapSection.tsx` per Phase 86 D-08
 * so the new cards and the legacy section can share one source of truth
 * during the transition; legacy file keeps its private copies until deletion
 * in Plan 86-05.
 *
 * Note: the legacy composite-skill helper (lines 155-165 of the source) is
 * intentionally NOT lifted here. Per Phase 86 D-04, the composite Endgame
 * Skill rate is now produced server-side via the `skill` / `opp_skill` fields,
 * and the frontend helper is retired in Plan 04+.
 */

import {
  colorizeGaugeZones,
  type GaugeZone,
} from '@/lib/theme';
import {
  FIXED_GAUGE_ZONES as REGISTRY_FIXED_GAUGE_ZONES,
  ENDGAME_SKILL_ZONES as REGISTRY_ENDGAME_SKILL_ZONES,
} from '@/generated/endgameZones';
import type { MaterialBucket, MaterialRow } from '@/types/endgames';

// Short display names — the eval threshold indicator ("≥ +1.0", "≤ −1.0")
// lives in the section description, freeing column/card space (especially
// on mobile).
export const BUCKET_DISPLAY_LABELS: Record<MaterialBucket, string> = {
  conversion: 'Conversion',
  parity: 'Parity',
  recovery: 'Recovery',
};

// User-facing labels that also name the per-bucket metric, so readers can
// tell the percent column isn't the generic Score used elsewhere on the
// page. Used in the gauge strip, desktop table, and mobile cards; aria
// labels and gauge testIds keep the short form above.
export const BUCKET_DISPLAY_LABELS_WITH_METRIC: Record<MaterialBucket, string> = {
  conversion: 'Conversion (Win)',
  parity: 'Parity (Score)',
  recovery: 'Recovery (Save)',
};

/** Format a 0.0-1.0 rate as an integer percent string, e.g. 0.684 -> "68%". */
export function formatScorePct(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/** Format the visible diff as an integer percent with explicit sign, e.g. "-2%".
 *
 * Computed from the already-rounded You/Opp percentages so the Diff always
 * equals (displayed You) − (displayed Opp). Rounding the raw rate diff
 * independently can disagree with the displayed values by 1pp (e.g. You 69% /
 * Opp 71% showing Diff −1% instead of −2%). */
export function formatDiffPct(userR: number, oppR: number): string {
  const pct = Math.round(userR * 100) - Math.round(oppR * 100);
  return `${pct >= 0 ? '+' : ''}${pct}%`;
}

// Mirror-bucket map: used to derive opponent rate from the user's WDL in
// the mirror bucket (same-game symmetry: opponent wins = user losses,
// opponent draws = user draws).
export const MIRROR_BUCKET: Record<MaterialBucket, MaterialBucket> = {
  conversion: 'recovery',
  parity: 'parity',
  recovery: 'conversion',
};

/** User's rate for this bucket using the bucket's headline definition:
 * - Conversion: win rate (W/G) — only wins count as a successful conversion
 * - Recovery: save rate ((W+D)/G) — draws also count as a successful defense
 * - Parity: chess score ((W+D/2)/G) — neutral midpoint at material balance
 *
 * win_pct/draw_pct/loss_pct are stored as 0-100 on the row; we scale to 0-1
 * to match `row.score` and the bullet-chart domain. */
export function userRate(row: MaterialRow): number {
  if (row.bucket === 'conversion') return row.win_pct / 100;
  if (row.bucket === 'recovery') return (row.win_pct + row.draw_pct) / 100;
  return row.score;
}

/** Opponent's rate in the mirror bucket under the same definition.
 * By same-game symmetry, an opponent's win/draw/loss within the mirror
 * bucket = user's loss/draw/win in the mirror bucket.
 * - Conversion opp = opp wins in user's recovery bucket = user losses there
 * - Recovery opp  = opp wins+draws in user's conversion bucket = user losses+draws there
 * - Parity opp    = 1 − user parity score (chess-score symmetry)
 *
 * Returns null if mirror bucket is missing from response (defensive). */
export function opponentRate(row: MaterialRow, mirror: MaterialRow | undefined): number | null {
  if (!mirror) return null;
  if (row.bucket === 'conversion') return mirror.loss_pct / 100;
  if (row.bucket === 'recovery') return (mirror.loss_pct + mirror.draw_pct) / 100;
  return 1 - row.score;
}

// Opponent baseline: single symmetric neutral zone for all buckets.
// Equally-rated players should score equally in mirrored situations,
// so the expected diff is zero everywhere. ±0.05 (5pp) reads as
// "essentially matched" for the Diff color and bullet-chart neutral band.
export const NEUTRAL_ZONE_MIN = -0.05;
export const NEUTRAL_ZONE_MAX = 0.05;

// Bullet domain half-width for opponent-calibrated diffs. Equally-rated
// players cluster near zero, so ±0.20 covers realistic diffs without
// making typical values look tiny.
export const BULLET_DOMAIN = 0.20;

// Hide the bullet bar when the opponent's mirror-bucket sample is too
// small. Mirrors backend `_MIN_OPPONENT_SAMPLE = 10` and the WDL-bar
// mute threshold used in the Opening Explorer moves list.
export const MIN_OPPONENT_BASELINE_GAMES = 10;

// Fixed per-bucket gauge zones. Numeric boundaries come from the Python zone
// registry via the codegen'd `@/generated/endgameZones` mirror; colors come
// from the FE theme. The blue band marks the typical skill-cohort range for
// each bucket; red below, green above. Bands are deliberately stable across
// users, filters, and opponent pools — the "fixed target" the opponent-
// calibrated design couldn't offer. Calibrated from FlawChess prod data
// (users ±50 ELO vs opponents, 0-2499 ELO brackets): conversion and recovery
// stay within ~4pp across rating ranges, so a single rating-agnostic band
// is used for each bucket.
export const FIXED_GAUGE_ZONES: Record<MaterialBucket, GaugeZone[]> = {
  conversion: colorizeGaugeZones(REGISTRY_FIXED_GAUGE_ZONES.conversion),
  parity: colorizeGaugeZones(REGISTRY_FIXED_GAUGE_ZONES.parity),
  recovery: colorizeGaugeZones(REGISTRY_FIXED_GAUGE_ZONES.recovery),
};

// Zones for the composite Endgame Skill gauge. The blue band mirrors the
// Parity gauge (45–55%) so the color story stays consistent with the
// per-bucket gauges users are already reading. Typical value lands around
// 52% on FlawChess data, sitting in the middle of the blue band.
export const ENDGAME_SKILL_ZONES: GaugeZone[] = colorizeGaugeZones(REGISTRY_ENDGAME_SKILL_ZONES);
