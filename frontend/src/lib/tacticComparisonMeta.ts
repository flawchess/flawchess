/**
 * Shared metadata for the tactic-motif family comparison bullets (19 families).
 *
 * Single source of truth consumed by MostCommonTacticsCard (the Library Stats tactic card),
 * TacticMotifChip (family color + icon), and the FilterPanel tactic-motif filter.
 *
 * Mirrors flawComparisonMeta.ts in structure. The families map the TacticMotif strings to
 * chip families. The family taxonomy must remain consistent with the backend
 * FAMILY_TO_MOTIF_INTS mapping in library_repository.py — the keys here are the
 * cross-stack contract (string-for-string).
 *
 * The "Advanced" group holds the tier-3 motifs (trapped-piece, x-ray, deflection,
 * intermezzo, interference, capturing-defender, attraction, sacrifice) and the move-type
 * families (en-passant, under-promotion, promotion). Clearance is suppressed (the real-game
 * keep/suppress bar measured real_share=0.667 with only 3 of 16 surviving rows — below both
 * REALGAME_MIN_ROWS_FOR_FLOOR and the 0.80 keep bar); it belongs to no family, same as
 * self-interference. Old ?tactic=pin_skewer / discovery / combinations URL params
 * are inert (backend .get(fam, []) no-op; union excludes them).
 */

import type { ComponentType, CSSProperties } from 'react';
import {
  GitFork,
  MoveUp,
  MapPin,
  ScanLine,
  ChevronsUp,
  Eye,
  EyeDashed,
  Footprints,
  Crosshair,
  Crown,
  Magnet,
  Shuffle,
  Split,
  ShieldOff,
  Wind,
  Gift,
  ArrowLeftRight,
  ArrowDownFromLine,
  ArrowUpFromLine,
} from 'lucide-react';

import {
  TAC_FORK,
  TAC_FORK_BG,
  TAC_SKEWER,
  TAC_SKEWER_BG,
  TAC_PIN,
  TAC_PIN_BG,
  TAC_X_RAY,
  TAC_X_RAY_BG,
  TAC_DOUBLE_CHECK,
  TAC_DOUBLE_CHECK_BG,
  TAC_DISCOVERED_CHECK,
  TAC_DISCOVERED_CHECK_BG,
  TAC_DISCOVERED_ATTACK,
  TAC_DISCOVERED_ATTACK_BG,
  TAC_TRAPPED_PIECE,
  TAC_TRAPPED_PIECE_BG,
  TAC_HANGING,
  TAC_HANGING_BG,
  TAC_MATE,
  TAC_MATE_BG,
  TAC_DEFLECTION,
  TAC_DEFLECTION_BG,
  TAC_INTERMEZZO,
  TAC_INTERMEZZO_BG,
  TAC_INTERFERENCE,
  TAC_INTERFERENCE_BG,
  TAC_CAPTURING_DEFENDER,
  TAC_CAPTURING_DEFENDER_BG,
  TAC_ATTRACTION,
  TAC_ATTRACTION_BG,
  TAC_SACRIFICE,
  TAC_SACRIFICE_BG,
  TAC_EN_PASSANT,
  TAC_EN_PASSANT_BG,
  TAC_UNDER_PROMOTION,
  TAC_UNDER_PROMOTION_BG,
  TAC_PROMOTION,
  TAC_PROMOTION_BG,
} from '@/lib/theme';
import { TACTIC_MOTIF_DEFINITIONS } from '@/lib/tacticMotifDefinitions';
import {
  toDisplayDepthForOrientation,
  ALLOWED_DECISION_DEPTH_OFFSET,
  DEPTH_MIN,
  DEPTH_MAX,
  DEFAULT_TACTIC_DEPTH_VALUE,
  type TacticDepthOrientation,
} from '@/lib/tacticDepth';
import type { GapCell } from '@/lib/gapBar';
import type { TacticBullet, TacticSide } from '@/types/library';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

// ─── Icon shape ───────────────────────────────────────────────────────────────

/** Icon type shared by lucide icons (same constraint as FlawIcon in flawComparisonMeta). */
export type TacticIcon = ComponentType<{
  className?: string;
  style?: CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}>;

