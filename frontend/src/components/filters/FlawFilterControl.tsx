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
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { BlunderIcon, MistakeIcon } from '@/components/icons/SeverityGlyphIcon';
import { GemIcon } from '@/components/icons/GemIcon';
import { GreatMoveIcon } from '@/components/icons/GreatMoveIcon';
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
  MAIA_ACCENT,
  MAIA_ACCENT_BG,
  GREAT_ACCENT,
  GREAT_ACCENT_BG,
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
  /**
   * "Has gem" / "has great" toggles (FILT-01, D-05, Phase 175) — independent
   * booleans narrowing the Library games list. The "Best Moves" section renders
   * only when the parent supplies onHasGemToggle/onHasGreatToggle — which only
   * GamesTab does; FlawsTab passes neither. (showTacticFilter can NOT distinguish
   * the two tabs: both pass it true, so it is the wrong gate for this section.)
   */
  hasGem?: boolean;
  hasGreat?: boolean;
  onHasGemToggle?: () => void;
  onHasGreatToggle?: () => void;
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

// ─── Best-move filter button (gem / great, FILT-01, Phase 175) ────────────────

interface BestMoveFilterButtonProps {
  testId: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  ariaLabel: string;
  color: string;
  bg: string;
  selected: boolean;
  onToggle: () => void;
}

/**
 * A "has gem" / "has great" toggle pill, styled identically to
 * SeverityFilterButton (same pill shape, colored border/background when
 * selected) but backed by a single independent boolean rather than an
 * array-membership check — two of these compose as an OR at the backend.
 */
