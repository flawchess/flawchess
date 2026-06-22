/**
 * PresetRangeFilter — shared two-handle range filter (Quick 260620-l5k, Phase 130).
 *
 * Extracted from the near-identical TacticDepthFilter / OpponentStrengthFilter
 * clones. Renders a label row with an InfoPopover + active-summary, a preset
 * chip grid, and a dual-thumb Slider. The caller owns all domain logic (preset
 * detection, slider ↔ value mapping, summary text) and passes the results in as
 * plain props, so this component stays purely presentational.
 */

import type { ReactNode } from 'react';
import { Slider } from '@/components/ui/slider';
import { InfoPopover } from '@/components/ui/info-popover';
import { cn } from '@/lib/utils';

export interface PresetOption {
  /** Stable preset key (used for callbacks + data-testid). */
  key: string;
  /** Chip text — may include a range suffix and may wrap to two lines. */
  label: string;
}

interface PresetRangeFilterProps {
  /** Visible filter title (e.g. "Tactic Difficulty"). */
  label: string;
  /** data-testid prefix; derives root/info/summary/presets/preset/slider ids. */
  testIdPrefix: string;
  /** aria-label for the InfoPopover trigger. */
  infoAriaLabel: string;
  /** InfoPopover body. */
  infoChildren: ReactNode;
  /** Preset chips, rendered in source order. */
  presets: readonly PresetOption[];
  /** Tailwind grid-cols class for the chip grid (e.g. "grid-cols-3"). */
  gridClassName: string;
  /** Key of the currently-active preset, or null for a custom range. */
  activePreset: string | null;
  onPreset: (key: string) => void;
  /** Top-right summary text. */
  summary: string;
  /** Whether the summary should render in the active (highlighted) style. */
  isSummaryActive: boolean;
  /** Slider configuration + handlers. */
  slider: {
    min: number;
    max: number;
    step: number;
    minStepsBetweenThumbs: number;
    value: [number, number];
    onValueChange: (values: number[]) => void;
    thumbLabels: [string, string];
  };
}

export function PresetRangeFilter({
  label,
  testIdPrefix,
  infoAriaLabel,
  infoChildren,
  presets,
  gridClassName,
  activePreset,
  onPreset,
  summary,
  isSummaryActive,
  slider,
}: PresetRangeFilterProps) {
  return (
    <div data-testid={testIdPrefix}>
      <div className="mb-1 flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            {label}
            <InfoPopover ariaLabel={infoAriaLabel} testId={`${testIdPrefix}-info`} side="bottom">
              {infoChildren}
            </InfoPopover>
          </span>
        </p>
        <span
          className={cn(
            'text-sm tabular-nums',
            isSummaryActive ? 'font-medium text-toggle-active' : 'text-muted-foreground',
          )}
          data-testid={`${testIdPrefix}-summary`}
        >
          {summary}
        </span>
      </div>

      {/* Preset chips */}
      <div className={cn('mb-1 grid gap-1', gridClassName)} data-testid={`${testIdPrefix}-presets`}>
        {presets.map((preset) => {
          const isActive = activePreset === preset.key;
          return (
            <button
              key={preset.key}
              type="button"
              onClick={() => onPreset(preset.key)}
              data-testid={`${testIdPrefix}-preset-${preset.key}`}
              aria-pressed={isActive}
              className={cn(
                'rounded border h-11 sm:h-7 text-sm transition-colors',
                isActive
                  ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground'
                  : 'border-border bg-inactive-bg text-muted-foreground pointer-fine:hover:bg-inactive-bg-hover pointer-fine:hover:text-foreground',
              )}
            >
              {preset.label}
            </button>
          );
        })}
      </div>

      {/* Range slider */}
      <div className="px-1.5">
        <Slider
          min={slider.min}
          max={slider.max}
          step={slider.step}
          minStepsBetweenThumbs={slider.minStepsBetweenThumbs}
          value={slider.value}
          onValueChange={slider.onValueChange}
          thumbLabels={slider.thumbLabels}
          data-testid={`${testIdPrefix}-slider`}
        />
      </div>
    </div>
  );
}
