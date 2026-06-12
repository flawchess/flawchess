/**
 * FlawComparisonGrid — the 15-bullet you-vs-opponent flaw comparison, laid out
 * as one Card per family (Phase 115 UAT).
 *
 * Layout: six family Cards in a 3-column grid on desktop (lg), 1 column on
 * mobile. Each Card's header is the family name; its body stacks the family's
 * metric rows. Per row (mirrors the endgame metric layout):
 *   <family-colored icon> <label>  …  <rate_diff> <magnifying-glass tooltip>
 *   <MiniBulletChart>
 * The rate_diff is tinted with its zone color only when the result is
 * statistically significant (95% CI excludes zero); otherwise it stays muted.
 *
 * Data: self-fetching via useLibraryFlawComparison (D-07: zone bounds come from
 * the API response, not hardcoded TS constants).
 *
 * States (handled in order):
 *   isLoading → lightweight skeleton (data-testid flaw-comparison-loading)
 *   isError   → LoadError CLAUDE.md-mandated copy
 *   !data     → null
 *   below_gate → CTA (data-testid flaw-comparison-gate-cta, D-10)
 *   normal    → grid (data-testid flaw-comparison-grid)
 *
 * Zero-event bullets (D-11): delta === null → muted "No events" placeholder;
 * the row stays in its card (no reflow).
 */

import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { LoadError } from '@/components/ui/load-error';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { FlawBulletPopover } from '@/components/popovers/FlawBulletPopover';
import { useLibraryFlawComparison } from '@/hooks/useLibrary';
import { cn } from '@/lib/utils';
import {
  FLAW_COMPARISON_FAMILIES,
  FLAW_COMPARISON_META,
  FLAW_FAMILY_COLORS,
  flawDeltaZoneColor,
  isFlawDeltaSignificant,
} from '@/lib/flawComparisonMeta';
import type { FlawBullet, FlawComparisonResponse } from '@/types/library';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

// ─── FlawBulletRow sub-component ──────────────────────────────────────────────

interface FlawBulletRowProps {
  bullet: FlawBullet;
}

/** Signed 2-decimal string (e.g. +0.42, -1.00). */
function signedDelta(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}`;
}

function FlawBulletRow({ bullet }: FlawBulletRowProps) {
  const meta = FLAW_COMPARISON_META[bullet.tag];
  const label = meta?.label ?? bullet.tag;
  const Icon = meta?.icon;
  const familyColor = meta ? FLAW_FAMILY_COLORS[meta.family].color : undefined;
  const isZeroEvent = bullet.delta === null;

  // Tint the rate_diff with its zone color only when the result is significant
  // (95% CI excludes zero); otherwise keep it muted (UAT: "zone-color if
  // statistically significant").
  const numberColor =
    !isZeroEvent && bullet.delta !== null && isFlawDeltaSignificant(bullet)
      ? flawDeltaZoneColor(bullet.delta, bullet.zone_lo, bullet.zone_hi)
      : undefined;

  return (
    <div className="flex flex-col gap-1" data-testid={`flaw-bullet-row-${bullet.tag}`}>
      {/* Label + rate_diff + popover trigger row */}
      <div className="flex items-center gap-1.5">
        {Icon && <Icon className="h-3.5 w-3.5 shrink-0" style={{ color: familyColor }} aria-hidden="true" />}
        <span className="text-sm font-medium truncate">{label}</span>
        <span
          className={cn('ml-auto text-sm font-bold tabular-nums shrink-0', !numberColor && 'text-muted-foreground')}
          style={numberColor ? { color: numberColor } : undefined}
        >
          {bullet.delta !== null ? signedDelta(bullet.delta) : '—'}
        </span>
        <FlawBulletPopover
          bullet={bullet}
          testId={`flaw-bullet-popover-${bullet.tag}`}
          ariaLabel={`Flaw comparison: ${label}`}
        />
      </div>

      {/* Bullet chart or zero-event placeholder */}
      {isZeroEvent ? (
        <p className="text-sm text-muted-foreground/50 italic">No events in current filter</p>
      ) : (
        <MiniBulletChart
          value={bullet.delta ?? 0}
          neutralMin={bullet.zone_lo}
          neutralMax={bullet.zone_hi}
          domain={bullet.domain}
          center={0}
          ciLow={bullet.ci_low ?? undefined}
          ciHigh={bullet.ci_high ?? undefined}
          invertColors
          barColor="neutral"
        />
      )}
    </div>
  );
}

// ─── Grid body (rendered when data is available and not below-gate) ────────────

interface GridBodyProps {
  data: FlawComparisonResponse;
}

function GridBody({ data }: GridBodyProps) {
  // Build a lookup map for O(1) access by tag.
  const bulletByTag = new Map<string, FlawBullet>();
  for (const b of data.bullets) {
    bulletByTag.set(b.tag, b);
  }

  return (
    <div data-testid="flaw-comparison-grid" className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {FLAW_COMPARISON_FAMILIES.map((family) => (
        <Card key={family.family} data-testid={`flaw-family-card-${family.family}`}>
          <CardHeader data-testid={`flaw-family-header-${family.family}`}>{family.name}</CardHeader>
          <CardBody className="space-y-3">
            {family.tags.map((tag) => {
              const bullet = bulletByTag.get(tag);
              if (!bullet) return null;
              return <FlawBulletRow key={tag} bullet={bullet} />;
            })}
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div
      className="grid grid-cols-1 lg:grid-cols-3 gap-4 animate-pulse"
      data-testid="flaw-comparison-loading"
      aria-label="Loading comparison"
    >
      {[...Array(6)].map((_, i) => (
        <div
          key={i}
          className="h-40 rounded-md border border-border"
          style={{ background: 'var(--color-charcoal)' }}
        />
      ))}
    </div>
  );
}

// ─── Below-gate CTA ───────────────────────────────────────────────────────────

interface GateCTAProps {
  analyzedN: number;
  analyzedGate: number;
}

function GateCTA({ analyzedN, analyzedGate }: GateCTAProps) {
  return (
    <div
      data-testid="flaw-comparison-gate-cta"
      className="rounded border border-border p-4 text-sm text-muted-foreground space-y-2"
      style={{ background: 'var(--color-charcoal)' }}
      aria-live="polite"
    >
      <p className="font-semibold text-foreground">
        {analyzedN} of {analyzedGate} analyzed games needed
      </p>
      <p>
        You need at least {analyzedGate} analyzed games to see the comparison grid. Currently
        you have {analyzedN} in the current filter.
      </p>
      <p>
        To get more games analyzed, use{' '}
        <strong>Lichess server analysis</strong>: open a game on Lichess, click Analysis board,
        then Request computer analysis. Analyzed games are imported on your next sync.
      </p>
    </div>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface FlawComparisonGridProps {
  filters: FilterState;
  flawFilter: FlawFilterState;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Family-card grid for the 15-metric flaw comparison.
 *
 * Self-fetches via useLibraryFlawComparison; handles all states internally.
 * The parent (FlawStatsPanel) keeps the Band + trend chart live regardless of
 * the gate — this grid only gates itself.
 */
export function FlawComparisonGrid({ filters, flawFilter }: FlawComparisonGridProps) {
  const { isLoading, isError, data } = useLibraryFlawComparison(filters, flawFilter);

  if (isLoading) return <LoadingSkeleton />;
  if (isError) return <LoadError resource="comparison" />;
  if (!data) return null;

  if (data.below_gate) {
    return <GateCTA analyzedN={data.analyzed_n} analyzedGate={data.analyzed_gate} />;
  }

  return <GridBody data={data} />;
}
