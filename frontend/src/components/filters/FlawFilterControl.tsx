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
import { TAG_DEFINITIONS } from '@/lib/tagDefinitions';
import { isFlawFilterNonDefault } from '@/hooks/useFlawFilterStore';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FlawFilterControlProps {
  severity: ('blunder' | 'mistake')[];
  tags: FlawTag[];
  onSeverityChange: (next: ('blunder' | 'mistake')[]) => void;
  onTagChange: (next: FlawTag[]) => void;
  onClear: () => void;
}

// ─── Tag → glyph (lucide icons, rendered at h-3 w-3) ──────────────────────────

const TAG_ICONS: Record<string, LucideIcon> = {
  'low-clock': Clock,
  'hasty': Zap,
  'unrushed': Brain,
  'miss': Target,
  'lucky': Clover,
  'reversed': Swords,
  'squandered': TrendingDown,
};

// ─── Family sections ──────────────────────────────────────────────────────────

// Non-phase tags only (phase tags excluded per UI-SPEC §Tag-family sections + Pitfall 5).
interface FamilySection {
  label: string;
  ariaLabel: string;
  testid: string;
  tags: FlawTag[];
  color: string; // foreground + border when selected
  bg: string;    // background when selected
}

const FAMILY_SECTIONS: FamilySection[] = [
  {
    label: 'Timing',
    ariaLabel: 'Timing tag filters',
    testid: 'filter-flaw-family-tempo',
    tags: ['low-clock', 'hasty', 'unrushed'],
    color: FAM_TEMPO,
    bg: FAM_TEMPO_BG,
  },
  {
    label: 'Opportunity',
    ariaLabel: 'Opportunity tag filters',
    testid: 'filter-flaw-family-opportunity',
    tags: ['miss', 'lucky'],
    color: FAM_OPPORTUNITY,
    bg: FAM_OPPORTUNITY_BG,
  },
  {
    label: 'Impact',
    ariaLabel: 'Impact tag filters',
    testid: 'filter-flaw-family-impact',
    tags: ['reversed', 'squandered'],
    color: FAM_IMPACT,
    bg: FAM_IMPACT_BG,
  },
];

// ─── Tag filter button (with hover definition popover) ────────────────────────

interface TagFilterButtonProps {
  tag: FlawTag;
  selected: boolean;
  color: string;
  bg: string;
  onToggle: (tag: FlawTag) => void;
}

/**
 * A single tag toggle button that shows the tag's definition on hover.
 *
 * Renders the canonical lowercase-with-dash tag string (e.g. `lucky`) — the same
 * names the chips and Flaw-Stats panel use. The definition popover mirrors TagChip: a
 * Radix Popover opened on hover (100ms delay), body "<bold tag-name>: <definition>".
 *
 * The popover uses Popover.Anchor (not Trigger) so the button's onClick keeps toggling the
 * filter — only hover opens the popover, never the click. Hover is desktop-only by nature
 * (CLAUDE.md mobile-parity exception for hover tooltips); tap still toggles the filter.
 */
