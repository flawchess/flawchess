import * as React from 'react';
import { cn } from '@/lib/utils';
import {
  TACTIC_FAMILY_FOR_MOTIF,
  TACTIC_FAMILY_COLORS,
  TACTIC_FAMILY_ICON,
} from '@/lib/tacticComparisonMeta';
import { TACTIC_MOTIF_DEFINITIONS } from '@/lib/tacticMotifDefinitions';

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
 * in this file. Icon from TACTIC_FAMILY_ICON.
 */
export function TacticMotifChip({ motif, flawId, orientation, onHover, onActivate }: TacticMotifChipProps) {
  const family = TACTIC_FAMILY_FOR_MOTIF[motif];
  const colors = family != null ? TACTIC_FAMILY_COLORS[family] : null;
  const Icon = family != null ? TACTIC_FAMILY_ICON[family] : null;
  const definition = TACTIC_MOTIF_DEFINITIONS[motif] ?? motif;

  // Phase 129 TACUI-07 (D-10): orientation-prefixed label/aria/testid.
  // Visible label uses colon ("missed: fork"); aria-label uses space ("Tactic: missed fork — def").
  const visibleLabel = orientation != null ? `${orientation}: ${motif}` : motif;
  const ariaLabel =
    orientation != null
      ? `Tactic: ${orientation} ${motif} — ${definition}`
      : `Tactic: ${motif} — ${definition}`;
  const testId =
    orientation != null
      ? `chip-tactic-${orientation}-${motif}-${flawId}`
      : `chip-tactic-${motif}-${flawId}`;

  // Brighten the chip while it is hovered or focused (tap-focus on mobile).
  const [highlighted, setHighlighted] = React.useState(false);

  // The chip earns hover/tap affordances only when something is wired to it (Games
  // card). FlawCard renders it with no callbacks — purely decorative, matching the
  // sibling TagChips there (definition=false, no callbacks).
  const interactive = Boolean(onHover || onActivate);

  // Unknown motif (no family mapping) — render nothing rather than a broken chip.
  if (colors == null || Icon == null) return null;

  const { color, bg } = colors;

  return (
    <span
      className={cn(
        // text-xs is the documented chip exception (CLAUDE.md / UI-SPEC):
        // tactic motif chips match the flaw-tag chip sizing.
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-bold',
        interactive && 'cursor-pointer transition-all hover:-translate-y-px',
      )}
      style={{
        color,
        backgroundColor: highlighted ? HIGHLIGHT_BG(bg) : bg,
        borderColor: color,
        filter: highlighted ? 'brightness(1.2)' : undefined,
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
      <Icon className="h-3 w-3 shrink-0" />
      {visibleLabel}
    </span>
  );
}
