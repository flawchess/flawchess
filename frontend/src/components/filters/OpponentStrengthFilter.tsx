import { useCallback } from 'react';
import { PresetRangeFilter } from './PresetRangeFilter';
import type { PresetOption } from './PresetRangeFilter';
import { trackFeature } from '@/lib/analytics';
import { useDebouncedTrackFeature } from '@/hooks/useDebouncedTrackFeature';
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
  const trackCommit = useDebouncedTrackFeature('filter-change');

  const handleSliderChange = useCallback(
    (values: number[]) => {
      const lo = values[0] ?? SLIDER_MIN;
      const hi = values[1] ?? SLIDER_MAX;
      onChange(sliderToRange(lo, hi));
    },
    [onChange],
  );

  // Tracked on commit (Radix onValueCommit), never per drag step (Phase 229
  // Pitfall 2), and debounced to one event per adjustment burst because Radix also
  // commits on every keyboard step. The raw Elo gap is never sent: only the
  // matching preset or 'custom'.
  const handleSliderCommit = useCallback(
    (values: number[]) => {
      const lo = values[0] ?? SLIDER_MIN;
      const hi = values[1] ?? SLIDER_MAX;
      trackCommit({
        target: 'opponent-strength',
        value: derivePreset(sliderToRange(lo, hi)) ?? 'custom',
      });
    },
    [trackCommit],
  );

  const handlePreset = useCallback(
    (preset: string) => {
      const next = preset as OpponentStrengthPreset;
      onChange(presetToRange(next));
      // Re-clicking the active preset changes nothing, so it is not a filter change.
      if (next !== activePreset) {
        trackFeature('filter-change', { target: 'opponent-strength', value: next });
      }
    },
    [onChange, activePreset],
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
        onValueCommit: handleSliderCommit,
        thumbLabels: ['Minimum opponent Elo gap', 'Maximum opponent Elo gap'],
      }}
    />
  );
}
