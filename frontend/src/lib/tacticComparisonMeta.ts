/**
 * Shared metadata for the 10 tactic-motif family comparison bullets (Phase 126, updated Phase 129).
 *
 * Single source of truth consumed by TacticComparisonGrid (family cards + rows),
 * TacticMotifChip (family color + icon), and the FilterPanel tactic-motif filter.
 *
 * Mirrors flawComparisonMeta.ts in structure. The 10 families map the TacticMotif
 * strings (D-08, Phase 129 plan 04 taxonomy redesign). The family taxonomy must
 * remain consistent with the backend FAMILY_TO_MOTIF_INTS mapping in
 * library_repository.py — the keys here are the cross-stack contract (string-for-string).
 *
 * Phase 129 plan 04 removed the combinations family; those motif strings (sacrifice,
 * deflection, attraction, intermezzo, interference, self-interference, clearance,
 * capturing-defender) now belong to no family. Old ?tactic=pin_skewer / discovery /
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
  Search,
  Footprints,
  AlertTriangle,
  Crown,
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
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
} from '@/lib/theme';
import { TACTIC_MOTIF_DEFINITIONS } from '@/lib/tacticMotifDefinitions';
import type { TacticBullet } from '@/types/library';

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
 * The 10 tactic family keys — cross-stack contract with backend FAMILY_TO_MOTIF_INTS.
 * These strings must equal the backend dict keys string-for-string (plan 129-04).
 * Filter display order (mechanism-grouped, Quick 260620-onv):
 *   Piece Attacks: fork → pin → skewer → x_ray → hanging → trapped_piece
 *   Checkmate, Checks & Discoveries: mate → double_check → discovered_check → discovered_attack
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
  | 'mate';

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
};

export const TACTIC_FAMILY_ICON: Record<TacticFamily, TacticIcon> = {
  fork: GitFork,
  skewer: MoveUp,
  pin: MapPin,
  x_ray: ScanLine,
  double_check: ChevronsUp,
  discovered_check: Eye,
  discovered_attack: Search,
  trapped_piece: Footprints,
  hanging: AlertTriangle,
  mate: Crown,
};

// ─── Mechanism groups (filter panel, Quick 260620-onv) ─────────────────────────

/**
 * The two mechanism-based sections of the tactic-motif filter. Display order
 * matters; chip order within a group follows TACTIC_COMPARISON_FAMILIES array order.
 */
export type TacticGroupKey = 'piece_attacks' | 'discoveries';

export interface TacticGroupDef {
  key: TacticGroupKey;
  /** Title-Case section label shown above the group's chips. */
  label: string;
}

/** Ordered groups rendered top-to-bottom in the filter panel. */
export const TACTIC_GROUPS: TacticGroupDef[] = [
  { key: 'piece_attacks', label: 'Piece Attacks' },
  { key: 'discoveries', label: 'Checkmate, Checks & Discoveries' },
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
 * The 10 tactic families in filter display order (mechanism-grouped, Quick 260620-onv).
 * Array order doubles as the chip order within each group — the filter panel groups
 * these by `group` preserving this order. The comparison grid resolves families by
 * `.find(f => f.family === ...)` and renders in server order, so it is unaffected by
 * this ordering. The motifs arrays mirror the backend FAMILY_TO_MOTIF_INTS mapping in
 * library_repository.py (plan 129-04 contract). Dropped combinations motif strings
 * (sacrifice, deflection, etc.) belong to no family.
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
    name: 'X-ray',
    family: 'x_ray',
    group: 'piece_attacks',
    chipLabel: 'x-ray',
    definition: 'A piece exerts indirect pressure through an enemy piece, threatening the square or piece behind it.',
    motifs: ['x-ray'],
  },
  {
    name: 'Hanging piece',
    family: 'hanging',
    group: 'piece_attacks',
    chipLabel: 'hanging-piece',
    definition: 'An undefended piece that can be captured for free.',
    motifs: ['hanging-piece'],
  },
  {
    name: 'Trapped piece',
    family: 'trapped_piece',
    group: 'piece_attacks',
    chipLabel: 'trapped-piece',
    definition: 'A piece has no safe square to move to and will be lost regardless of where it goes.',
    motifs: ['trapped-piece'],
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
];

/**
 * Derived mapping from motif string to its TacticFamily key.
 * Built by flattening TACTIC_COMPARISON_FAMILIES — no manual duplication.
 * Each family's `chipLabel` is also registered as a resolvable key so the
 * filter-panel legend (keyed on chipLabel) resolves icon/color — this is what
 * lets the synthetic "checkmate" label map to the `mate` family even though it
 * is not a backend motif string (Quick 260620-onv). For single-motif families
 * chipLabel already equals the motif, so the extra key is a harmless no-op.
 * Dropped combinations motif strings (sacrifice, deflection, etc.) map to no family;
 * consumers already guard `family == null`.
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
