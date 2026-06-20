/**
 * TacticDepthFilter — Phase 129 TACUI-06 (D-01/D-02/D-03).
 *
 * Single-handle depth filter control cloned from OpponentStrengthFilter.
 * The slider domain is FULL MOVES (1..DEPTH_SLIDER_MAX_MOVES).
 * The stored/API value (TacticDepthValue.maxMoves) is in HALF-PLIES.
 * sliderToMax / maxToSlider bridge the two via HALF_PLIES_PER_MOVE.
 */

import { useCallback } from 'react';
import { Slider } from '@/components/ui/slider';
import { InfoPopover } from '@/components/ui/info-popover';
import { cn } from '@/lib/utils';
import {
  DEPTH_SLIDER_MIN_MOVES,
  DEPTH_SLIDER_MAX_MOVES,
  DEPTH_SLIDER_STEP,
  DEPTH_PRESET_INTERMEDIATE_MAX,
  derivePreset,
  presetToMax,
  sliderToMax,
  maxToSlider,
  formatDepthSummary,
} from '@/lib/tacticDepth';
import type { TacticDepthPreset, TacticDepthValue } from '@/lib/tacticDepth';

// Preset chip labels (in display order).
const PRESET_ORDER: TacticDepthPreset[] = ['beginner', 'intermediate', 'advanced'];
const PRESET_LABELS: Record<TacticDepthPreset, string> = {
  beginner: 'Beginner',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
};

interface TacticDepthFilterProps {
  value: TacticDepthValue;
  onChange: (next: TacticDepthValue) => void;
}

export function TacticDepthFilter({ value, onChange }: TacticDepthFilterProps) {
  const activePreset = derivePreset(value.maxMoves);

  // Convert half-ply maxMoves → full-move slider position for rendering.
  const sliderPosition = maxToSlider(value.maxMoves);

  const handleSliderChange = useCallback(
    (values: number[]) => {
      // values[0] is a full-move slider position (D-03).
      const fullMoves = values[0] ?? DEPTH_SLIDER_MIN_MOVES;
      const max = sliderToMax(fullMoves);
      const detected = derivePreset(max);
      onChange({
        // Keep current preset label if no preset matches (custom).
        preset: detected ?? value.preset,
        maxMoves: max,
      });
    },
    [onChange, value.preset],
  );

  const handlePreset = useCallback(
    (preset: TacticDepthPreset) => {
      onChange({ preset, maxMoves: presetToMax(preset) });
    },
    [onChange],
  );

  // D-02: the summary text goes text-toggle-active when the active preset is not Intermediate.
  const isSummaryActive = activePreset !== 'intermediate';

  return (
    <div data-testid="filter-tactic-depth">
      <div className="mb-1 flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            Tactic Difficulty
            <InfoPopover
              ariaLabel="Tactic difficulty filter info"
              testId="filter-tactic-depth-info"
              side="bottom"
            >
              <p>
                Limits tactics by how many moves deep the winning sequence runs.
                Beginner shows simple 1-move threats; Intermediate adds 2 to 3-move
                combinations; Advanced includes deep sequences. Forced mates always
                show, regardless of difficulty.
              </p>
            </InfoPopover>
          </span>
        </p>
        <span
          className={cn(
            'text-sm tabular-nums',
            isSummaryActive ? 'font-medium text-toggle-active' : 'text-muted-foreground',
          )}
          data-testid="filter-tactic-depth-summary"
        >
          {formatDepthSummary(value)}
        </span>
      </div>

      {/* Preset chips — 3-column grid (Beginner / Intermediate / Advanced) */}
      <div className="mb-3 grid grid-cols-3 gap-1" data-testid="filter-tactic-depth-presets">
        {PRESET_ORDER.map((preset) => {
          const isActive = activePreset === preset;
          return (
            <button
              key={preset}
              type="button"
              onClick={() => handlePreset(preset)}
              data-testid={`filter-tactic-depth-preset-${preset}`}
              aria-pressed={isActive}
              className={cn(
                'rounded border h-11 sm:h-7 text-sm transition-colors',
                isActive
                  ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground'
                  : 'border-border bg-inactive-bg text-muted-foreground pointer-fine:hover:bg-inactive-bg-hover pointer-fine:hover:text-foreground',
              )}
            >
              {PRESET_LABELS[preset]}
            </button>
          );
        })}
      </div>

      {/* Single-handle slider — domain is FULL MOVES (D-03); the stored value is half-plies */}
      <div className="px-1.5">
        <Slider
          min={DEPTH_SLIDER_MIN_MOVES}
          max={DEPTH_SLIDER_MAX_MOVES}
          step={DEPTH_SLIDER_STEP}
          value={[sliderPosition]}
          onValueChange={handleSliderChange}
          thumbLabels={['Maximum tactic depth in moves']}
          data-testid="filter-tactic-depth-slider"
        />
        {/* Tick labels in FULL MOVES (D-03 — WARNING-2 fix) */}
        <div className="mt-1 flex justify-between text-sm tabular-nums text-muted-foreground">
          <span>{DEPTH_SLIDER_MIN_MOVES}</span>
          <span>{DEPTH_SLIDER_MAX_MOVES}</span>
        </div>
      </div>
    </div>
  );
}

// Default export for convenience (callers who omit value get the default intermediate preset).
export const DEFAULT_TACTIC_DEPTH_VALUE: TacticDepthValue = {
  preset: 'intermediate',
  maxMoves: DEPTH_PRESET_INTERMEDIATE_MAX,
};
