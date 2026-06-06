import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { Clock, Zap, Brain, Target, Clover, TrendingDown, Swords } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  FAM_TEMPO,
  FAM_TEMPO_BG,
  FAM_OPPORTUNITY,
  FAM_OPPORTUNITY_BG,
  FAM_IMPACT,
  FAM_IMPACT_BG,
} from '@/lib/theme';
import type { FlawTag } from '@/types/library';
import { TAG_DEFINITIONS, TAG_LABELS } from '@/lib/tagDefinitions';

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
 * Family-colored tag chip with a hover/tap definition popover.
 *
 * Desktop: hovering the chip shows the popover after a 100ms delay.
 * Mobile (no hover): tapping the chip toggles the popover open/closed.
 *
 * The chip itself is the Radix Popover trigger (no separate HelpCircle icon).
 * Popover content shows: "<bold tag label>: <one-sentence definition>".
 * The definition text is sourced from tagDefinitions.ts (thresholds from
 * flawThresholds.ts, never hardcoded in JSX).
 *
 * Colors come from theme.ts FAM_* constants — no per-tag color sprawl.
 */
export function TagChip({ tag, gameId }: TagChipProps) {
  const family = getTagFamily(tag);
  const { color, bg } = TAG_FAMILY_COLORS[family];
  const Icon = TAG_ICONS[tag];

  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = () => {
    hoverTimeout.current = setTimeout(() => setOpen(true), 100);
  };

  const handleMouseLeave = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setOpen(false);
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 cursor-pointer text-sm font-bold transition-all hover:brightness-110 hover:-translate-y-px"
          style={{ color, backgroundColor: bg, borderColor: color }}
          role="button"
          tabIndex={0}
          aria-label={`Tag: ${tag} — ${TAG_DEFINITIONS[tag]}`}
          data-testid={`chip-${tag}-${gameId}`}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <Icon className="h-3 w-3 shrink-0" />
          {tag}
        </span>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="top"
          sideOffset={4}
          onMouseEnter={() => {
            if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
          }}
          onMouseLeave={handleMouseLeave}
          data-testid={`tag-popover-${tag}-${gameId}`}
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          <span className="font-bold">{TAG_LABELS[tag]}</span>: {TAG_DEFINITIONS[tag]}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
