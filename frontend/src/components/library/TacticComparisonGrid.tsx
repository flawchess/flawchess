/**
 * TacticComparisonGrid — beta-gated you-vs-opponent tactic-motif comparison,
 * laid out as one Card per family with two bullet rows (Phase 129 TACUI-08).
 *
 * Layout: single column on mobile, 3 columns on desktop (lg). Server returns
 * up to 12 bullets (6 families × 2 orientations). Top-6 families by Missed
 * you_rate (server-side) render in the main grid; any remaining families render
 * inside a collapsible "More Tactics" accordion (cloned from Endgame Statistics
 * Concepts in Endgames.tsx). Cards are rendered in server order (no client re-sort).
 *
 * Per-family card anatomy:
 *   [CardHeader] Family name (font-medium, existing style unchanged)
 *   [CardBody]
 *     [TacticBulletRow] "Missed {Family}" — orientation=missed bullet
 *     [TacticBulletRow] "Allowed {Family}" — orientation=allowed bullet
 *
 * Per-row anatomy (mirrors FlawBulletRow):
 *   "Missed {Family}" label (text-sm text-muted-foreground Regular 400) — delta — InfoPopover
 *   [MiniBulletChart — delta bar + CI whiskers + zone band where available]
 *
 * Zone degradation: when has_zone=false (no tactic benchmark pipeline yet),
 * neutralMin/neutralMax collapse to 0/0 — the chart still shows the delta bar
 * and CI whiskers; no "no benchmark" label needed.
 *
 * Beta gate: returns null immediately for non-beta users (D-01).
 * Grid is independent of the Flaws-tab orientation/depth filters (D-09).
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
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from '@/components/ui/accordion';
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

/** Max families shown in the main grid before overflow goes into "More Tactics". */
const MAX_MAIN_GRID_FAMILIES = 6;

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
  /** Row label override ("Missed Fork" / "Allowed Fork"). When omitted, shows family name. */
  rowLabel?: string;
  /** data-testid for the row container. */
  rowTestId?: string;
}

