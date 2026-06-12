import {
  Clock,
  Zap,
  Brain,
  Target,
  Clover,
  TrendingDown,
  ArrowDownUp,
  BookOpen,
  Swords,
  Trophy,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { InfoPopover } from '@/components/ui/info-popover';
import { BlunderIcon, MistakeIcon } from '@/components/icons/SeverityGlyphIcon';
import type { FlawIcon } from '@/lib/flawComparisonMeta';
import {
  FAM_TEMPO,
  FAM_TEMPO_BG,
  FAM_OPPORTUNITY,
  FAM_OPPORTUNITY_BG,
  FAM_IMPACT,
  FAM_IMPACT_BG,
  FAM_PHASE,
  FAM_PHASE_BG,
  SEV_BLUNDER,
  SEV_BLUNDER_BG,
  SEV_MISTAKE,
  SEV_MISTAKE_BG,
} from '@/lib/theme';
import type { FlawTag } from '@/types/library';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FlawFilterControlProps {
  severity: ('blunder' | 'mistake')[];
  tags: FlawTag[];
  onSeverityChange: (next: ('blunder' | 'mistake')[]) => void;
  onTagChange: (next: FlawTag[]) => void;
}

// ─── Tag → glyph (lucide icons, rendered at h-3 w-3) ──────────────────────────

const TAG_ICONS: Record<string, LucideIcon> = {
  'low-clock': Clock,
  'hasty': Zap,
  'unrushed': Brain,
  'miss': Target,
  'lucky': Clover,
  'reversed': ArrowDownUp,
  'squandered': TrendingDown,
  // Phase family — same glyphs as the Stats comparison grid (flawComparisonMeta).
  'opening': BookOpen,
  'middlegame': Swords,
  'endgame': Trophy,
};

// ─── Severity → pill style (mirrors the page severity badges) ─────────────────

interface SeverityButtonConfig {
  sev: 'blunder' | 'mistake';
  label: string;
  icon: FlawIcon;
  color: string;
  bg: string;
}

const SEVERITY_BUTTONS: SeverityButtonConfig[] = [
  { sev: 'blunder', label: 'Blunders', icon: BlunderIcon, color: SEV_BLUNDER, bg: SEV_BLUNDER_BG },
  { sev: 'mistake', label: 'Mistakes', icon: MistakeIcon, color: SEV_MISTAKE, bg: SEV_MISTAKE_BG },
];

// ─── Family sections ──────────────────────────────────────────────────────────

// Tag-family sections, including the phase family (Quick 260612-fow — phase is now
// a first-class filter family, filtered on game_flaws.phase by the backend).
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
  {
    label: 'Game Phase',
    ariaLabel: 'Game phase tag filters',
    testid: 'filter-flaw-family-phase',
    tags: ['opening', 'middlegame', 'endgame'],
    color: FAM_PHASE,
    bg: FAM_PHASE_BG,
  },
];

// ─── Tag filter button ────────────────────────────────────────────────────────

interface TagFilterButtonProps {
  tag: FlawTag;
  selected: boolean;
  color: string;
  bg: string;
  onToggle: (tag: FlawTag) => void;
}

/**
 * A single tag toggle button. Renders the canonical lowercase-with-dash tag string
 * (e.g. `lucky`) — the same names the chips and Flaw-Stats panel use. Definitions are
 * surfaced once via the <TagLegend> "Tags" popover on the Games cards, not as a
 * per-button hover tooltip here.
 */
function TagFilterButton({ tag, selected, color, bg, onToggle }: TagFilterButtonProps) {
  const Icon = TAG_ICONS[tag];
  return (
    <button
      type="button"
      data-testid={`filter-flaw-tag-${tag}`}
      aria-pressed={selected}
      aria-label={`Filter flaws by tag: ${tag}`}
      className={cn(
        'inline-flex items-center gap-1 h-11 sm:h-7 rounded-full px-3 py-0.5 text-sm border transition-colors',
        !selected
          && 'border-border bg-inactive-bg text-muted-foreground pointer-fine:hover:bg-inactive-bg-hover pointer-fine:hover:text-foreground',
      )}
      style={selected ? { color, borderColor: color, backgroundColor: bg } : undefined}
      onClick={() => onToggle(tag)}
    >
      {Icon && <Icon className="h-3 w-3 shrink-0" />}
      {tag}
    </button>
  );
}

// ─── Severity filter button ───────────────────────────────────────────────────

