import { useNavigate } from 'react-router-dom';
import { Clock, Zap, Brain, Target, Clover, TrendingDown, Swords } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import {
  FAM_TEMPO,
  FAM_TEMPO_BG,
  FAM_OPPORTUNITY,
  FAM_OPPORTUNITY_BG,
  FAM_IMPACT,
  FAM_IMPACT_BG,
} from '@/lib/theme';
import type { FlawTag } from '@/types/library';

// ─── Tag → family mapping ────────────────────────────────────────────────────

type TagFamily = 'tempo' | 'opportunity' | 'impact';

function getTagFamily(tag: FlawTag): TagFamily {
  switch (tag) {
    case 'low-clock':
    case 'impatient':
    case 'considered':
      return 'tempo';
    case 'miss':
    case 'lucky-escape':
      return 'opportunity';
    case 'while-ahead':
    case 'result-changing':
      return 'impact';
    // Phase tags are excluded by upstream curation (Phase 106); render as impact
    // fallback if somehow received — no branching on phase tags expected here.
    case 'opening':
    case 'middlegame':
    case 'endgame':
      return 'impact';
  }
}

// ─── Family → colors (from theme.ts FAM_* constants) ──────────────────────

interface FamilyColors {
  color: string; // foreground + border
  bg: string;    // background
}

const TAG_FAMILY_COLORS: Record<TagFamily, FamilyColors> = {
  tempo: { color: FAM_TEMPO, bg: FAM_TEMPO_BG },
  opportunity: { color: FAM_OPPORTUNITY, bg: FAM_OPPORTUNITY_BG },
  impact: { color: FAM_IMPACT, bg: FAM_IMPACT_BG },
};

// ─── Tag → glyph (lucide icons, rendered at h-3 w-3) ─────────────────────

const TAG_ICONS: Record<FlawTag, LucideIcon> = {
  'low-clock': Clock,
  'impatient': Zap,
  'considered': Brain,
  'miss': Target,
  'lucky-escape': Clover,
  'while-ahead': TrendingDown,
  'result-changing': Swords,
  'opening': Brain,
  'middlegame': Brain,
  'endgame': Brain,
};

// ─── Component ───────────────────────────────────────────────────────────────

interface TagChipProps {
  tag: FlawTag;
  gameId: number;
}

/**
 * Family-colored tag chip that navigates to /library/flaws?tag={TAG} on click (D-05).
 *
 * Phase 107 shipped chips as display-only (Radix Popover trigger). Phase 108 Plan 08
 * converts them to navigation triggers: clicking deep-links to the Flaws tab
 * pre-filtered to the selected tag across ALL games (no game_id in URL, D-05).
 *
 * D-05 explicitly drops game_id from the URL so the chip acts as a broad doorway
 * ("all my flaws of this kind"), not a per-game drill-down.
 *
 * aria-label changed from "Tag: {tag} — {definition}" to "Filter flaws by tag: {tag}"
 * to reflect the navigable (not popover-info) interaction. data-testid is unchanged.
 *
 * Colors come from theme.ts FAM_* constants — no per-tag color sprawl.
 */
export function TagChip({ tag, gameId }: TagChipProps) {
  const navigate = useNavigate();
  const family = getTagFamily(tag);
  const { color, bg } = TAG_FAMILY_COLORS[family];
  const Icon = TAG_ICONS[tag];

  return (
    <button
      type="button"
      className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 cursor-pointer text-sm font-bold transition-all hover:brightness-110 hover:-translate-y-px"
      style={{ color, backgroundColor: bg, borderColor: color }}
      aria-label={`Filter flaws by tag: ${tag}`}
      data-testid={`chip-${tag}-${gameId}`}
      onClick={() => navigate(`/library/flaws?tag=${tag}`)}
    >
      <Icon className="h-3 w-3 shrink-0" />
      {tag}
    </button>
  );
}
