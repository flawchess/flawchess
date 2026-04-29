import { useCallback } from 'react';
import { Slider } from '@/components/ui/slider';
import { InfoPopover } from '@/components/ui/info-popover';
import { cn } from '@/lib/utils';
import type { OpponentStrengthPreset, OpponentStrengthRange } from '@/types/api';
import {
  PRESET_LABELS,
  PRESET_ORDER,
  SLIDER_MAX,
  SLIDER_MIN,
  SLIDER_STEP,
  derivePreset,
  formatRangeSummary,
  presetToRange,
  rangeToSlider,
  sliderToRange,
} from '@/lib/opponentStrength';

interface OpponentStrengthFilterProps {
  value: OpponentStrengthRange;
  onChange: (next: OpponentStrengthRange) => void;
}

export function OpponentStrengthFilter({ value, onChange }: OpponentStrengthFilterProps) {
  const activePreset = derivePreset(value);
  const [sliderLo, sliderHi] = rangeToSlider(value);

  const handleSliderChange = useCallback(
    (values: number[]) => {
      const lo = values[0] ?? SLIDER_MIN;
      const hi = values[1] ?? SLIDER_MAX;
      onChange(sliderToRange(lo, hi));
    },
    [onChange],
  );

  const handlePreset = useCallback(
    (preset: OpponentStrengthPreset) => {
      onChange(presetToRange(preset));
    },
    [onChange],
  );

  return (
    <div>
      <div className="mb-1 flex items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            Opponent Strength
            <InfoPopover
              ariaLabel="Opponent strength filter info"
              testId="filter-opponent-strength-info"
              side="bottom"
            >
              <div className="space-y-2">
                <div className="space-y-1">
                  <p>
                    <strong>Any</strong>: no filter, all opponents.
                  </p>
                  <p>
                    <strong>Stronger</strong>: opponents rated 50+ Elo above you.
                  </p>
                  <p>
                    <strong>Similar</strong>: opponents within ±50 Elo.
                  </p>
                  <p>
                    <strong>Weaker</strong>: opponents rated 50+ Elo below you.
                  </p>
                </div>
                <p>
                  Drag the slider for a custom range in 50-Elo steps. The
                  endpoints are unbounded: ≤−200 includes anyone weaker than
                  that, ≥+200 includes anyone stronger.
                </p>
              </div>
            </InfoPopover>
          </span>
        </p>
        <span
          className={cn(
            'text-xs tabular-nums',
            activePreset && activePreset !== 'any'
              ? 'font-medium text-toggle-active'
              : 'text-muted-foreground',
          )}
          data-testid="filter-opponent-strength-summary"
        >
          {formatRangeSummary(value)}
        </span>
      </div>

      {/* Preset chips */}
      <div className="mb-3 grid grid-cols-4 gap-1" data-testid="filter-opponent-strength-presets">
        {PRESET_ORDER.map((preset) => {
          const isActive = activePreset === preset;
          return (
            <button
              key={preset}
              type="button"
              onClick={() => handlePreset(preset)}
              data-testid={`filter-opponent-strength-preset-${preset}`}
              aria-pressed={isActive}
              className={cn(
                'rounded border h-11 sm:h-7 text-xs transition-colors',
                isActive
                  ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground'
                  : 'border-border bg-inactive-bg text-muted-foreground hover:bg-inactive-bg-hover hover:text-foreground',
              )}
            >
              {PRESET_LABELS[preset]}
            </button>
          );
        })}
      </div>

      {/* Range slider */}
      <div className="px-1.5">
        <Slider
          min={SLIDER_MIN}
          max={SLIDER_MAX}
          step={SLIDER_STEP}
          minStepsBetweenThumbs={1}
          value={[sliderLo, sliderHi]}
          onValueChange={handleSliderChange}
          thumbLabels={['Minimum opponent Elo gap', 'Maximum opponent Elo gap']}
          data-testid="filter-opponent-strength-slider"
        />
        <div className="mt-1 flex justify-between text-xs tabular-nums text-muted-foreground">
          <span>≤−{Math.abs(SLIDER_MIN)}</span>
          <span>0</span>
          <span>≥+{SLIDER_MAX}</span>
        </div>
      </div>
    </div>
  );
}
