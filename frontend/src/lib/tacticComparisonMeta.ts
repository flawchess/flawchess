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
  Minus,
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
 * Display order: fork → skewer → pin → x_ray → double_check → discovered_check
 *   → discovered_attack → trapped_piece → hanging → mate.
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
  skewer: Minus,
  pin: MapPin,
  x_ray: ScanLine,
  double_check: ChevronsUp,
  discovered_check: Eye,
  discovered_attack: Search,
  trapped_piece: Footprints,
  hanging: AlertTriangle,
  mate: Crown,
};

// ─── Family definitions ───────────────────────────────────────────────────────

export interface TacticFamilyDef {
  /** Card-header title / filter label. */
  name: string;
  family: TacticFamily;
  /** One-line explanation for the comparison tooltip's first paragraph. */
  definition: string;
  /** All motif strings that belong to this family (must match FAMILY_TO_MOTIF_INTS). */
  motifs: string[];
}

/**
 * The 10 tactic families in display order. The motifs arrays mirror the backend
 * FAMILY_TO_MOTIF_INTS mapping in library_repository.py (plan 129-04 contract).
 * Dropped combinations motif strings (sacrifice, deflection, etc.) belong to no family.
 */
export const TACTIC_COMPARISON_FAMILIES: TacticFamilyDef[] = [
  {
    name: 'Fork',
    family: 'fork',
    definition: 'A single piece attacks two or more enemy pieces at the same time.',
    motifs: ['fork'],
  },
  {
    name: 'Skewer',
    family: 'skewer',
    definition: 'A valuable piece is forced to move, leaving a less valuable piece behind it undefended.',
    motifs: ['skewer'],
  },
  {
    name: 'Pin',
    family: 'pin',
    definition: 'A piece cannot move without exposing a more valuable piece behind it to capture.',
    motifs: ['pin'],
  },
  {
    name: 'X-ray',
    family: 'x_ray',
    definition: 'A piece exerts indirect pressure through an enemy piece, threatening the square or piece behind it.',
    motifs: ['x-ray'],
  },
  {
    name: 'Double check',
    family: 'double_check',
    definition: 'The king is placed in check by two pieces simultaneously, leaving only a king move as the reply.',
    motifs: ['double-check'],
  },
  {
    name: 'Discovered check',
    family: 'discovered_check',
    definition: 'Moving one piece uncovers a check delivered by the piece behind it, not the piece that moved.',
    motifs: ['discovered-check'],
  },
  {
    name: 'Discovered attack',
    family: 'discovered_attack',
    definition: 'Moving one piece uncovers an attack from the piece behind it.',
    motifs: ['discovered-attack'],
  },
  {
    name: 'Trapped piece',
    family: 'trapped_piece',
    definition: 'A piece has no safe square to move to and will be lost regardless of where it goes.',
    motifs: ['trapped-piece'],
  },
  {
    name: 'Hanging piece',
    family: 'hanging',
    definition: 'An undefended piece that can be captured for free.',
    motifs: ['hanging-piece'],
  },
  {
    name: 'Mate patterns',
    family: 'mate',
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
];

/**
 * Derived mapping from motif string to its TacticFamily key.
 * Built by flattening TACTIC_COMPARISON_FAMILIES — no manual duplication.
 * Dropped combinations motif strings (sacrifice, deflection, etc.) map to no family;
 * consumers already guard `family == null`.
 */
export const TACTIC_FAMILY_FOR_MOTIF: Record<string, TacticFamily> = Object.fromEntries(
  TACTIC_COMPARISON_FAMILIES.flatMap(({ family, motifs }) =>
    motifs.map((motif) => [motif, family]),
  ),
);

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
