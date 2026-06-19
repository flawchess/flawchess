/**
 * Shared metadata for the 6 tactic-motif family comparison bullets (Phase 126).
 *
 * Single source of truth consumed by TacticComparisonGrid (family cards + rows),
 * TacticMotifChip (family color + icon), and the FilterPanel tactic-motif filter.
 *
 * Mirrors flawComparisonMeta.ts in structure. The six families collapse the 24
 * TacticMotif strings (D-08). The family taxonomy must remain consistent with the
 * backend FAMILY_TO_MOTIF_INTS mapping in library_repository.py.
 */

import type { ComponentType, CSSProperties } from 'react';
import { GitFork, MoveUp, Zap, Crown, AlertTriangle, Swords } from 'lucide-react';

import {
  TAC_FORK,
  TAC_FORK_BG,
  TAC_PIN_SKEWER,
  TAC_PIN_SKEWER_BG,
  TAC_DISCOVERY,
  TAC_DISCOVERY_BG,
  TAC_MATE,
  TAC_MATE_BG,
  TAC_HANGING,
  TAC_HANGING_BG,
  TAC_COMBINATIONS,
  TAC_COMBINATIONS_BG,
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

export type TacticFamily =
  | 'fork'
  | 'pin_skewer'
  | 'discovery'
  | 'mate'
  | 'hanging'
  | 'combinations';

export interface TacticFamilyColors {
  /** Icon + chip foreground color. */
  color: string;
  /** Soft background tint (translucent, same pattern as FlawFamilyColors). */
  bg: string;
}

export const TACTIC_FAMILY_COLORS: Record<TacticFamily, TacticFamilyColors> = {
  fork: { color: TAC_FORK, bg: TAC_FORK_BG },
  pin_skewer: { color: TAC_PIN_SKEWER, bg: TAC_PIN_SKEWER_BG },
  discovery: { color: TAC_DISCOVERY, bg: TAC_DISCOVERY_BG },
  mate: { color: TAC_MATE, bg: TAC_MATE_BG },
  hanging: { color: TAC_HANGING, bg: TAC_HANGING_BG },
  combinations: { color: TAC_COMBINATIONS, bg: TAC_COMBINATIONS_BG },
};

export const TACTIC_FAMILY_ICON: Record<TacticFamily, TacticIcon> = {
  fork: GitFork,
  pin_skewer: MoveUp,
  discovery: Zap,
  mate: Crown,
  hanging: AlertTriangle,
  combinations: Swords,
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
 * The six tactic families in display order. The motifs arrays collectively cover
 * all 24 TacticMotif strings exactly once (D-08). Must match backend
 * FAMILY_TO_MOTIF_INTS in library_repository.py.
 */
export const TACTIC_COMPARISON_FAMILIES: TacticFamilyDef[] = [
  {
    name: 'Fork',
    family: 'fork',
    definition: 'A single piece attacks two or more enemy pieces at the same time.',
    motifs: ['fork'],
  },
  {
    name: 'Pin / Skewer',
    family: 'pin_skewer',
    definition:
      'A piece is stuck in front of (pin) or behind (skewer) a more valuable piece along the same line.',
    motifs: ['pin', 'skewer', 'x-ray'],
  },
  {
    name: 'Discovery',
    family: 'discovery',
    definition: 'Moving one piece uncovers an attack from the piece behind it, sometimes with check.',
    motifs: ['discovered-attack', 'double-check'],
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
  {
    name: 'Hanging piece',
    family: 'hanging',
    definition: 'An undefended piece that can be captured for free.',
    motifs: ['hanging-piece'],
  },
  {
    name: 'Combinations',
    family: 'combinations',
    definition:
      'Forcing sequences like sacrifices, deflections, and decoys that win material or deliver mate.',
    motifs: [
      'sacrifice',
      'deflection',
      'attraction',
      'intermezzo',
      'interference',
      'self-interference',
      'clearance',
      'capturing-defender',
    ],
  },
];

/**
 * Derived mapping from motif string to its TacticFamily key.
 * Built by flattening TACTIC_COMPARISON_FAMILIES — no manual duplication.
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