// ─── Families ─────────────────────────────────────────────────────────────────

/**
 * The 19 tactic family keys — cross-stack contract with backend FAMILY_TO_MOTIF_INTS.
 * These strings must equal the backend dict keys string-for-string.
 * Filter display order (mechanism-grouped):
 *   Piece Attacks: fork → pin → skewer → hanging
 *   Checkmate, Checks & Discoveries: mate → double_check → discovered_check → discovered_attack
 *   Advanced: trapped_piece → x_ray → deflection → intermezzo → interference → capturing_defender → attraction → sacrifice → en_passant → under_promotion → promotion
 *
 * There is no "clearance" family: it is suppressed (see the module comment).
 */
export type TacticFamily =
  | 'fork'
  | 'skewer'
  | 'pin'
  | 'x_ray'
  | 'double_check'
  | 'discovered_check'
  | 'discovered_attack'
  | 'trapped_piece'
  | 'hanging'
  | 'mate'
  // Tier-3 "Advanced" families
  | 'deflection'
  | 'intermezzo'
  | 'interference'
  | 'capturing_defender'
  | 'attraction'
  | 'sacrifice'
  // Move-type families
  | 'en_passant'
  | 'under_promotion'
  // promotion (28): perfect-precision residual motif
  | 'promotion';

export interface TacticFamilyColors {
  /** Icon + chip foreground color. */
  color: string;
  /** Soft background tint (translucent, same pattern as FlawFamilyColors). */
  bg: string;
}

export const TACTIC_FAMILY_COLORS: Record<TacticFamily, TacticFamilyColors> = {
  fork: { color: TAC_FORK, bg: TAC_FORK_BG },
  skewer: { color: TAC_SKEWER, bg: TAC_SKEWER_BG },
  pin: { color: TAC_PIN, bg: TAC_PIN_BG },
  x_ray: { color: TAC_X_RAY, bg: TAC_X_RAY_BG },
  double_check: { color: TAC_DOUBLE_CHECK, bg: TAC_DOUBLE_CHECK_BG },
  discovered_check: { color: TAC_DISCOVERED_CHECK, bg: TAC_DISCOVERED_CHECK_BG },
  discovered_attack: { color: TAC_DISCOVERED_ATTACK, bg: TAC_DISCOVERED_ATTACK_BG },
  trapped_piece: { color: TAC_TRAPPED_PIECE, bg: TAC_TRAPPED_PIECE_BG },
  hanging: { color: TAC_HANGING, bg: TAC_HANGING_BG },
  mate: { color: TAC_MATE, bg: TAC_MATE_BG },
  deflection: { color: TAC_DEFLECTION, bg: TAC_DEFLECTION_BG },
  intermezzo: { color: TAC_INTERMEZZO, bg: TAC_INTERMEZZO_BG },
  interference: { color: TAC_INTERFERENCE, bg: TAC_INTERFERENCE_BG },
  capturing_defender: { color: TAC_CAPTURING_DEFENDER, bg: TAC_CAPTURING_DEFENDER_BG },
  attraction: { color: TAC_ATTRACTION, bg: TAC_ATTRACTION_BG },
  sacrifice: { color: TAC_SACRIFICE, bg: TAC_SACRIFICE_BG },
  // Move-type families
  en_passant: { color: TAC_EN_PASSANT, bg: TAC_EN_PASSANT_BG },
  under_promotion: { color: TAC_UNDER_PROMOTION, bg: TAC_UNDER_PROMOTION_BG },
  promotion: { color: TAC_PROMOTION, bg: TAC_PROMOTION_BG },
};

export const TACTIC_FAMILY_ICON: Record<TacticFamily, TacticIcon> = {
  fork: GitFork,
  skewer: MoveUp,
  pin: MapPin,
  x_ray: ScanLine,
  double_check: ChevronsUp,
  discovered_check: Eye,
  discovered_attack: EyeDashed,
  trapped_piece: Footprints,
  hanging: Crosshair,
  mate: Crown,
  deflection: Wind,
  intermezzo: Shuffle,
  interference: Split,
  capturing_defender: ShieldOff,
  attraction: Magnet,
  sacrifice: Gift,
  // Move-type families
  en_passant: ArrowLeftRight,
  under_promotion: ArrowDownFromLine,
  promotion: ArrowUpFromLine,
};

