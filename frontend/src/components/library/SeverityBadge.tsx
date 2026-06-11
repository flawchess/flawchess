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
  ACTIVE_FILTER_RING_CLASS,
} from '@/lib/theme';
import { cn } from '@/lib/utils';
import { useFlawFilterStore } from '@/hooks/useFlawFilterStore';
import type { FlawSeverity } from '@/types/library';

// Per UI-SPEC §Severity: badge bg = foreground at 14% alpha, border = 30% alpha.
// The composites live in theme.ts (SEV_*_BG / SEV_*_BORDER) and are shared with
// the severity filter toggles (FlawFilterControl).

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
   * When false, render the singular label only ("Blunder") with no leading count —
   * the Flaws card uses this since each card is exactly one flaw. Defaults to true
   * (Games card keeps the count + plural, e.g. "3 Blunders").
   */
  showCount?: boolean;
  /** Extra classes merged onto the badge span (e.g. `self-start` to size to content). */
  className?: string;
}

/**
 * A single severity count badge (Blunders / Mistakes / Inaccuracies) rendered as
 * a colored pill per UI-SPEC §"Severity count row". Colors come from theme.ts
 * SEV_* constants; backgrounds and borders are alpha-composites of those same
 * oklch values — no new color values are hard-coded here.
 *
 * Active-filter ring: mirrors TagChip — the badge subscribes to useFlawFilterStore
 * and rings when the severity filter is narrowed to exactly this severity. The
 * filter default is both M+B selected, so a ring would always show if we keyed off
 * plain membership; gating on length===1 means the ring marks the *active
 * constraint* (you've filtered to only blunders, or only mistakes). Inaccuracy is
 * not a filterable severity, so its badge never rings.
 */
export function SeverityBadge({
  severity,
  count,
  gameId,
  onHover,
  showCount = true,
  className,
}: SeverityBadgeProps) {
  const [flawFilter] = useFlawFilterStore();
  const isActive =
    (severity === 'blunder' || severity === 'mistake') &&
    flawFilter.severity.length === 1 &&
    flawFilter.severity.includes(severity);

  // Brighten the badge while it is hovered or focused (tap-focus on mobile), held
  // for as long as it has focus.
  const [highlighted, setHighlighted] = React.useState(false);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 whitespace-nowrap transition-all hover:-translate-y-px',
        isActive && ACTIVE_FILTER_RING_CLASS,
        className,
      )}
      style={{
        color: SEV_COLORS[severity],
        backgroundColor: highlighted ? HIGHLIGHT_BG(SEV_BG_COLORS[severity]) : SEV_BG_COLORS[severity],
        borderColor: SEV_BORDER_COLORS[severity],
        // Brighten font/border while hovered or focused.
        filter: highlighted ? 'brightness(1.2)' : undefined,
        // Ring color matches the severity color for active-filter emphasis.
        ...(isActive ? ({ '--tw-ring-color': SEV_COLORS[severity] } as React.CSSProperties) : {}),
      }}
      aria-label={showCount ? `${count} ${severity}s` : SEVERITY_LABELS_SINGULAR[severity]}
      data-testid={`severity-${severity}-${gameId}`}
      onMouseEnter={() => {
        onHover?.(true);
        setHighlighted(true);
      }}
      onMouseLeave={() => {
        onHover?.(false);
        setHighlighted(false);
      }}
      onFocus={() => {
        onHover?.(true);
        setHighlighted(true);
      }}
      onBlur={() => {
        onHover?.(false);
        setHighlighted(false);
      }}
    >
      {showCount && <span className="text-base font-bold">{count}</span>}
      <span className="text-sm font-bold">
        {showCount ? SEVERITY_LABELS[severity] : SEVERITY_LABELS_SINGULAR[severity]}
      </span>
    </span>
  );
}
