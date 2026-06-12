import {
  Clock,
  Zap,
  Brain,
  Target,
  Clover,
  TrendingDown,
  ArrowDownUp,
  Swords,
  BookOpen,
  Trophy,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import {
  FAM_TEMPO,
  FAM_TEMPO_BG,
  FAM_OPPORTUNITY,
  FAM_OPPORTUNITY_BG,
  FAM_IMPACT,
  FAM_IMPACT_BG,
  FAM_PHASE,
  FAM_PHASE_BG,
} from '@/lib/theme';
import type { FlawTag } from '@/types/library';

// Shared flaw-tag visuals (icon + family color), so the chips, the filter panel,
// and the eval-chart tooltip all draw a tag the same way. Lives in lib/ (not a
// component file) so it can be imported anywhere without tripping react-refresh.

// ─── Tag → glyph (lucide icons, rendered at h-3 w-3) ─────────────────────
export const TAG_ICONS: Record<FlawTag, LucideIcon> = {
  'low-clock': Clock,
  'hasty': Zap,
  'unrushed': Brain,
  'miss': Target,
  'lucky': Clover,
  'reversed': ArrowDownUp,
  'squandered': TrendingDown,
  'opening': BookOpen,
  'middlegame': Swords,
  'endgame': Trophy,
};

// ─── Tag → family ────────────────────────────────────────────────────────
export type TagFamily = 'tempo' | 'opportunity' | 'impact' | 'phase';

export function getTagFamily(tag: FlawTag): TagFamily {
  switch (tag) {
    case 'low-clock':
    case 'hasty':
    case 'unrushed':
      return 'tempo';
    case 'miss':
    case 'lucky':
      return 'opportunity';
    case 'reversed':
    case 'squandered':
      return 'impact';
    case 'opening':
    case 'middlegame':
    case 'endgame':
      return 'phase';
  }
}

// ─── Family → colors (from theme.ts FAM_* constants) ──────────────────────
export interface FamilyColors {
  color: string; // foreground + border
  bg: string; // background
}

export const TAG_FAMILY_COLORS: Record<TagFamily, FamilyColors> = {
  tempo: { color: FAM_TEMPO, bg: FAM_TEMPO_BG },
  opportunity: { color: FAM_OPPORTUNITY, bg: FAM_OPPORTUNITY_BG },
  impact: { color: FAM_IMPACT, bg: FAM_IMPACT_BG },
  phase: { color: FAM_PHASE, bg: FAM_PHASE_BG },
};

/** A tag's family foreground color (chips, filter buttons, eval-chart tooltip). */
export function getTagColor(tag: FlawTag): string {
  return TAG_FAMILY_COLORS[getTagFamily(tag)].color;
}