// ─── Mechanism groups (filter panel) ─────────────────────────────────────────

/**
 * The mechanism-based sections of the tactic-motif filter. Display order matters;
 * chip order within a group follows TACTIC_COMPARISON_FAMILIES array order. The
 * 'advanced' group (tier-3 motifs) renders inside a collapsible,
 * collapsed-by-default section below the others (FlawFilterControl).
 */
export type TacticGroupKey = 'piece_attacks' | 'discoveries' | 'advanced';

export interface TacticGroupDef {
  key: TacticGroupKey;
  /** Title-Case section label shown above the group's chips. */
  label: string;
}

/** Ordered groups rendered top-to-bottom in the filter panel. */
export const TACTIC_GROUPS: TacticGroupDef[] = [
  { key: 'piece_attacks', label: 'Piece Attacks' },
  { key: 'discoveries', label: 'Checkmate, Checks & Discoveries' },
  { key: 'advanced', label: 'Advanced' },
];

/**
 * The families the Library Stats tactic card shows: the four most
 * common, and the only ones whose benchmark typical range is viable on both the missed and
 * the allowed side. The other 15 occur under once per 100 games per player, so their
 * you-vs-opponent gaps were mostly noise. The filter panel still offers all 19.
 */
export const LIBRARY_STATS_TACTIC_FAMILIES: readonly TacticFamily[] = ['fork', 'pin', 'hanging', 'mate'];

// ─── Family definitions ───────────────────────────────────────────────────────

export interface TacticFamilyDef {
  /** Card-header title / comparison-tooltip label (Title Case, e.g. "Hanging piece"). */
  name: string;
  family: TacticFamily;
  /** Mechanism group this family belongs to (filter panel sectioning). */
  group: TacticGroupKey;
  /** Kebab-case label shown on the filter chip (e.g. "hanging-piece"). */
  chipLabel: string;
  /** All motif strings that belong to this family (must match FAMILY_TO_MOTIF_INTS). */
  motifs: string[];
}

/**
 * The 19 tactic families in filter display order (mechanism-grouped).
 * Array order doubles as the chip order within each group — the filter panel groups
 * these by `group` preserving this order, and the Library Stats tactic card renders
 * its rows in exactly this order (never re-sorted by rate). The motifs arrays mirror the
 * backend FAMILY_TO_MOTIF_INTS mapping in library_repository.py. self-interference and
 * clearance belong to no family (see the module comment for clearance).
 */
