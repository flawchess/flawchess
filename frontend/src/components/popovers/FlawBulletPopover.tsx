/**
 * FlawBulletPopover — magnifying-glass info popover for one flaw-comparison
 * bullet (Phase 115 UAT). Mirrors the endgame MetricStatPopover shell exactly
 * (Search trigger, 100ms hover-open, Portal + Content side="top").
 *
 * Body — four paragraphs, matching the endgame metric tooltips:
 *   1. Family-colored icon + bold label, then the tag definition (sourced from
 *      the Game / Flaw card tag tooltips where available).
 *   2. "You have <rate_diff> more/fewer <noun> per 100 moves than your opponents
 *      (you: x, opponents: y)."
 *   3. Verdict + confidence + p-value, e.g. "Likely a real strength. High
 *      confidence (p < 0.001)." Buckets match scoreConfidence.ts.
 *   4. Italic methodology — definition, Test, Confidence interval on separate
 *      lines, matching the endgame metric tooltips' last paragraph.
 *
 * Zero-event bullets (delta === null) render only paragraph 1 + a short
 * "no events" line.
 *
 * Font-size: text-xs allowed per CLAUDE.md hover-activated info-tooltip exception.
 */

import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { Search } from 'lucide-react';

import { cn } from '@/lib/utils';
import {
  FLAW_COMPARISON_META,
  FLAW_FAMILY_COLORS,
  flawConfidenceLevel,
  formatPValue,
} from '@/lib/flawComparisonMeta';
import type { ConfidenceLevel } from '@/lib/scoreConfidence';
import type { FlawBullet } from '@/types/library';

const HOVER_OPEN_DELAY_MS = 100;

const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
};

/** Signed 2-decimal string (e.g. +0.42, -1.00). */
function signed(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}`;
}

/** Per-100 rate, 2 decimals, unsigned. */
function rate(value: number): string {
  return value.toFixed(2);
}

// ─── Tooltip body ──────────────────────────────────────────────────────────────

function TooltipBody({ bullet }: { bullet: FlawBullet }) {
  const meta = FLAW_COMPARISON_META[bullet.tag];
  if (!meta) return null;

  const Icon = meta.icon;
  const color = FLAW_FAMILY_COLORS[meta.family].color;

  // Paragraph 1 — icon + colored label + definition.
  const definitionPara = (
    <p>
      <span className="inline-flex items-center gap-1 align-middle">
        <Icon className="h-3.5 w-3.5 shrink-0" style={{ color }} aria-hidden="true" />
        <strong style={{ color }}>{meta.label}</strong>
      </span>
      : {meta.definition}
    </p>
  );

  // Zero-event: nothing measured on either side under the current filter.
  if (
    bullet.delta === null ||
    bullet.player_rate === null ||
    bullet.opp_rate === null
  ) {
    return (
      <div className="text-left space-y-1">
        {definitionPara}
        <p className="opacity-70">No {meta.label.toLowerCase()} events in the current filter.</p>
      </div>
    );
  }

  // Paragraph 2 — you vs opponent per 100 moves.
  const magnitude = Math.abs(bullet.delta).toFixed(2);
  const ratesSuffix = ` (you: ${rate(bullet.player_rate)}, opponents: ${rate(bullet.opp_rate)})`;
  const valuePara =
    bullet.delta === 0 ? (
      <p>
        You have the same rate of {meta.noun} per 100 moves as your opponents{ratesSuffix}.
      </p>
    ) : (
      <p>
        You have <strong>{magnitude}</strong> {bullet.delta < 0 ? 'fewer' : 'more'} {meta.noun} per
        100 moves than your opponents{ratesSuffix}.
      </p>
    );

  // Paragraph 3 — verdict + confidence + p-value.
  const level = flawConfidenceLevel(bullet.p_value);
  const verdict = bullet.delta < 0 ? 'strength' : 'weakness';
  const headline =
    level === 'low' || bullet.delta === 0
      ? 'Inconclusive.'
      : `${level === 'high' ? 'Likely' : 'Possibly'} a real ${verdict}.`;
  const verdictPara = (
    <p>
      <strong>{headline}</strong> {CONFIDENCE_LABEL[level]} confidence
      {bullet.p_value !== null ? ` (${formatPValue(bullet.p_value)})` : ''}.
    </p>
  );

  // Paragraph 4 — methodology, one labeled line each (mirrors the endgame metric
  // tooltips: definition → Test → Confidence interval, on separate lines).
  const ciPara =
    bullet.ci_low !== null && bullet.ci_high !== null ? (
      <p className="opacity-70 italic">
        Metric: paired you-minus-opponent delta per 100 of your moves.
        <br />
        Test: Wald-z normal approximation.
        <br />
        Confidence interval: 95% [{signed(bullet.ci_low)}, {signed(bullet.ci_high)}].
      </p>
    ) : null;

  return (
    <div className="text-left space-y-1">
      {definitionPara}
      {valuePara}
      {verdictPara}
      {ciPara}
    </div>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

export interface FlawBulletPopoverProps {
  /** The bullet to describe — drives all four paragraphs. */
  bullet: FlawBullet;
  testId: string;
  ariaLabel: string;
  /** Extra classes for the trigger span. */
  triggerClassName?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function FlawBulletPopover({
  bullet,
  testId,
  ariaLabel,
  triggerClassName,
}: FlawBulletPopoverProps) {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = (): void => {
    hoverTimeout.current = setTimeout(() => setOpen(true), HOVER_OPEN_DELAY_MS);
  };

  const handleMouseLeave = (): void => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setOpen(false);
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          role="button"
          tabIndex={0}
          className={cn(
            'inline-flex items-center text-brand-brown-light/70 hover:text-brand-brown focus:outline-none cursor-pointer',
            triggerClassName,
          )}
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
          <TooltipBody bullet={bullet} />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
