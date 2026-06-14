import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { cn } from '@/lib/utils';
import { ACTIVE_FILTER_RING_CLASS } from '@/lib/theme';
import { TAG_ICONS, getTagFamily, TAG_FAMILY_COLORS } from '@/lib/tagVisuals';
import type { FlawTag } from '@/types/library';
import { TAG_DEFINITIONS } from '@/lib/tagDefinitions';
import { useFlawFilterStore } from '@/hooks/useFlawFilterStore';
import { InfoPopover } from '@/components/ui/info-popover';

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

// Hover/focus highlight: the family BG constants are translucent (alpha 0.15), so a
// plain brightness filter barely registers on them. While the chip is the active
// pointer/focus target we bump the fill to a denser alpha (and brighten the
// font/icon/border via a filter) so it clearly reads as highlighted for as long as
// it has focus. All three FAM_*_BG strings end in `/ 0.15)`.
const HIGHLIGHT_BG = (bg: string): string => bg.replace('/ 0.15)', '/ 0.3)');

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
  /**
   * Optional click/tap activation (Games card only, used with definition={false}).
   * Fires when the chip is clicked or activated via keyboard — the card uses it to
   * cycle the eval chart through this tag's flaw plies. Omitted call sites are
   * unaffected (the chip stays a plain highlight-only span).
   */
  onActivate?: () => void;
  /**
   * When false, the per-chip hover/tap definition popover is suppressed and the
   * chip renders as a plain (highlight-only) span. The Games card sets this and
   * surfaces definitions once via <TagLegend> below the chip row instead, so the
   * eval chart is never covered by a per-chip overlay. Defaults to true (FlawsTab
   * keeps the inline popover).
   */
  definition?: boolean;
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
export function TagChip({ tag, gameId, count, onHover, onActivate, definition = true }: TagChipProps) {
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

  // The chip only earns hover/tap affordances when something is actually wired to
  // it: a chart-highlight callback (onHover), a click action (onActivate), or the
  // inline definition popover (definition). FlawsTab renders chips with none of
  // these (it surfaces definitions via <TagLegend> instead), so there they are
  // purely decorative — no highlight, no lift, no cursor, not focusable.
  const interactive = Boolean(onHover || onActivate || definition);

  const [open, setOpen] = React.useState(false);
  // Brighten the chip while it is hovered or focused (tap-focus on mobile), held
  // for as long as it has focus.
  const [highlighted, setHighlighted] = React.useState(false);
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

  // Clear any pending open/close timer on unmount. Without this, a hover-armed
  // setTimeout could fire setOpen() after the component (and, in tests, the
  // jsdom window) was torn down — surfacing as a "window is not defined"
  // unhandled error that failed CI non-deterministically.
  React.useEffect(() => {
    return () => {
      if (openTimeout.current) clearTimeout(openTimeout.current);
      if (closeTimeout.current) clearTimeout(closeTimeout.current);
    };
  }, []);

  const chip = (
    <span
      className={cn(
        // text-xs (one level below the severity badges) is an intentional
        // deviation from the CLAUDE.md text-sm floor, per explicit request to
        // make the tag chips a bit smaller than the M/B/I count badges.
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-bold',
        interactive && 'cursor-pointer transition-all hover:-translate-y-px',
        isActive && ACTIVE_FILTER_RING_CLASS,
      )}
      style={{
        color,
        backgroundColor: highlighted ? HIGHLIGHT_BG(bg) : bg,
        borderColor: color,
        // Brighten font/icon/border while hovered or focused.
        filter: highlighted ? 'brightness(1.2)' : undefined,
        // Ring color matches the family color for D-05 active-filter emphasis.
        ...(isActive ? { '--tw-ring-color': color } as React.CSSProperties : {}),
      }}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-label={`Tag: ${tag} — ${TAG_DEFINITIONS[tag]}`}
      data-testid={`chip-${tag}-${gameId}`}
      onMouseEnter={
        interactive
          ? () => {
              if (definition) scheduleOpen();
              onHover?.(true);
              setHighlighted(true);
            }
          : undefined
      }
      onMouseLeave={
        interactive
          ? () => {
              if (definition) scheduleClose();
              onHover?.(false);
              setHighlighted(false);
            }
          : undefined
      }
      onFocus={interactive ? () => setHighlighted(true) : undefined}
      onBlur={interactive ? () => setHighlighted(false) : undefined}
      onClick={onActivate ? () => onActivate() : undefined}
      onKeyDown={
        onActivate
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onActivate();
              }
            }
          : undefined
      }
    >
      {count != null && count > 1 && <span className="font-bold">{count}</span>}
      <Icon className="h-3 w-3 shrink-0" />
      {tag}
    </span>
  );

  // Games card suppresses the per-chip overlay (definition=false) and shows a
  // single <TagLegend> below the chip row instead; return the plain chip.
  if (!definition) return chip;

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>{chip}</PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side={popoverSide}
          sideOffset={4}
          // This is a hover/tap definition popover, not a focus-managed dialog.
          // Radix returns focus to the trigger <span> (tabIndex=0) when the popover
          // closes; on mouse leave that left a lingering white focus ring (the global
          // outline-ring) on every chip, looking like a stray border. Suppress the
          // close-auto-focus so only the colored active-filter ring is ever shown.
          onCloseAutoFocus={(e) => e.preventDefault()}
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

// ─── Tag legend ────────────────────────────────────────────────────────────────

interface TagLegendProps {
  /** The (unique) tags shown on this card; only these are explained. */
  tags: FlawTag[];
  gameId: number;
  /** Visible label before the info icon. Defaults to "Tags"; the label doubles as
   *  the section heading on both the Games card and FlawCard. */
  label?: string;
}

/**
 * Single shared explanation line rendered below a card's tag chip row. Replaces
 * the per-chip hover/tap popovers on the Games card (which covered the eval chart);
 * one HelpCircle popover lists every tag on this card with its family-colored icon
 * and definition. Opt-in by click/hover on the icon — no overlay during normal use.
 */
export function TagLegend({ tags, gameId, label = 'Tags' }: TagLegendProps) {
  if (tags.length === 0) return null;
  return (
    <div className="flex items-center gap-1 text-sm text-muted-foreground">
      <span>{label}</span>
      <InfoPopover ariaLabel="Tag explanations" testId={`tag-legend-${gameId}`} side="bottom">
        <div className="flex flex-col gap-1.5">
          {tags.map((tag) => {
            const Icon = TAG_ICONS[tag];
            const { color } = TAG_FAMILY_COLORS[getTagFamily(tag)];
            return (
              <div key={tag} className="flex items-start gap-1.5">
                <Icon className="mt-0.5 h-3 w-3 shrink-0" style={{ color }} />
                <span>
                  <span className="font-bold" style={{ color }}>
                    {tag}
                  </span>
                  : {TAG_DEFINITIONS[tag]}
                </span>
              </div>
            );
          })}
        </div>
      </InfoPopover>
    </div>
  );
}