export const TACTIC_COMPARISON_FAMILIES: TacticFamilyDef[] = [
  // ── Piece Attacks ──
  {
    name: 'Fork',
    family: 'fork',
    group: 'piece_attacks',
    chipLabel: 'fork',
    motifs: ['fork'],
  },
  {
    name: 'Pin',
    family: 'pin',
    group: 'piece_attacks',
    chipLabel: 'pin',
    motifs: ['pin'],
  },
  {
    name: 'Skewer',
    family: 'skewer',
    group: 'piece_attacks',
    chipLabel: 'skewer',
    motifs: ['skewer'],
  },
  {
    name: 'Hanging piece',
    family: 'hanging',
    group: 'piece_attacks',
    chipLabel: 'hanging-piece',
    motifs: ['hanging-piece'],
  },
  // ── Checkmate, Checks & Discoveries ──
  // Mate leads the group (chip "checkmate"); the legend shows a single "checkmate"
  // row rather than the nine named-mate motifs. Then
  // the checks (double-check, discovered-check), then the pure discovery.
  {
    name: 'Checkmate',
    family: 'mate',
    group: 'discoveries',
    chipLabel: 'checkmate',
    motifs: [
      'back-rank-mate',
      'smothered-mate',
      'anastasia-mate',
      'hook-mate',
      'arabian-mate',
      'boden-mate',
      'double-bishop-mate',
      'dovetail-mate',
      'mate',
    ],
  },
  {
    name: 'Double check',
    family: 'double_check',
    group: 'discoveries',
    chipLabel: 'double-check',
    motifs: ['double-check'],
  },
  {
    name: 'Discovered check',
    family: 'discovered_check',
    group: 'discoveries',
    chipLabel: 'discovered-check',
    motifs: ['discovered-check'],
  },
  {
    name: 'Discovered attack',
    family: 'discovered_attack',
    group: 'discoveries',
    chipLabel: 'discovered-attack',
    motifs: ['discovered-attack'],
  },
  // ── Advanced (tier-3) ──
  // Cook-aligned motifs surfaced behind the collapsible "Advanced" filter section.
  // trapped-piece leads, then x-ray (geometric), then the lure/disruption motifs.
  // There is no clearance family (suppressed, see the module comment).
  {
    name: 'Trapped piece',
    family: 'trapped_piece',
    group: 'advanced',
    chipLabel: 'trapped-piece',
    motifs: ['trapped-piece'],
  },
  {
    name: 'X-ray',
    family: 'x_ray',
    group: 'advanced',
    chipLabel: 'x-ray',
    motifs: ['x-ray'],
  },
  {
    name: 'Deflection',
    family: 'deflection',
    group: 'advanced',
    chipLabel: 'deflection',
    motifs: ['deflection'],
  },
  {
    name: 'Intermezzo',
    family: 'intermezzo',
    group: 'advanced',
    chipLabel: 'intermezzo',
    motifs: ['intermezzo'],
  },
  {
    name: 'Interference',
    family: 'interference',
    group: 'advanced',
    chipLabel: 'interference',
    motifs: ['interference'],
  },
  {
    name: 'Capturing defender',
    family: 'capturing_defender',
    group: 'advanced',
    chipLabel: 'capturing-defender',
    motifs: ['capturing-defender'],
  },
  // attraction + sacrifice (Advanced).
  {
    name: 'Attraction',
    family: 'attraction',
    group: 'advanced',
    chipLabel: 'attraction',
    motifs: ['attraction'],
  },
  {
    name: 'Sacrifice',
    family: 'sacrifice',
    group: 'advanced',
    chipLabel: 'sacrifice',
    motifs: ['sacrifice'],
  },
  // Move-type families: en-passant + under-promotion (P=1.000 on the tagger fixture).
  // Both fire only at Tier 5 (residual), so these chips are low-volume.
  {
    name: 'En passant',
    family: 'en_passant',
    group: 'advanced',
    chipLabel: 'en-passant',
    motifs: ['en-passant'],
  },
  {
    name: 'Under-promotion',
    family: 'under_promotion',
    group: 'advanced',
    chipLabel: 'under-promotion',
    motifs: ['under-promotion'],
  },
  // promotion (28): perfect-precision residual move-type
  // motif — fires only when the winning line queens a pawn and no sharper tactic applies.
  // Sibling of under-promotion; the "allowed" orientation ("you let the opponent queen")
  // is an instructive endgame mistake.
  {
    name: 'Promotion',
    family: 'promotion',
    group: 'advanced',
    chipLabel: 'promotion',
    motifs: ['promotion'],
  },
];

/**
 * Derived mapping from motif string to its TacticFamily key.
 * Built by flattening TACTIC_COMPARISON_FAMILIES — no manual duplication.
 * Each family's `chipLabel` is also registered as a resolvable key so the
 * filter-panel legend (keyed on chipLabel) resolves icon/color — this is what
 * lets the synthetic "checkmate" label map to the `mate` family even though it
 * is not a backend motif string. For single-motif families
 * chipLabel already equals the motif, so the extra key is a harmless no-op.
 * Only self-interference (and the suppressed clearance) maps to no family; consumers
 * already guard `family == null`.
 */
export const TACTIC_FAMILY_FOR_MOTIF: Record<string, TacticFamily> = Object.fromEntries(
  TACTIC_COMPARISON_FAMILIES.flatMap(({ family, motifs, chipLabel }) =>
    [...motifs, chipLabel].map((key) => [key, family]),
  ),
);