function BestMoveFilterButton({
  testId,
  icon: Icon,
  label,
  ariaLabel,
  color,
  bg,
  selected,
  onToggle,
}: BestMoveFilterButtonProps) {
  return (
    <button
      type="button"
      data-testid={testId}
      aria-pressed={selected}
      aria-label={ariaLabel}
      className={cn(
        'inline-flex items-center gap-1 h-11 sm:h-7 rounded-full px-3 py-0.5 text-sm border transition-colors',
        !selected
          && 'border-border bg-inactive-bg text-muted-foreground pointer-fine:hover:bg-inactive-bg-hover pointer-fine:hover:text-foreground',
      )}
      style={selected ? { color, borderColor: color, backgroundColor: bg } : undefined}
      onClick={onToggle}
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
}

/**
 * One mechanism group of tactic-family filter pills: a section label + scoped Tags-icon
 * legend, then a wrapped row of family toggle buttons. Shared by every tactic group
 * (Piece Attacks, Checkmate/Checks/Discoveries, Advanced) so the chip markup lives in
 * one place.
 */
function TacticFamilyGroup({
  groupKey,
  label,
  selectedFamilies,
  onToggle,
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

// ─── Filter-logic info popover ──────────────────────────────────────────────────

/**
 * TagFilterLogicInfo — the "how tag filters combine" help popover. Rendered next to
 * the "Tags" panel heading (SidebarLayout headerExtra / MobileFilterDrawer
 * titleAccessory) rather than inside the control, so the explanation lives with the
 * panel title. `side` defaults to "bottom" since it sits at the top of the panel.
 */
export function TagFilterLogicInfo({ side = 'bottom' }: { side?: 'top' | 'bottom' | 'left' | 'right' }) {
  return (
    <InfoPopover
      ariaLabel="How tag filters combine"
      testId="filter-flaw-logic-info"
      side={side}
    >
      <p>
        Narrow your games to the ones with the flaws, tactics, and moments
        you care about, then combine tags to zero in on specific patterns.
      </p>
      <p className="mt-1.5">
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
  );
}

/**
 * BestMovesInfo — help popover for the "Best Moves" (Gem / Great) filter section.
 * Explains how the two tiers are derived (objectively best move + how rare it is
 * among rating peers) and that rarity is measured relative to the player's
 * lichess-blitz-equivalent rating (the scale the Maia model is calibrated on).
 */
function BestMovesInfo() {
  return (
    <InfoPopover
      ariaLabel="How best moves are calculated"
      testId="filter-best-moves-info"
      side="bottom"
    >
      <p>
        <strong>Gem</strong> and <strong>Great</strong> highlight moves you played that
        were the engine&apos;s top choice <em>and</em> clearly better than any
        alternative.
      </p>
      <p className="mt-1.5">
        The two tiers differ by how hard the move was to find. We estimate how often
        players at your level would find it, measured against your rating converted to
        a <strong>lichess blitz</strong> equivalent (the scale our model is calibrated
        on), so a move is judged relative to your own strength.
      </p>
      <p className="mt-1.5">
        <strong>Gem</strong>: fewer than ~1 in 5 rating peers would find it.
        <br />
        <strong>Great</strong>: found by roughly 1 in 5 to 1 in 2 peers.
      </p>
    </InfoPopover>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * FlawFilterControl — severity × tag-family multi-select filter control.
 *
 * Renders (top to bottom):
 * - Severity (Blunders / Mistakes) — always on top of the panel (Quick 260624)
 * - Best Moves (Gem / Great, FILT-01 Phase 175) — Games tab only (gated on the
 *   presence of the onHasGem/GreatToggle handlers, which only GamesTab passes)
 * - Orientation toggle (showTacticFilter only)
 * - Tactic Depth filter (showTacticFilter only)
 * - Tactic Type families incl. "Advanced" (showTacticFilter only) — each a titled section
 * - "Context" section (always) — Timing / Opportunity / Impact / Game Phase
 *
 * The "how tag filters combine" explainer is rendered next to the panel's "Tags"
 * heading (TagFilterLogicInfo), not inside this control.
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
  hasGem = false,
  hasGreat = false,
  onHasGemToggle,
  onHasGreatToggle,
}: FlawFilterControlProps) {
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

  return (
    <div data-testid="flaw-filter-control" className="flex flex-col gap-3">
      {/* ── Severity (Blunders / Mistakes) — empty = both shown ──────────────
          Pinned to the top of the panel, above Tactic Depth, on both tabs
          (Quick 260624). Was previously inside the Context collapsible. ──── */}
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">Flaws</p>
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

      {/* ── Best Moves (Gem / Great toggles, FILT-01 D-05, Phase 175) ──────────
          Two independent booleans (not a 3-state cycle) narrowing the Library
          games list to games with a stored user-move gem/great; both on is a
          union at the backend.
          Bug fix (post-verify): this was gated on `!showTactics`, but BOTH the
          Games AND Flaws tabs pass showTacticFilter=true, so the section never
          rendered on the real Games tab. The true discriminator is the parent
          opting in via the gem/great toggle handlers — only GamesTab passes
          them; FlawsTab passes none — so gate on their presence instead. ──── */}
      {(onHasGemToggle || onHasGreatToggle) && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-1">
            <p className="text-sm text-muted-foreground">Best Moves</p>
            <BestMovesInfo />
          </div>
          <div className="flex gap-2 flex-wrap">
            <BestMoveFilterButton
              testId="filter-has-gem"
              icon={GemIcon}
              label="Gem"
              ariaLabel="Filter by gem moves"
              color={MAIA_ACCENT}
              bg={MAIA_ACCENT_BG}
              selected={hasGem}
              onToggle={() => onHasGemToggle?.()}
            />
            <BestMoveFilterButton
              testId="filter-has-great"
              icon={GreatMoveIcon}
              label="Great"
              ariaLabel="Filter by great moves"
              color={GREAT_ACCENT}
              bg={GREAT_ACCENT_BG}
              selected={hasGreat}
              onToggle={() => onHasGreatToggle?.()}
            />
          </div>
        </div>
      )}

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
      {/* Always-on motif groups (Piece Attacks, Checkmate/Checks/Discoveries) plus the
          tier-3 Advanced group, each rendered as a normal titled section with its own
          scoped Tags-icon legend; chips read kebab-case. Gated to the Flaws tab. */}
      {showTactics
        && TACTIC_GROUPS.map(({ key, label }) => (
          <TacticFamilyGroup
            key={key}
            groupKey={key}
            label={label}
            selectedFamilies={tacticFamilies}
            onToggle={handleTacticFamilyToggle}
          />
        ))}

      {/* ── Context tag families (Quick 260620-mjh / 260623) ──
          Timing / Opportunity / Impact / Game Phase, rendered as a normal "Context"
          section below the tactic sections. Renders on both the Games tab
          (showTacticFilter=false) and Flaws tab. ──── */}
      <div className="pt-3 border-t border-border/40">
        <p
          className="text-sm text-muted-foreground"
          data-testid="filter-flaw-context-heading"
        >
          Context
        </p>
        <div className="flex flex-col gap-3 mt-2">
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
        </div>
      </div>
    </div>
  );
}