function TacticBulletRow({ bullet, rowLabel, rowTestId }: TacticBulletRowProps) {
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

  // When a row label override is provided (two-bullet card mode), the family
  // icon appears only on the header (CardHeader), not repeated per row.
  const showIcon = !rowLabel;
  const displayLabel = rowLabel ?? familyName;

  return (
    <div
      className="flex flex-col gap-1"
      data-testid={rowTestId ?? `tactic-bullet-row-${bullet.family}`}
    >
      {/* Label + delta + popover trigger row */}
      <div className="flex items-center gap-1.5">
        {showIcon && Icon && (
          <Icon className="h-3.5 w-3.5 shrink-0" style={{ color }} aria-hidden="true" />
        )}
        {/* Row label: text-sm text-muted-foreground Regular 400 (per UI-SPEC — do NOT
            extend the existing font-medium on the CardHeader family label to these rows). */}
        <span className="text-sm text-muted-foreground truncate">{displayLabel}</span>
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

// ─── Family grouping ──────────────────────────────────────────────────────────

/**
 * Groups bullets by family, preserving server order of first appearance.
 * Each family maps to { missed?: TacticBullet; allowed?: TacticBullet }.
 * No client re-sort — backend's top-6-by-Missed ranking is the canonical order (D-14).
 */
function groupBulletsByFamily(
  bullets: TacticBullet[],
): { family: string; missed?: TacticBullet; allowed?: TacticBullet }[] {
  const order: string[] = [];
  const map = new Map<string, { missed?: TacticBullet; allowed?: TacticBullet }>();

  for (const bullet of bullets) {
    if (!map.has(bullet.family)) {
      order.push(bullet.family);
      map.set(bullet.family, {});
    }
    const entry = map.get(bullet.family)!;
    if (bullet.orientation === 'missed') {
      entry.missed = bullet;
    } else {
      entry.allowed = bullet;
    }
  }

  return order.map((family) => ({ family, ...map.get(family) }));
}

// ─── FamilyCard renderer ──────────────────────────────────────────────────────

interface FamilyCardProps {
  family: string;
  missed?: TacticBullet;
  allowed?: TacticBullet;
}

/**
 * One Card per tactic family with two TacticBulletRows: "Missed {Family}" then
 * "Allowed {Family}". The card's header shows the family name with its existing
 * font-medium style. Row labels use text-sm text-muted-foreground Regular 400
 * (per UI-SPEC — do NOT extend font-medium to bullet row labels).
 */
function FamilyCard({ family, missed, allowed }: FamilyCardProps) {
  const familyDef = TACTIC_COMPARISON_FAMILIES.find((f) => f.family === family);
  const familyName = familyDef?.name ?? family;
  const Icon = TACTIC_FAMILY_ICON[family as TacticFamily];
  const color = TACTIC_FAMILY_COLORS[family as TacticFamily]?.color;

  return (
    <Card data-testid={`tactic-family-card-${family}`}>
      <CardHeader data-testid={`tactic-family-header-${family}`}>
        <span className="inline-flex items-center gap-1.5">
          {Icon && <Icon className="h-4 w-4 shrink-0" style={{ color }} aria-hidden="true" />}
          {familyName}
        </span>
      </CardHeader>
      <CardBody className="space-y-3">
        {missed && (
          <TacticBulletRow
            bullet={missed}
            rowLabel={`Missed ${familyName}`}
            rowTestId={`tactic-grid-missed-${family}`}
          />
        )}
        {allowed && (
          <TacticBulletRow
            bullet={allowed}
            rowLabel={`Allowed ${familyName}`}
            rowTestId={`tactic-grid-allowed-${family}`}
          />
        )}
      </CardBody>
    </Card>
  );
}

// ─── Grid body ────────────────────────────────────────────────────────────────

interface GridBodyProps {
  data: TacticComparisonResponse;
}

/**
 * Groups the API-returned bullets by family (preserving server order) and renders:
 * - First up-to-6 families in the main grid (data-testid="tactic-comparison-grid").
 * - Any remaining families inside a "More Tactics" accordion (data-testid="tactic-grid-more-tactics").
 *
 * No client-side re-sort — the backend's top-6-by-Missed-you_rate ordering is canonical (D-14).
 * No orientation toggle — the grid always shows both orientations per family (D-09).
 */
function GridBody({ data }: GridBodyProps) {
  const grouped = groupBulletsByFamily(data.bullets);
  const mainFamilies = grouped.slice(0, MAX_MAIN_GRID_FAMILIES);
  const overflowFamilies = grouped.slice(MAX_MAIN_GRID_FAMILIES);

  return (
    <div>
      <div data-testid="tactic-comparison-grid" className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {mainFamilies.map(({ family, missed, allowed }) => (
          <FamilyCard key={family} family={family} missed={missed} allowed={allowed} />
        ))}
      </div>

      {/* More Tactics accordion — only rendered when there are overflow families (D-14).
          Cloned verbatim from Endgames.tsx:390-397 (Endgame Statistics Concepts pattern). */}
      {overflowFamilies.length > 0 && (
        <Accordion type="single" collapsible className="mt-4">
          <AccordionItem
            value="more-tactics"
            className="charcoal-texture rounded-md overflow-hidden border-none"
            data-testid="tactic-grid-more-tactics"
          >
            <AccordionTrigger band>
              <span className="flex items-center gap-2 flex-1">
                <h3 className="text-base font-semibold text-foreground">More Tactics</h3>
              </span>
            </AccordionTrigger>
            <AccordionContent className="p-4">
              {/* Same FamilyCard renderer as top-6 — no compact variant (CONTEXT discretion). */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {overflowFamilies.map(({ family, missed, allowed }) => (
                  <FamilyCard key={family} family={family} missed={missed} allowed={allowed} />
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      )}
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
 * Beta-gated family-card grid for the tactic-motif comparison (TACUI-08).
 *
 * Self-fetches via useTacticComparison (no orientation arg — grid always shows
 * both orientations regardless of the Flaws-tab toggle, D-09). Handles all states
 * internally. The parent (FlawStatsPanel Zone 3) renders this directly after
 * FlawComparisonGrid — no extra beta guard needed at the call site (grid self-gates).
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
  // No orientation arg — grid always shows both orientations (D-09).
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
