import { DEFAULT_FILTERS, resetFilterState, type FilterState } from '@/components/filters/FilterPanel';
import { derivePreset } from '@/lib/opponentStrength';

/**
 * The filter state Endgame Insights can be generated for: every filter back
 * at its default except opponent strength, which may stay on one of the four
 * presets (the LLM cache key is the preset name). A custom slider range has no
 * preset, so it resets to the default too.
 *
 * Mirrors the router's `filters_not_supported` gate
 * (app/routers/insights.py). Generate applies this to the page filters before
 * firing, instead of disabling the button and asking the user to reset.
 */
export function toInsightsFilters(filters: FilterState): FilterState {
  const keepStrength = derivePreset(filters.opponentStrength) !== null;
  return {
    ...resetFilterState(filters),
    opponentStrength: keepStrength ? filters.opponentStrength : DEFAULT_FILTERS.opponentStrength,
  };
}
