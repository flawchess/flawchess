/**
 * Shared metadata for the tactic-motif family comparison bullets (Phase 126, updated
 * Phase 129; tier-3 Advanced families added Quick 260623-6pd → 15 families; Phase 133
 * plan 133-02 added attraction + sacrifice → 17 families; Quick 260623 added the move-type
 * families en-passant + under-promotion → 19 families).
 *
 * Single source of truth consumed by TacticComparisonGrid (family cards + rows),
 * TacticMotifChip (family color + icon), and the FilterPanel tactic-motif filter.
 *
 * Mirrors flawComparisonMeta.ts in structure. The families map the TacticMotif strings
 * (D-08, Phase 129 plan 04 taxonomy redesign). The family taxonomy must remain
 * consistent with the backend FAMILY_TO_MOTIF_INTS mapping in library_repository.py —
 * the keys here are the cross-stack contract (string-for-string).
 *
 * Quick 260623-6pd surfaced the shipped Phase-132 tier-3 motifs (x-ray, deflection,
 * intermezzo, interference, clearance, capturing-defender) under an "Advanced" group.
 * Phase 133 (plan 133-02) added attraction and sacrifice as Advanced families.
 * Only self-interference belongs to no family. Old ?tactic=pin_skewer / discovery /
 * combinations URL params are inert (backend .get(fam, []) no-op; union excludes them).
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
  DoorOpen,
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
  TAC_CLEARANCE,
  TAC_CLEARANCE_BG,
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
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
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
import type { TacticBullet } from '@/types/library';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

// Re-export TacticBullet for consumers that import from this module.
export type { TacticBullet };

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
 * These strings must equal the backend dict keys string-for-string (plan 129-04).
 * Filter display order (mechanism-grouped, Quick 260620-onv; Advanced added 260623-6pd):
 *   Piece Attacks: fork → pin → skewer → hanging
 *   Checkmate, Checks & Discoveries: mate → double_check → discovered_check → discovered_attack
 *   Advanced (tier-3): trapped_piece → x_ray → deflection → intermezzo → interference → clearance → capturing_defender → attraction → sacrifice
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
  // Tier-3 "Advanced" families (Quick 260623-6pd)
  | 'deflection'
  | 'intermezzo'
  | 'interference'
  | 'clearance'
  | 'capturing_defender'
  // Phase 133 (plan 133-02): attraction + sacrifice unsuppressed
  | 'attraction'
  | 'sacrifice'
  // Move-type families (Quick 260623): en-passant + under-promotion unsuppressed
  | 'en_passant'
  | 'under_promotion'
  // promotion (28) surfaced (was hidden under D-09; perfect-precision residual motif)
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
  clearance: { color: TAC_CLEARANCE, bg: TAC_CLEARANCE_BG },
  capturing_defender: { color: TAC_CAPTURING_DEFENDER, bg: TAC_CAPTURING_DEFENDER_BG },
  // Phase 133 (plan 133-02): attraction + sacrifice
  attraction: { color: TAC_ATTRACTION, bg: TAC_ATTRACTION_BG },
  sacrifice: { color: TAC_SACRIFICE, bg: TAC_SACRIFICE_BG },
  // Move-type families (Quick 260623): en-passant + under-promotion
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
  clearance: DoorOpen,
  capturing_defender: ShieldOff,
  // Phase 133 (plan 133-02): attraction + sacrifice
  attraction: Magnet,
  sacrifice: Gift,
  // Move-type families (Quick 260623): en-passant + under-promotion
  en_passant: ArrowLeftRight,
  under_promotion: ArrowDownFromLine,
  promotion: ArrowUpFromLine,
};

// ─── Mechanism groups (filter panel, Quick 260620-onv) ─────────────────────────

/**
 * The mechanism-based sections of the tactic-motif filter. Display order matters;
 * chip order within a group follows TACTIC_COMPARISON_FAMILIES array order. The
 * 'advanced' group (tier-3 motifs, Quick 260623-6pd) renders inside a collapsible,
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

// ─── Family definitions ───────────────────────────────────────────────────────

export interface TacticFamilyDef {
  /** Card-header title / comparison-tooltip label (Title Case, e.g. "Hanging piece"). */
  name: string;
  family: TacticFamily;
  /** Mechanism group this family belongs to (filter panel sectioning). */
  group: TacticGroupKey;
  /** Kebab-case label shown on the filter chip (e.g. "hanging-piece"). */
  chipLabel: string;
  /** One-line explanation for the comparison tooltip's first paragraph. */
  definition: string;
  /** All motif strings that belong to this family (must match FAMILY_TO_MOTIF_INTS). */
  motifs: string[];
}

/**
 * The 19 tactic families in filter display order (mechanism-grouped, Quick 260620-onv;
 * tier-3 Advanced group added Quick 260623-6pd; attraction + sacrifice added Phase 133;
 * en-passant + under-promotion added Quick 260623).
 * Array order doubles as the chip order within each group — the filter panel groups
 * these by `group` preserving this order. The comparison grid resolves families by
 * `.find(f => f.family === ...)` and renders in server order, so it is unaffected by
 * this ordering. The motifs arrays mirror the backend FAMILY_TO_MOTIF_INTS mapping in
 * library_repository.py (plan 129-04 contract). Only self-interference belongs to no family
 * (promotion was added here when D-09 was reversed).
 */
