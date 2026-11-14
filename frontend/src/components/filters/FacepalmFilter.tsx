/**
 * Two-handle RANGE filter over the Facepalm score (whole percents 0..100, step 5).
 * Presentation is delegated to the shared PresetRangeFilter; this wrapper owns only
 * the facepalm domain logic. Cloned from TacticDepthFilter.
 *
 * Any range other than All narrows to scored blunders, so a hint says mistakes are
 * excluded while narrowed (D-12).
 */

import { useCallback } from 'react';
import { PresetRangeFilter } from './PresetRangeFilter';
import type { PresetOption } from './PresetRangeFilter';
import { trackFeature } from '@/lib/analytics';
import { useDebouncedTrackFeature } from '@/hooks/useDebouncedTrackFeature';
import {
  FACEPALM_DEFAULT_PRESET,
  FACEPALM_PCT_MAX,
  FACEPALM_PCT_MIN,
  FACEPALM_STEP,
  PRESET_LABELS,
  PRESET_ORDER,
  derivePreset,
  formatFacepalmSummary,
  isFacepalmNarrowed,
  presetToRange,
  sliderToRange,
} from '@/lib/facepalm';
import type { FacepalmPreset, FacepalmValue } from '@/lib/facepalm';

/** One-line note shown under the slider while the range is not All (D-12). */
const FACEPALM_NARROWED_HINT = 'Mistakes are excluded';

interface FacepalmFilterProps {
  value: FacepalmValue;
  onChange: (next: FacepalmValue) => void;
}

const PRESETS: PresetOption[] = PRESET_ORDER.map((preset) => ({
  key: preset,
  label: PRESET_LABELS[preset],
}));

export function FacepalmFilter({ value, onChange }: FacepalmFilterProps) {
  const activePreset = derivePreset(value.min, value.max);
  const trackCommit = useDebouncedTrackFeature('filter-change');

  const handleSliderChange = useCallback(
    (values: number[]) => {
      const lo = values[0] ?? FACEPALM_PCT_MIN;
      const hi = values[1] ?? FACEPALM_PCT_MAX;
      onChange(sliderToRange(lo, hi));
    },
    [onChange],
  );

  // Tracked on commit (Radix onValueCommit), never per drag step, and debounced to
  // one event per adjustment burst because Radix also commits on every keyboard
  // step. Only the matching preset or 'custom' is sent, never the bounds.
  const handleSliderCommit = useCallback(
    (values: number[]) => {
      const lo = values[0] ?? FACEPALM_PCT_MIN;
      const hi = values[1] ?? FACEPALM_PCT_MAX;
      const range = sliderToRange(lo, hi);
      trackCommit({
        target: 'facepalm',
        value: derivePreset(range.min, range.max) ?? 'custom',
      });
    },
    [trackCommit],
  );

  const handlePreset = useCallback(
    (preset: string) => {
      const next = preset as FacepalmPreset;
      onChange(presetToRange(next));
      // Re-clicking the active preset changes nothing, so it is not a filter change.
      if (next !== activePreset) {
        trackFeature('filter-change', { target: 'facepalm', value: next });
      }
    },
    [onChange, activePreset],
  );

  // The summary goes active when the range leaves the default (All); a custom
  // range (activePreset null) counts as active.
  const isSummaryActive = activePreset !== FACEPALM_DEFAULT_PRESET;

  return (
    <PresetRangeFilter
      label="Facepalm Score"
      testIdPrefix="filter-facepalm"
      infoAriaLabel="Facepalm score filter info"
      infoChildren={
        <>
          <p>
            How easy it is to see for a player at your level that the move is a blunder, as
            estimated by our model. A high facepalm score means it should be easy to see, low
            means it's probably hard to see.
          </p>
          <p className="mt-2">
            Low keeps 0 to 29%, Mid 30 to 69%, High 70 to 100%. Drag either handle for a custom
            range. Any range other than All shows blunders only.
          </p>
        </>
      }
      presets={PRESETS}
      gridClassName="grid-cols-4"
      activePreset={activePreset}
      onPreset={handlePreset}
      summary={formatFacepalmSummary(value)}
      isSummaryActive={isSummaryActive}
      slider={{
        min: FACEPALM_PCT_MIN,
        max: FACEPALM_PCT_MAX,
        step: FACEPALM_STEP,
        minStepsBetweenThumbs: 0,
        value: [value.min, value.max],
        onValueChange: handleSliderChange,
        onValueCommit: handleSliderCommit,
        thumbLabels: ['Minimum facepalm score', 'Maximum facepalm score'],
      }}
      hint={isFacepalmNarrowed(value) ? FACEPALM_NARROWED_HINT : undefined}
    />
  );
}
