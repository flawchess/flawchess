import { SEV_BLUNDER, SEV_MISTAKE, SEV_INACCURACY } from '@/lib/theme';
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
  inaccuracy: 'Inacc.',
};

interface SeverityBadgeProps {
  severity: FlawSeverity;
  count: number;
  gameId: number;
}

/**
 * A single severity count badge (Blunders / Mistakes / Inacc.) rendered as a
 * colored pill per UI-SPEC §"Severity count row". Colors come from theme.ts
 * SEV_* constants; backgrounds and borders are alpha-composites of those same
 * oklch values — no new color values are hard-coded here.
 */
export function SeverityBadge({ severity, count, gameId }: SeverityBadgeProps) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 whitespace-nowrap"
      style={{
        color: SEV_COLORS[severity],
        backgroundColor: SEV_BG_COLORS[severity],
        borderColor: SEV_BORDER_COLORS[severity],
      }}
      aria-label={`${count} ${severity}s`}
      data-testid={`severity-${severity}-${gameId}`}
    >
      <span className="text-base font-bold">{count}</span>
      <span className="text-sm font-bold">{SEVERITY_LABELS[severity]}</span>
    </span>
  );
}