export const TACTIC_COMPARISON_FAMILIES: TacticFamilyDef[] = [
  // ── Piece Attacks ──
  {
    name: 'Fork',
    family: 'fork',
    group: 'piece_attacks',
    chipLabel: 'fork',
    definition: 'A single piece attacks two or more enemy pieces at the same time.',
    motifs: ['fork'],
  },
  {
    name: 'Pin',
    family: 'pin',
    group: 'piece_attacks',
    chipLabel: 'pin',
    definition: 'A piece cannot move without exposing a more valuable piece behind it to capture.',
    motifs: ['pin'],
  },
  {
    name: 'Skewer',
    family: 'skewer',
    group: 'piece_attacks',
    chipLabel: 'skewer',
    definition: 'A valuable piece is forced to move, leaving a less valuable piece behind it undefended.',
    motifs: ['skewer'],
  },
  {
    name: 'Hanging piece',
    family: 'hanging',
    group: 'piece_attacks',
    chipLabel: 'hanging-piece',
    definition: 'An undefended piece that can be captured for free.',
    motifs: ['hanging-piece'],
  },
  // ── Checkmate, Checks & Discoveries ──
  // Mate leads the group (chip "checkmate"); the legend shows a single "checkmate"
  // row rather than the nine named-mate motifs (Quick 260620-onv follow-up). Then
  // the checks (double-check, discovered-check), then the pure discovery.
  {
    name: 'Checkmate',
    family: 'mate',
    group: 'discoveries',
    chipLabel: 'checkmate',
    definition: 'Recurring checkmate configurations such as back-rank, smothered, and corner mates.',
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
    definition: 'The king is placed in check by two pieces simultaneously, leaving only a king move as the reply.',
    motifs: ['double-check'],
  },
  {
    name: 'Discovered check',
    family: 'discovered_check',
    group: 'discoveries',
    chipLabel: 'discovered-check',
    definition: 'Moving one piece uncovers a check delivered by the piece behind it, not the piece that moved.',
    motifs: ['discovered-check'],
  },
  {
    name: 'Discovered attack',
    family: 'discovered_attack',
    group: 'discoveries',
    chipLabel: 'discovered-attack',
    definition: 'Moving one piece uncovers an attack from the piece behind it.',
    motifs: ['discovered-attack'],
  },
  // ── Advanced (tier-3, Quick 260623-6pd) ──
  // Shipped Phase-132 cook-aligned motifs surfaced behind the collapsible "Advanced"
  // filter section. trapped-piece leads, then x-ray (geometric), then the lure/disruption motifs.
  {
    name: 'Trapped piece',
    family: 'trapped_piece',
    group: 'advanced',
    chipLabel: 'trapped-piece',
    definition: 'A piece has no safe square to move to and will be lost regardless of where it goes.',
    motifs: ['trapped-piece'],
  },
  {
    name: 'X-ray',
    family: 'x_ray',
    group: 'advanced',
    chipLabel: 'x-ray',
    definition: 'A piece exerts indirect pressure through an enemy piece, threatening the square or piece behind it.',
    motifs: ['x-ray'],
  },
  {
    name: 'Deflection',
    family: 'deflection',
    group: 'advanced',
    chipLabel: 'deflection',
    definition: 'An opponent\'s piece is lured or forced away from a critical square it was defending.',
    motifs: ['deflection'],
  },
  {
    name: 'Intermezzo',
    family: 'intermezzo',
    group: 'advanced',
    chipLabel: 'intermezzo',
    definition: 'An in-between move is played before completing an expected sequence, often gaining tempo.',
    motifs: ['intermezzo'],
  },
  {
    name: 'Interference',
    family: 'interference',
    group: 'advanced',
    chipLabel: 'interference',
    definition: 'A piece is placed on a square that disrupts the coordination between two of the opponent\'s pieces.',
    motifs: ['interference'],
  },
  {
    name: 'Clearance',
    family: 'clearance',
    group: 'advanced',
    chipLabel: 'clearance',
    definition: 'A piece vacates a square or line so another piece can use it more effectively.',
    motifs: ['clearance'],
  },
  {
    name: 'Capturing defender',
    family: 'capturing_defender',
    group: 'advanced',
    chipLabel: 'capturing-defender',
    definition: 'The piece defending a key square or piece is captured to remove that protection.',
    motifs: ['capturing-defender'],
  },
  // Phase 133 (plan 133-02): attraction + sacrifice unsuppressed, added as Advanced families.
  {
    name: 'Attraction',
    family: 'attraction',
    group: 'advanced',
    chipLabel: 'attraction',
    definition: "An opponent's piece is drawn onto a square where it becomes vulnerable to a follow-up tactic.",
    motifs: ['attraction'],
  },
  {
    name: 'Sacrifice',
    family: 'sacrifice',
    group: 'advanced',
    chipLabel: 'sacrifice',
    definition: 'A piece or pawn is given up deliberately to gain a positional or tactical advantage.',
    motifs: ['sacrifice'],
  },
  // Move-type families (Quick 260623): en-passant + under-promotion unsuppressed (P=1.000 on
  // the Phase-134 fixture). Both fire only at Tier 5 (residual), so these chips are low-volume.
  {
    name: 'En passant',
    family: 'en_passant',
    group: 'advanced',
    chipLabel: 'en-passant',
    definition: 'A pawn captures an enemy pawn that has just advanced two squares, as if it had moved only one.',
    motifs: ['en-passant'],
  },
  {
    name: 'Under-promotion',
    family: 'under_promotion',
    group: 'advanced',
    chipLabel: 'under-promotion',
    definition: 'A pawn promotes to a knight, bishop, or rook instead of a queen to deliver a specific tactic.',
    motifs: ['under-promotion'],
  },
  // promotion (28): surfaced (was D-09-hidden). Perfect-precision residual move-type
  // motif — fires only when the winning line queens a pawn and no sharper tactic applies.
  // Sibling of under-promotion; the "allowed" orientation ("you let the opponent queen")
  // is an instructive endgame mistake.
  {
    name: 'Promotion',
    family: 'promotion',
    group: 'advanced',
    chipLabel: 'promotion',
    definition: 'A pawn reaches the back rank and promotes to a queen, often deciding the game.',
    motifs: ['promotion'],
  },
];

