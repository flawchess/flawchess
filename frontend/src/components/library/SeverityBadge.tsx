import * as React from 'react';
import { SEV_BLUNDER, SEV_MISTAKE, SEV_INACCURACY, ACTIVE_FILTER_RING_CLASS } from '@/lib/theme';
import { cn } from '@/lib/utils';
import { useFlawFilterStore } from '@/hooks/useFlawFilterStore';
import type { FlawSeverity } from '@/types/library';

// Per UI-SPEC §Severity: badge bg = foreground at 14% alpha, border = 30% alpha.
// We derive these from the base oklch values using CSS oklch(L C H / alpha) syntax.
// Only the alpha component is appended; no new hue/chroma values are introduced.

// Maps severity to CSS color string from theme.ts (foreground)
const SEV_COLORS: Record<FlawSeverity, string> = {
  blunder: SEV_BLUNDER,
  mistake: SEV_MISTAKE,
  inaccuracy: SEV_INACCURACY,
};

// Background = foreground color at 14% alpha
const SEV_BG_COLORS: Record<FlawSeverity, string> = {
  blunder: 'oklch(0.58 0.19 25 / 0.14)',
  mistake: 'oklch(0.70 0.16 55 / 0.14)',
  inaccuracy: 'oklch(0.82 0.13 95 / 0.14)',
};

// Border = foreground color at 30% alpha
const SEV_BORDER_COLORS: Record<FlawSeverity, string> = {
  blunder: 'oklch(0.58 0.19 25 / 0.30)',
  mistake: 'oklch(0.70 0.16 55 / 0.30)',
  inaccuracy: 'oklch(0.82 0.13 95 / 0.30)',
};

// Full label text per severity (displayed in the badge)
const SEVERITY_LABELS: Record<FlawSeverity, string> = {
  blunder: 'Blunders',
  mistake: 'Mistakes',
  inaccuracy: 'Inaccuracies',
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
export function SeverityBadge({ severity, count, gameId, onHover }: SeverityBadgeProps) {
  const [flawFilter] = useFlawFilterStore();
  const isActive =
    (severity === 'blunder' || severity === 'mistake') &&
    flawFilter.severity.length === 1 &&
    flawFilter.severity.includes(severity);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 whitespace-nowrap',
        isActive && ACTIVE_FILTER_RING_CLASS,
      )}
      style={{
        color: SEV_COLORS[severity],
        backgroundColor: SEV_BG_COLORS[severity],
        borderColor: SEV_BORDER_COLORS[severity],
        // Ring color matches the severity color for active-filter emphasis.
        ...(isActive ? ({ '--tw-ring-color': SEV_COLORS[severity] } as React.CSSProperties) : {}),
      }}
      aria-label={`${count} ${severity}s`}
      data-testid={`severity-${severity}-${gameId}`}
      onMouseEnter={onHover ? () => onHover(true) : undefined}
      onMouseLeave={onHover ? () => onHover(false) : undefined}
      onFocus={onHover ? () => onHover(true) : undefined}
      onBlur={onHover ? () => onHover(false) : undefined}
    >
      <span className="text-base font-bold">{count}</span>
      <span className="text-sm font-bold">{SEVERITY_LABELS[severity]}</span>
    </span>
  );
}