function TagFilterButton({ tag, selected, color, bg, onToggle }: TagFilterButtonProps) {
  const Icon = TAG_ICONS[tag];
  const [open, setOpen] = React.useState(false);
  const openTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const closeTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Open on hover after a short delay; close on a brief grace delay so moving the
  // pointer from the button into the portal-rendered popover body does not close it
  // first (the body's onMouseEnter cancels the pending close).
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
      <PopoverPrimitive.Anchor asChild>
        <button
          type="button"
          data-testid={`filter-flaw-tag-${tag}`}
          aria-pressed={selected}
          aria-label={`Filter flaws by tag: ${tag}`}
          className={cn(
            'inline-flex items-center gap-1 h-11 sm:h-7 rounded-full px-3 py-0.5 text-sm font-bold border transition-colors',
            !selected && 'border-border bg-inactive-bg text-muted-foreground',
          )}
          style={selected ? { color, borderColor: color, backgroundColor: bg } : undefined}
          onClick={() => onToggle(tag)}
          onMouseEnter={scheduleOpen}
          onMouseLeave={scheduleClose}
        >
          {Icon && <Icon className="h-3 w-3 shrink-0" />}
          {tag}
        </button>
      </PopoverPrimitive.Anchor>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="top"
          sideOffset={4}
          onOpenAutoFocus={(e) => e.preventDefault()}
          onMouseEnter={cancelClose}
          onMouseLeave={scheduleClose}
          data-testid={`filter-flaw-tag-popover-${tag}`}
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

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * FlawFilterControl — severity × tag-family multi-select filter control.
 *
 * Renders:
 * - "Show flaws with:" label
 * - Two severity toggle buttons (Blunders / Mistakes) with at-least-one guard
 * - Three family groups: Timing / Opportunity / Impact (phase tags excluded)
 * - "Clear flaw filter" link when non-default state
 *
 * Tag buttons show the canonical lowercase-with-dash name (matching chips + panel) and
 * surface the tag's definition on hover.
 *
 * UI-SPEC: uses toggle-active CSS variables for severity; family FAM_* colors for tags.
 * All interactive elements have data-testid + ARIA per CLAUDE.md browser automation rules.
 * text-sm floor throughout (CLAUDE.md typography rule; popover body uses the text-xs tooltip exception).
 */
export function FlawFilterControl({
  severity,
  tags,
  onSeverityChange,
  onTagChange,
  onClear,
}: FlawFilterControlProps) {
  // At-least-one-severity guard: ignore click that would empty the severity array
  const handleSeverityToggle = (sev: 'blunder' | 'mistake'): void => {
    const next = severity.includes(sev)
      ? severity.filter((s) => s !== sev)
      : [...severity, sev];
    if (next.length === 0) return; // prevent deselecting last active severity
    onSeverityChange(next);
  };

  const handleTagToggle = (tag: FlawTag): void => {
    const next = tags.includes(tag) ? tags.filter((t) => t !== tag) : [...tags, tag];
    onTagChange(next);
  };

  const nonDefault = isFlawFilterNonDefault({ severity, tags });

  return (
    <div data-testid="flaw-filter-control" className="flex flex-col gap-3">
      {/* ── Severity section ───────────────────────────────────────────── */}
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">Show flaws with:</p>
        <div className="flex gap-2 flex-wrap">
          <button
            type="button"
            data-testid="filter-flaw-severity-blunder"
            aria-pressed={severity.includes('blunder')}
            className={cn(
              'h-11 sm:h-7 rounded-md px-3 text-sm font-bold border transition-colors',
              severity.includes('blunder')
                ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground'
                : 'border-border bg-inactive-bg text-muted-foreground',
            )}
            onClick={() => handleSeverityToggle('blunder')}
          >
            Blunders
          </button>
          <button
            type="button"
            data-testid="filter-flaw-severity-mistake"
            aria-pressed={severity.includes('mistake')}
            className={cn(
              'h-11 sm:h-7 rounded-md px-3 text-sm font-bold border transition-colors',
              severity.includes('mistake')
                ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground'
                : 'border-border bg-inactive-bg text-muted-foreground',
            )}
            onClick={() => handleSeverityToggle('mistake')}
          >
            Mistakes
          </button>
        </div>
      </div>

      <div className="border-t border-border/40" />

      {/* ── Tag family groups (Timing / Opportunity / Impact) ──────────── */}
      {FAMILY_SECTIONS.map((section) => (
        <div key={section.testid} className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground font-bold uppercase tracking-wide">
            {section.label}
          </p>
          <div
            role="group"
            aria-label={section.ariaLabel}
            data-testid={section.testid}
            className="flex flex-wrap gap-2"
          >
            {section.tags.map((tag) => (
              <TagFilterButton
                key={tag}
                tag={tag}
                selected={tags.includes(tag)}
                color={section.color}
                bg={section.bg}
                onToggle={handleTagToggle}
              />
            ))}
          </div>
        </div>
      ))}

      {/* ── Clear affordance ───────────────────────────────────────────── */}
      {nonDefault && (
        <button
          type="button"
          data-testid="btn-clear-flaw-filter"
          aria-label="Clear all flaw filter selections"
          className="text-sm text-muted-foreground underline cursor-pointer text-left"
          onClick={onClear}
        >
          Clear flaw filter
        </button>
      )}
    </div>
  );
}
