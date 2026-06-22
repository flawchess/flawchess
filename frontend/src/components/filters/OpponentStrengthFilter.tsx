import { useCallback } from 'react';
import { PresetRangeFilter } from './PresetRangeFilter';
import type { PresetOption } from './PresetRangeFilter';
import type { OpponentStrengthPreset, OpponentStrengthRange } from '@/types/api';
import {
  PRESET_LABELS,
  PRESET_ORDER,
  PRESET_THRESHOLD,
  SLIDER_MAX,
  SLIDER_MIN,
  SLIDER_STEP,
  STRONG_WEAK_THRESHOLD,
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

const PRESETS: PresetOption[] = PRESET_ORDER.map((preset) => ({
  key: preset,
  label: PRESET_LABELS[preset],
}));

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
    (preset: string) => {
      onChange(presetToRange(preset as OpponentStrengthPreset));
    },
    [onChange],
  );

  return (
    <PresetRangeFilter
      label="Opponent Strength"
      testIdPrefix="filter-opponent-strength"
      infoAriaLabel="Opponent strength filter info"
      infoChildren={
        <div className="space-y-2">
          <div className="space-y-1">
            <p>
              <strong>Any</strong>: no filter, all opponents.
            </p>
            <p>
              <strong>Stronger</strong>: opponents rated {STRONG_WEAK_THRESHOLD}+ Elo above you.
            </p>
            <p>
              <strong>Similar</strong>: opponents within ±{PRESET_THRESHOLD} Elo.
            </p>
            <p>
              <strong>Weaker</strong>: opponents rated {STRONG_WEAK_THRESHOLD}+ Elo below you.
            </p>
          </div>
          <p>
            Drag the slider for a custom range in {SLIDER_STEP}-Elo steps. The endpoints are
            unbounded: ≤−{Math.abs(SLIDER_MIN)} includes anyone weaker than that, ≥+{SLIDER_MAX}{' '}
            includes anyone stronger.
          </p>
        </div>
      }
      presets={PRESETS}
      gridClassName="grid-cols-4"
      activePreset={activePreset}
      onPreset={handlePreset}
      summary={formatRangeSummary(value)}
      isSummaryActive={Boolean(activePreset && activePreset !== 'any')}
      slider={{
        min: SLIDER_MIN,
        max: SLIDER_MAX,
        step: SLIDER_STEP,
        minStepsBetweenThumbs: 1,
        value: [sliderLo, sliderHi],
        onValueChange: handleSliderChange,
        thumbLabels: ['Minimum opponent Elo gap', 'Maximum opponent Elo gap'],
      }}
    />
  );
}
