/**
 * TacticComparisonGrid — beta-gated you-vs-opponent tactic-motif comparison,
 * laid out as one Card per API-returned family (Phase 126 TACUI-02).
 *
 * Layout: single column on mobile, 3 columns on desktop (lg). Up to 6 family
 * cards, ranked server-side by largest significant gap (Wilson-gated), volume
 * fallback. Cards are rendered in the order returned by the API (no client
 * re-sort).
 *
 * Per-row anatomy (mirrors FlawBulletRow):
 *   [FamilyIcon]  [Family label]  …  [±delta zone-colored?]  [InfoPopover trigger]
 *   [MiniBulletChart — delta bar + CI whiskers + zone band where available]
 *
 * Zone degradation: when has_zone=false (no tactic benchmark pipeline yet),
 * neutralMin/neutralMax collapse to 0/0 — the chart still shows the delta bar
 * and CI whiskers; no "no benchmark" label needed.
 *
 * Beta gate: returns null immediately for non-beta users (D-01).
 *
 * States (in priority order):
 *   isLoading  → pulse skeleton (data-testid="tactic-comparison-loading")
 *   isError    → LoadError CLAUDE.md-mandated copy
 *   !data      → null
 *   below_gate → gate CTA (data-testid="tactic-comparison-gate-cta")
 *   normal     → grid (data-testid="tactic-comparison-grid")
 *
 * Zero-event rows (delta === null): muted italic "No events in current filter".
 */

import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { Search } from 'lucide-react';

import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { LoadError } from '@/components/ui/load-error';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { useUserProfile } from '@/hooks/useUserProfile';
import { useTacticComparison } from '@/hooks/useLibrary';
import { cn } from '@/lib/utils';
import {
  TACTIC_COMPARISON_FAMILIES,
  TACTIC_FAMILY_COLORS,
  TACTIC_FAMILY_ICON,
  isTacticDeltaSignificant,
  tacticDeltaZoneColor,
} from '@/lib/tacticComparisonMeta';
import type { TacticFamily } from '@/lib/tacticComparisonMeta';
import type { TacticBullet, TacticComparisonResponse } from '@/types/library';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

const HOVER_OPEN_DELAY_MS = 100;

// ─── Signed delta helper ──────────────────────────────────────────────────────