/**
 * Derived mapping from motif string to its TacticFamily key.
 * Built by flattening TACTIC_COMPARISON_FAMILIES — no manual duplication.
 * Each family's `chipLabel` is also registered as a resolvable key so the
 * filter-panel legend (keyed on chipLabel) resolves icon/color — this is what
 * lets the synthetic "checkmate" label map to the `mate` family even though it
 * is not a backend motif string (Quick 260620-onv). For single-motif families
 * chipLabel already equals the motif, so the extra key is a harmless no-op.
 * Only self-interference maps to no family now; consumers already guard `family == null`.
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
 * flaw cards do not distinguish named-mate subtypes (Quick 260620-onv). All other
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
 * Bundled visibility decision for one tactic slot (Quick 260625-qbj). When non-null,
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
 * already-confident tactics (the backend nulls sub-threshold slots, D-09).
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
 * chip + depth-badge data (or null when hidden). Replaces the former separate
 * `tacticDepthBadge` / `tacticOrientationPasses` / inline depth-label derivations so the
 * chip and the depth number can never diverge (Quick 260625-qbj).
 *
 * Always applies the family guard: family-less motifs (promotion (28), self-interference
 * (14)) surface no chip (TacticMotifChip returns null), so their depth must never paint as
 * a bare number (D-09). When `filter` is supplied (TacticLineExplorer only), additionally
 * applies the live filter via `slotPassesFilter` so the explorer matches the
 * server-filtered Games/Flaws surfaces. Card surfaces pass no filter — their slots are
 * already nulled server-side, so only the family guard runs.
 */
export function resolveVisibleTactic(
  orientation: TacticDepthOrientation,
  motif: string | null,
  depth: number | null,
  filter?: FlawFilterState,
): VisibleTactic | null {
  if (motif == null) return null;
  const label = tacticMotifLabel(motif);
  if (TACTIC_FAMILY_FOR_MOTIF[label] == null) return null;
  if (filter != null && !slotPassesFilter(orientation, motif, depth, filter)) return null;
  return {
    motif,
    motifLabel: label,
    depthLabel: depth != null ? String(toDisplayDepthForOrientation(depth, orientation)) : null,
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
): string | null {
  return resolveVisibleTactic(orientation, motif, depth)?.depthLabel ?? null;
}

// ─── Stat helpers (shared by the grid + tooltips) ──────────────────────────────

/**
 * Two-sided significance at alpha = 0.05: the 95% CI excludes zero.
 * Mirrors isFlawDeltaSignificant from flawComparisonMeta.ts.
 * Used to gate the delta color: significant → zone color, otherwise muted.
 */
export function isTacticDeltaSignificant(bullet: TacticBullet): boolean {
  if (bullet.ci_low == null || bullet.ci_high == null) return false;
  return bullet.ci_low > 0 || bullet.ci_high < 0;
}

/**
 * Zone color for the signed tactic delta. Inverted convention: fewer tactic
 * allowances than opponents (delta below the band) is good → green (ZONE_SUCCESS).
 * Mirrors flawDeltaZoneColor from flawComparisonMeta.ts.
 */
export function tacticDeltaZoneColor(delta: number, zoneLo: number, zoneHi: number): string {
  if (delta >= zoneHi) return ZONE_DANGER;
  if (delta >= zoneLo) return ZONE_NEUTRAL;
  return ZONE_SUCCESS;
}
