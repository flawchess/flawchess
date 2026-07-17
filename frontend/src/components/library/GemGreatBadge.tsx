import * as React from 'react';
import { GemIcon } from '@/components/icons/GemIcon';
import { GreatMoveIcon } from '@/components/icons/GreatMoveIcon';
import { MAIA_ACCENT, MAIA_ACCENT_BG, GREAT_ACCENT, GREAT_ACCENT_BG } from '@/lib/theme';
import { cn } from '@/lib/utils';

/**
 * Gem/great tier count badge (Phase 175 Plan 06) — mirrors SeverityBadge's pill
 * shape/interaction so the gem/great badges read as part of the same "count badge
 * family" as the severity badges, on both the Library game card (LibraryGameCard)
 * and the analysis panel (AnalysisTagsPanel). A small leading GemIcon/GreatMoveIcon
 * (already self-colored via GEM_GLYPH/GREAT_GLYPH, matching MAIA_ACCENT/GREAT_ACCENT)
 * distinguishes it from the plain-text severity badges at a glance.
 */

export type BestMoveTier = 'gem' | 'great';

const TIER_COLORS: Record<BestMoveTier, string> = {
  gem: MAIA_ACCENT,
  great: GREAT_ACCENT,
};
const TIER_BG_COLORS: Record<BestMoveTier, string> = {
  gem: MAIA_ACCENT_BG,
  great: GREAT_ACCENT_BG,
};
const TIER_LABELS: Record<BestMoveTier, string> = {
  gem: 'Gem',
  great: 'Great',
};
const TIER_ICONS: Record<BestMoveTier, typeof GemIcon> = {
  gem: GemIcon,
  great: GreatMoveIcon,
};

// Hover/focus highlight (mirrors SeverityBadge's HIGHLIGHT_BG): both *_ACCENT_BG
// composites end in `/ 0.14)` (theme.ts), so a plain brightness filter barely
// registers — bump the fill to a denser alpha while highlighted.
const HIGHLIGHT_BG = (bg: string): string => bg.replace('/ 0.14)', '/ 0.3)');

interface GemGreatBadgeProps {
  tier: BestMoveTier;
  count: number;
  gameId: number;
  /** Hover callback — lets the parent highlight this tier's eval-chart dots. */
  onHover?: (active: boolean) => void;
  /** Click/tap activation — the parent cycles the eval chart/board through this
   *  tier's plies. Omitted call sites stay a plain non-interactive span. */
  onActivate?: () => void;
  /** Extra classes merged onto the badge span. */
  className?: string;
}

/**
 * A single gem/great count badge ("N Gem" / "N Great") rendered as a colored pill,
 * matching SeverityBadge's structure field-for-field (interactive gating, hover
 * highlight, keyboard activation) so the two badge families behave identically.
 */
export function GemGreatBadge({
  tier,
  count,
  gameId,
  onHover,
  onActivate,
  className,
}: GemGreatBadgeProps) {
  const [highlighted, setHighlighted] = React.useState(false);
  const interactive = Boolean(onHover || onActivate);
  const Icon = TIER_ICONS[tier];

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
        className,
      )}
      style={{
        color: TIER_COLORS[tier],
        backgroundColor: highlighted ? HIGHLIGHT_BG(TIER_BG_COLORS[tier]) : TIER_BG_COLORS[tier],
        borderColor: TIER_COLORS[tier],
        filter: highlighted ? 'brightness(1.2)' : undefined,
      }}
      aria-label={`${count} ${TIER_LABELS[tier]}`}
      data-testid={`badge-${tier}-${gameId}`}
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
      <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span className="text-base font-bold">{count}</span>
      <span className="text-sm font-bold">{TIER_LABELS[tier]}</span>
    </span>
  );
}
