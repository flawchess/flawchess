import { useState } from 'react';
import { useRevealOnOpen } from '@/hooks/useRevealOnOpen';
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
  ChevronDown,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { InfoPopover } from '@/components/ui/info-popover';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { BlunderIcon, MistakeIcon } from '@/components/icons/SeverityGlyphIcon';
import { TagLegend } from '@/components/library/TagChip';
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
import type { FlawTag, TacticOrientation } from '@/types/library';
import type { TacticFamily, TacticGroupKey } from '@/lib/tacticComparisonMeta';
import {
  TACTIC_COMPARISON_FAMILIES,
  TACTIC_FAMILY_COLORS,
  TACTIC_FAMILY_ICON,
  TACTIC_GROUPS,
} from '@/lib/tacticComparisonMeta';
import { TacticDepthFilter } from '@/components/filters/TacticDepthFilter';
import { DEFAULT_TACTIC_DEPTH_VALUE } from '@/lib/tacticDepth';
import type { TacticDepthValue } from '@/lib/tacticDepth';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FlawFilterControlProps {
  severity: ('blunder' | 'mistake')[];
  tags: FlawTag[];
  onSeverityChange: (next: ('blunder' | 'mistake')[]) => void;
  onTagChange: (next: FlawTag[]) => void;
  /**
   * Tactic-motif family filter (Phase 126). Only relevant when `showTacticFilter`
   * is true (the Flaws tab). The flaw-tags panel is shared with the Games tab, where
   * tactic filtering is a no-op, so the section is gated off by default.
   */
  tacticFamilies?: TacticFamily[];
  onTacticFamiliesChange?: (next: TacticFamily[]) => void;
  /** Render the tactic-motif family section. Default false (Flaws tab passes true). */
  showTacticFilter?: boolean;
  /**
   * Phase 129 TACUI-06 (D-06/D-07): orientation filter.
   * Default 'either'. Rendered above TacticDepthFilter when showTacticFilter=true.
   */
  orientation?: TacticOrientation;
  onOrientationChange?: (next: TacticOrientation) => void;
  /**
   * Phase 129 TACUI-06 (D-01/D-02/D-03): tactic depth value.
   * Default Intermediate. Rendered above Tactic Motif when showTacticFilter=true.
   */
  tacticDepth?: TacticDepthValue;
  onTacticDepthChange?: (next: TacticDepthValue) => void;
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

// Flat set of all tags in the Context (FAMILY_SECTIONS) block — used for count badge.
// Computed once at module level to avoid per-render allocations.
const CONTEXT_TAGS = new Set<FlawTag>(FAMILY_SECTIONS.flatMap((s) => s.tags));

// Tier-3 "Advanced" tactic families (Quick 260623-6pd) — collapsed-by-default group.
// Derived once from the registry: family keys (for the toggle count badge) and chip
// labels (for the Tags-icon legend shown beside the toggle).
const ADVANCED_TACTIC_FAMILIES = TACTIC_COMPARISON_FAMILIES.filter((f) => f.group === 'advanced');
const ADVANCED_TACTIC_FAMILY_KEYS = new Set<TacticFamily>(
  ADVANCED_TACTIC_FAMILIES.map((f) => f.family),
);
const ADVANCED_TACTIC_MOTIF_LABELS = ADVANCED_TACTIC_FAMILIES.map((f) => f.chipLabel);

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
      {/* Icon hidden on mobile to declutter the chips; shown from `sm` up. */}
      {Icon && <Icon className="h-3 w-3 shrink-0 hidden sm:block" />}
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

// ─── Tactic family group ────────────────────────────────────────────────────────

interface TacticFamilyGroupProps {
  groupKey: TacticGroupKey;
  /** Section label (also used for the chips' aria-label). */
  label: string;
  selectedFamilies: TacticFamily[];
  onToggle: (family: TacticFamily) => void;
  /**
   * Render the section label + Tags-icon legend above the chips. Default true for the
   * always-on groups; the collapsible Advanced group passes false because its toggle row
   * already carries the label + legend (Quick 260623-6pd).
   */
  showHeader?: boolean;
}

/**
 * One mechanism group of tactic-family filter pills: an optional section label + scoped
 * Tags-icon legend, then a wrapped row of family toggle buttons. Shared by the always-on
 * groups (Piece Attacks, Checkmate/Checks/Discoveries) and the collapsible Advanced group
 * so the chip markup lives in one place.
 */
function TacticFamilyGroup({
  groupKey,
  label,
  selectedFamilies,
  onToggle,
  showHeader = true,
}: TacticFamilyGroupProps) {
  const groupFamilies = TACTIC_COMPARISON_FAMILIES.filter((f) => f.group === groupKey);
  // Legend is family-level (one row per chip): key on chipLabel so the mate family shows
  // a single "checkmate" row, not its nine named-mate motifs.
  const groupMotifs = groupFamilies.map((f) => f.chipLabel);
  const chips = (
    <div
      role="group"
      aria-label={`${label} filters`}
      data-testid={`filter-flaw-tactic-group-${groupKey}-chips`}
      className="flex flex-wrap gap-2"
    >
      {groupFamilies.map(({ family, name, chipLabel }) => {
        const { color, bg } = TACTIC_FAMILY_COLORS[family];
        const Icon = TACTIC_FAMILY_ICON[family];
        const selected = selectedFamilies.includes(family);
        return (
          <button
            key={family}
            type="button"
            data-testid={`filter-flaw-tactic-${family}`}
            aria-pressed={selected}
            aria-label={`Filter flaws by tactic motif: ${name}`}
            className={cn(
              'inline-flex items-center gap-1 h-11 sm:h-7 rounded-full px-3 py-0.5 text-sm border transition-colors',
              !selected
                && 'border-border bg-inactive-bg text-muted-foreground pointer-fine:hover:bg-inactive-bg-hover pointer-fine:hover:text-foreground',
            )}
            style={selected ? { color, borderColor: color, backgroundColor: bg } : undefined}
            onClick={() => onToggle(family)}
          >
            {/* Icon hidden on mobile to declutter the chips; shown from `sm` up. */}
            <Icon className="h-3.5 w-3.5 shrink-0 hidden sm:block" aria-hidden="true" />
            {chipLabel}
          </button>
        );
      })}
    </div>
  );

  if (!showHeader) return chips;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1.5">
        <p className="text-sm text-muted-foreground" data-testid={`filter-flaw-tactic-group-${groupKey}`}>
          {label}
        </p>
        <TagLegend
          variant="icon"
          tags={[]}
          tacticMotifs={groupMotifs}
          testId={`filter-flaw-tactic-group-${groupKey}-legend`}
        />
      </div>
      {chips}
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * FlawFilterControl — severity × tag-family multi-select filter control.
 *
 * Renders (top to bottom):
 * - Severity (Blunders / Mistakes) — always on top of the panel (Quick 260624)
 * - Orientation toggle (showTacticFilter only)
 * - Tactic Depth filter (showTacticFilter only)
 * - Tactic Type family (showTacticFilter only)
 * - Collapsed "Context" section (always) — Timing / Opportunity / Impact / Game Phase,
 *   behind a hand-rolled toggle (Quick 260620-mjh). Shows count badge when tags selected.
 * - Filter Logic explainer
 *
 * Tag buttons show the canonical lowercase-with-dash name (matching chips + panel).
 * Each family label carries a brown <TagLegend> Tags-icon popover that explains every
 * tag (or tactic motif) in that family — same pattern as the Games/Flaws cards — so
 * definitions are not repeated as per-button hover tooltips here.
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
  tacticFamilies = [],
  onSeverityChange,
  onTagChange,
  onTacticFamiliesChange,
  showTacticFilter = false,
  orientation = 'either',
  onOrientationChange,
  tacticDepth = DEFAULT_TACTIC_DEPTH_VALUE,
  onTacticDepthChange,
}: FlawFilterControlProps) {
  const [contextOpen, setContextOpen] = useState(false);
  // Advanced tactic group (tier-3 motifs) — collapsed by default (Quick 260623-6pd).
  const [advancedOpen, setAdvancedOpen] = useState(false);
  // Smoothly reveal a section's content (and the headers below it) when it expands
  // inside the scrolling mobile filter drawer.
  const { ref: advancedRef, reveal: revealAdvanced } = useRevealOnOpen<HTMLDivElement>();
  const { ref: contextRef, reveal: revealContext } = useRevealOnOpen<HTMLDivElement>();

  // Tactic-specific sections (depth / orientation / motif families / advanced) are
  // gated on the tab opt-in: the Flaws tab passes showTacticFilter, the Games tab does not.
  const showTactics = showTacticFilter;

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

  // Tactic-motif families behave exactly like the tag families: off by default,
  // applied only when ≥1 is selected (Phase 126).
  const handleTacticFamilyToggle = (fam: TacticFamily): void => {
    const next = tacticFamilies.includes(fam)
      ? tacticFamilies.filter((f) => f !== fam)
      : [...tacticFamilies, fam];
    onTacticFamiliesChange?.(next);
  };

  // Count of currently selected tags that belong to the Context (FAMILY_SECTIONS) block.
  // Drives the count badge on the collapsed Context toggle header.
  const selectedContextCount = tags.filter((t) => CONTEXT_TAGS.has(t)).length;

  // Count of selected families in the Advanced (tier-3) group — drives the toggle badge.
  const selectedAdvancedCount = tacticFamilies.filter((f) =>
    ADVANCED_TACTIC_FAMILY_KEYS.has(f),
  ).length;

  return (
    <div data-testid="flaw-filter-control" className="flex flex-col gap-3">
      {/* ── Severity (Blunders / Mistakes) — empty = both shown ──────────────
          Pinned to the top of the panel, above Tactic Depth, on both tabs
          (Quick 260624). Was previously inside the Context collapsible. ──── */}
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">Severity</p>
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

      {/* ── Tactic difficulty filter (Phase 129 TACUI-06, D-01/D-02/D-03) ──
          Placed first so users size the difficulty band before narrowing by
          orientation/type (Quick 260620-onv follow-up). ──── */}
      {showTactics && (
        <TacticDepthFilter
          value={tacticDepth}
          onChange={onTacticDepthChange ?? (() => undefined)}
        />
      )}

      {/* ── Orientation toggle (Phase 129 TACUI-06, D-06/D-07) ────────────── */}
      {showTactics && (
        <div>
          <p className="mb-1 text-sm text-muted-foreground">Tactic Missed vs Allowed</p>
          <ToggleGroup
            type="single"
            value={orientation}
            onValueChange={(v) => {
              // D-06: deselect guard — empty string means user tapped the active item;
              // preserve current value (same guard as "Played as").
              if (!v) return;
              onOrientationChange?.(v as TacticOrientation);
            }}
            variant="outline"
            size="sm"
            data-testid="filter-tactic-orientation"
            className="w-full"
          >
            <ToggleGroupItem
              value="either"
              data-testid="filter-tactic-orientation-either"
              className="min-h-11 sm:min-h-0 flex-1 text-sm"
            >
              Either
            </ToggleGroupItem>
            <ToggleGroupItem
              value="missed"
              data-testid="filter-tactic-orientation-missed"
              className="min-h-11 sm:min-h-0 flex-1 text-sm"
            >
              Missed
            </ToggleGroupItem>
            <ToggleGroupItem
              value="allowed"
              data-testid="filter-tactic-orientation-allowed"
              className="min-h-11 sm:min-h-0 flex-1 text-sm"
            >
              Allowed
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
      )}

      {/* ── Tactic motif families (Phase 126; grouped into mechanism sections in
          Quick 260620-onv) — opt-in, off by default. Gated to the Flaws tab
          (showTacticFilter); shared Games-tab panel hides it. Always-on groups
          (Piece Attacks, Checkmate/Checks/Discoveries) render here; the tier-3
          Advanced group renders collapsed below (Quick 260623-6pd). Each group has
          its own scoped Tags-icon legend; chips read kebab-case. ──── */}
      {showTactics
        && TACTIC_GROUPS.filter((g) => g.key !== 'advanced').map(({ key, label }) => (
          <TacticFamilyGroup
            key={key}
            groupKey={key}
            label={label}
            selectedFamilies={tacticFamilies}
            onToggle={handleTacticFamilyToggle}
          />
        ))}

      {/* ── Advanced tactic families (tier-3, Quick 260623-6pd) — collapsed by default ──
          x-ray + the shipped Phase-132 motifs (deflection, intermezzo, interference,
          clearance, capturing-defender) behind an "Advanced" toggle below the always-on
          groups. The Tags-icon legend sits on the toggle row so the motif explanations
          are reachable without expanding. Gated to the Flaws tab (showTacticFilter). ──── */}
      {showTactics && (
        <div ref={advancedRef}>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => {
                const next = !advancedOpen;
                setAdvancedOpen(next);
                revealAdvanced(next);
              }}
              aria-expanded={advancedOpen}
              aria-controls="flaw-filter-advanced-content"
              data-testid="filter-flaw-advanced-toggle"
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronDown
                className={cn('h-3.5 w-3.5 transition-transform', advancedOpen && 'rotate-180')}
              />
              {selectedAdvancedCount > 0 ? `Advanced · ${selectedAdvancedCount}` : 'Advanced'}
            </button>
            <TagLegend
              variant="icon"
              tags={[]}
              tacticMotifs={ADVANCED_TACTIC_MOTIF_LABELS}
              testId="filter-flaw-tactic-group-advanced-legend"
            />
          </div>
          {advancedOpen && (
            <div id="flaw-filter-advanced-content" className="mt-2">
              <TacticFamilyGroup
                groupKey="advanced"
                label="Advanced"
                selectedFamilies={tacticFamilies}
                onToggle={handleTacticFamilyToggle}
                showHeader={false}
              />
            </div>
          )}
        </div>
      )}

      {/* ── Context tag families (Quick 260620-mjh / 260623) ──
          Timing / Opportunity / Impact / Game Phase. Sits behind a "Context" toggle
          below the tactic sections. Renders on both the Games tab
          (showTacticFilter=false) and Flaws tab. ──── */}
      <div ref={contextRef} className="pt-3 border-t border-border/40">
        <button
          type="button"
          onClick={() => {
            const next = !contextOpen;
            setContextOpen(next);
            revealContext(next);
          }}
          aria-expanded={contextOpen}
          aria-controls="flaw-filter-context-content"
          data-testid="filter-flaw-context-toggle"
          className="flex w-full items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronDown
            className={cn('h-3.5 w-3.5 transition-transform', contextOpen && 'rotate-180')}
          />
          {selectedContextCount > 0 ? `Context · ${selectedContextCount}` : 'Context'}
        </button>
        {contextOpen && (
          <div
            id="flaw-filter-context-content"
            className="flex flex-col gap-3 mt-2"
          >
            {FAMILY_SECTIONS.map((section) => (
              <div key={section.testid} className="flex flex-col gap-2">
                <div className="flex items-center gap-1.5">
                  <p className="text-sm text-muted-foreground">
                    {section.label}
                  </p>
                  <TagLegend
                    variant="icon"
                    tags={section.tags}
                    testId={`${section.testid}-legend`}
                  />
                </div>
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
            {/* ── Filter Logic explainer ─────────────────────────────────── */}
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <span>Filter Logic</span>
              <InfoPopover
                ariaLabel="How tag filters combine"
                testId="filter-flaw-logic-info"
                side="top"
              >
                <p>
                  Tags in the same group are combined with <strong>OR</strong>;
                  different groups are combined with <strong>AND</strong>.
                </p>
                <p className="mt-1.5">
                  Example: picking <em>Hasty</em> and <em>Unrushed</em> (Timing)
                  plus <em>Miss</em> (Opportunity) keeps flaws that are{' '}
                  <em>(hasty or unrushed)</em> and a <em>miss</em>.
                </p>
                <p className="mt-1.5">
                  Applied to games, only games with at least one matching blunder
                  or mistake are included.
                </p>
              </InfoPopover>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
