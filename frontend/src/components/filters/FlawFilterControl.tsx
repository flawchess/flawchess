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
import { TAG_LABELS } from '@/lib/tagDefinitions';
import { isFlawFilterNonDefault } from '@/hooks/useFlawFilterStore';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FlawFilterControlProps {
  severity: ('blunder' | 'mistake')[];
  tags: FlawTag[];
  onSeverityChange: (next: ('blunder' | 'mistake')[]) => void;
  onTagChange: (next: FlawTag[]) => void;
  onClear: () => void;
}

// ─── Family tag definitions ───────────────────────────────────────────────────

// Non-phase tags only (phase tags excluded per UI-SPEC §Tag-family sections + Pitfall 5)
const TIMING_TAGS: FlawTag[] = ['low-clock', 'impatient', 'considered'];
const OPPORTUNITY_TAGS: FlawTag[] = ['miss', 'lucky-escape'];
const IMPACT_TAGS: FlawTag[] = ['result-changing', 'while-ahead'];

const TAG_ICONS: Record<string, LucideIcon> = {
  'low-clock': Clock,
  'impatient': Zap,
  'considered': Brain,
  'miss': Target,
  'lucky-escape': Clover,
  'result-changing': Swords,
  'while-ahead': TrendingDown,
};

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
 * UI-SPEC: uses toggle-active CSS variables for severity; family FAM_* colors for tags.
 * All interactive elements have data-testid + ARIA per CLAUDE.md browser automation rules.
 * text-sm floor throughout (CLAUDE.md typography rule).
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

      {/* ── Timing family ──────────────────────────────────────────────── */}
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground font-bold uppercase tracking-wide">Timing</p>
        <div
          role="group"
          aria-label="Timing tag filters"
          data-testid="filter-flaw-family-tempo"
          className="flex flex-wrap gap-2"
        >
          {TIMING_TAGS.map((tag) => {
            const Icon = TAG_ICONS[tag];
            const selected = tags.includes(tag);
            return (
              <button
                key={tag}
                type="button"
                data-testid={`filter-flaw-tag-${tag}`}
                aria-pressed={selected}
                aria-label={`Filter flaws by tag: ${tag}`}
                className={cn(
                  'inline-flex items-center gap-1 h-11 sm:h-7 rounded-full px-3 py-0.5 text-sm font-bold border transition-colors',
                  !selected && 'border-border bg-inactive-bg text-muted-foreground',
                )}
                style={selected ? {
                  color: FAM_TEMPO,
                  borderColor: FAM_TEMPO,
                  backgroundColor: FAM_TEMPO_BG,
                } : undefined}
                onClick={() => handleTagToggle(tag)}
              >
                {Icon && <Icon className="h-3 w-3 shrink-0" />}
                {TAG_LABELS[tag]}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Opportunity family ─────────────────────────────────────────── */}
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground font-bold uppercase tracking-wide">Opportunity</p>
        <div
          role="group"
          aria-label="Opportunity tag filters"
          data-testid="filter-flaw-family-opportunity"
          className="flex flex-wrap gap-2"
        >
          {OPPORTUNITY_TAGS.map((tag) => {
            const Icon = TAG_ICONS[tag];
            const selected = tags.includes(tag);
            return (
              <button
                key={tag}
                type="button"
                data-testid={`filter-flaw-tag-${tag}`}
                aria-pressed={selected}
                aria-label={`Filter flaws by tag: ${tag}`}
                className={cn(
                  'inline-flex items-center gap-1 h-11 sm:h-7 rounded-full px-3 py-0.5 text-sm font-bold border transition-colors',
                  !selected && 'border-border bg-inactive-bg text-muted-foreground',
                )}
                style={selected ? {
                  color: FAM_OPPORTUNITY,
                  borderColor: FAM_OPPORTUNITY,
                  backgroundColor: FAM_OPPORTUNITY_BG,
                } : undefined}
                onClick={() => handleTagToggle(tag)}
              >
                {Icon && <Icon className="h-3 w-3 shrink-0" />}
                {TAG_LABELS[tag]}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Impact family ──────────────────────────────────────────────── */}
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground font-bold uppercase tracking-wide">Impact</p>
        <div
          role="group"
          aria-label="Impact tag filters"
          data-testid="filter-flaw-family-impact"
          className="flex flex-wrap gap-2"
        >
          {IMPACT_TAGS.map((tag) => {
            const Icon = TAG_ICONS[tag];
            const selected = tags.includes(tag);
            return (
              <button
                key={tag}
                type="button"
                data-testid={`filter-flaw-tag-${tag}`}
                aria-pressed={selected}
                aria-label={`Filter flaws by tag: ${tag}`}
                className={cn(
                  'inline-flex items-center gap-1 h-11 sm:h-7 rounded-full px-3 py-0.5 text-sm font-bold border transition-colors',
                  !selected && 'border-border bg-inactive-bg text-muted-foreground',
                )}
                style={selected ? {
                  color: FAM_IMPACT,
                  borderColor: FAM_IMPACT,
                  backgroundColor: FAM_IMPACT_BG,
                } : undefined}
                onClick={() => handleTagToggle(tag)}
              >
                {Icon && <Icon className="h-3 w-3 shrink-0" />}
                {TAG_LABELS[tag]}
              </button>
            );
          })}
        </div>
      </div>

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