interface SeverityFilterButtonProps {
  config: SeverityButtonConfig;
  selected: boolean;
  onToggle: (sev: 'blunder' | 'mistake') => void;
}

/**
 * A severity toggle styled like the tag pills (and the page severity badges):
 * rounded-full, severity-colored when selected, with the severity glyph icon
 * (red "??" / orange "?"). Replaces the old neutral rectangular toggle so the
 * severity row reads as the same family of pills as the tags below it.
 */
function SeverityFilterButton({ config, selected, onToggle }: SeverityFilterButtonProps) {
  const { sev, label, icon: Icon, color, bg } = config;
  return (
    <button
      type="button"
      data-testid={`filter-flaw-severity-${sev}`}
      aria-pressed={selected}
      aria-label={`Filter flaws by severity: ${label}`}
      className={cn(
        'inline-flex items-center gap-1 h-11 sm:h-7 rounded-full px-3 py-0.5 text-sm border transition-colors',
        !selected
          && 'border-border bg-inactive-bg text-muted-foreground pointer-fine:hover:bg-inactive-bg-hover pointer-fine:hover:text-foreground',
      )}
      style={selected ? { color, borderColor: color, backgroundColor: bg } : undefined}
      onClick={() => onToggle(sev)}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </button>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * FlawFilterControl — severity × tag-family multi-select filter control.
 *
 * Renders:
 * - Two severity toggle buttons (Blunders / Mistakes) — empty = both shown
 * - Four family groups: Timing / Opportunity / Impact / Game Phase
 *
 * Tag buttons show the canonical lowercase-with-dash name (matching chips + panel).
 * Definitions live in the <TagLegend> "Tags" popover on the Games cards, not as
 * per-button hover tooltips here.
 *
 * UI-SPEC: uses toggle-active CSS variables for severity; family FAM_* colors for tags.
 * All interactive elements have data-testid + ARIA per CLAUDE.md browser automation rules.
 * text-sm floor throughout (CLAUDE.md typography rule).
 *
 * The Reset+Apply footer is owned by the parent panel (FilterActions) — this component
 * does not render it.
 */
export function FlawFilterControl({
  severity,
  tags,
  onSeverityChange,
  onTagChange,
}: FlawFilterControlProps) {
  // Severity toggles narrow like the tag families: empty = both shown, one = that
  // tier only, both = both shown (same as empty). Deselecting the last severity is
  // allowed (yields []) — there is no at-least-one guard.
  const handleSeverityToggle = (sev: 'blunder' | 'mistake'): void => {
    const next = severity.includes(sev)
      ? severity.filter((s) => s !== sev)
      : [...severity, sev];
    onSeverityChange(next);
  };

  const handleTagToggle = (tag: FlawTag): void => {
    const next = tags.includes(tag) ? tags.filter((t) => t !== tag) : [...tags, tag];
    onTagChange(next);
  };

  return (
    <div data-testid="flaw-filter-control" className="flex flex-col gap-3">
      {/* ── Severity section ───────────────────────────────────────────── */}
      <div className="flex flex-col gap-2">
        <div className="flex gap-2 flex-wrap">
          {SEVERITY_BUTTONS.map((config) => (
            <SeverityFilterButton
              key={config.sev}
              config={config}
              selected={severity.includes(config.sev)}
              onToggle={handleSeverityToggle}
            />
          ))}
        </div>
      </div>

      <div className="border-t border-border/40" />

      {/* ── Tag family groups (Timing / Opportunity / Impact) ──────────── */}
      {FAMILY_SECTIONS.map((section) => (
        <div key={section.testid} className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">
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

      {/* ── Filter Logic explainer ─────────────────────────────────────── */}
      <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <span>Filter Logic</span>
        <InfoPopover
          ariaLabel="How tag filters combine"
          testId="filter-flaw-logic-info"
          side="top"
        >
          <p>
            Tags in the same group are combined with <strong>OR</strong>; different
            groups are combined with <strong>AND</strong>.
          </p>
          <p className="mt-1.5">
            Example: picking <em>Hasty</em> and <em>Unrushed</em> (Timing) plus{' '}
            <em>Miss</em> (Opportunity) keeps flaws that are{' '}
            <em>(hasty or unrushed)</em> and a <em>miss</em>.
          </p>
          <p className="mt-1.5">
            Applied to games, only games with at least one matching blunder or
            mistake are included.
          </p>
        </InfoPopover>
      </div>
    </div>
  );
}