// ─── Motif display helpers (cards, chips, tooltips) ────────────────────────────

/**
 * Display label for a tactic motif. Every mate-family motif (back-rank-mate,
 * smothered-mate, …, mate) collapses to a single "checkmate" label — the game and
 * flaw cards do not distinguish named-mate subtypes. All other
 * motifs render as their own kebab string.
 */
export function tacticMotifLabel(motif: string): string {
  return TACTIC_FAMILY_FOR_MOTIF[motif] === 'mate' ? 'checkmate' : motif;
}

/**
 * Definition paired with tacticMotifLabel: mate-family motifs share the generic
 * "checkmate" copy so the collapsed "checkmate" label never shows a subtype-specific
 * sentence. Falls back to the raw motif string when no definition exists.
 */
export function tacticMotifDefinition(motif: string): string {
  const key = TACTIC_FAMILY_FOR_MOTIF[motif] === 'mate' ? 'checkmate' : motif;
  return TACTIC_MOTIF_DEFINITIONS[key] ?? motif;
}

/**
 * Bundled visibility decision for one tactic slot. When non-null,
 * BOTH the motif chip and the depth badge are allowed to render; when null, NEITHER
 * may. This is the single source of truth that makes a depth number physically unable
 * to leak onto a board without its paired chip — the chip and the depth read from the
 * same object instead of two parallel derivations that can drift.
 */
export interface VisibleTactic {
  /** Raw motif string (the chip's `motif` prop → family color/icon). */
  motif: string;
  /** Display label (mate-family motifs collapse to "checkmate"). */
  motifLabel: string;
  /**
   * Orientation-aware 1-based depth string for the board badge, or null when the slot
   * carries no depth — the chip still shows, just without a board number.
   */
  depthLabel: string | null;
}

/**
 * Decide whether a tactic slot's live FILTER predicate passes, mirroring the backend
 * `tactic_slot_visible` (app/repositories/library_repository.py) axis-for-axis:
 * orientation scope, family narrowing, and the decision-anchored depth range (full-range
 * short-circuit; the +1 ALLOWED_DECISION_DEPTH_OFFSET applied to the allowed slot). Only
 * the TacticLineExplorer needs this — its API returns BOTH raw lines un-nulled so it must
 * re-filter client-side; the Games/Flaws card surfaces receive server-nulled slots. The
 * confidence gate is intentionally omitted here: the tactic-lines API only returns
 * already-confident tactics (the backend nulls sub-threshold slots).
 *
 * If this and the backend predicate ever drift, resolveVisibleTactic.test.ts fails.
 */
function slotPassesFilter(
  orientation: TacticDepthOrientation,
  motif: string,
  depth: number | null,
  filter: FlawFilterState,
): boolean {
  // 1. Orientation scope.
  const orientationFilter = filter.tacticOrientation ?? 'either';
  if (orientationFilter !== 'either' && orientationFilter !== orientation) return false;

  // 2. Family narrowing (skip when no families selected — all motifs pass).
  const families = filter.tacticFamilies ?? [];
  if (families.length > 0) {
    const family = TACTIC_FAMILY_FOR_MOTIF[motif];
    if (family == null || !families.includes(family)) return false;
  }

  // 3. Decision-anchored depth range — skip entirely on the full range, else compare
  //    (depth + allowed-offset) against the inclusive [min, max] bounds.
  const depthMin = filter.tacticDepthMin ?? DEFAULT_TACTIC_DEPTH_VALUE.min;
  const depthMax = filter.tacticDepthMax ?? DEFAULT_TACTIC_DEPTH_VALUE.max;
  const rangeActive = depthMin !== DEPTH_MIN || depthMax !== DEPTH_MAX;
  if (rangeActive) {
    if (depth == null) return false;
    const anchored = depth + (orientation === 'allowed' ? ALLOWED_DECISION_DEPTH_OFFSET : 0);
    if (anchored < depthMin || anchored > depthMax) return false;
  }
  return true;
}

