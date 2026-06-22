import * as React from 'react';
import { cn } from '@/lib/utils';
import {
  ACTIVE_FILTER_RING_CLASS,
  TAC_MISSED,
  TAC_MISSED_BG,
  TAC_ALLOWED,
  TAC_ALLOWED_BG,
  TAC_ALLOWED_BORDER,
} from '@/lib/theme';
import { useFlawFilterStore } from '@/hooks/useFlawFilterStore';
import {
  TACTIC_FAMILY_FOR_MOTIF,
  TACTIC_FAMILY_COLORS,
  tacticMotifLabel,
  tacticMotifDefinition,
} from '@/lib/tacticComparisonMeta';

// Same highlight-bg helper as TagChip: bump the translucent alpha from 0.15 to 0.3
// on hover/focus so the chip clearly reads as highlighted.
const HIGHLIGHT_BG = (bg: string): string => bg.replace('/ 0.15)', '/ 0.3)');

// ─── Component ───────────────────────────────────────────────────────────────

interface TacticMotifChipProps {
  /**
   * The tactic motif string (one of the 24 TacticMotif literals). The caller
   * must already have applied the confidence gate — the chip renders unconditionally
   * when mounted (the backend nulls sub-threshold motifs at query time, D-09).
   */
  motif: string;
  /**
   * The flaw id used to make data-testid unique within a card.
   * Mirrors the gameId param in TagChip.
   */
  flawId: number;
  /**
   * Phase 129 TACUI-07 (D-10): optional orientation prefix for the chip label.
   * When set: visible label = "{orientation}: {motif}"; aria-label uses a space
   * (not colon) between orientation and motif; testid includes orientation.
   * When unset: unchanged behavior (backward-compatible — existing callers pass nothing).
   * PROHIBITED: no Popover import — D-12 narration is chip label + shared TagLegend.
   */
  orientation?: 'missed' | 'allowed';
  /**
   * Quick 260620-sep: when the chip lives inside an orientation-grouped row (the
   * Games card "Allowed"/"Missed" groups), the group already conveys orientation, so
   * the redundant "{orientation}: " prefix is dropped from the VISIBLE label. The
   * aria-label and testid still encode orientation (accessibility + browser automation).
   */
  hidePrefix?: boolean;
  /**
   * Quick 260620-sep: per-motif occurrence count within the game. Rendered count-first
   * (before the label) only when > 1, matching TagChip and the severity count badges.
   */
  count?: number;
  /**
   * Optional hover callback (Games card only). Fires true on pointer enter, false
   * on leave — lets the parent highlight this motif's eval-chart markers. Mirrors
   * TagChip.onHover; omitted call sites (FlawCard) get a plain decorative chip.
   */
  onHover?: (active: boolean) => void;
  /**
   * Optional click/tap activation (Games card only). Fires on click or keyboard
   * activation — the card uses it to cycle the eval chart through this motif's flaw
   * plies. Mirrors TagChip.onActivate; omitted call sites are unaffected.
   */
  onActivate?: () => void;
}

/**
 * Family-colored tactic motif chip (Phase 126, TACUI-01).
 *
 * Phase 126 UAT: the per-chip definition popover was removed — definitions are
 * surfaced once via the shared <TagLegend> below the chip row, exactly like the
 * flaw-tag chips (which render with `definition={false}`). On the Games card the
 * chip is a highlight/cycle control (onHover dims non-matching eval-chart markers,
 * onActivate cycles the chart through this motif's flaw plies), matching TagChip.
 * On FlawCard (no callbacks) it is a plain decorative span. Parent must gate
 * rendering on `user?.beta_enabled && flaw.allowed_tactic_motif != null`. Phase 128 D-07.
 *
 * Colors come from TACTIC_FAMILY_COLORS (theme.ts TAC_* constants) — no hardcoded oklch
 * in this file.
 */
