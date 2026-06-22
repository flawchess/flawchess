/**
 * TacticDepthFilter — Quick 260620-l5k (Phase 130).
 *
 * Two-handle RANGE filter over tactic depth (0-based ply, domain 0..11). The
 * slider domain IS the API/DB domain — no full-move ↔ half-ply conversion.
 * min === max (e.g. 0..0) is selectable. Presentation is delegated to the
 * shared PresetRangeFilter; this wrapper owns only the depth domain logic.
 */

import { useCallback } from 'react';
import { PresetRangeFilter } from './PresetRangeFilter';
import type { PresetOption } from './PresetRangeFilter';
import {
  DEPTH_MIN,
  DEPTH_MAX,
  DEPTH_STEP,
  PRESET_LABELS,
  PRESET_ORDER,
  derivePreset,
  presetToRange,
  sliderToRange,
  formatDepthSummary,
} from '@/lib/tacticDepth';
import type { TacticDepthPreset, TacticDepthValue } from '@/lib/tacticDepth';

interface TacticDepthFilterProps {
  value: TacticDepthValue;
  onChange: (next: TacticDepthValue) => void;
}

const PRESETS: PresetOption[] = PRESET_ORDER.map((preset) => ({
  key: preset,
  label: PRESET_LABELS[preset],
}));

export function TacticDepthFilter({ value, onChange }: TacticDepthFilterProps) {
  const activePreset = derivePreset(value.min, value.max);

  const handleSliderChange = useCallback(
    (values: number[]) => {
      const lo = values[0] ?? DEPTH_MIN;
      const hi = values[1] ?? DEPTH_MAX;
      onChange(sliderToRange(lo, hi));
    },
    [onChange],
  );

  const handlePreset = useCallback(
    (preset: string) => {
      onChange(presetToRange(preset as TacticDepthPreset));
    },
    [onChange],
  );

  // The summary goes text-toggle-active when the active range is not the
  // always-on Medium default (preset null/custom or non-medium).
  const isSummaryActive = activePreset !== 'medium';

  return (
    <PresetRangeFilter
      label="Tactic Depth"
      testIdPrefix="filter-tactic-depth"
      infoAriaLabel="Tactic depth filter info"
      infoChildren={
        <p>
          Filters tactics by depth: how many plies into the winning line the decisive point
          appears (1 = immediate). Low keeps depth 1 to 2; Medium 1 to 6; High the
          full range. Drag either handle for a custom range. Forced mates obey the range too.
        </p>
      }
      presets={PRESETS}
      gridClassName="grid-cols-3"
      activePreset={activePreset}
      onPreset={handlePreset}
      summary={formatDepthSummary(value)}
      isSummaryActive={isSummaryActive}
      slider={{
        min: DEPTH_MIN,
        max: DEPTH_MAX,
        step: DEPTH_STEP,
        minStepsBetweenThumbs: 0,
        value: [value.min, value.max],
        onValueChange: handleSliderChange,
        thumbLabels: ['Minimum tactic depth', 'Maximum tactic depth'],
      }}
    />
  );
}