/**
 * The single predicate deciding whether a tactic slot is shown, returning the paired
 * chip + depth-badge data (or null when hidden), so the chip and the depth number can
 * never diverge (`tacticDepthBadge` delegates to it).
 *
 * Always applies the family guard: family-less motifs (self-interference, clearance) surface no chip
 * (TacticMotifChip returns null), so their depth must never paint as
 * a bare number. When `filter` is supplied (TacticLineExplorer only), additionally
 * applies the live filter via `slotPassesFilter` so the explorer matches the
 * server-filtered Games/Flaws surfaces. Card surfaces pass no filter — their slots are
 * already nulled server-side, so only the family guard runs.
 */
export function resolveVisibleTactic(
  orientation: TacticDepthOrientation,
  motif: string | null,
  depth: number | null,
  filter?: FlawFilterState,
  anchored = true,
): VisibleTactic | null {
  if (motif == null) return null;
  const label = tacticMotifLabel(motif);
  if (TACTIC_FAMILY_FOR_MOTIF[label] == null) return null;
  // NOTE: `anchored` only changes the DISPLAY depth (depthLabel). The filter predicate
  // (`slotPassesFilter`) is the FE mirror of the backend depth filter and always keeps
  // the +1 allowed anchor offset, regardless of this flag.
  if (filter != null && !slotPassesFilter(orientation, motif, depth, filter)) return null;
  return {
    motif,
    motifLabel: label,
    depthLabel:
      depth != null ? String(toDisplayDepthForOrientation(depth, orientation, anchored)) : null,
  };
}

/**
 * Orientation-aware display depth for a miniboard depth badge, or null when the badge
 * must be hidden. Thin delegate over `resolveVisibleTactic` (no live filter) so the
 * family guard and depth formatting live in exactly one place. A badge shows only when
 * the motif also surfaces a chip — i.e. its motif resolves to a visible family.
 */
export function tacticDepthBadge(
  motif: string | null,
  depth: number | null,
  orientation: TacticDepthOrientation,
  anchored = true,
): string | null {
  return resolveVisibleTactic(orientation, motif, depth, undefined, anchored)?.depthLabel ?? null;
}

// ─── Library Stats tactic card ───────────────────────────────────────────────

/** Adapt one API bullet to the gap-bar view model (the components never see API types). */
export function tacticBulletToGapCell(b: TacticBullet): GapCell {
  return {
    delta: b.delta,
    zoneLo: b.zone_lo,
    zoneHi: b.zone_hi,
    hasZone: b.has_zone,
    significant: b.significant,
    youRate: b.you_rate,
    oppRate: b.opp_rate,
    ciLow: b.ci_low,
    ciHigh: b.ci_high,
    pValue: b.p_value,
    youEvents: b.you_events,
    oppEvents: b.opp_events,
  };
}

/** "a" or "an" for a lowercase noun phrase: "an" before a vowel letter or "x-" (x-ray). */
export function indefiniteArticle(name: string): 'a' | 'an' {
  return /^([aeiou]|x-)/i.test(name) ? 'an' : 'a';
}

export interface TacticSideCopy {
  /** Popover label: "Missed fork". */
  label: string;
  /** One plain sentence for the popover: "Your opponent left a fork on the board and you did not play it." */
  definition: string;
  /** Plural noun for the popover footer counts: "flaws with a missed fork". */
  noun: string;
}

/** Per-side popover copy for one tactic family Says flaws, never events. */
export function tacticSideCopy(familyName: string, side: TacticSide): TacticSideCopy {
  const name = familyName.toLowerCase();
  const article = indefiniteArticle(name);
  if (side === 'missed') {
    return {
      label: `Missed ${name}`,
      definition: `Your opponent left ${article} ${name} on the board and you did not play it.`,
      noun: `flaws with a missed ${name}`,
    };
  }
  return {
    label: `Allowed ${name}`,
    definition: `Your move handed your opponent ${article} ${name}.`,
    noun: `flaws with an allowed ${name}`,
  };
}

/** `discovered_attack` -> `discovered-attack`: the family segment of the tactic testids. */
export function tacticTestIdSegment(family: TacticFamily): string {
  return family.replace(/_/g, '-');
}
