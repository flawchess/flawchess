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
import type { EndgameClass, MaterialBucket } from '@/types/endgames';

// Short display names — the eval threshold indicator ("≥ +1.0", "≤ −1.0")
// lives in the section description, freeing column/card space (especially
// on mobile).
export const BUCKET_DISPLAY_LABELS: Record<MaterialBucket, string> = {
  conversion: 'Conversion',
  parity: 'Parity',
  recovery: 'Recovery',
};

// User-facing labels that also name the per-bucket metric. Currently identical
// to BUCKET_DISPLAY_LABELS — the explanatory "(Win)/(Score)/(Save)" suffix was
// dropped per phase 86 feedback. Kept as a separate export so callers that
// want the "name the metric" surface keep a stable import site if it diverges
// again later.
export const BUCKET_DISPLAY_LABELS_WITH_METRIC: Record<MaterialBucket, string> = {
  conversion: 'Conversion',
  parity: 'Parity',
  recovery: 'Recovery',
};

/** Format a 0.0-1.0 rate as an integer percent string, e.g. 0.684 -> "68%". */
export function formatScorePct(score: number): string {
  return `${Math.round(score * 100)}%`;
}

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

// Phase 87 (D-11): One-sentence descriptions per endgame class, surfaced in the
// per-card title InfoPopover on EndgameTypeCard. Lifted from
// EndgameWDLChart.tsx:30-37 in Plan 02; `pawnless` omitted because pawnless is
// hidden via HIDDEN_ENDGAME_CLASSES (Endgames.tsx:53) and never reaches the new
// section orchestrator.
export const ENDGAME_TYPE_DESCRIPTIONS: Record<Exclude<EndgameClass, 'pawnless'>, string> = {
  rook: 'Endgames with rooks as the only non-king, non-pawn pieces. The most common Endgame Type besides Mixed.',
  minor_piece: 'Endgames with bishops and/or knights as the only non-king, non-pawn pieces.',
  pawn: 'King and pawn endgames only. No other pieces remain on the board.',
  queen: 'Endgames where queens are the only non-king, non-pawn pieces.',
  mixed: 'Endgames with pieces from two or more piece types: rooks, minor pieces (bishops/knights), and queens (e.g. queen + rook, rook + knight).',
};

// Phase 87 (D-04): Mobile real-device density check in Plan 03 HUMAN-UAT decides
// the final value. When false, the WDL bar row in EndgameTypeCard is suppressed
// and the Games deep-link moves to a standalone row under the gauges so the
// deep-link stays visible (per D-07 fallback rule). Card layout adapts; gauges
// and peer bullets are never dropped under the fallback.
export const SHOW_WDL_BAR_IN_TYPE_CARDS: boolean = true;

// Phase 87 (D-16): Hyphenated URL slug + testid suffix per endgame class. Powers
// /endgames/games?type=... deep-link and `type-card-{slug}` data-testid in
// EndgameTypeCard / EndgameTypeBreakdownSection. Lifted verbatim from
// EndgameWDLChart.tsx:21-28; all 6 entries kept for completeness even though
// pawnless is filtered upstream by HIDDEN_ENDGAME_CLASSES.
export const ENDGAME_CLASS_TO_SLUG: Record<EndgameClass, string> = {
  rook: 'rook',
  minor_piece: 'minor-piece',
  pawn: 'pawn',
  queen: 'queen',
  mixed: 'mixed',
  pawnless: 'pawnless',
};

// Phase 87 (Plan 03 D-03): Pawnless endgames are rare (~0.5% of positions in
// prod) and per-user sample sizes are usually too small to be meaningful. Hidden
// from the Endgames tab UI and from EndgameTypeBreakdownSection. Classification
// stays in the DB so the class can be re-enabled without a reimport. Lifted
// from Endgames.tsx:53 so the orchestrator and the page share one source of
// truth.
export const HIDDEN_ENDGAME_CLASSES: ReadonlySet<EndgameClass> = new Set(['pawnless']);
