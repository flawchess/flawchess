import * as React from 'react';
import {
  SEV_BLUNDER,
  SEV_MISTAKE,
  SEV_INACCURACY,
  SEV_BLUNDER_BG,
  SEV_MISTAKE_BG,
  SEV_INACCURACY_BG,
  SEV_BLUNDER_BORDER,
  SEV_MISTAKE_BORDER,
  SEV_INACCURACY_BORDER,
  SEV_FACEPALM,
  SEV_FACEPALM_ON,
  ACTIVE_FILTER_RING_CLASS,
} from '@/lib/theme';
import { cn } from '@/lib/utils';
import { useFlawFilterStore } from '@/hooks/useFlawFilterStore';
import { isSeverityNarrowed } from '@/lib/flawSeverityFilter';
import { MoveQualityIcon } from '@/components/icons/MoveQualityIcon';
import { FacepalmBlunderIcon } from '@/components/icons/SeverityGlyphIcon';
import type { FlawSeverity, FlawSeverityFilter } from '@/types/library';

// Badge bg = foreground at 14% alpha, border = 30% alpha.
// The composites live in theme.ts (SEV_*_BG / SEV_*_BORDER) and are shared with
// the severity filter toggles (FlawFilterControl). Exception: the Facepalm chip is a solid
// SEV_FACEPALM fill with a light SEV_FACEPALM_ON label (260-G1), see badgePalette.

// Maps severity to CSS color string from theme.ts (foreground)
const SEV_COLORS: Record<FlawSeverity, string> = {
  blunder: SEV_BLUNDER,
  mistake: SEV_MISTAKE,
  inaccuracy: SEV_INACCURACY,
};

const SEV_BG_COLORS: Record<FlawSeverity, string> = {
  blunder: SEV_BLUNDER_BG,
  mistake: SEV_MISTAKE_BG,
  inaccuracy: SEV_INACCURACY_BG,
};

const SEV_BORDER_COLORS: Record<FlawSeverity, string> = {
  blunder: SEV_BLUNDER_BORDER,
  mistake: SEV_MISTAKE_BORDER,
  inaccuracy: SEV_INACCURACY_BORDER,
};

// Hover/focus highlight (mirrors TagChip): the SEV_*_BG composites are translucent
// (alpha 0.14), so a plain brightness filter barely registers on them. While the
// badge is the active pointer/focus target we bump the fill to a denser alpha (and
// brighten the font/border via a filter) so it clearly reads as highlighted for as
// long as it has focus. All three SEV_*_BG strings end in `/ 0.14)`.
const HIGHLIGHT_BG = (bg: string): string => bg.replace('/ 0.14)', '/ 0.3)');

interface BadgePalette {
  foreground: string;
  background: string;
  border: string;
  ring: string;
}

/** Colours of a badge: the solid dark red Facepalm chip, or the tinted pill of its severity. */
function badgePalette(severity: FlawSeverity, isFacepalmBadge: boolean): BadgePalette {
  if (isFacepalmBadge) {
    return {
      foreground: SEV_FACEPALM_ON,
      background: SEV_FACEPALM,
      border: SEV_FACEPALM,
      ring: SEV_FACEPALM,
    };
  }
  return {
    foreground: SEV_COLORS[severity],
    background: SEV_BG_COLORS[severity],
    border: SEV_BORDER_COLORS[severity],
    ring: SEV_COLORS[severity],
  };
}

// Full (plural) label text per severity — used with a leading count (Games card)
const SEVERITY_LABELS: Record<FlawSeverity, string> = {
  blunder: 'Blunders',
  mistake: 'Mistakes',
  inaccuracy: 'Inacc.',
};

// Singular label — used by the Flaws card, where each card is a single flaw so a
// count + plural ("1 Blunders") would be wrong/noisy. Just "Blunder".
const SEVERITY_LABELS_SINGULAR: Record<FlawSeverity, string> = {
  blunder: 'Blunder',
  mistake: 'Mistake',
  inaccuracy: 'Inaccuracy',
};

// A blunder badge carrying `facepalm` is a Facepalm chip: it reads "Facepalm" (260-G2).
const FACEPALM_LABEL_SINGULAR = 'Facepalm';
const FACEPALM_LABEL_PLURAL = 'Facepalms';

const BADGE_ICON_CLASS = 'h-4 w-4 shrink-0';

interface SeverityBadgeProps {
  severity: FlawSeverity;
  count: number;
  gameId: number;
  /**
   * Optional hover callback (Games card only). Fires true on pointer/focus enter,
   * false on leave — lets the parent highlight this severity's eval-chart markers.
   * Omitted call sites (e.g. FlawsTab) get no hover behavior.
   */
  onHover?: (active: boolean) => void;
  /**
   * Optional click/tap activation (Games card only). Fires on click or keyboard
   * (Enter/Space) — the card uses it to cycle the eval chart through this
   * severity's flaw plies. When provided the badge becomes a button (role/tabIndex/
   * cursor); omitted call sites (FlawsTab) stay a plain non-interactive span.
   */
  onActivate?: () => void;
  /**
   * When false, render the singular label only ("Blunder") with no leading count —
   * the Flaws card uses this since each card is exactly one flaw. Defaults to true
   * (Games card keeps the count + plural, e.g. "3 Blunders").
   */
  showCount?: boolean;
  /**
   * When false, never ring for the Library's severity filter. For surfaces outside
   * the Library (Train Archive), where that filter does not apply. Defaults to true.
   */
  showActiveFilterRing?: boolean;
  /**
   * Flaws card only. Leads the badge with the move-quality glyph ("??" / "?" / "?!"
   * in a severity-colored circle), the same icon as the move list and board markers.
   * Defaults to false (Games card count badges stay icon-less).
   */
  showIcon?: boolean;
  /**
   * On a blunder: the badge is a Facepalm chip (the flaw's facepalm score reaches
   * FACEPALM_HIGH_CUTOFF). It reads "Facepalm" instead of "Blunder", with showIcon it leads
   * with the "???" glyph instead of "??", and its own filter tag is Facepalm instead of
   * Blunder. The stored severity and the testid stay blunder (D-12). Ignored on other
   * severities. Defaults to false.
   */
  facepalm?: boolean;
  /** Extra classes merged onto the badge span (e.g. `self-start` to size to content). */
  className?: string;
}