export function TacticMotifChip({
  motif,
  flawId,
  orientation,
  hidePrefix,
  count,
  onHover,
  onActivate,
}: TacticMotifChipProps) {
  const family = TACTIC_FAMILY_FOR_MOTIF[motif];
  const colors = family != null ? TACTIC_FAMILY_COLORS[family] : null;
  const definition = tacticMotifDefinition(motif);
  // Mate-family motifs (back-rank-mate, smothered-mate, …) collapse to "checkmate"
  // on the cards — subtypes are not distinguished (Quick 260620-onv).
  const label = tacticMotifLabel(motif);

  // Phase 129 TACUI-07 (D-10): orientation-prefixed label/aria/testid.
  // Visible label uses colon ("missed: fork"); aria-label uses space ("Tactic: missed fork — def").
  // Quick 260620-sep: hidePrefix drops the visible "{orientation}: " when the chip sits in
  // an orientation-grouped row (the group label conveys orientation) — aria/testid keep it.
  const visibleLabel = orientation != null && !hidePrefix ? `${orientation}: ${label}` : label;
  const ariaLabel =
    orientation != null
      ? `Tactic: ${orientation} ${label} — ${definition}`
      : `Tactic: ${label} — ${definition}`;
  const testId =
    orientation != null
      ? `chip-tactic-${orientation}-${motif}-${flawId}`
      : `chip-tactic-${motif}-${flawId}`;

  // Brighten the chip while it is hovered or focused (tap-focus on mobile).
  const [highlighted, setHighlighted] = React.useState(false);

  // Active-filter ring (mirrors TagChip's D-05 ring): subscribe to the flaw filter
  // store so both LibraryGameCard (Games tab) and FlawCard (Flaws tab) light the ring
  // without prop drilling. Ring shows when this chip's tactic family is in the active
  // tacticFamilies filter and the orientation filter matches (either, or this chip's
  // orientation). orientation == null (no orientation context) ignores that axis.
  const [flawFilter] = useFlawFilterStore();
  const isActive =
    family != null &&
    (flawFilter.tacticFamilies ?? []).includes(family) &&
    (flawFilter.tacticOrientation === 'either' ||
      orientation == null ||
      flawFilter.tacticOrientation === orientation);

  // The chip earns hover/tap affordances only when something is wired to it (Games
  // card). FlawCard renders it with no callbacks — purely decorative, matching the
  // sibling TagChips there (definition=false, no callbacks).
  const interactive = Boolean(onHover || onActivate);

  // Unknown motif (no family mapping) — render nothing rather than a broken chip.
  if (colors == null) return null;

  // Orientation drives the chip color (Missed = blue, Allowed = light red) so the two
  // orientations read apart at a glance; fall back to the family color when no
  // orientation context is provided. The family icon is unchanged.
  const color =
    orientation === 'missed' ? TAC_MISSED : orientation === 'allowed' ? TAC_ALLOWED : colors.color;
  const bg =
    orientation === 'missed'
      ? TAC_MISSED_BG
      : orientation === 'allowed'
        ? TAC_ALLOWED_BG
        : colors.bg;
  // Allowed chips use a dedicated lower-alpha border (rather than the text color, the
  // default for other orientations) so the light-red fill stays legible.
  const border = orientation === 'allowed' ? TAC_ALLOWED_BORDER : color;

  return (
    <span
      className={cn(
        // text-xs is the documented chip exception (CLAUDE.md / UI-SPEC):
        // tactic motif chips match the flaw-tag chip sizing.
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-bold',
        interactive && 'cursor-pointer transition-all hover:-translate-y-px',
        isActive && ACTIVE_FILTER_RING_CLASS,
      )}
      style={{
        color,
        backgroundColor: highlighted ? HIGHLIGHT_BG(bg) : bg,
        borderColor: border,
        filter: highlighted ? 'brightness(1.2)' : undefined,
        // Ring color matches the family color for active-filter emphasis (TagChip parity).
        ...(isActive ? { '--tw-ring-color': color } as React.CSSProperties : {}),
      }}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-label={ariaLabel}
      data-testid={testId}
      onMouseEnter={
        interactive
          ? () => {
              onHover?.(true);
              setHighlighted(true);
            }
          : undefined
      }
      onMouseLeave={
        interactive
          ? () => {
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
      {/* Count-first when repeated (Quick 260620-sep), matching TagChip + severity badges. */}
      {count != null && count > 1 && <span>{count}</span>}
      {visibleLabel}
    </span>
  );
}
