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
  ACTIVE_FILTER_RING_CLASS,
} from '@/lib/theme';
import type { FlawTag } from '@/types/library';
import { TAG_DEFINITIONS } from '@/lib/tagDefinitions';
import { useFlawFilterStore } from '@/hooks/useFlawFilterStore';

// Card switches to the stacked mobile layout below Tailwind's `sm` (640px), where
// the tag chips sit *below* the eval chart. A top-opening popover would then cover
// the chart, so on mobile we open the definition popover downward instead.
const SM_BREAKPOINT_PX = 640;

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = React.useState(
    () =>
      typeof window !== 'undefined' &&
      window.matchMedia(`(max-width: ${SM_BREAKPOINT_PX - 1}px)`).matches,
  );
  React.useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${SM_BREAKPOINT_PX - 1}px)`);
    const update = (): void => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}

// ─── Tag → family mapping ────────────────────────────────────────────────────

type TagFamily = 'tempo' | 'opportunity' | 'impact';

function getTagFamily(tag: FlawTag): TagFamily {
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
  'hasty': Zap,
  'unrushed': Brain,
  'miss': Target,
  'lucky': Clover,
  'reversed': Swords,
  'squandered': TrendingDown,
  'opening': Brain,
  'middlegame': Brain,
  'endgame': Brain,
};

// ─── Component ───────────────────────────────────────────────────────────────

interface TagChipProps {
  tag: FlawTag;
  gameId: number;
  /**
   * Occurrence count for this tag within the game (Games card only). Rendered
   * count-first like the severity badges, but only when > 1 (a lone occurrence
   * adds no information). Omitted (FlawsTab, where each row is a single flaw) →
   * no number shown.
   */
  count?: number;
  /**
   * Optional hover callback (Games card only). Fires true on pointer enter, false
   * on leave — lets the parent highlight this tag's eval-chart markers. Fires
   * alongside the definition popover; omitted call sites get no highlight wiring.
   */
  onHover?: (active: boolean) => void;
}

/**
 * Family-colored tag chip with a hover/tap definition popover (D-05 / D-06).
 *
 * Desktop: hovering the chip shows the popover after a 100ms delay.
 * Mobile (no hover): tapping the chip toggles the popover open/closed.
 *
 * Navigation removed (D-06): chips no longer deep-link to the flaws filtered view.
 * The whole chip is the Radix Popover trigger (no separate HelpCircle icon).
 * Popover body: "<bold tag-name>: <one-sentence definition>".
 *   - The bold heading is the raw lowercase-with-dash tag string (D-07).
 *   - Definitions are sourced from tagDefinitions.ts; thresholds from flawThresholds.ts.
 *
 * Active-filter ring (D-05): the chip subscribes to useFlawFilterStore internally.
 * When the chip's tag matches an active filter, a colored ring is applied (theme.ts
 * ACTIVE_FILTER_RING_CLASS). Both Games and Flaws card call sites get the ring
 * without prop drilling or changes to either call site.
 *
 * Colors come from theme.ts FAM_* constants — no per-tag color sprawl.
 */
export function TagChip({ tag, gameId, count, onHover }: TagChipProps) {
  const family = getTagFamily(tag);
  const { color, bg } = TAG_FAMILY_COLORS[family];
  const Icon = TAG_ICONS[tag];

  // D-05: subscribe to the flaw filter store internally so both LibraryGameCard
  // (Games tab) and FlawsTab (Flaws tab) get the ring without prop drilling.
  const [flawFilter] = useFlawFilterStore();
  const isActive = flawFilter.tags.includes(tag);

  // Mobile: open the popover below the chip so it doesn't cover the eval chart
  // (which sits above the tags in the stacked layout). Desktop: keep it above.
  const isMobile = useIsMobile();
  const popoverSide = isMobile ? 'bottom' : 'top';

  const [open, setOpen] = React.useState(false);
  const openTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const closeTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Open on hover after a short delay; close on a brief grace delay so moving the
  // pointer from the trigger into the portal-rendered popover body does not close it
  // first (the body's onMouseEnter cancels the pending close). Fixes the hover→content
  // flicker that an immediate setOpen(false) on mouseleave caused.
  const scheduleOpen = (): void => {
    if (closeTimeout.current) clearTimeout(closeTimeout.current);
    openTimeout.current = setTimeout(() => setOpen(true), 100);
  };
  const scheduleClose = (): void => {
    if (openTimeout.current) clearTimeout(openTimeout.current);
    closeTimeout.current = setTimeout(() => setOpen(false), 80);
  };
  const cancelClose = (): void => {
    if (closeTimeout.current) clearTimeout(closeTimeout.current);
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          className={cn(
            // text-xs (one level below the severity badges) is an intentional
            // deviation from the CLAUDE.md text-sm floor, per explicit request to
            // make the tag chips a bit smaller than the M/B/I count badges.
            'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 cursor-pointer text-xs font-bold transition-all hover:brightness-110 hover:-translate-y-px',
            isActive && ACTIVE_FILTER_RING_CLASS,
          )}
          style={{
            color,
            backgroundColor: bg,
            borderColor: color,
            // Ring color matches the family color for D-05 active-filter emphasis.
            ...(isActive ? { '--tw-ring-color': color } as React.CSSProperties : {}),
          }}
          role="button"
          tabIndex={0}
          aria-label={`Tag: ${tag} — ${TAG_DEFINITIONS[tag]}`}
          data-testid={`chip-${tag}-${gameId}`}
          onMouseEnter={() => {
            scheduleOpen();
            onHover?.(true);
          }}
          onMouseLeave={() => {
            scheduleClose();
            onHover?.(false);
          }}
        >
          {count != null && count > 1 && <span className="font-bold">{count}</span>}
          <Icon className="h-3 w-3 shrink-0" />
          {tag}
        </span>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side={popoverSide}
          sideOffset={4}
          onMouseEnter={cancelClose}
          onMouseLeave={scheduleClose}
          data-testid={`tag-popover-${tag}-${gameId}`}
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          <span className="font-bold">{tag}</span>: {TAG_DEFINITIONS[tag]}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