/** The Flaws filter tag a badge stands for: Facepalm for a "???" badge, null for inaccuracy. */
function ownFilterTag(severity: FlawSeverity, facepalm: boolean): FlawSeverityFilter | null {
  if (severity === 'inaccuracy') return null;
  return severity === 'blunder' && facepalm ? 'facepalm' : severity;
}

/**
 * A single severity count badge (Blunders / Mistakes / Inaccuracies) rendered as
 * a colored pill (the severity count row). Colors come from theme.ts
 * SEV_* constants; backgrounds and borders are alpha-composites of those same
 * oklch values — no new color values are hard-coded here.
 *
 * Active-filter ring: mirrors TagChip. The badge subscribes to useFlawFilterStore and
 * rings when its OWN filter tag is selected and the selection narrows (at least one of
 * the three Flaws tags selected, at least one not). The own tag is Facepalm for a "???"
 * badge (blunder with `facepalm`), else the badge's severity; inaccuracy is not a
 * filterable tag, so its badge never rings. Nothing selected and all three selected
 * both mean no filter, so no badge rings.
 */
export function SeverityBadge({
  severity,
  count,
  gameId,
  onHover,
  onActivate,
  showCount = true,
  showActiveFilterRing = true,
  showIcon = false,
  facepalm = false,
  className,
}: SeverityBadgeProps) {
  const [flawFilter] = useFlawFilterStore();
  const ownTag = ownFilterTag(severity, facepalm);
  const isFacepalmBadge = facepalm && severity === 'blunder';
  const label = isFacepalmBadge
    ? showCount
      ? FACEPALM_LABEL_PLURAL
      : FACEPALM_LABEL_SINGULAR
    : showCount
      ? SEVERITY_LABELS[severity]
      : SEVERITY_LABELS_SINGULAR[severity];
  const palette = badgePalette(severity, isFacepalmBadge);
  const ariaLabel = showCount
    ? `${count} ${isFacepalmBadge ? 'facepalm' : severity}s`
    : label;
  const isActive =
    showActiveFilterRing &&
    ownTag != null &&
    isSeverityNarrowed(flawFilter.severity) &&
    flawFilter.severity.includes(ownTag);

  // Brighten the badge while it is hovered or focused (tap-focus on mobile), held
  // for as long as it has focus.
  const [highlighted, setHighlighted] = React.useState(false);

  // The badge earns hover/tap affordances only when something is wired to it (Games
  // card: onHover highlights the chart, onActivate cycles it). The Flaws card renders
  // it with no callbacks — a plain decorative span (no lift, no brighten, no cursor),
  // matching the sibling TagChips there.
  const interactive = Boolean(onHover || onActivate);

  return (
    <span
      role={onActivate ? 'button' : undefined}
      tabIndex={onActivate ? 0 : undefined}
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
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 whitespace-nowrap',
        interactive && 'transition-all hover:-translate-y-px',
        onActivate && 'cursor-pointer',
        isActive && ACTIVE_FILTER_RING_CLASS,
        className,
      )}
      style={{
        color: palette.foreground,
        // The alpha swap is a no-op on the solid Facepalm fill; the brightness filter still applies.
        backgroundColor: highlighted ? HIGHLIGHT_BG(palette.background) : palette.background,
        borderColor: palette.border,
        // Brighten font/border while hovered or focused.
        filter: highlighted ? 'brightness(1.2)' : undefined,
        // Ring color matches the badge's own colour for active-filter emphasis.
        ...(isActive ? ({ '--tw-ring-color': palette.ring } as React.CSSProperties) : {}),
      }}
      aria-label={ariaLabel}
      data-testid={`severity-${severity}-${gameId}`}
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
      onFocus={
        interactive
          ? () => {
              onHover?.(true);
              setHighlighted(true);
            }
          : undefined
      }
      onBlur={
        interactive
          ? () => {
              onHover?.(false);
              setHighlighted(false);
            }
          : undefined
      }
    >
      {showIcon &&
        (isFacepalmBadge ? (
          <FacepalmBlunderIcon className={BADGE_ICON_CLASS} />
        ) : (
          <MoveQualityIcon quality={severity} className={BADGE_ICON_CLASS} />
        ))}
      {showCount && <span className="text-base font-bold">{count}</span>}
      <span className="text-sm font-bold">{label}</span>
    </span>
  );
}