/** Signed 2-decimal string (e.g. +0.42, -1.00). */
function signedDelta(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}`;
}

// ─── TacticBulletPopover ──────────────────────────────────────────────────────

interface TacticBulletPopoverProps {
  bullet: TacticBullet;
  familyName: string;
  testId: string;
  ariaLabel: string;
}

/**
 * Info popover for one tactic family row (mirrors FlawBulletPopover).
 *
 * Body (per UI-SPEC copywriting contract):
 *   1. Family-colored icon + bold label, then the family definition (explains the
 *      tactic — mirrors the flaw-tag tooltips' first paragraph).
 *   2. "You: {you_rate} per game | Opponents: {opp_rate} per game"
 *   3. Sign-convention sentence
 *   4. Confidence sentence ("statistically notable / within normal variation")
 *
 * font-size: text-xs — allowed per CLAUDE.md hover-activated info-tooltip exception.
 */
function TacticBulletPopover({
  bullet,
  familyName,
  testId,
  ariaLabel,
}: TacticBulletPopoverProps) {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = (): void => {
    hoverTimeout.current = setTimeout(() => setOpen(true), HOVER_OPEN_DELAY_MS);
  };

  const handleMouseLeave = (): void => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setOpen(false);
  };

  const family = bullet.family as TacticFamily;
  const familyDef = TACTIC_COMPARISON_FAMILIES.find((f) => f.family === family);
  const definition = familyDef?.definition ?? '';
  const color = TACTIC_FAMILY_COLORS[family]?.color;
  const Icon = TACTIC_FAMILY_ICON[family];

  const isZeroEvent = bullet.delta === null;
  const isSignificant = !isZeroEvent && isTacticDeltaSignificant(bullet);

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          role="button"
          tabIndex={0}
          className="inline-flex items-center text-brand-brown-light/70 hover:text-brand-brown focus:outline-none cursor-pointer"
          aria-label={ariaLabel}
          data-testid={testId}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <Search className="h-4 w-4" />
        </span>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="top"
          sideOffset={4}
          onMouseEnter={() => {
            if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
          }}
          onMouseLeave={handleMouseLeave}
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          <div className="text-left space-y-1">
            <p>
              <span className="inline-flex items-center gap-1 align-middle">
                {Icon && (
                  <Icon className="h-3.5 w-3.5 shrink-0" style={{ color }} aria-hidden="true" />
                )}
                <strong style={{ color }}>{familyName}</strong>
              </span>
              : {definition}
            </p>
            {isZeroEvent ? (
              <p className="opacity-70">No events in the current filter.</p>
            ) : (
              <>
                <p>
                  You:{' '}
                  <strong>
                    {bullet.you_rate !== null ? bullet.you_rate.toFixed(2) : '—'}
                  </strong>{' '}
                  per game | Opponents:{' '}
                  <strong>
                    {bullet.opp_rate !== null ? bullet.opp_rate.toFixed(2) : '—'}
                  </strong>{' '}
                  per game
                </p>
                <p>
                  Positive delta means you allow more tactic flaws than opponents (worse). Negative
                  delta means you allow fewer (better).
                </p>
                <p>
                  {isSignificant
                    ? 'Result is statistically notable.'
                    : 'Result is within normal variation.'}
                </p>
              </>
            )}
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}

// ─── TacticBulletRow ──────────────────────────────────────────────────────────

interface TacticBulletRowProps {
  bullet: TacticBullet;
}

function TacticBulletRow({ bullet }: TacticBulletRowProps) {
  const family = bullet.family as TacticFamily;
  const familyDef = TACTIC_COMPARISON_FAMILIES.find((f) => f.family === family);
  const familyName = familyDef?.name ?? bullet.family;
  const familyColors = TACTIC_FAMILY_COLORS[family];
  const color = familyColors?.color;
  const Icon = TACTIC_FAMILY_ICON[family];

  const isZeroEvent = bullet.delta === null;

  // Tint the delta with its zone color only when the result is significant
  // (95% CI excludes zero); otherwise keep it muted.
  const numberColor =
    !isZeroEvent && bullet.delta !== null && isTacticDeltaSignificant(bullet)
      ? tacticDeltaZoneColor(bullet.delta, bullet.zone_lo, bullet.zone_hi)
      : undefined;

  return (
    <div className="flex flex-col gap-1" data-testid={`tactic-bullet-row-${bullet.family}`}>
      {/* Label + delta + popover trigger row */}
      <div className="flex items-center gap-1.5">
        {Icon && <Icon className="h-3.5 w-3.5 shrink-0" style={{ color }} aria-hidden="true" />}
        <span className="text-sm font-medium truncate">{familyName}</span>
        <span
          className={cn(
            'ml-auto text-sm font-bold tabular-nums shrink-0',
            !numberColor && 'text-muted-foreground',
          )}
          style={numberColor ? { color: numberColor } : undefined}
        >
          {bullet.delta !== null ? signedDelta(bullet.delta) : '—'}
        </span>
        <TacticBulletPopover
          bullet={bullet}
          familyName={familyName}
          testId={`tactic-bullet-popover-${bullet.family}`}
          ariaLabel={`Tactic comparison: ${familyName}`}
        />
      </div>

      {/* Bullet chart or zero-event placeholder */}
      {isZeroEvent ? (
        <p className="text-sm text-muted-foreground/50 italic">No events in current filter</p>
      ) : (
        <MiniBulletChart
          value={bullet.delta ?? 0}
          // When has_zone=false, neutralMin/neutralMax collapse to 0/0 —
          // the band disappears but the delta bar and CI whiskers remain (T-126-10).
          neutralMin={bullet.has_zone ? bullet.zone_lo : 0}
          neutralMax={bullet.has_zone ? bullet.zone_hi : 0}
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

// ─── Grid body ────────────────────────────────────────────────────────────────

interface GridBodyProps {
  data: TacticComparisonResponse;
}

/**
 * Renders the API-returned bullets in order (server already ranked + capped at 6).
 * No client-side re-sort — the backend's significant-gap-first / volume-fallback
 * ordering is the canonical presentation order.
 */
function GridBody({ data }: GridBodyProps) {
  return (
    <div data-testid="tactic-comparison-grid" className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {data.bullets.map((bullet) => (
        <Card
          key={bullet.family}
          data-testid={`tactic-family-card-${bullet.family}`}
        >
          <CardHeader data-testid={`tactic-family-header-${bullet.family}`}>
            {TACTIC_COMPARISON_FAMILIES.find((f) => f.family === bullet.family)?.name ??
              bullet.family}
          </CardHeader>
          <CardBody className="space-y-3">
            <TacticBulletRow bullet={bullet} />
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
      data-testid="tactic-comparison-loading"
      aria-label="Loading tactic comparison"
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
      data-testid="tactic-comparison-gate-cta"
      className="rounded border border-border p-4 text-sm text-muted-foreground space-y-2"
      style={{ background: 'var(--color-charcoal)' }}
      aria-live="polite"
    >
      <p className="font-semibold text-foreground">
        {analyzedN} of {analyzedGate} analyzed games needed
      </p>
      <p>
        You need at least {analyzedGate} analyzed games with full engine analysis to see the tactic
        comparison. Currently you have {analyzedN} in the current filter.
      </p>
      <p>
        To get more games analyzed, use <strong>Lichess server analysis</strong>: open a game on
        Lichess, click Analysis board, then Request computer analysis. Analyzed games are imported
        on your next sync.
      </p>
    </div>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface TacticComparisonGridProps {
  filters: FilterState;
  flawFilter: FlawFilterState;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Beta-gated family-card grid for the 6-family tactic-motif comparison.
 *
 * Self-fetches via useTacticComparison; handles all states internally.
 * The parent (FlawStatsPanel Zone 3) renders this directly after FlawComparisonGrid —
 * no extra beta guard needed at the call site (grid self-gates on beta_enabled).
 *
 * Grid is single-column at 375px (TACUI-03), 3-column on desktop.
 */
export function TacticComparisonGrid({ filters, flawFilter }: TacticComparisonGridProps) {
  const { data: userProfile } = useUserProfile();

  // Beta gate (D-01): non-beta users see no tactic surfaces.
  if (!userProfile?.beta_enabled) return null;

  return (
    <TacticComparisonGridInner
      filters={filters}
      flawFilter={flawFilter}
    />
  );
}

/**
 * Inner component (post-beta-gate). Separated so the hook is only called
 * when the user is confirmed beta-enabled (hook-after-conditional guard).
 */
function TacticComparisonGridInner({ filters, flawFilter }: TacticComparisonGridProps) {
  // The comparison grid always shows every family (its purpose is to compare across
  // families), so it is NOT narrowed by the Flaws-tab tactic-motif filter — pass no
  // family narrowing. Game-metadata filters + severity still apply via filters/flawFilter.
  const { isLoading, isError, data } = useTacticComparison(filters, flawFilter, []);

  if (isLoading) return <LoadingSkeleton />;
  if (isError) return <LoadError resource="tactic comparison" />;
  if (!data) return null;

  if (data.below_gate) {
    return <GateCTA analyzedN={data.analyzed_n} analyzedGate={data.analyzed_gate} />;
  }

  return (
    <div>
      {/* Section heading (UI-SPEC copywriting contract) */}
      <h3 className="text-base font-semibold mb-1">Tactic Motifs</h3>
      <p className="text-sm text-muted-foreground mb-4">
        You vs. your opponents — flaws allowed per game
      </p>
      <GridBody data={data} />
    </div>
  );
}
